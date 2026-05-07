from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
import logging
import time
import os
import json
from bson import ObjectId
from pydantic import BaseModel
from app.models.bill import BillData, OCRResult
from app.models.rag import RAGRequest, RAGResponse, DocumentChunk
from app.models.extraction import ExtractionResult, PowerFactorDetail, FundPriceDetail
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service, RecursiveCharacterTextSplitter
from app.services.llm_service import llm_service
from app.services.electricity_extractor import ElectricityExtractor
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password, get_current_user, require_admin
from app.core.database import db
from app.core.scheduler import scheduler
from app.models.user import UserCreate, UserResponse, TokenResponse
import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Text splitter for RAG
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# Initialize extractor with shared services
extractor = ElectricityExtractor()

import threading

_users_lock = threading.Lock()
_users_file = os.path.join(settings.BASE_DIR, "data", "users.json")


def _load_users() -> dict:
    """Load users dict from JSON file."""
    if os.path.exists(_users_file):
        try:
            with open(_users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_users(users: dict):
    """Save users dict to JSON file."""
    os.makedirs(os.path.dirname(_users_file), exist_ok=True)
    with open(_users_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _get_users_collection():
    """Safely get users collection. Returns Mongo collection if available, None otherwise."""
    try:
        if db.db is None:
            return None
        return db.get_collection("users")
    except Exception:
        return None


def _verify_db_user(collection, username: str, password: str):
    """Verify username/password against DB. Returns (success, role) tuple."""
    try:
        user = collection.find_one({"username": username})
        if user and verify_password(password, user["hashed_password"]):
            return True, user["role"]
    except Exception:
        pass
    return False, None


def _verify_file_user(username: str, password: str):
    """Verify against JSON file store. Returns (success, role) tuple."""
    users = _load_users()
    if username in users:
        if verify_password(password, users[username]["hashed_password"]):
            return True, users[username]["role"]
    return False, None


def _create_file_user(username: str, hashed_password: str, role: str):
    """Create a user in the JSON file store."""
    with _users_lock:
        users = _load_users()
        if username in users:
            return False  # already exists
        users[username] = {
            "hashed_password": hashed_password,
            "role": role,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        _save_users(users)
    return True


@router.post("/register", response_model=TokenResponse)
def register(user_data: UserCreate):
    """Register a new user. First registered user becomes admin, subsequent ones are regular users.
    Stores in JSON file; also in MongoDB if available."""
    # Determine role: first user is admin
    users = _load_users()
    collection = _get_users_collection()
    total_users = len(users)
    if collection is not None:
        try:
            total_users = max(total_users, collection.count_documents({}))
        except Exception:
            pass
    role = "admin" if total_users == 0 else "user"

    # Check duplicate
    if user_data.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    if collection is not None:
        try:
            if collection.find_one({"username": user_data.username}):
                raise HTTPException(status_code=400, detail="Username already exists")
        except Exception:
            pass

    # Hash password once (PBKDF2 is expensive)
    hashed_pw = get_password_hash(user_data.password)

    # Save to file store
    ok = _create_file_user(user_data.username, hashed_pw, role)
    if not ok:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Also save to MongoDB if available
    if collection is not None:
        try:
            collection.insert_one({
                "username": user_data.username,
                "hashed_password": hashed_pw,
                "role": role,
                "created_at": datetime.datetime.now(datetime.timezone.utc)
            })
        except Exception:
            pass  # File store is primary; MongoDB is optional

    token = create_access_token(user_data.username, role)
    return TokenResponse(access_token=token, username=user_data.username, role=role)


@router.post("/login/access-token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username/password. Returns JWT token with role.
    Checks: JSON file store → MongoDB → default admin fallback."""
    admin_user = settings.ADMIN_USERNAME
    admin_pass = settings.ADMIN_PASSWORD

    # 1. Try file store
    ok, role = _verify_file_user(form_data.username, form_data.password)
    if ok:
        token = create_access_token(form_data.username, role)
        return TokenResponse(access_token=token, username=form_data.username, role=role)

    # 2. Try MongoDB
    collection = _get_users_collection()
    if collection is not None:
        ok, role = _verify_db_user(collection, form_data.username, form_data.password)
        if ok:
            token = create_access_token(form_data.username, role)
            return TokenResponse(access_token=token, username=form_data.username, role=role)

    # 3. Default admin fallback
    if form_data.username == admin_user and form_data.password == admin_pass:
        token = create_access_token("admin", "admin")
        return TokenResponse(access_token=token, username="admin", role="admin")

    raise HTTPException(status_code=400, detail="Incorrect username or password")


@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user info."""
    return UserResponse(username=current_user["username"], role=current_user["role"],
                        created_at=datetime.datetime.now(datetime.timezone.utc))

@router.post("/extract", response_model=ExtractionResult)
async def extract_bill(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Extract structured electricity bill data.
    """
    try:
        content = await file.read()
        filename = file.filename
        
        # Save to temporary directory
        import os
        temp_dir = os.path.join(settings.BASE_DIR, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{int(time.time())}_{filename}")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File saved to temporary directory: {file_path}")
        
        # 1. Extract
        result = await extractor.extract_from_file(content, filename)
        
        # 2. Attach username for isolation
        result.username = current_user["username"]
        
        # 3. Save to MongoDB
        try:
            database = db.get_db()
            if database is not None:
                collection = database.get_collection("electricity_bills")
                doc = result.model_dump(by_alias=True, exclude={"id"})
                insert_result = collection.insert_one(doc)
                result.id = str(insert_result.inserted_id)
                logger.info(f"Bill saved to MongoDB with id: {result.id} by user: {current_user['username']}")
            else:
                logger.warning("MongoDB is not connected. Result will not be persisted.")
        except Exception as e:
            logger.error(f"Database error: {e}. Result returned without DB persistence.")

        return result
        
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bills")
def list_user_bills(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """
    List current user's bills, ordered by creation time descending.
    """
    try:
        database = db.get_db()
        if database is None:
            return {"bills": [], "total": 0}
        collection = database.get_collection("electricity_bills")
        username = current_user["username"]

        cursor = collection.find({"username": username}).sort("created_at", -1).skip(skip).limit(limit)
        total = collection.count_documents({"username": username})

        bills = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            bills.append(doc)

        return {"bills": bills, "total": total}
    except Exception as e:
        logger.error(f"Failed to list bills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "embedding_service": embedding_service.get_status(),
        "ocr_service": "active",
        "concurrency": scheduler.get_status()
    }

@router.post("/concurrency")
def set_concurrency(max_parallel: int = Form(...), admin: dict = Depends(require_admin)):
    """
    Adjust the maximum concurrency for heavy tasks (OCR/LLM).
    Range: 1-3
    """
    try:
        scheduler.set_max_parallel(max_parallel)
        return {"status": "success", "config": scheduler.get_status()}
    except Exception as e:
        logger.error(f"Failed to set concurrency: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/system")
def get_system_config():
    """
    Get current system configuration and status.
    """
    return {
        "llm": llm_service.get_config(),
        "embedding": embedding_service.get_status(),
        "file_processing": {
            "pdf_engine": "PyMuPDF (fitz)",
            "ocr_engine": "PaddleOCR (PP-OCRv4)",
            "strategy": "Hybrid (Text Extraction -> Image Fallback)"
        }
    }

@router.get("/config/token-usage")
def get_token_usage(hours: int = 24):
    """
    Get token consumption data for the last N hours (default 24).
    Returns hourly buckets with prompt_tokens, completion_tokens, total_tokens, llm_calls.
    """
    try:
        token_file = os.path.join(settings.BASE_DIR, "data", "token_usage.json")
        if not os.path.exists(token_file):
            return {"buckets": [], "total_prompt_tokens": 0, "total_completion_tokens": 0, "total_llm_calls": 0}

        with open(token_file, "r", encoding="utf-8") as f:
            all_data = json.load(f)

        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(hours=hours)

        buckets = []
        total_prompt = 0
        total_completion = 0
        total_calls = 0

        for hour_key, entry in sorted(all_data.items()):
            try:
                t = datetime.datetime.fromisoformat(hour_key.replace("Z", "+00:00"))
                if t >= cutoff:
                    buckets.append({
                        "hour": hour_key,
                        "prompt_tokens": entry["prompt_tokens"],
                        "completion_tokens": entry["completion_tokens"],
                        "total_tokens": entry["total_tokens"],
                        "llm_calls": entry["llm_calls"],
                    })
                    total_prompt += entry["prompt_tokens"]
                    total_completion += entry["completion_tokens"]
                    total_calls += entry["llm_calls"]
            except Exception:
                continue

        return {
            "buckets": buckets,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "total_llm_calls": total_calls,
        }
    except Exception as e:
        logger.error(f"Failed to read token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config/llm")
def update_llm_config(
    provider: str = Form(...),
    model: str = Form(...),
    api_key: Optional[str] = Form(None),
    api_base: Optional[str] = Form(None),
    admin: dict = Depends(require_admin),
):
    """
    Update LLM configuration and persist to .env file.
    """
    try:
        # 1. Update runtime service
        llm_service.update_config(provider, model, api_key, api_base)
        
        # 2. Persist to .env (same file that config.py loads from)
        env_path = os.path.join(settings.BASE_DIR, ".env")
        
        # Read existing
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Update or Append
        new_lines = []
        updated_keys = set()
        
        # Prepare updates
        updates = {
            "LLM_PROVIDER": provider,
            "LLM_MODEL_NAME": model
        }
        if api_key:
            updates["LLM_API_KEY"] = api_key
        if api_base:
            updates["LLM_API_BASE"] = api_base
            
        for line in env_lines:
            key = line.split('=')[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        
        # Add missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                if new_lines and not new_lines[-1].endswith('\n'):
                    new_lines.append('\n')
                new_lines.append(f"{key}={value}\n")
        
        # Write back
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        logger.info(f"Updated .env config at {env_path}")
        
        return {"status": "success", "config": llm_service.get_config()}
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config/embedding")
def update_embedding_config(
    model_type: str = Form(..., description="embedding or rerank"),
    model_path: str = Form(...),
    admin: dict = Depends(require_admin),
):
    """
    Switch embedding or rerank model.
    """
    try:
        if model_type == "embedding":
            embedding_service.switch_model(model_path)
            return {"status": "success", "config": embedding_service.get_status()}
        else:
             # Placeholder for rerank switch if needed
             return {"status": "ignored", "message": "Rerank switch not implemented yet"}
    except Exception as e:
        logger.error(f"Switch model failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/models")
def list_local_models():
    """
    List available local models.
    """
    import os
    base_path = "./models/embedding"
    models = []
    if os.path.exists(base_path):
        for name in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, name)):
                models.append(name)
    return {"local_models": models}

class BillUpdateRequest(BaseModel):
    month: str
    power_factor: Optional[PowerFactorDetail] = None
    fund_price: Optional[FundPriceDetail] = None

@router.put("/bills/{id}/months/{month}")
async def update_bill_month(
    id: str,
    month: str,
    update_data: BillUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update a specific month's data (Power Factor, Fund Price) in an electricity bill document.
    """
    try:
        if not ObjectId.is_valid(id):
             raise HTTPException(status_code=400, detail="Invalid ID format")

        database = db.get_db()
        collection = database.get_collection("electricity_bills")
        
        # 1. Find the document
        doc = collection.find_one({"_id": ObjectId(id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        # 2. Check ownership
        if doc.get("username") != current_user["username"]:
            raise HTTPException(status_code=403, detail="Access denied: not your bill")
            
        # 3. Find the month in monthly_bills
        monthly_bills = doc.get("monthly_bills", [])
        updated = False
        
        # Normalize month input if needed, but assuming exact match for now
        target_month = month
        
        for bill in monthly_bills:
            if bill.get("month") == target_month:
                # Update Power Factor
                if update_data.power_factor:
                    # Validate month consistency
                    if update_data.power_factor.month and update_data.power_factor.month != target_month:
                         # Force it to match
                         update_data.power_factor.month = target_month
                    
                    bill["power_factor"] = update_data.power_factor.model_dump()
                    
                # Update Fund Price
                if update_data.fund_price:
                    if update_data.fund_price.month and update_data.fund_price.month != target_month:
                         update_data.fund_price.month = target_month

                    bill["fund_price"] = update_data.fund_price.model_dump()
                
                updated = True
                break
        
        if not updated:
             raise HTTPException(status_code=404, detail=f"Month {target_month} not found in this bill")
             
        # 3. Save back
        result = collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"monthly_bills": monthly_bills}}
        )
        
        if result.modified_count == 0:
             logger.warning(f"No changes made to bill {id}")
        
        logger.info(f"Updated bill {id} month {month}")
        return {"status": "success", "message": "Bill updated successfully"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))