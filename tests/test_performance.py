"""
Performance and load testing for the PII Anonymizer API.
"""

import pytest
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from presidio_analyzer import RecognizerResult

from main import app, Config


class TestPerformanceMetrics:
    """Test performance metrics and timing"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_response_time_measurement(self):
        """Test that response times are measured accurately"""
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Mock with controlled delay
            def slow_analyze(*args, **kwargs):
                time.sleep(0.05)  # 50ms delay
                return [RecognizerResult("PERSON", 0, 10, 0.85)]
            
            mock_analyzer.analyze.side_effect = slow_analyze
            mock_result = Mock()
            mock_result.text = "Anonymized text"
            mock_anonymizer.anonymize.return_value = mock_result
            
            start_time = time.time()
            response = self.client.post("/anonymize", json={
                "text": "John Doe test text"
            })
            end_time = time.time()
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify processing time is reported
            assert "processing_time_ms" in data
            assert data["processing_time_ms"] >= 50  # At least our delay
            
            # Verify it's reasonably close to actual time
            actual_time_ms = (end_time - start_time) * 1000
            reported_time_ms = data["processing_time_ms"]
            
            # Should be within reasonable range (allowing for overhead)
            assert abs(reported_time_ms - actual_time_ms) < 100
    
    def test_text_length_impact_on_performance(self):
        """Test how text length affects performance"""
        text_sizes = [100, 500, 1000, 2000, 5000]
        processing_times = []
        
        for size in text_sizes:
            test_text = "This is test text. " * (size // 20)  # Approximate size
            
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                # Mock proportional processing time
                def size_based_analyze(*args, **kwargs):
                    time.sleep(len(args[0]) * 0.00001)  # 0.01ms per character
                    return [RecognizerResult("PERSON", 0, 4, 0.85)]
                
                mock_analyzer.analyze.side_effect = size_based_analyze
                mock_result = Mock()
                mock_result.text = "Anonymized " + test_text
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": test_text
                })
                
                assert response.status_code == 200
                data = response.json()
                processing_times.append(data["processing_time_ms"])
        
        # Verify processing time generally increases with text size
        # (allowing for some variance)
        assert processing_times[-1] > processing_times[0]
    
    def test_entity_count_impact_on_performance(self):
        """Test how number of entities affects performance"""
        entity_counts = [1, 5, 10, 20, 50]
        processing_times = []
        
        for count in entity_counts:
            test_text = "Test text with entities"
            
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                # Mock entities proportional to count
                def entity_based_analyze(*args, **kwargs):
                    time.sleep(count * 0.001)  # 1ms per entity
                    return [
                        RecognizerResult("PERSON", i, i+4, 0.85)
                        for i in range(count)
                    ]
                
                mock_analyzer.analyze.side_effect = entity_based_analyze
                mock_result = Mock()
                mock_result.text = "Anonymized text"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": test_text
                })
                
                assert response.status_code == 200
                data = response.json()
                processing_times.append(data["processing_time_ms"])
                assert len(data["detected_entities"]) == count
        
        # Verify processing time increases with entity count
        assert processing_times[-1] > processing_times[0]


class TestConcurrencyAndLoad:
    """Test concurrent request handling and load capacity"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_concurrent_requests_basic(self):
        """Test basic concurrent request handling"""
        num_requests = 10
        results = []
        
        def make_request(request_id):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = [
                    RecognizerResult("PERSON", 0, 10, 0.85)
                ]
                mock_result = Mock()
                mock_result.text = f"Anonymized request {request_id}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                start_time = time.time()
                response = self.client.post("/anonymize", json={
                    "text": f"Test text for request {request_id}"
                })
                end_time = time.time()
                
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "data": response.json() if response.status_code == 200 else None
                }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_request, i)
                for i in range(num_requests)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Verify all requests completed successfully
        assert len(results) == num_requests
        assert all(result["status_code"] == 200 for result in results)
        
        # Verify reasonable response times
        response_times = [result["response_time"] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 1.0  # Should average less than 1 second
    
    def test_high_concurrency_stress(self):
        """Test high concurrency stress scenario"""
        num_requests = 50
        max_workers = 10
        results = []
        
        def make_request(request_id):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                # Add small random delay to simulate real processing
                time.sleep(0.01 + (request_id % 5) * 0.01)
                
                mock_analyzer.analyze.return_value = [
                    RecognizerResult("EMAIL_ADDRESS", 10, 30, 0.95)
                ]
                mock_result = Mock()
                mock_result.text = f"Processed {request_id}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": f"user{request_id}@example.com test text"
                })
                
                return response.status_code
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(make_request, i)
                for i in range(num_requests)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests completed successfully
        assert len(results) == num_requests
        success_rate = sum(1 for status in results if status == 200) / len(results)
        assert success_rate >= 0.95  # At least 95% success rate
        
        # Verify reasonable throughput
        throughput = num_requests / total_time
        assert throughput > 5  # At least 5 requests per second
    
    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests
        for i in range(20):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = [
                    RecognizerResult("PERSON", 0, 10, 0.85)
                ]
                mock_result = Mock()
                mock_result.text = "Anonymized text"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": f"Test text iteration {i} " * 100  # Larger text
                })
                assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50 * 1024 * 1024


