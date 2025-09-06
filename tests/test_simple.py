"""
Simple tests that don't rely on complex presidio imports.
These tests focus on the API structure and basic functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from main import app, Config, AnonymizationStrategy, EntityType


class TestBasicAPI:
    """Basic API tests without complex presidio dependencies."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health endpoint returns proper structure."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "dependencies" in data
        
        # Check dependencies structure
        deps = data["dependencies"]
        assert "presidio_analyzer" in deps
        assert "presidio_anonymizer" in deps
    
    def test_info_endpoint(self):
        """Test info endpoint returns configuration."""
        response = self.client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "configuration" in data
        assert "supported_entities" in data
        assert "supported_strategies" in data
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint returns system info."""
        response = self.client.get("/metrics")
        # May return 200 or 500 depending on psutil availability
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "system" in data or "process" in data or "application" in data
    
    def test_anonymize_endpoint_validation(self):
        """Test anonymize endpoint input validation."""
        # Test missing text
        response = self.client.post("/anonymize", json={})
        assert response.status_code == 422
        
        # Test empty text
        response = self.client.post("/anonymize", json={"text": ""})
        assert response.status_code == 422
        
        # Test text too long
        long_text = "a" * (Config.MAX_TEXT_LENGTH + 1)
        response = self.client.post("/anonymize", json={"text": long_text})
        assert response.status_code == 422
        
        # Test invalid language
        response = self.client.post("/anonymize", json={
            "text": "test",
            "language": "invalid"
        })
        assert response.status_code == 422
    
    @patch('main.analyzer_engine')
    @patch('main.anonymizer_engine')
    def test_anonymize_endpoint_success(self, mock_anonymizer, mock_analyzer):
        """Test successful anonymization with mocked engines."""
        # Mock analyzer results
        mock_result = Mock()
        mock_result.entity_type = "PERSON"
        mock_result.start = 0
        mock_result.end = 8
        mock_result.score = 0.85
        mock_analyzer.analyze.return_value = [mock_result]
        
        # Mock anonymizer result
        mock_anon_result = Mock()
        mock_anon_result.text = "PERSON_1 is a test"
        mock_anonymizer.anonymize.return_value = mock_anon_result
        
        response = self.client.post("/anonymize", json={
            "text": "John Doe is a test"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "anonymized_text" in data
        assert "detected_entities" in data
        assert "processing_time_ms" in data
        assert "original_length" in data
        assert "anonymized_length" in data
        
        # Check entity structure
        entities = data["detected_entities"]
        assert len(entities) == 1
        entity = entities[0]
        assert "entity_type" in entity
        assert "start" in entity
        assert "end" in entity
        assert "score" in entity
        assert "text" in entity
    
    def test_anonymize_endpoint_engines_not_initialized(self):
        """Test anonymize endpoint when engines are not initialized."""
        with patch('main.analyzer_engine', None), \
             patch('main.anonymizer_engine', None):
            
            response = self.client.post("/anonymize", json={
                "text": "test text"
            })
            
            # The API returns 500 when engines are not initialized due to the exception handler
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "engines not initialized" in data["detail"].lower()


class TestConfiguration:
    """Test configuration and enums."""
    
    def test_config_values(self):
        """Test configuration values are reasonable."""
        assert Config.MAX_TEXT_LENGTH > 0
        assert Config.DEFAULT_LANGUAGE in Config.SUPPORTED_LANGUAGES
        assert len(Config.SUPPORTED_LANGUAGES) > 0
    
    def test_anonymization_strategies(self):
        """Test anonymization strategy enum."""
        strategies = list(AnonymizationStrategy)
        assert len(strategies) > 0
        
        # Check common strategies exist
        strategy_values = [s.value for s in strategies]
        assert "replace" in strategy_values
        assert "redact" in strategy_values
        assert "mask" in strategy_values
    
    def test_entity_types(self):
        """Test entity type enum."""
        entities = list(EntityType)
        assert len(entities) > 0
        
        # Check common entities exist
        entity_values = [e.value for e in entities]
        assert "PERSON" in entity_values
        assert "EMAIL_ADDRESS" in entity_values
        assert "PHONE_NUMBER" in entity_values


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        response = self.client.post("/anonymize", data="invalid json")
        assert response.status_code == 422
    
    def test_wrong_content_type(self):
        """Test handling of wrong content type."""
        response = self.client.post("/anonymize", data="text=test")
        assert response.status_code == 422
    
    @patch('main.analyzer_engine')
    def test_analyzer_exception(self, mock_analyzer):
        """Test handling of analyzer exceptions."""
        mock_analyzer.analyze.side_effect = ValueError("Test error")
        
        response = self.client.post("/anonymize", json={
            "text": "test text"
        })
        
        # All exceptions in the anonymize endpoint get caught and converted to 500 HTTPException
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Anonymization failed" in data["detail"]
    
    @patch('main.analyzer_engine')
    def test_general_exception(self, mock_analyzer):
        """Test handling of general exceptions."""
        mock_analyzer.analyze.side_effect = RuntimeError("Unexpected error")
        
        response = self.client.post("/anonymize", json={
            "text": "test text"
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Anonymization failed" in data["detail"]


class TestCustomExceptionHandlers:
    """Test custom exception handlers using test endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_value_error_handler(self):
        """Test ValueError exception handler."""
        response = self.client.get("/test/error/value")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"] == "ValidationError"
        assert "Test ValueError" in data["message"]
    
    def test_runtime_error_handler(self):
        """Test RuntimeError exception handler."""
        response = self.client.get("/test/error/runtime")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "RuntimeError"
        assert "Test RuntimeError" in data["message"]
    
    def test_http_exception_passthrough(self):
        """Test that HTTPExceptions are not caught by custom handlers."""
        response = self.client.get("/test/error/http")
        assert response.status_code == 418
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "I'm a teapot"
    
    def test_no_error(self):
        """Test test endpoint with no error."""
        response = self.client.get("/test/error/none")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No error raised"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
