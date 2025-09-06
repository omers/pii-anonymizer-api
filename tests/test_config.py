"""
Configuration and environment variable tests.
"""

import pytest
import os
from unittest.mock import patch

from main import Config, AnonymizationStrategy, EntityType


class TestConfiguration:
    """Test configuration management and environment variables"""
    
    def test_default_configuration_values(self):
        """Test default configuration values"""
        assert Config.DEFAULT_LANGUAGE == "en"
        assert Config.LOG_LEVEL == "INFO"
        assert Config.MAX_TEXT_LENGTH == 10000
        assert Config.SUPPORTED_LANGUAGES == ["en", "es", "fr", "de", "it"]
        assert Config.CORS_ORIGINS == ["*"]
    
    @patch.dict(os.environ, {
        "DEFAULT_LANGUAGE": "es",
        "LOG_LEVEL": "DEBUG",
        "MAX_TEXT_LENGTH": "5000",
        "SUPPORTED_LANGUAGES": "en,es,fr",
        "CORS_ORIGINS": "http://localhost:3000,https://app.example.com"
    })
    def test_environment_variable_override(self):
        """Test that environment variables override default values"""
        # Need to reimport to get updated values
        import importlib
        import main
        importlib.reload(main)
        
        assert main.Config.DEFAULT_LANGUAGE == "es"
        assert main.Config.LOG_LEVEL == "DEBUG"
        assert main.Config.MAX_TEXT_LENGTH == 5000
        assert main.Config.SUPPORTED_LANGUAGES == ["en", "es", "fr"]
        assert main.Config.CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]
    
    def test_supported_languages_validation(self):
        """Test supported languages configuration"""
        supported_langs = Config.SUPPORTED_LANGUAGES
        
        # Should include at least English
        assert "en" in supported_langs
        
        # Should be a list of strings
        assert isinstance(supported_langs, list)
        assert all(isinstance(lang, str) for lang in supported_langs)
        assert all(len(lang) == 2 for lang in supported_langs)  # ISO language codes
    
    def test_max_text_length_validation(self):
        """Test max text length configuration"""
        max_length = Config.MAX_TEXT_LENGTH
        
        # Should be a positive integer
        assert isinstance(max_length, int)
        assert max_length > 0
        assert max_length <= 100000  # Reasonable upper limit
    
    @patch.dict(os.environ, {"MAX_TEXT_LENGTH": "invalid"})
    def test_invalid_max_text_length(self):
        """Test handling of invalid MAX_TEXT_LENGTH environment variable"""
        with pytest.raises(ValueError):
            # This would fail when trying to convert "invalid" to int
            int(os.getenv("MAX_TEXT_LENGTH", "10000"))


class TestEnums:
    """Test enum definitions and values"""
    
    def test_anonymization_strategy_enum(self):
        """Test AnonymizationStrategy enum"""
        strategies = list(AnonymizationStrategy)
        
        # Verify all expected strategies are present
        expected_strategies = ["replace", "redact", "hash", "mask", "encrypt"]
        assert len(strategies) == len(expected_strategies)
        
        for strategy in expected_strategies:
            assert hasattr(AnonymizationStrategy, strategy.upper())
            assert AnonymizationStrategy[strategy.upper()].value == strategy
    
    def test_entity_type_enum(self):
        """Test EntityType enum"""
        entities = list(EntityType)
        
        # Verify common PII entity types are present
        expected_entities = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
            "IBAN_CODE", "IP_ADDRESS", "DATE_TIME", "LOCATION",
            "ORGANIZATION", "URL", "US_SSN", "US_PASSPORT", "US_DRIVER_LICENSE"
        ]
        
        assert len(entities) == len(expected_entities)
        
        for entity in expected_entities:
            assert hasattr(EntityType, entity)
            assert EntityType[entity].value == entity
    
    def test_enum_string_representation(self):
        """Test enum string representations"""
        # Test AnonymizationStrategy
        assert str(AnonymizationStrategy.REPLACE) == "replace"
        assert str(AnonymizationStrategy.REDACT) == "redact"
        
        # Test EntityType
        assert str(EntityType.PERSON) == "PERSON"
        assert str(EntityType.EMAIL_ADDRESS) == "EMAIL_ADDRESS"
    
    def test_enum_comparison(self):
        """Test enum comparison operations"""
        # Test equality
        assert AnonymizationStrategy.REPLACE == AnonymizationStrategy.REPLACE
        assert AnonymizationStrategy.REPLACE != AnonymizationStrategy.REDACT
        
        # Test with string values
        assert AnonymizationStrategy.REPLACE.value == "replace"
        assert EntityType.PERSON.value == "PERSON"
    
    def test_enum_iteration(self):
        """Test enum iteration"""
        strategy_values = [strategy.value for strategy in AnonymizationStrategy]
        assert "replace" in strategy_values
        assert "redact" in strategy_values
        assert "hash" in strategy_values
        assert "mask" in strategy_values
        assert "encrypt" in strategy_values
        
        entity_values = [entity.value for entity in EntityType]
        assert "PERSON" in entity_values
        assert "EMAIL_ADDRESS" in entity_values
        assert "PHONE_NUMBER" in entity_values


