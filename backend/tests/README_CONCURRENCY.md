# Backend Concurrency Tests

## Usage

Run tests using pytest:

```bash
cd backend
pytest tests/test_concurrency.py
```

## Test Cases

1. **Default Serial Execution**: Verifies that tasks run sequentially when max_parallel=1.
2. **Parallel Execution**: Verifies that tasks run in parallel when max_parallel > 1.
3. **Dynamic Adjustment**: Verifies that increasing capacity allows waiting tasks to proceed.
