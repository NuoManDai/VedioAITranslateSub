"""
Test batch API routes
"""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from io import BytesIO

# Import main app
import sys

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database.batch_db import BatchDB


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_db_path(tmp_path):
    """Create temporary database file"""
    db_path = tmp_path / "test_batch.db"
    return str(db_path)


@pytest.fixture(autouse=True)
def setup_test_env(test_db_path, monkeypatch):
    """Setup test environment before each test"""
    # Patch the batch_service instance in the routes module to use test db
    from api.routes import batch as batch_module
    from services.batch_service import BatchService

    # Create test service instance
    test_service = BatchService(db_path=test_db_path)

    # Replace the module-level batch_service instance
    monkeypatch.setattr(batch_module, "batch_service", test_service)

    yield

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


# ------------
# Test POST /api/batch/ - Create batch
# ------------


def test_create_batch_success(client):
    """Test creating a new batch"""
    response = client.post("/api/batch/")
    assert response.status_code == 200

    data = response.json()
    assert "jobId" in data
    assert isinstance(data["jobId"], str)


def test_create_multiple_batches(client):
    """Test creating multiple batches"""
    response1 = client.post("/api/batch/")
    response2 = client.post("/api/batch/")

    assert response1.status_code == 200
    assert response2.status_code == 200

    job_id1 = response1.json()["jobId"]
    job_id2 = response2.json()["jobId"]

    assert job_id1 != job_id2


# ------------
# Test POST /api/batch/{job_id}/files - Register file
# ------------


def test_register_file_success(client):
    """Test registering a file to a batch"""
    # Create batch first
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    # Register file
    response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test_video.mp4"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_video.mp4"
    assert data["status"] == "pending"


def test_register_file_with_settings(client):
    """Test registering a file with custom settings"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    response = client.post(
        f"/api/batch/{job_id}/files",
        json={
            "filename": "test_video.mp4",
            "sourceLang": "en",
            "targetLang": "zh-CN",
            "dubbing": True,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["sourceLang"] == "en"
    assert data["targetLang"] == "zh-CN"
    assert data["dubbing"] is True


def test_register_file_invalid_job_id(client):
    """Test registering a file to non-existent batch"""
    response = client.post(
        "/api/batch/invalid-job-id/files", json={"filename": "test.mp4"}
    )
    assert response.status_code == 404


# ------------
# Test PUT /api/batch/{job_id}/files/{file_id}/upload - Upload file
# ------------


def test_upload_file_success(client, tmp_path):
    """Test uploading file content"""
    # Create batch and register file
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    register_response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test_video.mp4"}
    )
    file_id = register_response.json()["id"]

    # Create test video file
    video_content = b"fake video content for testing"
    files = {"file": ("test_video.mp4", BytesIO(video_content), "video/mp4")}

    # Upload file
    response = client.put(f"/api/batch/{job_id}/files/{file_id}/upload", files=files)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "queued"
    assert "filepath" in data


def test_upload_file_invalid_format(client):
    """Test uploading unsupported file format"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    register_response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test.txt"}
    )
    file_id = register_response.json()["id"]

    files = {"file": ("test.txt", BytesIO(b"text content"), "text/plain")}

    response = client.put(f"/api/batch/{job_id}/files/{file_id}/upload", files=files)
    assert response.status_code == 400
    assert "不支持的文件格式" in response.json()["detail"]


def test_upload_file_not_found(client):
    """Test uploading to non-existent file"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    files = {"file": ("test.mp4", BytesIO(b"content"), "video/mp4")}
    response = client.put(
        f"/api/batch/{job_id}/files/invalid-file-id/upload", files=files
    )
    assert response.status_code == 404


# ------------
# Test GET /api/batch/ - List all batches
# ------------


def test_list_batches_empty(client):
    """Test listing batches when none exist"""
    response = client.get("/api/batch/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_batches_with_data(client):
    """Test listing batches with data"""
    # Create 2 batches
    client.post("/api/batch/")
    client.post("/api/batch/")

    response = client.get("/api/batch/")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert all("id" in batch for batch in data)
    assert all("status" in batch for batch in data)


# ------------
# Test GET /api/batch/{job_id}/status - Get batch status
# ------------


def test_get_batch_status_success(client):
    """Test getting batch status with files"""
    # Create batch
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    # Add files
    client.post(f"/api/batch/{job_id}/files", json={"filename": "video1.mp4"})
    client.post(f"/api/batch/{job_id}/files", json={"filename": "video2.mp4"})

    # Get status
    response = client.get(f"/api/batch/{job_id}/status")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == job_id
    assert data["status"] == "pending"
    assert data["totalFiles"] == 2
    assert len(data["files"]) == 2


def test_get_batch_status_not_found(client):
    """Test getting status of non-existent batch"""
    response = client.get("/api/batch/invalid-job-id/status")
    assert response.status_code == 404


# ------------
# Test PATCH /api/batch/{job_id}/files/{file_id} - Update file settings
# ------------


def test_update_file_settings_success(client):
    """Test updating file settings"""
    # Create batch and file
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    register_response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test.mp4"}
    )
    file_id = register_response.json()["id"]

    # Update settings
    response = client.patch(
        f"/api/batch/{job_id}/files/{file_id}",
        json={"sourceLang": "en", "targetLang": "zh-CN", "dubbing": True},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["sourceLang"] == "en"
    assert data["targetLang"] == "zh-CN"
    assert data["dubbing"] is True


def test_update_file_settings_partial(client):
    """Test partial update of file settings"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    register_response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test.mp4"}
    )
    file_id = register_response.json()["id"]

    # Update only dubbing
    response = client.patch(
        f"/api/batch/{job_id}/files/{file_id}", json={"dubbing": True}
    )
    assert response.status_code == 200
    assert response.json()["dubbing"] is True


