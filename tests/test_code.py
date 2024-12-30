import pytest
from fastapi.testclient import TestClient
from main import app, Event

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_anonymize_data_empty_text():
    response = client.post("/anonymize", json={"text": None})
    assert response.status_code == 200
    assert response.json() == {"text": ""}

def test_anonymize_data_with_text(mocker):
    mock_analyze = mocker.patch('main.analyzer.analyze', return_value=[])
    mock_anonymize = mocker.patch('main.anonymizer.anonymize', return_value=Event(text="anonymized text"))

    response = client.post("/anonymize", json={"text": "some text"})
    assert response.status_code == 200
    assert response.json() == {"text": "anonymized text"}

    mock_analyze.assert_called_once_with(text="some text", language='en')
    mock_anonymize.assert_called_once()