####
# Ananonymizer API
###
from fastapi import FastAPI
from typing import Union
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

app = FastAPI()

class Event(BaseModel):
    text: Union[str, None] = None

anonymizer = AnonymizerEngine()
analyzer = AnalyzerEngine()

@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint.
    """
    return {"status": "ok"}

@app.post("/anonymize")
async def anonymize_data(item: Event) -> dict:
    """
    Anonymize the provided text data.
    
    Args:
        item (Event): The event containing the text to be anonymized.
    
    Returns:
        dict: A dictionary containing the anonymized text.
    """
    text = item.text
    if text is None:
        return {"text": ""}
    
    results = analyzer.analyze(text=text, language='en')
    anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)
    return {"text": anonymized_text.text}
