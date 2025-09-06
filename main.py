import logging
import os
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
try:
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    # Fallback for newer versions of presidio-anonymizer
    try:
        from presidio_anonymizer import OperatorConfig
    except ImportError:
        # Create a mock class if neither import works
        class OperatorConfig:
            def __init__(self, operator_name, params=None):
                self.operator_name = operator_name
                self.params = params or {}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration"""
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "10000"))
    SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,es,fr,de,it").split(",")

# Enums
class AnonymizationStrategy(str, Enum):
    """Available anonymization strategies"""
    REPLACE = "replace"
    REDACT = "redact"
    HASH = "hash"
    MASK = "mask"
    ENCRYPT = "encrypt"

class EntityType(str, Enum):
    """Supported PII entity types"""
    PERSON = "PERSON"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    CREDIT_CARD = "CREDIT_CARD"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    DATE_TIME = "DATE_TIME"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    URL = "URL"
    US_SSN = "US_SSN"
    US_PASSPORT = "US_PASSPORT"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"

# Pydantic Models
class AnonymizationConfig(BaseModel):
    """Configuration for anonymization process"""
    strategy: AnonymizationStrategy = Field(default=AnonymizationStrategy.REPLACE, description="Anonymization strategy to use")
    entities_to_anonymize: Optional[List[EntityType]] = Field(default=None, description="Specific entities to anonymize. If None, all detected entities will be anonymized")
    replacement_text: Optional[str] = Field(default=None, description="Custom replacement text for REPLACE strategy")
    mask_char: str = Field(default="*", description="Character to use for MASK strategy")
    hash_type: str = Field(default="sha256", description="Hash algorithm for HASH strategy")

class AnonymizeRequest(BaseModel):
    """Request model for anonymization endpoint"""
    text: str = Field(..., min_length=1, max_length=Config.MAX_TEXT_LENGTH, description="Text to anonymize")
    language: str = Field(default=Config.DEFAULT_LANGUAGE, description="Language of the text")
    config: Optional[AnonymizationConfig] = Field(default=None, description="Anonymization configuration")
    
    @validator('language')
    def validate_language(cls, v):
        if v not in Config.SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{v}' not supported. Supported languages: {', '.join(Config.SUPPORTED_LANGUAGES)}")
        return v

class DetectedEntity(BaseModel):
    """Model for detected PII entities"""
    entity_type: str = Field(..., description="Type of detected entity")
    start: int = Field(..., description="Start position in text")
    end: int = Field(..., description="End position in text")
    score: float = Field(..., description="Confidence score")
    text: str = Field(..., description="Original text of the entity")

class AnonymizeResponse(BaseModel):
    """Response model for anonymization endpoint"""
    anonymized_text: str = Field(..., description="The anonymized text")
    detected_entities: List[DetectedEntity] = Field(..., description="List of detected PII entities")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    original_length: int = Field(..., description="Length of original text")
    anonymized_length: int = Field(..., description="Length of anonymized text")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")

# Global variables for engines
analyzer_engine: Optional[AnalyzerEngine] = None
anonymizer_engine: Optional[AnonymizerEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global analyzer_engine, anonymizer_engine
    
    logger.info("Starting PII Anonymizer API...")
    
    try:
        # Initialize engines
        logger.info("Initializing Presidio engines...")
        analyzer_engine = AnalyzerEngine()
        anonymizer_engine = AnonymizerEngine()
        logger.info("Presidio engines initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise
    finally:
        logger.info("Shutting down PII Anonymizer API...")

# FastAPI app initialization
app = FastAPI(
    title="PII Anonymizer API",
    description="A FastAPI service for anonymizing Personally Identifiable Information (PII) in text data using Microsoft Presidio",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"ValueError: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="ValidationError",
            message=str(exc)
        ).dict()
    )

@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error(f"RuntimeError: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="RuntimeError",
            message=str(exc)
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred"
        ).dict()
    )

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint that returns the status of the service and its dependencies.
    """
    try:
        # Check if engines are initialized
        analyzer_status = "healthy" if analyzer_engine is not None else "unhealthy"
        anonymizer_status = "healthy" if anonymizer_engine is not None else "unhealthy"
        
        return HealthResponse(
            status="healthy" if analyzer_status == "healthy" and anonymizer_status == "healthy" else "unhealthy",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            version="2.0.0",
            dependencies={
                "presidio_analyzer": analyzer_status,
                "presidio_anonymizer": anonymizer_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

@app.post("/anonymize", response_model=AnonymizeResponse, tags=["Anonymization"])
async def anonymize_text(request: AnonymizeRequest) -> AnonymizeResponse:
    """
    Anonymize PII in the provided text data.
    
    This endpoint analyzes the input text for personally identifiable information (PII)
    and anonymizes it according to the specified configuration.
    """
    start_time = time.time()
    
    try:
        if not analyzer_engine or not anonymizer_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anonymization engines not initialized"
            )
        
        logger.info(f"Processing anonymization request for text of length {len(request.text)}")
        
        # Analyze text for PII entities
        analyzer_results = analyzer_engine.analyze(
            text=request.text,
            language=request.language
        )
        
        # Filter entities if specific types are requested
        if request.config and request.config.entities_to_anonymize:
            analyzer_results = [
                result for result in analyzer_results
                if result.entity_type in [e.value for e in request.config.entities_to_anonymize]
            ]
        
        # Configure anonymization operators
        operators = {}
        if request.config:
            if request.config.strategy == AnonymizationStrategy.REPLACE:
                operators = {"DEFAULT": OperatorConfig("replace", {"new_value": request.config.replacement_text or "<ANONYMIZED>"})}
            elif request.config.strategy == AnonymizationStrategy.REDACT:
                operators = {"DEFAULT": OperatorConfig("redact")}
            elif request.config.strategy == AnonymizationStrategy.MASK:
                operators = {"DEFAULT": OperatorConfig("mask", {"masking_char": request.config.mask_char, "chars_to_mask": -1})}
            elif request.config.strategy == AnonymizationStrategy.HASH:
                operators = {"DEFAULT": OperatorConfig("hash", {"hash_type": request.config.hash_type})}
        
        # Anonymize text
        anonymized_result = anonymizer_engine.anonymize(
            text=request.text,
            analyzer_results=analyzer_results,
            operators=operators if operators else None
        )
        
        # Prepare detected entities for response
        detected_entities = [
            DetectedEntity(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
                text=request.text[result.start:result.end]
            )
            for result in analyzer_results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Anonymization completed in {processing_time:.2f}ms, detected {len(detected_entities)} entities")
        
        return AnonymizeResponse(
            anonymized_text=anonymized_result.text,
            detected_entities=detected_entities,
            processing_time_ms=processing_time,
            original_length=len(request.text),
            anonymized_length=len(anonymized_result.text)
        )
        
    except Exception as e:
        logger.error(f"Error during anonymization: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anonymization failed: {str(e)}"
        )

# Additional endpoints for monitoring and metrics
@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Get application metrics for monitoring.
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        return {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
            },
            "process": {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
            },
            "application": {
                "analyzer_status": "healthy" if analyzer_engine is not None else "unhealthy",
                "anonymizer_status": "healthy" if anonymizer_engine is not None else "unhealthy",
                "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )

@app.get("/info", tags=["Information"])
async def get_info():
    """
    Get application information and configuration.
    """
    return {
        "name": "PII Anonymizer API",
        "version": "2.0.0",
        "description": "A FastAPI service for anonymizing Personally Identifiable Information (PII) in text data",
        "configuration": {
            "max_text_length": Config.MAX_TEXT_LENGTH,
            "supported_languages": Config.SUPPORTED_LANGUAGES,
            "default_language": Config.DEFAULT_LANGUAGE,
        },
        "supported_entities": [entity.value for entity in EntityType],
        "supported_strategies": [strategy.value for strategy in AnonymizationStrategy],
        "endpoints": {
            "health": "/health",
            "anonymize": "/anonymize",
            "metrics": "/metrics",
            "info": "/info",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

# Add startup event to track application start time
@app.on_event("startup")
async def startup_event():
    """Track application startup time for uptime calculation"""
    app.state.start_time = time.time()
    logger.info("Application startup completed")

# Test endpoints (only available in development/testing)
if os.getenv("ENVIRONMENT", "development") in ["development", "testing"]:
    @app.get("/test/error/{error_type}", tags=["Testing"], include_in_schema=False)
    async def test_error_handler(error_type: str):
        """Test endpoint for error handling (development/testing only)."""
        try:
            if error_type == "value":
                raise ValueError("Test ValueError")
            elif error_type == "runtime":
                raise RuntimeError("Test RuntimeError")
            elif error_type == "http":
                raise HTTPException(status_code=418, detail="I'm a teapot")
            else:
                return {"message": "No error raised"}
        except HTTPException:
            # Re-raise HTTPExceptions so they're handled properly
            raise
        except Exception as e:
            # For testing purposes, we'll manually call our exception handlers
            if isinstance(e, ValueError):
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        error="ValidationError",
                        message=str(e)
                    ).dict()
                )
            elif isinstance(e, RuntimeError):
                return JSONResponse(
                    status_code=500,
                    content=ErrorResponse(
                        error="RuntimeError", 
                        message=str(e)
                    ).dict()
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content=ErrorResponse(
                        error="InternalServerError",
                        message="An unexpected error occurred"
                    ).dict()
                )