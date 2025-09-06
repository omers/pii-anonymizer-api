"""
Integration tests for the PII Anonymizer API.
These tests verify the complete functionality with real or realistic data.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
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

from main import app


class TestRealWorldScenarios:
    """Test real-world anonymization scenarios"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_email_log_anonymization(self):
        """Test anonymizing email server logs"""
        log_text = """
        2024-01-15 10:30:45 INFO: Email sent from john.doe@company.com to jane.smith@client.org
        2024-01-15 10:31:12 INFO: User authentication successful for user ID: john.doe@company.com
        2024-01-15 10:31:45 ERROR: Failed to deliver email to invalid.email@nonexistent.domain
        """
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Mock realistic email detection
            mock_analyzer.analyze.return_value = [
                RecognizerResult("EMAIL_ADDRESS", 67, 89, 0.95),  # john.doe@company.com
                RecognizerResult("EMAIL_ADDRESS", 93, 113, 0.95),  # jane.smith@client.org
                RecognizerResult("EMAIL_ADDRESS", 175, 197, 0.95),  # john.doe@company.com
                RecognizerResult("EMAIL_ADDRESS", 275, 305, 0.95),  # invalid.email@nonexistent.domain
            ]
            
            mock_result = Mock()
            mock_result.text = log_text.replace("john.doe@company.com", "<EMAIL_1>") \
                                     .replace("jane.smith@client.org", "<EMAIL_2>") \
                                     .replace("invalid.email@nonexistent.domain", "<EMAIL_3>")
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": log_text,
                "config": {
                    "strategy": "replace",
                    "entities_to_anonymize": ["EMAIL_ADDRESS"],
                    "replacement_text": "<EMAIL_REDACTED>"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify emails were detected
            assert len(data["detected_entities"]) == 4
            assert all(entity["entity_type"] == "EMAIL_ADDRESS" for entity in data["detected_entities"])
            
            # Verify processing metrics
            assert data["processing_time_ms"] > 0
            assert data["original_length"] == len(log_text)
    
    def test_customer_support_chat_anonymization(self):
        """Test anonymizing customer support chat logs"""
        chat_text = """
        Customer: Hi, I'm having trouble with my account. My name is Sarah Johnson and my phone number is 555-0123.
        Agent: Hello Sarah! I can help you with that. Can you provide your email address for verification?
        Customer: Sure, it's sarah.johnson@email.com. My account number is ACC-789456123.
        Agent: Thank you. I see your account. Your registered address shows 123 Main St, New York, NY 10001.
        """
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 85, 98, 0.85),  # Sarah Johnson
                RecognizerResult("PHONE_NUMBER", 118, 126, 0.90),  # 555-0123
                RecognizerResult("PERSON", 145, 150, 0.75),  # Sarah
                RecognizerResult("EMAIL_ADDRESS", 230, 252, 0.95),  # sarah.johnson@email.com
                RecognizerResult("LOCATION", 380, 410, 0.80),  # 123 Main St, New York, NY 10001
            ]
            
            mock_result = Mock()
            mock_result.text = "Anonymized chat conversation with PII removed"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": chat_text,
                "config": {
                    "strategy": "mask",
                    "mask_char": "*"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify multiple entity types detected
            entity_types = {entity["entity_type"] for entity in data["detected_entities"]}
            expected_types = {"PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION"}
            assert entity_types.intersection(expected_types)
    
    def test_medical_record_anonymization(self):
        """Test anonymizing medical records"""
        medical_text = """
        Patient: John Smith, DOB: 03/15/1985, SSN: 123-45-6789
        Address: 456 Oak Avenue, Los Angeles, CA 90210
        Phone: (555) 987-6543, Email: j.smith@healthmail.com
        Insurance ID: INS-998877665544
        Visit Date: 2024-01-20
        Diagnosis: Patient presents with symptoms consistent with...
        """
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 9, 19, 0.90),  # John Smith
                RecognizerResult("DATE_TIME", 26, 36, 0.85),  # 03/15/1985
                RecognizerResult("US_SSN", 43, 54, 0.95),  # 123-45-6789
                RecognizerResult("LOCATION", 64, 98, 0.80),  # 456 Oak Avenue, Los Angeles, CA 90210
                RecognizerResult("PHONE_NUMBER", 107, 121, 0.90),  # (555) 987-6543
                RecognizerResult("EMAIL_ADDRESS", 130, 152, 0.95),  # j.smith@healthmail.com
                RecognizerResult("DATE_TIME", 185, 195, 0.85),  # 2024-01-20
            ]
            
            mock_result = Mock()
            mock_result.text = "Anonymized medical record with all PII redacted"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": medical_text,
                "config": {
                    "strategy": "redact"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify sensitive medical PII detected
            entity_types = {entity["entity_type"] for entity in data["detected_entities"]}
            assert "US_SSN" in entity_types
            assert "PERSON" in entity_types
            assert "EMAIL_ADDRESS" in entity_types
    
    def test_financial_transaction_log_anonymization(self):
        """Test anonymizing financial transaction logs"""
        financial_text = """
        Transaction ID: TXN-20240115-001
        Date: 2024-01-15 14:30:22
        From Account: 1234-5678-9012-3456 (John Doe)
        To Account: 9876-5432-1098-7654 (Jane Smith)
        Amount: $1,500.00
        Description: Payment for services
        IP Address: 192.168.1.100
        Phone verification: +1-555-123-4567
        """
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("DATE_TIME", 29, 48, 0.85),  # 2024-01-15 14:30:22
                RecognizerResult("CREDIT_CARD", 63, 82, 0.95),  # 1234-5678-9012-3456
                RecognizerResult("PERSON", 84, 92, 0.85),  # John Doe
                RecognizerResult("CREDIT_CARD", 106, 125, 0.95),  # 9876-5432-1098-7654
                RecognizerResult("PERSON", 127, 137, 0.85),  # Jane Smith
                RecognizerResult("IP_ADDRESS", 210, 224, 0.90),  # 192.168.1.100
                RecognizerResult("PHONE_NUMBER", 246, 262, 0.90),  # +1-555-123-4567
            ]
            
            mock_result = Mock()
            mock_result.text = "Anonymized financial transaction log"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": financial_text,
                "config": {
                    "strategy": "hash",
                    "hash_type": "sha256"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify financial PII detected
            entity_types = {entity["entity_type"] for entity in data["detected_entities"]}
            assert "CREDIT_CARD" in entity_types
            assert "IP_ADDRESS" in entity_types
            assert "PHONE_NUMBER" in entity_types


class TestMultiLanguageSupport:
    """Test multi-language anonymization support"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_spanish_text_anonymization(self):
        """Test anonymizing Spanish text"""
        spanish_text = "Mi nombre es María García y mi correo es maria.garcia@ejemplo.com"
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 13, 26, 0.85),  # María García
                RecognizerResult("EMAIL_ADDRESS", 45, 69, 0.95),  # maria.garcia@ejemplo.com
            ]
            
            mock_result = Mock()
            mock_result.text = "Mi nombre es <PERSONA> y mi correo es <EMAIL>"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": spanish_text,
                "language": "es"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["detected_entities"]) == 2
    
    def test_french_text_anonymization(self):
        """Test anonymizing French text"""
        french_text = "Je m'appelle Pierre Dupont et mon téléphone est 01 23 45 67 89"
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 13, 26, 0.85),  # Pierre Dupont
                RecognizerResult("PHONE_NUMBER", 48, 62, 0.90),  # 01 23 45 67 89
            ]
            
            mock_result = Mock()
            mock_result.text = "Je m'appelle <PERSONNE> et mon téléphone est <TELEPHONE>"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": french_text,
                "language": "fr"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["detected_entities"]) == 2


class TestPerformanceScenarios:
    """Test performance with various text sizes and complexities"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_large_text_processing(self):
        """Test processing large text documents"""
        # Create a large text with multiple PII instances
        large_text = """
        This is a large document containing multiple instances of PII data.
        """ + "\n".join([
            f"User {i}: john.doe{i}@example.com, phone: 555-{i:04d}, SSN: {i:03d}-{i:02d}-{i:04d}"
            for i in range(100)
        ])
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Mock many PII detections
            mock_analyzer.analyze.return_value = [
                RecognizerResult("EMAIL_ADDRESS", i*50, i*50+20, 0.95)
                for i in range(100)
            ]
            
            mock_result = Mock()
            mock_result.text = "Anonymized large document"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": large_text[:Config.MAX_TEXT_LENGTH]  # Respect max length
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify performance metrics are reasonable
            assert data["processing_time_ms"] < 5000  # Should complete within 5 seconds
            assert len(data["detected_entities"]) > 0
    
    def test_complex_mixed_pii_document(self):
        """Test document with many different types of PII"""
        complex_text = """
        Employee Database Export - CONFIDENTIAL
        
        Record 1:
        Name: John Smith, SSN: 123-45-6789, DOB: 1985-03-15
        Email: john.smith@company.com, Phone: +1-555-123-4567
        Address: 123 Main St, Anytown, ST 12345
        Credit Card: 4532-1234-5678-9012, Exp: 12/25
        IP Address: 192.168.1.100, MAC: 00:1B:44:11:3A:B7
        
        Record 2:
        Name: Jane Doe, SSN: 987-65-4321, DOB: 1990-07-22
        Email: jane.doe@company.com, Phone: +1-555-987-6543
        Address: 456 Oak Ave, Another City, ST 67890
        Credit Card: 5555-4444-3333-2222, Exp: 06/26
        IP Address: 10.0.0.50, MAC: 00:1A:2B:3C:4D:5E
        """
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Mock detection of various PII types
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 70, 80, 0.90),
                RecognizerResult("US_SSN", 87, 98, 0.95),
                RecognizerResult("DATE_TIME", 105, 115, 0.85),
                RecognizerResult("EMAIL_ADDRESS", 125, 148, 0.95),
                RecognizerResult("PHONE_NUMBER", 157, 172, 0.90),
                RecognizerResult("LOCATION", 182, 210, 0.80),
                RecognizerResult("CREDIT_CARD", 225, 244, 0.95),
                RecognizerResult("IP_ADDRESS", 260, 274, 0.90),
            ]
            
            mock_result = Mock()
            mock_result.text = "Anonymized employee database export"
            mock_anonymizer.anonymize.return_value = mock_result
            
            response = self.client.post("/anonymize", json={
                "text": complex_text,
                "config": {
                    "strategy": "replace",
                    "replacement_text": "[REDACTED]"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify comprehensive PII detection
            entity_types = {entity["entity_type"] for entity in data["detected_entities"]}
            expected_types = {"PERSON", "US_SSN", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IP_ADDRESS"}
            assert len(entity_types.intersection(expected_types)) >= 5


class TestErrorRecoveryAndResilience:
    """Test error recovery and system resilience"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_malformed_text_handling(self):
        """Test handling of malformed or unusual text"""
        malformed_texts = [
            "Email with no domain: user@",
            "Phone with extra digits: 555-123-4567-8901-2345",
            "Mixed encoding: café résumé naïve",
            "Special chars: !@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
            "Unicode: 你好世界 🌍 emoji test",
        ]
        
        for text in malformed_texts:
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = []
                mock_result = Mock()
                mock_result.text = f"Processed: {text}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={"text": text})
                
                # Should handle gracefully without errors
                assert response.status_code == 200
                data = response.json()
                assert "anonymized_text" in data
    
    def test_concurrent_request_handling(self):
        """Test handling multiple concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request(request_id):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                # Simulate some processing time
                def slow_analyze(*args, **kwargs):
                    time.sleep(0.1)
                    return [RecognizerResult("PERSON", 0, 10, 0.85)]
                
                mock_analyzer.analyze.side_effect = slow_analyze
                mock_result = Mock()
                mock_result.text = f"Processed request {request_id}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": f"Test text for request {request_id}"
                })
                results.append((request_id, response.status_code))
        
        # Create multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all requests completed successfully
        assert len(results) == 5
        assert all(status == 200 for _, status in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
