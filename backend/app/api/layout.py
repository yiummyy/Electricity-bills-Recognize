import os
import time
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.concurrency import run_in_threadpool
from app.services.ocr_service import ocr_service
from app.models.layout import LayoutResult
from app.models.extraction import ExtractionResult
from app.core.config import settings
from app.services.electricity_extractor import ElectricityExtractor
from app.core.database import db
from app.core.security import get_current_user
from bson import ObjectId

router = APIRouter()
logger = logging.getLogger(__name__)

# Reusing extractor instance
extractor = ElectricityExtractor()

@router.post("/analyze", response_model=LayoutResult)
async def analyze_layout(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload file for layout analysis and visualization.
    Returns layout regions and image for review.
    """
    try:
        content = await file.read()
        filename = file.filename
        
        # Save to temp directory
        temp_dir = os.path.join(settings.BASE_DIR, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        timestamp = int(time.time())
        saved_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(temp_dir, saved_filename)
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        logger.info(f"File saved for analysis: {file_path}")
        
        # Analyze layout (CPU intensive -> threadpool)
        result = await run_in_threadpool(ocr_service.analyze_layout, content, filename)
        
        # Add file token (path relative to temp or just filename)
        result.file_token = saved_filename
        
        return result
        
    except Exception as e:
        logger.error(f"Layout analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract", response_model=ExtractionResult)
async def extract_from_token(
    file_token: str = Form(..., description="The token returned by /analyze endpoint"),
    confirmed_layout: str = Form(None, description="Optional JSON string of modified layout (not used yet)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Perform extraction on a previously uploaded file (identified by file_token).
    """
    try:
        temp_dir = os.path.join(settings.BASE_DIR, "temp_uploads")
        file_path = os.path.join(temp_dir, file_token)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File token expired or invalid")
            
        with open(file_path, "rb") as f:
            content = f.read()
            
        # Extract using existing logic
        # Ideally, we should use the `confirmed_layout` here to guide extraction, 
        # but for now we just reuse the existing pipeline as per spec (visualization first).
        
        filename = file_token.split('_', 1)[1] if '_' in file_token else file_token
        result = await extractor.extract_from_file(content, filename)
        
        # Attach username for isolation
        result.username = current_user["username"]
        
        # Save to DB (reusing logic from endpoints.py)
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
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
