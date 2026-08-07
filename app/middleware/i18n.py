"""
FastAPI middleware for language detection and i18n support.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Optional, Callable

from app.i18n import get_language_from_header, translate


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Middleware that detects language from request headers
    and adds translation context to the request state.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Detect language from Accept-Language header
        accept_language = request.headers.get("accept-language")
        language = get_language_from_header(accept_language)
        
        # Also check query parameter for language override
        lang_param = request.query_params.get("lang")
        if lang_param:
            language = lang_param
        
        # Store language in request state
        request.state.language = language
        
        response = await call_next(request)
        
        # Add language header to response
        response.headers["Content-Language"] = language
        
        return response


def get_request_language(request: Request) -> str:
    """
    Get the language from the request context.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Language code string
    """
    return getattr(request.state, "language", "en")


def translate_response(data: dict, language: str) -> dict:
    """
    Recursively translate string values in a response dict.
    
    Args:
        data: Response data dictionary
        language: Target language code
        
    Returns:
        Translated response data
    """
    if isinstance(data, str):
        return translate(data, language)
    elif isinstance(data, dict):
        return {k: translate_response(v, language) for k, v in data.items()}
    elif isinstance(data, list):
        return [translate_response(item, language) for item in data]
    return data
