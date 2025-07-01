# Test

```bash
uv sync --dev

# Run all tests
python -m pytest test/

# Run with verbose output
python -m pytest test/ -v

# Run specific test file
python -m pytest test/test_shared_camera_server.py

# Run specific test class
python -m pytest test/test_shared_camera_server.py::TestCameraManagement

# Run specific test
python -m pytest test/test_shared_camera_server.py::TestCameraManagement::test_append_camera

# HTML coverage report
python -m pytest test/ --cov=src/malphite --cov-report=html

# Terminal coverage report
python -m pytest test/ --cov=src/malphite --cov-report=term-missing
```
