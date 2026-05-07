import os
import time
import threading
import logging

logger = logging.getLogger(__name__)

_cleanup_thread_started = False


def _cleanup_temp_files(base_dir: str, subdirs: list[str], max_age_seconds: int):
    now = time.time()
    for sub in subdirs:
        target = os.path.join(base_dir, sub)
        if not os.path.isdir(target):
            continue
        try:
            for fname in os.listdir(target):
                fpath = os.path.join(target, fname)
                try:
                    if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                        os.remove(fpath)
                        logger.info(f"Cleaned up old file: {fpath}")
                except OSError:
                    pass
        except OSError:
            pass


def _cleanup_loop(base_dir: str, interval_seconds: int = 3600, max_age_days: int = 7):
    max_age_seconds = max_age_days * 86400
    subdirs = ["temp_uploads", "logs/ocr_results", "logs/llm_responses", "logs/final_results"]
    while True:
        time.sleep(interval_seconds)
        try:
            _cleanup_temp_files(base_dir, subdirs, max_age_seconds)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


def start_cleanup(base_dir: str):
    global _cleanup_thread_started
    if _cleanup_thread_started:
        return
    _cleanup_thread_started = True
    t = threading.Thread(target=_cleanup_loop, args=(base_dir,), daemon=True)
    t.start()
    logger.info("File cleanup thread started (runs hourly, keeps 7 days)")
