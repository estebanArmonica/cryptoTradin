from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_status():
    """Verifica el estado del servicio"""
    return {"status": "OK", "message": "Service is running"}