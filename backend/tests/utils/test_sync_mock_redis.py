"""
Sync-only tests for the SyncMockRedis and SyncMockPipeline.
These tests should be run in a synchronous context (e.g., with pytest, not pytest-asyncio).
"""
import pytest
from tests.utils.mock_redis import SyncMockRedis

def test_pipeline_basic():
    """Test basic pipeline batching and result order (sync mock only)."""
    pipe = SyncMockRedis().pipeline()
    pipe.set(b"pkey1", b"v1")
    pipe.set(b"pkey2", b"v2")
    pipe.get(b"pkey1")
    pipe.delete(b"pkey2")
    results = pipe.execute()
    assert results == [True, True, b"v1", 1]
    # Confirm state
    redis = pipe.redis
    assert redis.get(b"pkey1") == b"v1"
    assert redis.get(b"pkey2") is None 