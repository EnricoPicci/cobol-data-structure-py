"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_fixture():
    """Example fixture for testing."""
    return {"key": "value"}
