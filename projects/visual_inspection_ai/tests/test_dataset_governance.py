import pytest
from inspection_ai.datasets.governance import validate_download_record


def test_pending_dataset_is_blocked():
    with pytest.raises(PermissionError):
        validate_download_record({
            "status": "PENDING",
            "user_approved": False,
            "sha256": "",
            "official_url": "http://example.com/file.zip",
            "commercial_use": "UNKNOWN",
        })
