"""
Error handling middleware for development debugging.
"""
import traceback
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Development error handling middleware that prints detailed error information.
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            print(f"\n{'='*80}")
            print(f"🚨 HTTP EXCEPTION CAUGHT")
            print(f"{'='*80}")
            print(f"📍 Route: {request.method} {request.url}")
            print(f"🔢 Status Code: {e.status_code}")
            print(f"📝 Detail: {e.detail}")
            print(f"📚 Headers: {dict(e.headers) if e.headers else 'None'}")
            
            # Try to get request body for POST/PUT requests
            if hasattr(request, '_body'):
                try:
                    body = await request.body()
                    if body:
                        print(f"📦 Request Body: {body.decode()}")
                except:
                    print(f"📦 Request Body: Could not decode")
            
            print(f"{'='*80}\n")
            
            # Return the original HTTP exception
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
            
        except StarletteHTTPException as e:
            # Handle Starlette HTTP exceptions
            print(f"\n{'='*80}")
            print(f"🚨 STARLETTE HTTP EXCEPTION CAUGHT")
            print(f"{'='*80}")
            print(f"📍 Route: {request.method} {request.url}")
            print(f"🔢 Status Code: {e.status_code}")
            print(f"📝 Detail: {e.detail}")
            print(f"{'='*80}\n")
            
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
            
        except Exception as e:
            # Handle all other exceptions
            print(f"\n{'='*80}")
            print(f"💥 UNHANDLED EXCEPTION CAUGHT")
            print(f"{'='*80}")
            print(f"📍 Route: {request.method} {request.url}")
            print(f"🏷️  Exception Type: {type(e).__name__}")
            print(f"📝 Exception Message: {str(e)}")
            
            # Try to get request body
            try:
                if hasattr(request, '_body'):
                    body = await request.body()
                    if body:
                        print(f"📦 Request Body: {body.decode()}")
                else:
                    # For requests that haven't been read yet
                    body = await request.body()
                    if body:
                        print(f"📦 Request Body: {body.decode()}")
            except Exception as body_error:
                print(f"📦 Request Body: Could not read - {body_error}")
            
            # Print full traceback
            print(f"🐛 Full Traceback:")
            print(traceback.format_exc())
            print(f"{'='*80}\n")
            
            # Return a 500 error
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {str(e)}",
                    "type": type(e).__name__,
                    "development_mode": True
                }
            )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for 422 validation errors to provide detailed logging.
    """
    print(f"\n{'='*80}")
    print(f"🚨 422 VALIDATION ERROR CAUGHT")
    print(f"{'='*80}")
    print(f"📍 Route: {request.method} {request.url}")
    print(f"🔢 Status Code: 422")
    
    # Print request headers
    print(f"📑 Headers: {dict(request.headers)}")
    
    # Try to get request body
    try:
        body = await request.body()
        if body:
            print(f"📦 Request Body: {body.decode()}")
            try:
                parsed_body = json.loads(body.decode())
                print(f"📝 Parsed JSON: {json.dumps(parsed_body, indent=2)}")
            except:
                print(f"📝 Could not parse JSON from body")
    except Exception as e:
        print(f"📦 Request Body: Could not read - {e}")
    
    # Print validation errors
    print(f"❌ Validation Errors:")
    for error in exc.errors():
        print(f"   • Field: {' -> '.join(str(loc) for loc in error['loc'])}")
        print(f"     Input: {error.get('input', 'N/A')}")
        print(f"     Message: {error['msg']}")
        print(f"     Type: {error['type']}")
        print(f"     URL: {error.get('url', 'N/A')}")
        print()
    
    print(f"{'='*80}\n")
    
    # Return the validation error response
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

def setup_error_middleware(app):
    """
    Add error handling middleware to the FastAPI app.
    """
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add custom exception handler for validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    
    print("🛡️  Error handling middleware enabled for development")
    print("🛡️  422 validation error handler added for debugging")
