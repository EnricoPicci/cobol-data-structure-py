"""Example test module."""

from cobol_data_structure import __version__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_example_with_fixture(sample_fixture):
    """Example test using a fixture."""
    assert sample_fixture["key"] == "value"