def test_update_file_settings_not_found(client):
    """Test updating settings for non-existent file"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    response = client.patch(
        f"/api/batch/{job_id}/files/invalid-file-id", json={"dubbing": True}
    )
    assert response.status_code == 404


# ------------
# Test POST /api/batch/{job_id}/start - Start processing
# ------------


def test_start_batch_processing_success(client):
    """Test starting batch processing"""
    # Create batch with files
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    # Start processing
    response = client.post(f"/api/batch/{job_id}/start")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "processing"


def test_start_batch_processing_not_found(client):
    """Test starting non-existent batch"""
    response = client.post("/api/batch/invalid-job-id/start")
    assert response.status_code == 404


def test_start_batch_processing_no_files(client):
    """Test starting batch with no files"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    response = client.post(f"/api/batch/{job_id}/start")
    assert response.status_code == 400
    assert "没有文件" in response.json()["detail"]


# ------------
# Test POST /api/batch/{job_id}/cancel - Cancel batch
# ------------


def test_cancel_batch_success(client):
    """Test cancelling a batch"""
    # Create batch with files
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    # Cancel batch
    response = client.post(f"/api/batch/{job_id}/cancel")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "cancelled"


def test_cancel_batch_not_found(client):
    """Test cancelling non-existent batch"""
    response = client.post("/api/batch/invalid-job-id/cancel")
    assert response.status_code == 404


# ------------
# Test DELETE /api/batch/{job_id}/files/{file_id} - Remove file
# ------------


def test_remove_file_success(client):
    """Test removing a file from batch"""
    # Create batch and file
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    register_response = client.post(
        f"/api/batch/{job_id}/files", json={"filename": "test.mp4"}
    )
    file_id = register_response.json()["id"]

    # Remove file
    response = client.delete(f"/api/batch/{job_id}/files/{file_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "文件已删除"

    # Verify file is removed
    status_response = client.get(f"/api/batch/{job_id}/status")
    assert len(status_response.json()["files"]) == 0


def test_remove_file_not_found(client):
    """Test removing non-existent file"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]

    response = client.delete(f"/api/batch/{job_id}/files/invalid-file-id")
    assert response.status_code == 404


# ------------
# Test status validation - start completed/cancelled batch
# ------------


def test_start_completed_batch_returns_400(client):
    """Test starting a completed batch returns 400"""
    # Create batch with file
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]
    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    # Manually set batch status to completed via service
    from api.routes import batch as batch_module

    batch_module.batch_service.update_job_status(job_id, "completed")

    # Try to start again
    response = client.post(f"/api/batch/{job_id}/start")
    assert response.status_code == 400
    assert "已结束" in response.json()["detail"]


def test_start_cancelled_batch_returns_400(client):
    """Test starting a cancelled batch returns 400"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]
    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    from api.routes import batch as batch_module

    batch_module.batch_service.update_job_status(job_id, "cancelled")

    response = client.post(f"/api/batch/{job_id}/start")
    assert response.status_code == 400
    assert "已结束" in response.json()["detail"]


def test_cancel_completed_batch_returns_400(client):
    """Test cancelling a completed batch returns 400"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]
    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    from api.routes import batch as batch_module

    batch_module.batch_service.update_job_status(job_id, "completed")

    response = client.post(f"/api/batch/{job_id}/cancel")
    assert response.status_code == 400
    assert "已结束" in response.json()["detail"]


def test_cancel_failed_batch_returns_400(client):
    """Test cancelling a failed batch returns 400"""
    batch_response = client.post("/api/batch/")
    job_id = batch_response.json()["jobId"]
    client.post(f"/api/batch/{job_id}/files", json={"filename": "test.mp4"})

    from api.routes import batch as batch_module

    batch_module.batch_service.update_job_status(job_id, "failed")

    response = client.post(f"/api/batch/{job_id}/cancel")
    assert response.status_code == 400
    assert "已结束" in response.json()["detail"]
