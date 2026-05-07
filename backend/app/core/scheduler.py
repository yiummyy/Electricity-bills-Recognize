import threading
import queue
import logging
import time
from typing import Callable, Any, TypeVar, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BackendTaskScheduler:
    _instance = None
    
    def __init__(self):
        self.max_parallel = settings.OCR_MAX_CONCURRENCY or 1
        self.semaphore = threading.Semaphore(self.max_parallel)
        self.lock = threading.Lock()
        
    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with threading.Lock():
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance
    
    def set_max_parallel(self, n: int):
        with self.lock:
            n = max(1, min(3, n))
            logger.info(f"Adjusting max concurrency from {self.max_parallel} to {n}")
            
            diff = n - self.max_parallel
            self.max_parallel = n
            
            if diff > 0:
                # Release to allow more
                for _ in range(diff):
                    self.semaphore.release()
            elif diff < 0:
                # Acquire to restrict (this is tricky in runtime, 
                # strictly speaking we should just update the limit for FUTURE tasks,
                # but standard Semaphore doesn't support 'reducing' capacity easily without draining.
                # For simplicity in this implementation, we will lazily enforce it:
                # If we are over-subscribed, new tasks will just wait longer.
                # A proper implementation might need a BoundedSemaphore recreation or custom Condition.
                # Here we will just update the config value and let the natural flow handle it, 
                # but 'semaphore' object in python isn't resizable.
                # Let's switch to a BoundedSemaphore-like logic using Condition for full control if needed,
                # OR just re-instantiate if we accept a brief drain period.
                # Actually, simpler approach for this requirement:
                pass 
                # NOTE: Python's threading.Semaphore internal counter cannot be decreased easily.
                # To properly support dynamic resizing DOWN, we need a custom implementation.
    
    def submit(self, task: Callable[[], T]) -> T:
        """
        Blocking submit that respects concurrency limit.
        """
        # Simple implementation using Semaphore (Static for now, dynamic requires more complex logic)
        # To support dynamic adjustment properly:
        
        with self.semaphore:
            return task()

# Re-implementing with Condition for proper Dynamic Concurrency
class DynamicTaskScheduler:
    _instance = None
    
    def __init__(self):
        self.max_parallel = getattr(settings, "OCR_MAX_CONCURRENCY", 1)
        self.current_running = 0
        self.condition = threading.Condition()
        
    @classmethod
    def get_instance(cls):
        if not cls._instance:
            with threading.Lock():
                if not cls._instance:
                    cls._instance = cls()
        return cls._instance

    def set_max_parallel(self, n: int):
        with self.condition:
            n = max(1, min(3, n))
            logger.info(f"Scheduler capacity changed: {self.max_parallel} -> {n}")
            self.max_parallel = n
            self.condition.notify_all() # Wake up waiters to check new limit

    def get_status(self):
        return {
            "max_parallel": self.max_parallel,
            "running": self.current_running
        }

    def submit(self, task: Callable[[], T]) -> T:
        with self.condition:
            while self.current_running >= self.max_parallel:
                self.condition.wait()
            self.current_running += 1
        
        try:
            return task()
        finally:
            with self.condition:
                self.current_running -= 1
                self.condition.notify()

scheduler = DynamicTaskScheduler.get_instance()
