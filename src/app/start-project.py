from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .apis import status, api_coingecko
from .config.metrics import setup_metrics
from .core.config import settings
import os

# creamos la instacia de FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME, 
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# Mostramos el archivo statico 
folder = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=folder+"/../static",html=True), name="static")


# Configura la carpeta de templates
templates = Jinja2Templates(directory=os.path.join(folder, "../static/templates"))

# Ruta para visualizar el dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# configuramos las rutas
app.include_router(
    status.router,
    prefix=settings.API_PREFIX,
    tags=["Status"]
)

app.include_router(
    api_coingecko.router,
    prefix=settings.API_PREFIX,
    tags=["Cryptocurrencies"]
)