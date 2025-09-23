from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

class CoinGeckoAPIError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

def handle_api_error(error: Exception, message: str):
    """Maneja errores de API y lanza una excepción HTTP apropiada"""
    if isinstance(error, CoinGeckoAPIError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{message}: {str(error.detail)}"
        )
    elif isinstance(error, HTTPException):
        # Re-lanzar la excepción HTTP existente
        raise error
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{message}: Error interno del servidor"
        )