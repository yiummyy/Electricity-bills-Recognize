import pytest
import time
import threading
from app.core.scheduler import BackendTaskScheduler, DynamicTaskScheduler

def test_singleton_behavior():
    s1 = DynamicTaskScheduler.get_instance()
    s2 = DynamicTaskScheduler.get_instance()
    assert s1 is s2

def test_serial_execution():
    scheduler = DynamicTaskScheduler.get_instance()
    scheduler.set_max_parallel(1)
    
    results = []
    
    def task(n):
        time.sleep(0.1)
        results.append(n)
        return n
        
    start = time.time()
    
    t1 = threading.Thread(target=scheduler.submit, args=(lambda: task(1),))
    t2 = threading.Thread(target=scheduler.submit, args=(lambda: task(2),))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    duration = time.time() - start
    # Should take at least 0.2s
    assert duration >= 0.2
    assert len(results) == 2

def test_parallel_execution():
    scheduler = DynamicTaskScheduler.get_instance()
    scheduler.set_max_parallel(2)
    
    def task():
        time.sleep(0.1)
        
    start = time.time()
    
    threads = []
    for _ in range(2):
        t = threading.Thread(target=scheduler.submit, args=(lambda: task(),))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    duration = time.time() - start
    # Should take around 0.1s (parallel) not 0.2s
    assert duration < 0.18

def test_dynamic_adjustment():
    scheduler = DynamicTaskScheduler.get_instance()
    scheduler.set_max_parallel(1)
    
    active_tasks = 0
    max_concurrent_observed = 0
    lock = threading.Lock()
    
    def task():
        nonlocal active_tasks, max_concurrent_observed
        with lock:
            active_tasks += 1
            max_concurrent_observed = max(max_concurrent_observed, active_tasks)
        time.sleep(0.2)
        with lock:
            active_tasks -= 1
            
    # Start 3 tasks
    threads = []
    for _ in range(3):
        t = threading.Thread(target=scheduler.submit, args=(lambda: task(),))
        threads.append(t)
        t.start()
        
    time.sleep(0.05)
    # Should be 1 running
    assert scheduler.current_running <= 1
    
    # Increase to 3
    scheduler.set_max_parallel(3)
    
    for t in threads:
        t.join()
        
    # Should have seen concurrency > 1
    assert max_concurrent_observed > 1
