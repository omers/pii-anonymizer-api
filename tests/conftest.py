"""
Pytest configuration and shared fixtures for the PII Anonymizer API tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from presidio_analyzer import RecognizerResult
try:
    from presidio_anonymizer.entities import AnonymizeResult
except ImportError:
    # Fallback for newer versions of presidio-anonymizer
    try:
        from presidio_anonymizer import AnonymizeResult
    except ImportError:
        # Create a mock class if neither import works
        class AnonymizeResult:
            def __init__(self, text="", items=None):
                self.text = text
                self.items = items or []

from main import app, AnonymizationStrategy, EntityType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_text():
    """Sample text containing various PII types."""
    return "John Doe's email is john.doe@example.com and his phone number is 555-123-4567. He lives at 123 Main St, New York, NY 10001."


@pytest.fixture
def sample_analyzer_results():
    """Sample analyzer results for testing."""
    return [
        RecognizerResult(
            entity_type="PERSON",
            start=0,
            end=8,
            score=0.85
        ),
        RecognizerResult(
            entity_type="EMAIL_ADDRESS",
            start=20,
            end=42,
            score=0.95
        ),
        RecognizerResult(
            entity_type="PHONE_NUMBER",
            start=63,
            end=75,
            score=0.90
        ),
        RecognizerResult(
            entity_type="LOCATION",
            start=89,
            end=119,
            score=0.80
        )
    ]


@pytest.fixture
def sample_anonymize_result():
    """Sample anonymize result for testing."""
    result = Mock(spec=AnonymizeResult)
    result.text = "<PERSON> email is <EMAIL_ADDRESS> and phone is <PHONE_NUMBER>. Lives at <LOCATION>."
    return result


@pytest.fixture
def mock_engines():
    """Mock both analyzer and anonymizer engines."""
    with patch('main.analyzer_engine') as mock_analyzer, \
         patch('main.anonymizer_engine') as mock_anonymizer:
        yield mock_analyzer, mock_anonymizer


@pytest.fixture
def mock_analyzer_engine():
    """Mock analyzer engine only."""
    with patch('main.analyzer_engine') as mock_analyzer:
        yield mock_analyzer


@pytest.fixture
def mock_anonymizer_engine():
    """Mock anonymizer engine only."""
    with patch('main.anonymizer_engine') as mock_anonymizer:
        yield mock_anonymizer


@pytest.fixture(params=list(AnonymizationStrategy))
def anonymization_strategy(request):
    """Parametrized fixture for all anonymization strategies."""
    return request.param


@pytest.fixture(params=list(EntityType))
def entity_type(request):
    """Parametrized fixture for all entity types."""
    return request.param


@pytest.fixture
def valid_anonymize_request():
    """Valid anonymization request data."""
    return {
        "text": "John Doe email is john@example.com",
        "language": "en",
        "config": {
            "strategy": "replace",
            "entities_to_anonymize": ["PERSON", "EMAIL_ADDRESS"],
            "replacement_text": "[REDACTED]"
        }
    }


@pytest.fixture
def invalid_anonymize_requests():
    """List of invalid anonymization request data for testing validation."""
    return [
        {},  # Missing text
        {"text": ""},  # Empty text
        {"text": "a" * 10001},  # Text too long
        {"text": "valid text", "language": "invalid"},  # Invalid language
        {"text": 123},  # Wrong text type
        {"text": "valid text", "language": ["en"]},  # Wrong language type
    ]


@pytest.fixture
def multilingual_texts():
    """Sample texts in different languages."""
    return {
        "en": "My name is John Smith and my email is john@example.com",
        "es": "Mi nombre es Juan García y mi correo es juan@ejemplo.com",
        "fr": "Je m'appelle Pierre Dupont et mon email est pierre@exemple.com",
        "de": "Mein Name ist Hans Mueller und meine E-Mail ist hans@beispiel.com",
        "it": "Il mio nome è Marco Rossi e la mia email è marco@esempio.com"
    }


@pytest.fixture
def complex_pii_text():
    """Complex text with multiple types of PII."""
    return """
    Patient Information:
    Name: Sarah Johnson
    DOB: 03/15/1985
    SSN: 123-45-6789
    Phone: (555) 987-6543
    Email: sarah.johnson@healthmail.com
    Address: 456 Oak Avenue, Los Angeles, CA 90210
    Insurance: INS-998877665544
    Credit Card: 4532-1234-5678-9012
    IP Address: 192.168.1.100
    Visit Date: 2024-01-20
    """


@pytest.fixture
def performance_test_texts():
    """Texts of various sizes for performance testing."""
    return {
        "small": "John Doe email: john@example.com",
        "medium": "John Doe email: john@example.com. " * 50,
        "large": "John Doe email: john@example.com. " * 500,
        "xlarge": "John Doe email: john@example.com. " * 1000
    }


@pytest.fixture
def mock_successful_analysis(sample_analyzer_results, sample_anonymize_result):
    """Mock successful analysis and anonymization."""
    def _mock_successful_analysis(mock_analyzer, mock_anonymizer):
        mock_analyzer.analyze.return_value = sample_analyzer_results
        mock_anonymizer.anonymize.return_value = sample_anonymize_result
        return mock_analyzer, mock_anonymizer
    return _mock_successful_analysis


@pytest.fixture
def mock_failed_analysis():
    """Mock failed analysis."""
    def _mock_failed_analysis(mock_analyzer, exception=Exception("Analysis failed")):
        mock_analyzer.analyze.side_effect = exception
        return mock_analyzer
    return _mock_failed_analysis


@pytest.fixture
def mock_failed_anonymization(sample_analyzer_results):
    """Mock failed anonymization."""
    def _mock_failed_anonymization(mock_analyzer, mock_anonymizer, exception=Exception("Anonymization failed")):
        mock_analyzer.analyze.return_value = sample_analyzer_results
        mock_anonymizer.anonymize.side_effect = exception
        return mock_analyzer, mock_anonymizer
    return _mock_failed_anonymization


@pytest.fixture(scope="session")
def test_config():
    """Test configuration values."""
    return {
        "max_text_length": 10000,
        "supported_languages": ["en", "es", "fr", "de", "it"],
        "default_language": "en",
        "test_timeout": 30,
        "performance_threshold_ms": 1000
    }


@pytest.fixture
def log_capture():
    """Capture log messages during tests."""
    import logging
    from io import StringIO
    
    log_capture_string = StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.DEBUG)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture_string
    
    # Clean up
    logger.removeHandler(ch)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    import tempfile
    import os
    
    fd, path = tempfile.mkstemp()
    try:
        yield path
    finally:
        os.close(fd)
        os.unlink(path)


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow


# Custom assertions
def assert_valid_response_structure(response_data):
    """Assert that response has valid structure."""
    required_fields = [
        "anonymized_text", "detected_entities", "processing_time_ms",
        "original_length", "anonymized_length"
    ]
    
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"
    
    # Validate types
    assert isinstance(response_data["anonymized_text"], str)
    assert isinstance(response_data["detected_entities"], list)
    assert isinstance(response_data["processing_time_ms"], (int, float))
    assert isinstance(response_data["original_length"], int)
    assert isinstance(response_data["anonymized_length"], int)
    
    # Validate entity structure
    for entity in response_data["detected_entities"]:
        entity_fields = ["entity_type", "start", "end", "score", "text"]
        for field in entity_fields:
            assert field in entity, f"Missing entity field: {field}"


def assert_valid_health_response(response_data):
    """Assert that health response has valid structure."""
    required_fields = ["status", "timestamp", "version", "dependencies"]
    
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"
    
    assert response_data["status"] in ["healthy", "unhealthy"]
    assert isinstance(response_data["dependencies"], dict)


# Add custom assertions to pytest namespace
pytest.assert_valid_response_structure = assert_valid_response_structure
pytest.assert_valid_health_response = assert_valid_health_response