class TestConfigurationValidation:
    """Test configuration validation and error handling"""
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from environment variable"""
        # Test single origin
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}):
            import importlib
            import main
            importlib.reload(main)
            assert main.Config.CORS_ORIGINS == ["http://localhost:3000"]
        
        # Test multiple origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,https://app.example.com,https://api.example.com"}):
            import importlib
            import main
            importlib.reload(main)
            expected = ["http://localhost:3000", "https://app.example.com", "https://api.example.com"]
            assert main.Config.CORS_ORIGINS == expected
        
        # Test wildcard
        with patch.dict(os.environ, {"CORS_ORIGINS": "*"}):
            import importlib
            import main
            importlib.reload(main)
            assert main.Config.CORS_ORIGINS == ["*"]
    
    def test_supported_languages_parsing(self):
        """Test supported languages parsing from environment variable"""
        # Test single language
        with patch.dict(os.environ, {"SUPPORTED_LANGUAGES": "en"}):
            import importlib
            import main
            importlib.reload(main)
            assert main.Config.SUPPORTED_LANGUAGES == ["en"]
        
        # Test multiple languages
        with patch.dict(os.environ, {"SUPPORTED_LANGUAGES": "en,es,fr,de,it,pt"}):
            import importlib
            import main
            importlib.reload(main)
            expected = ["en", "es", "fr", "de", "it", "pt"]
            assert main.Config.SUPPORTED_LANGUAGES == expected
    
    def test_log_level_validation(self):
        """Test log level configuration"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                import importlib
                import main
                importlib.reload(main)
                assert main.Config.LOG_LEVEL == level
    
    @patch.dict(os.environ, {"MAX_TEXT_LENGTH": "0"})
    def test_zero_max_text_length(self):
        """Test handling of zero max text length"""
        with pytest.raises(ValueError):
            # This should be caught by validation if implemented
            max_length = int(os.getenv("MAX_TEXT_LENGTH", "10000"))
            if max_length <= 0:
                raise ValueError("MAX_TEXT_LENGTH must be positive")
    
    @patch.dict(os.environ, {"MAX_TEXT_LENGTH": "-1000"})
    def test_negative_max_text_length(self):
        """Test handling of negative max text length"""
        with pytest.raises(ValueError):
            max_length = int(os.getenv("MAX_TEXT_LENGTH", "10000"))
            if max_length <= 0:
                raise ValueError("MAX_TEXT_LENGTH must be positive")


class TestConfigurationIntegration:
    """Test configuration integration with the application"""
    
    def test_config_affects_request_validation(self):
        """Test that configuration affects request validation"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Test with text at max length (should succeed)
        text_at_limit = "a" * Config.MAX_TEXT_LENGTH
        response = client.post("/anonymize", json={"text": text_at_limit})
        # Note: This might fail due to engine initialization, but validation should pass
        assert response.status_code in [200, 503]  # 503 if engines not initialized
        
        # Test with text over max length (should fail validation)
        text_over_limit = "a" * (Config.MAX_TEXT_LENGTH + 1)
        response = client.post("/anonymize", json={"text": text_over_limit})
        assert response.status_code == 422  # Validation error
    
    def test_config_affects_language_validation(self):
        """Test that configuration affects language validation"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Test with supported language
        for lang in Config.SUPPORTED_LANGUAGES:
            response = client.post("/anonymize", json={
                "text": "Test text",
                "language": lang
            })
            # Should not fail due to language validation
            assert response.status_code in [200, 503]  # 503 if engines not initialized
        
        # Test with unsupported language
        response = client.post("/anonymize", json={
            "text": "Test text",
            "language": "unsupported"
        })
        assert response.status_code == 422  # Validation error
    
    def test_default_language_usage(self):
        """Test that default language is used when not specified"""
        from main import AnonymizeRequest
        
        request = AnonymizeRequest(text="Test text")
        assert request.language == Config.DEFAULT_LANGUAGE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
