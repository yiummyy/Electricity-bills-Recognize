import uvicorn
import sys
import os
import logging

# Suppress PaddleOCR logs (must be before importing paddle/ppocr)
os.environ["GLOG_minloglevel"] = "2"

# Add current directory to sys.path
sys.path.append(os.getcwd())

# Bridge standard logging to loguru
from loguru import logger as loguru_logger

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

print("="*50, flush=True)
print("Importing app...", flush=True)

try:
    # Try to suppress third-party logs
    logging.getLogger("ppocr").setLevel(logging.WARNING)
    logging.getLogger("paddle").setLevel(logging.WARNING)

    from app.main import app
    print(f"App imported successfully. Type: {type(app)}", flush=True)
    
    # Check settings
    from app.core.config import settings
    print(f"MongoDB URI: {settings.MONGODB_URI}", flush=True)
    print(f"LLM Provider: {settings.LLM_PROVIDER}", flush=True)
    print(f"Embedding Model Path: {settings.EMBEDDING_MODEL_PATH}", flush=True)
    
except Exception as e:
    print(f"Failed to import app: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    print("Starting Uvicorn Server on port 8003...", flush=True)
    print("="*50, flush=True)
    try:
        uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
    except Exception as e:
        print(f"Uvicorn failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
    print("Server exited.", flush=True)
