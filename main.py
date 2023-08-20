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
async def health():
  return {"status": "ok"}

@app.post("/anonymize")
async def annonimyze_data(item: Event):
  text = item.text
  results = analyzer.analyze(text=text,language='en')
  anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)
  return {"text": anonymized_text.text}
