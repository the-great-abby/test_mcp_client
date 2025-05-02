"""Unit tests for health check endpoint."""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.health import health_check
from app.models.health import Health

@pytest.mark.asyncio
async def test_health_check_success():
    """Test successful health check."""
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    
    # Call health check endpoint
    response = await health_check(db=mock_db)
    
    # Verify response structure
    assert response["status"] == "ok"
    assert "timestamp" in response
    assert isinstance(response["timestamp"], str)
    
    # Parse and verify timestamp
    timestamp = datetime.fromisoformat(response["timestamp"])
    assert timestamp.tzinfo == UTC
    
    # Verify details
    assert response["details"]["database"] == "ok"
    assert response["details"]["api"] == "ok"
    
    # Verify database interactions
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    
    # Verify health record was created
    health_record = mock_db.add.call_args[0][0]
    assert isinstance(health_record, Health)
    assert health_record.status == "ok"
    assert health_record.details == {"message": "Service is healthy"}

@pytest.mark.asyncio
async def test_health_check_database_error():
    """Test health check with database error."""
    # Mock database session with error
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock(side_effect=Exception("Database error"))
    
    # Call health check endpoint
    response = await health_check(db=mock_db)
    
    # Verify error response
    assert response["status"] == "error"
    assert "timestamp" in response
    assert isinstance(response["timestamp"], str)
    
    # Parse and verify timestamp
    timestamp = datetime.fromisoformat(response["timestamp"])
    assert timestamp.tzinfo == UTC
    
    # Verify error details
    assert "error" in response["details"]
    assert "Database error" in response["details"]["error"]
    
    # Verify database interactions
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once() 