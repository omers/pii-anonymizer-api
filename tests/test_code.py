import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
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

from main import (
    app, 
    AnonymizationStrategy, 
    EntityType,
    AnonymizeRequest,
    AnonymizationConfig,
    Config
)

# Test client
client = TestClient(app)

# Test fixtures
@pytest.fixture
def sample_analyzer_results():
    """Sample analyzer results for testing"""
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
            end=35,
            score=0.95
        ),
        RecognizerResult(
            entity_type="PHONE_NUMBER",
            start=50,
            end=62,
            score=0.90
        )
    ]

@pytest.fixture
def sample_anonymize_result():
    """Sample anonymize result for testing"""
    result = Mock(spec=AnonymizeResult)
    result.text = "PERSON_1 email is EMAIL_1 and phone is PHONE_1"
    return result

class TestHealthEndpoint:
    """Test cases for health check endpoint"""
    
    def test_health_check_success(self):
        """Test successful health check"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "version" in data
        assert "dependencies" in data
        assert "presidio_analyzer" in data["dependencies"]
        assert "presidio_anonymizer" in data["dependencies"]

    def test_health_check_response_model(self):
        """Test health check response follows correct model"""
        response = client.get("/health")
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["status", "timestamp", "version", "dependencies"]
        for field in required_fields:
            assert field in data
        
        # Verify dependencies structure
        assert isinstance(data["dependencies"], dict)
        assert len(data["dependencies"]) >= 2

class TestAnonymizeEndpoint:
    """Test cases for anonymization endpoint"""
    
    def test_anonymize_basic_request(self, sample_analyzer_results, sample_anonymize_result):
        """Test basic anonymization request"""
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = sample_analyzer_results
            mock_anonymizer.anonymize.return_value = sample_anonymize_result
            
            response = client.post("/anonymize", json={
                "text": "John Doe email is john@example.com and phone is 555-123-4567"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "anonymized_text" in data
            assert "detected_entities" in data
            assert "processing_time_ms" in data
            assert "original_length" in data
            assert "anonymized_length" in data
            
            # Verify detected entities
            assert len(data["detected_entities"]) == 3
            for entity in data["detected_entities"]:
                assert "entity_type" in entity
                assert "start" in entity
                assert "end" in entity
                assert "score" in entity
                assert "text" in entity

    def test_anonymize_with_custom_config(self, sample_analyzer_results, sample_anonymize_result):
        """Test anonymization with custom configuration"""
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = sample_analyzer_results
            mock_anonymizer.anonymize.return_value = sample_anonymize_result
            
            request_data = {
                "text": "John Doe email is john@example.com",
                "language": "en",
                "config": {
                    "strategy": "replace",
                    "entities_to_anonymize": ["PERSON", "EMAIL_ADDRESS"],
                    "replacement_text": "[REDACTED]"
                }
            }
            
            response = client.post("/anonymize", json=request_data)
            assert response.status_code == 200
            
            # Verify analyzer was called with correct parameters
            mock_analyzer.analyze.assert_called_once_with(
                text="John Doe email is john@example.com",
                language="en"
            )

    def test_anonymize_different_strategies(self, sample_analyzer_results):
        """Test different anonymization strategies"""
        strategies = [
            AnonymizationStrategy.REPLACE,
            AnonymizationStrategy.REDACT,
            AnonymizationStrategy.MASK,
            AnonymizationStrategy.HASH
        ]
        
        for strategy in strategies:
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = sample_analyzer_results
                mock_result = Mock()
                mock_result.text = f"anonymized with {strategy}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                request_data = {
                    "text": "Test text with PII",
                    "config": {"strategy": strategy.value}
                }
                
                response = client.post("/anonymize", json=request_data)
                assert response.status_code == 200

    def test_anonymize_multiple_languages(self, sample_analyzer_results, sample_anonymize_result):
        """Test anonymization with different languages"""
        languages = ["en", "es", "fr", "de", "it"]
        
        for lang in languages:
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = sample_analyzer_results
                mock_anonymizer.anonymize.return_value = sample_anonymize_result
                
                response = client.post("/anonymize", json={
                    "text": "Test text",
                    "language": lang
                })
                
                assert response.status_code == 200
                mock_analyzer.analyze.assert_called_with(text="Test text", language=lang)

    def test_anonymize_invalid_language(self):
        """Test anonymization with unsupported language"""
        response = client.post("/anonymize", json={
            "text": "Test text",
            "language": "unsupported"
        })
        
        assert response.status_code == 422  # Validation error

    def test_anonymize_empty_text(self):
        """Test anonymization with empty text"""
        response = client.post("/anonymize", json={
            "text": ""
        })
        
        assert response.status_code == 422  # Validation error due to min_length=1

    def test_anonymize_text_too_long(self):
        """Test anonymization with text exceeding max length"""
        long_text = "a" * (Config.MAX_TEXT_LENGTH + 1)
        
        response = client.post("/anonymize", json={
            "text": long_text
        })
        
        assert response.status_code == 422  # Validation error

    def test_anonymize_missing_text(self):
        """Test anonymization without text field"""
        response = client.post("/anonymize", json={})
        
        assert response.status_code == 422  # Validation error

    def test_anonymize_engines_not_initialized(self):
        """Test anonymization when engines are not initialized"""
        with patch('main.analyzer_engine', None), \
             patch('main.anonymizer_engine', None):
            
            response = client.post("/anonymize", json={
                "text": "Test text"
            })
            
            assert response.status_code == 503  # Service unavailable

class TestValidationAndErrorHandling:
    """Test cases for validation and error handling"""
    
    def test_invalid_json_request(self):
        """Test request with invalid JSON"""
        response = client.post("/anonymize", data="invalid json")
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Test request missing required fields"""
        response = client.post("/anonymize", json={})
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data

    def test_invalid_field_types(self):
        """Test request with invalid field types"""
        response = client.post("/anonymize", json={
            "text": 123,  # Should be string
            "language": ["en"]  # Should be string
        })
        assert response.status_code == 422

    def test_custom_error_handler(self):
        """Test custom error handlers"""
        with patch('main.analyzer_engine') as mock_analyzer:
            mock_analyzer.analyze.side_effect = ValueError("Test error")
            
            response = client.post("/anonymize", json={
                "text": "Test text"
            })
            
            assert response.status_code == 400
            error_data = response.json()
            assert error_data["error"] == "ValidationError"
            assert "Test error" in error_data["message"]