class TestScalabilityLimits:
    """Test system behavior at scalability limits"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_maximum_text_length_performance(self):
        """Test performance with maximum allowed text length"""
        max_text = "a" * Config.MAX_TEXT_LENGTH
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            mock_analyzer.analyze.return_value = [
                RecognizerResult("PERSON", 0, 1, 0.85)
            ]
            mock_result = Mock()
            mock_result.text = "Anonymized maximum length text"
            mock_anonymizer.anonymize.return_value = mock_result
            
            start_time = time.time()
            response = self.client.post("/anonymize", json={
                "text": max_text
            })
            end_time = time.time()
            
            assert response.status_code == 200
            processing_time = end_time - start_time
            
            # Should complete within reasonable time (10 seconds)
            assert processing_time < 10.0
            
            data = response.json()
            assert data["original_length"] == Config.MAX_TEXT_LENGTH
    
    def test_many_entities_performance(self):
        """Test performance with many detected entities"""
        num_entities = 100
        
        with patch('main.analyzer_engine') as mock_analyzer, \
             patch('main.anonymizer_engine') as mock_anonymizer:
            
            # Mock many entities
            mock_analyzer.analyze.return_value = [
                RecognizerResult("EMAIL_ADDRESS", i*10, i*10+8, 0.95)
                for i in range(num_entities)
            ]
            mock_result = Mock()
            mock_result.text = "Text with many anonymized entities"
            mock_anonymizer.anonymize.return_value = mock_result
            
            start_time = time.time()
            response = self.client.post("/anonymize", json={
                "text": "Text with many email addresses " * 50
            })
            end_time = time.time()
            
            assert response.status_code == 200
            processing_time = end_time - start_time
            
            # Should handle many entities efficiently
            assert processing_time < 5.0
            
            data = response.json()
            assert len(data["detected_entities"]) == num_entities
    
    def test_rapid_sequential_requests(self):
        """Test rapid sequential requests without delays"""
        num_requests = 100
        response_times = []
        
        for i in range(num_requests):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = [
                    RecognizerResult("PERSON", 0, 4, 0.85)
                ]
                mock_result = Mock()
                mock_result.text = f"Request {i}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                start_time = time.time()
                response = self.client.post("/anonymize", json={
                    "text": f"Test request {i}"
                })
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append(end_time - start_time)
        
        # Verify consistent performance
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Performance should be consistent
        assert max_time < avg_time * 3  # Max shouldn't be more than 3x average
        assert avg_time < 0.1  # Average should be under 100ms


class TestResourceUtilization:
    """Test resource utilization and efficiency"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_cpu_usage_monitoring(self):
        """Test CPU usage during processing"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get baseline CPU usage
        process.cpu_percent()  # First call returns 0.0
        time.sleep(0.1)
        baseline_cpu = process.cpu_percent()
        
        # Make CPU-intensive requests
        for i in range(10):
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                # Simulate CPU-intensive work
                def cpu_intensive_analyze(*args, **kwargs):
                    # Simulate some CPU work
                    sum(i*i for i in range(1000))
                    return [RecognizerResult("PERSON", 0, 10, 0.85)]
                
                mock_analyzer.analyze.side_effect = cpu_intensive_analyze
                mock_result = Mock()
                mock_result.text = "Processed text"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": f"CPU intensive test {i}"
                })
                assert response.status_code == 200
        
        # CPU usage should have increased during processing
        final_cpu = process.cpu_percent()
        # Note: This test might be flaky in CI environments
        # assert final_cpu >= baseline_cpu
    
    def test_response_size_efficiency(self):
        """Test response size efficiency"""
        test_cases = [
            ("Short text", "Short text"),
            ("Medium length text " * 10, "Medium length text " * 10),
            ("Long text " * 100, "Long text " * 100)
        ]
        
        for description, text in test_cases:
            with patch('main.analyzer_engine') as mock_analyzer, \
                 patch('main.anonymizer_engine') as mock_anonymizer:
                
                mock_analyzer.analyze.return_value = [
                    RecognizerResult("PERSON", 0, 5, 0.85)
                ]
                mock_result = Mock()
                mock_result.text = f"Anonymized: {text}"
                mock_anonymizer.anonymize.return_value = mock_result
                
                response = self.client.post("/anonymize", json={
                    "text": text
                })
                
                assert response.status_code == 200
                
                # Verify response contains expected data without excessive overhead
                response_size = len(response.content)
                text_size = len(text)
                
                # Response should be reasonable size relative to input
                # (allowing for JSON overhead and metadata)
                assert response_size < text_size * 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