class TestConfigurationAndModels:
    """Test cases for configuration and data models"""
    
    def test_anonymization_config_defaults(self):
        """Test AnonymizationConfig default values"""
        config = AnonymizationConfig()
        
        assert config.strategy == AnonymizationStrategy.REPLACE
        assert config.entities_to_anonymize is None
        assert config.replacement_text is None
        assert config.mask_char == "*"
        assert config.hash_type == "sha256"

    def test_anonymize_request_validation(self):
        """Test AnonymizeRequest validation"""
        # Valid request
        request = AnonymizeRequest(text="Test text")
        assert request.text == "Test text"
        assert request.language == Config.DEFAULT_LANGUAGE
        
        # Test language validation
        with pytest.raises(ValueError):
            AnonymizeRequest(text="Test", language="invalid")

    def test_entity_type_enum(self):
        """Test EntityType enum values"""
        expected_entities = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS", "DATE_TIME", "LOCATION",
            "ORGANIZATION", "URL", "US_SSN", "US_PASSPORT", "US_DRIVER_LICENSE"
        ]
        
        for entity in expected_entities:
            assert hasattr(EntityType, entity)
            assert EntityType[entity].value == entity

    def test_anonymization_strategy_enum(self):
        """Test AnonymizationStrategy enum values"""
        expected_strategies = ["replace", "redact", "hash", "mask", "encrypt"]
        
        for strategy in expected_strategies:
            assert hasattr(AnonymizationStrategy, strategy.upper())
            assert AnonymizationStrategy[strategy.upper()].value == strategy

class TestPerformanceAndMetrics:
    """Test cases for performance and metrics"""
    
    def test_processing_time_measurement(self, sample_analyzer_results, sample_anonymize_result):
        """Test that processing time is measured and returned"""
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Add delay to simulate processing
            def slow_analyze(*args, **kwargs):
                time.sleep(0.01)  # 10ms delay
                return sample_analyzer_results
            
            mock_analyzer.analyze.side_effect = slow_analyze
            mock_anonymizer.anonymize.return_value = sample_anonymize_result
            
            response = client.post("/anonymize", json={
                "text": "Test text with some PII"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Processing time should be at least 10ms
            assert data["processing_time_ms"] >= 10
            assert isinstance(data["processing_time_ms"], (int, float))

    def test_text_length_metrics(self, sample_analyzer_results, sample_anonymize_result):
        """Test that text length metrics are returned"""
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = sample_analyzer_results
            mock_anonymizer.anonymize.return_value = sample_anonymize_result
            
            original_text = "John Doe email is john@example.com"
            response = client.post("/anonymize", json={
                "text": original_text
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["original_length"] == len(original_text)
            assert data["anonymized_length"] == len(sample_anonymize_result.text)
            assert isinstance(data["original_length"], int)
            assert isinstance(data["anonymized_length"], int)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])