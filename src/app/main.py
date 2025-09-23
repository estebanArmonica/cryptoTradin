import json
from fastapi import FastAPI, HTTPException, Query, Request, Form, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from contextlib import contextmanager
import asyncpg, hashlib, secrets, smtplib, os, uuid, decimal, sqlite3, asyncio
from pydantic import BaseModel

# Importar routers
from app.apis.status import router as status_router
from app.apis.api_coingecko import router as coingecko_router
from app.apis.dashboard import router as dashboard_router
from app.apis.api_braintree import router as braintree_router
from app.apis.proton import router as proton_router  # Nuevo router de Proton
from app.services.trading_service import trading_service
from app.models.schemas import FilterRequest
from app.services.proton_service import proton_service  # Servicio de Proton

app = FastAPI(
    title="Crypto Trading Platform",
    description="Plataforma avanzada de trading de criptomonedas con procesamiento de pagos",
    version="2.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configuración de PostgreSQL
DATABASE_CONFIG = {
    "host": os.getenv("PGHOST"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "database": os.getenv("PGDATABASE"),
    "port": os.getenv("PGPORT"),
    "ssl": "require"
}

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Incluir routers
app.include_router(status_router, prefix="/api/v1", tags=["Status"])
app.include_router(coingecko_router, prefix="/api/v1", tags=["CoinGecko"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(braintree_router, prefix="/api", tags=["Payments"])
app.include_router(proton_router, prefix="/api", tags=["Proton Wallet"])  # Nuevo router de Proton

# Montar archivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

# Configurar templates
templates_dir = os.path.join(os.path.dirname(__file__), "..", "static", "templates")
templates = Jinja2Templates(directory=templates_dir)

# Configuración de la base de datos
DATABASE_NAME = "app.db"

# Context manager para manejar conexiones a la base de datos
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = asyncpg.connect(
            host=DATABASE_CONFIG['host'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            port=DATABASE_CONFIG['port']
        )
        yield conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise
    finally:
        if conn:
            conn.close()

async def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)

    try:
        # Tabla de usuarios
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Tabla de códigos de verificación
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        # Tabla de sesiones
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')

        # Tabla de transacciones
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            type TEXT NOT NULL,
            braintree_data TEXT,
            paypal_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')

        # Tabla de balances de usuarios
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_balances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            usd_balance DECIMAL(15, 2) DEFAULT 0.00,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
        
        # Tabla de configuraciones de notificación
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS notification_settings (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            email TEXT NOT NULL,
            notification_type TEXT DEFAULT 'both',
            enabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')
    finally:
        await conn.close()

# Inicializar la base de datos al iniciar
init_db()

# Configuración de email (debes configurar tus credenciales reales)
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email": "esteban.hernan.lobos@gmail.com",
    "password": "umksqvsxlzylcckr",
    "company_name": "Crypto Trading Platform",
    "support_email": "soporte@cryptotrading.com"
}

# Helper functions actualizadas para PostgreSQL
async def hash_password(password: str) -> str:
    """Hashea una contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash"""
    return await hash_password(plain_password) == hashed_password

def generate_verification_code() -> str:
    """Genera un código de verificación de 6 dígitos"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def send_verification_email(email: str, code: str):
    """Envía un código de verificación por email con diseño profesional"""
    try:
        # Crear mensaje MIME multipart
        msg = MIMEMultipart()
        msg['Subject'] = f'Código de Verificación - {EMAIL_CONFIG["company_name"]}'
        msg['From'] = f'{EMAIL_CONFIG["company_name"]} <{EMAIL_CONFIG["email"]}>'
        msg['To'] = email
        
        # Crear contenido HTML profesional
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Código de Verificación</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .code {{
                    background: #007bff;
                    color: white;
                    padding: 15px;
                    font-size: 24px;
                    font-weight: bold;
                    text-align: center;
                    border-radius: 5px;
                    margin: 20px 0;
                    letter-spacing: 3px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #856404;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{EMAIL_CONFIG["company_name"]}</h1>
                <p>Plataforma de Trading de Criptomonedas</p>
            </div>
            
            <div class="content">
                <h2>Código de Verificación</h2>
                <p>Estimado usuario,</p>
                <p>Hemos recibido una solicitud para acceder a su cuenta. Utilice el siguiente código de verificación:</p>
                
                <div class="code">{code}</div>
                
                <div class="warning">
                    <strong>⚠️ Importante:</strong> Este código es válido por 15 minutos. 
                    No comparta este código con nadie. Si no solicitó este código, 
                    por favor ignore este mensaje y contacte a soporte inmediatamente.
                </div>
                
                <p>Si tiene alguna pregunta, no dude en contactarnos en <a href="mailto:{EMAIL_CONFIG["support_email"]}">{EMAIL_CONFIG["support_email"]}</a></p>
                
                <p>Atentamente,<br>El equipo de {EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.</p>
                <p>Este es un mensaje automático, por favor no responda a este correo.</p>
            </div>
        </body>
        </html>
        """
        
        # Crear versión alternativa en texto plano
        text_content = f"""
        Código de Verificación - {EMAIL_CONFIG["company_name"]}
        
        Estimado usuario,
        
        Hemos recibido una solicitud para acceder a su cuenta. 
        Utilice el siguiente código de verificación:
        
        Código: {code}
        
        ⚠️ Importante: Este código es válido por 15 minutos. 
        No comparta este código con nadie. 
        
        Si tiene alguna pregunta, contacte a soporte: {EMAIL_CONFIG["support_email"]}
        
        Atentamente,
        El equipo de {EMAIL_CONFIG["company_name"]}
        
        © {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.
        """
        
        # Adjuntar ambas versionesxt_cont
        msg.attach(MIMEText(html_content, 'html'))
        
        # Enviar email
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando email: {e}")

def send_welcome_email(email: str, nombre: str, apellido: str):
    """Envía un email de bienvenida profesional al registrar una cuenta"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f'¡Bienvenido a {EMAIL_CONFIG["company_name"]}!'
        msg['From'] = f'{EMAIL_CONFIG["company_name"]} <{EMAIL_CONFIG["email"]}>'
        msg['To'] = email
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Bienvenido</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .features {{
                    margin: 20px 0;
                }}
                .feature {{
                    background: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #007bff;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>¡Bienvenido a {EMAIL_CONFIG["company_name"]}!</h1>
            </div>
            
            <div class="content">
                <h2>Hola {nombre} {apellido},</h2>
                
                <p>Nos complace darle la bienvenida a nuestra plataforma de trading de criptomonedas. 
                Su cuenta ha sido creada exitosamente y ya puede comenzar a operar.</p>
                
                <div class="features">
                    <h3>¿Qué puede hacer en nuestra plataforma?</h3>
                    
                    <div class="feature">
                        <strong>📊 Trading en tiempo real</strong><br>
                        Acceda a precios en tiempo real y realice operaciones de forma segura.
                    </div>
                    
                    <div class="feature">
                        <strong>💰 Gestión de fondos</strong><br>
                        Deposite y retire fondos de manera segura con múltiples métodos de pago.
                    </div>
                    
                    <div class="feature">
                        <strong>📈 Análisis avanzado</strong><br>
                        Utilice nuestras herramientas de análisis para tomar decisiones informadas.
                    </div>
                    
                    <div class="feature">
                        <strong>🔒 Seguridad garantizada</strong><br>
                        Su seguridad es nuestra prioridad. Utilizamos encriptación de grado bancario.
                    </div>
                </div>
                
                <p>Para comenzar, inicie sesión en su cuenta y complete la verificación de seguridad.</p>
                
                <p>Si tiene alguna pregunta o necesita asistencia, nuestro equipo de soporte está disponible 
                24/7 en <a href="mailto:{EMAIL_CONFIG["support_email"]}">{EMAIL_CONFIG["support_email"]}</a></p>
                
                <p>¡Le deseamos mucho éxito en sus operaciones!</p>
                
                <p>Atentamente,<br>El equipo de {EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.</p>
                <p>Este es un mensaje automático, por favor no responda a este correo.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        ¡Bienvenido a {EMAIL_CONFIG["company_name"]}!
        
        Hola {nombre} {apellido},
        
        Nos complace darle la bienvenida a nuestra plataforma de trading de criptomonedas. 
        Su cuenta ha sido creada exitosamente y ya puede comenzar a operar.
        
        Características principales:
        - 📊 Trading en tiempo real
        - 💰 Gestión de fondos segura
        - 📈 Análisis avanzado
        - 🔒 Seguridad garantizada
        
        Para comenzar, inicie sesión en su cuenta y complete la verificación de seguridad.
        
        Si tiene alguna pregunta, contacte a soporte: {EMAIL_CONFIG["support_email"]}
        
        ¡Le deseamos mucho éxito en sus operaciones!
        
        Atentamente,
        El equipo de {EMAIL_CONFIG["company_name"]}
        
        © {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando email de bienvenida: {e}")
        
# notificacion de cripto a email
def send_ema_notification_email(email: str, nombre: str, coin_id: str, signal_type: str, 
                               current_price: float, ema_value: float, confidence: str):
    """Envía notificación de señal EMA por email"""
    try:
        msg = MIMEMultipart()
        
        if signal_type == 'BUY':
            subject = f'🚀 Señal de COMPRA - {coin_id.upper()}'
            color = '#28a745'  # Verde
            action = "compra"
            reason = "El precio ha cruzado por encima de la EMA, indicando una tendencia alcista"
        else:
            subject = f'⚠️ Señal de VENTA - {coin_id.upper()}'
            color = '#dc3545'  # Rojo
            action = "venta"
            reason = "El precio ha cruzado por debajo de la EMA, indicando una tendencia bajista"
        
        msg['Subject'] = subject
        msg['From'] = f'{EMAIL_CONFIG["company_name"]} <{EMAIL_CONFIG["email"]}>'
        msg['To'] = email
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .signal-alert {{
                    background: {color}15;
                    border: 2px solid {color};
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .signal-icon {{
                    font-size: 48px;
                    margin-bottom: 15px;
                }}
                .signal-title {{
                    color: {color};
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .details {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 15px 0;
                }}
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }}
                .detail-row:last-child {{
                    border-bottom: none;
                }}
                .confidence-{confidence} {{
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .confidence-high {{ background: #28a745; color: white; }}
                .confidence-medium {{ background: #ffc107; color: black; }}
                .confidence-low {{ background: #6c757d; color: white; }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔔 Alerta de Trading</h1>
                <p>{EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="content">
                <h2>Hola {nombre},</h2>
                
                <p>Hemos detectado una señal de trading importante para {coin_id.upper()}:</p>
                
                <div class="signal-alert">
                    <div class="signal-icon">
                        {'📈' if signal_type == 'BUY' else '📉'}
                    </div>
                    <div class="signal-title">
                        SEÑAL DE {signal_type}
                    </div>
                    <p>Confianza: <span class="confidence-{confidence}">{confidence.upper()}</span></p>
                </div>
                
                <div class="details">
                    <h3>Detalles de la señal:</h3>
                    
                    <div class="detail-row">
                        <span>Criptomoneda:</span>
                        <span><strong>{coin_id.upper()}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span>Precio actual:</span>
                        <span><strong>${current_price:,.2f}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span>Valor EMA:</span>
                        <span><strong>${ema_value:,.2f}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span>Diferencia:</span>
                        <span><strong>{abs(((current_price - ema_value) / ema_value) * 100):.2f}%</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span>Razón:</span>
                        <span><strong>{reason}</strong></span>
                    </div>
                    
                    <div class="detail-row">
                        <span>Timestamp:</span>
                        <span><strong>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</strong></span>
                    </div>
                </div>
                
                <p><strong>Recomendación:</strong> Considerar {action} basado en el análisis técnico con EMA.</p>
                
                <p style="color: #666; font-size: 12px;">
                    ⚠️ Esta es una alerta automática. Por favor, realice su propio análisis 
                    antes de tomar cualquier decisión de inversión.
                </p>
                
                <p>Atentamente,<br>El equipo de {EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.</p>
                <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                <p><a href="/dashboard#notifications">Gestionar notificaciones</a></p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Alerta de Trading - {EMAIL_CONFIG["company_name"]}
        
        Hola {nombre},
        
        Señal de {signal_type} detectada para {coin_id.upper()}
        
        Detalles:
        - Criptomoneda: {coin_id.upper()}
        - Precio actual: ${current_price:,.2f}
        - Valor EMA: ${ema_value:,.2f}
        - Diferencia: {abs(((current_price - ema_value) / ema_value) * 100):.2f}%
        - Confianza: {confidence.upper()}
        - Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        
        Razón: {reason}
        
        Recomendación: Considerar {action} basado en el análisis técnico con EMA.
        
        ⚠️ Esta es una alerta automática. Realice su propio análisis antes de invertir.
        
        Atentamente,
        El equipo de {EMAIL_CONFIG["company_name"]}
        
        © {datetime.now().year} {EMAIL_CONFIG["company_name"]}
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando notificación EMA: {e}")

async def create_session(user_id: int) -> str:
    """Crea una nueva sesión para el usuario"""
    session_token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=24)
    
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        await conn.execute(
            "INSERT INTO sessions (user_id, session_token, expires_at) VALUES ($1, $2, $3)",
            user_id, session_token, expires_at
        )
    finally:
        await conn.close()
    
    return session_token

async def verify_session(session_token: str) -> Optional[int]:
    """Verifica si una sesión es válida y devuelve el user_id"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        result = await conn.fetchrow(
            "SELECT user_id FROM sessions WHERE session_token = $1 AND expires_at > $2",
            session_token, datetime.now()
        )
        return result['user_id'] if result else None
    finally:
        await conn.close()

async def get_user_balance(user_id: int) -> decimal.Decimal:
    """Obtiene el balance USD de un usuario"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        result = await conn.fetchrow(
            "SELECT usd_balance FROM user_balances WHERE user_id = $1",
            user_id
        )
        
        if result:
            return decimal.Decimal(str(result['usd_balance']))
        else:
            # Crear registro si no existe
            await conn.execute(
                "INSERT INTO user_balances (user_id, usd_balance) VALUES ($1, 0.00)",
            user_id
            )
            return decimal.Decimal('0.00')
    finally:
        await conn.close()

async def update_user_balance(user_id: int, amount: decimal.Decimal, transaction_type: str):
    """Actualiza el balance de un usuario"""
    current_balance = await get_user_balance(user_id)
    
    if transaction_type == 'deposit':
        new_balance = current_balance + amount
    elif transaction_type == 'withdrawal':
        if current_balance < amount:
            raise ValueError("Saldo insuficiente para el retiro")
        new_balance = current_balance - amount
    else:
        raise ValueError("Tipo de transacción no válido")
    
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        await conn.execute(
            "UPDATE user_balances SET usd_balance = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2",
            float(new_balance), user_id
        )
    finally:
        await conn.close()
    
    return new_balance

async def record_transaction(user_id: int, transaction_id: str, amount: decimal.Decimal, 
                           currency: str, status: str, transaction_type: str, 
                           braintree_data: dict = None, paypal_data: dict = None):
    """Registra una transacción en la base de datos"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        await conn.execute(
            """INSERT INTO transactions 
            (user_id, transaction_id, amount, currency, status, type, braintree_data, paypal_data) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            user_id, transaction_id, float(amount), currency, status, transaction_type, 
            json.dumps(braintree_data) if braintree_data else None,
            json.dumps(paypal_data) if paypal_data else None
        )
    finally:
        await conn.close()

# Dependencia para verificar autenticación (actualizada)
async def get_current_user(request: Request):
    """Obtiene el usuario actual desde la cookie de sesión"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    
    user_id = await verify_session(session_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")
    
    return user_id

# Endpoints de notificaciones de email
@app.post("/api/notifications/ema-alert")
async def send_ema_alert_notification(
    request: Request,
    user_id: int = Depends(get_current_user)
):
    """Envía una notificación de alerta EMA por email"""
    try:
        data = await request.json()
        
        coin_id = data.get("coin_id")
        signal_type = data.get("signal_type")
        current_price = data.get("current_price")
        ema_value = data.get("ema_value")
        confidence = data.get("confidence", "medium")
        
        # Validar datos
        if not all([coin_id, signal_type, current_price, ema_value]):
            raise HTTPException(status_code=400, detail="Faltan datos requeridos")
        
        if signal_type not in ['BUY', 'SELL']:
            raise HTTPException(status_code=400, detail="Tipo de señal inválido")
        
        # Obtener información del usuario
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            user = await conn.fetchrow(
                "SELECT nombre, apellido, correo FROM users WHERE id = $1",
                user_id
            )
            
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
                
            # Verificar configuración de notificaciones
            notification_settings = await conn.fetchrow(
                "SELECT email, notification_type, enabled FROM notification_settings WHERE user_id = $1",
                user_id
            )
            
            if not notification_settings or not notification_settings['enabled']:
                return {"success": False, "message": "Notificaciones desactivadas"}
                
            # Verificar tipo de notificación
            notification_type = notification_settings['notification_type']
            if (notification_type == 'buy' and signal_type != 'BUY') or \
               (notification_type == 'sell' and signal_type != 'SELL'):
                return {"success": False, "message": "Tipo de notificación no permitido"}
                
        finally:
            await conn.close()
        
        # Enviar email de notificación
        send_ema_notification_email(
            email=user['correo'],
            nombre=user['nombre'],
            coin_id=coin_id,
            signal_type=signal_type,
            current_price=current_price,
            ema_value=ema_value,
            confidence=confidence
        )
        
        return {
            "success": True,
            "message": "Notificación enviada exitosamente",
            "email": user['correo']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando notificación: {str(e)}")


# notificacion de configuracion para alertas
@app.post("/api/notifications/settings")
async def save_notification_settings(
    request: Request,
    user_id: int = Depends(get_current_user)
):
    """Guarda la configuración de notificaciones del usuario"""
    try:
        data = await request.json()
        
        email = data.get("email")
        notification_type = data.get("notification_type", "both")
        enabled = data.get("enabled", False)
        
        if not email:
            raise HTTPException(status_code=400, detail="Email es requerido")
        
        # Validar tipo de notificación
        if notification_type not in ['both', 'buy', 'sell']:
            notification_type = 'both'
        
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            # Insertar o actualizar configuración
            await conn.execute('''
                INSERT INTO notification_settings (user_id, email, notification_type, enabled)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    email = EXCLUDED.email,
                    notification_type = EXCLUDED.notification_type,
                    enabled = EXCLUDED.enabled,
                    updated_at = CURRENT_TIMESTAMP
            ''', user_id, email, notification_type, enabled)
            
        finally:
            await conn.close()
        
        return {
            "success": True,
            "message": "Configuración guardada exitosamente",
            "settings": {
                "email": email,
                "notification_type": notification_type,
                "enabled": enabled
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando configuración: {str(e)}")



# Endpoints de autenticación actualizados
@app.post("/api/register")
async def register_user(
    nombre: str = Form(...),
    apellido: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...)
):
    """Registra un nuevo usuario"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        # Verificar si el usuario ya existe
        existing_user = await conn.fetchrow(
            "SELECT id FROM users WHERE correo = $1", correo
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="El correo ya está registrado")
        
        # Crear usuario
        hashed_password = await hash_password(password)
        result = await conn.fetchrow(
            "INSERT INTO users (nombre, apellido, correo, password) VALUES ($1, $2, $3, $4) RETURNING id",
            nombre, apellido, correo, hashed_password
        )
        user_id = result['id']
        
        # Generar código de verificación (pero no enviarlo por email)
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=15)
        await conn.execute(
            "INSERT INTO verification_codes (user_id, code, expires_at) VALUES ($1, $2, $3)",
            user_id, code, expires_at
        )
        
        # Crear balance inicial
        await conn.execute(
            "INSERT INTO user_balances (user_id, usd_balance) VALUES ($1, 0.00)",
            user_id
        )
        
    finally:
        await conn.close()
    
    # Enviar email de bienvenida en lugar del código de verificación
    send_welcome_email(correo, nombre, apellido)
    
    # Redirigir automáticamente al login después del registro
    response = JSONResponse(
        content={
            "message": "Usuario registrado exitosamente. Redirigiendo al login...",
            "redirect": "/"
        },
        status_code=200
    )
    
    return response

@app.post("/api/login")
async def login_user(
    correo: str = Form(...),
    password: str = Form(...)
):
    """Inicia el proceso de login enviando un código de verificación"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        # Verificar credenciales
        user = await conn.fetchrow(
            "SELECT id, password FROM users WHERE correo = $1", correo
        )
        
        if not user or not await verify_password(password, user['password']):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        user_id = user['id']
        
        # Generar código de verificación
        code = generate_verification_code()
        expires_at = datetime.now() + timedelta(minutes=15)
        await conn.execute(
            "INSERT INTO verification_codes (user_id, code, expires_at) VALUES ($1, $2, $3)",
            user_id, code, expires_at
        )
        
    finally:
        await conn.close()
    
    # Enviar código por email
    send_verification_email(correo, code)
    
    return {"message": "Código de verificación enviado a tu email"}

@app.post("/api/verify-code")
async def verify_code(
    correo: str = Form(...),
    code: str = Form(...)
):
    """Verifica el código de verificación y crea una sesión"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        # Obtener usuario
        user = await conn.fetchrow("SELECT id FROM users WHERE correo = $1", correo)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user_id = user['id']
        
        # Verificar código
        valid_code = await conn.fetchrow(
            "SELECT id FROM verification_codes WHERE user_id = $1 AND code = $2 AND expires_at > $3 AND used = 0",
            user_id, code, datetime.now()
        )
        
        if not valid_code:
            raise HTTPException(status_code=401, detail="Código inválido or expirado")
        
        # Marcar código como usado
        await conn.execute(
            "UPDATE verification_codes SET used = 1 WHERE id = $1",
            valid_code['id']
        )
        
    finally:
        await conn.close()
    
    # Crear sesión
    session_token = await create_session(user_id)
    
    response = JSONResponse({
        "message": "Login exitoso",
        "redirect": "/dashboard"
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=24*60*60,
        samesite="lax"
    )
    
    return response

@app.post("/api/logout")
async def logout_user(request: Request):
    """Cierra la sesión del usuario"""
    session_token = request.cookies.get("session_token")
    if session_token:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            await conn.execute(
                "DELETE FROM sessions WHERE session_token = $1",
                session_token
            )
        finally:
            await conn.close()
    
    response = JSONResponse({"message": "Logout exitoso"})
    response.delete_cookie("session_token")
    return response

# Nuevo endpoint para obtener balance del usuario (actualizado)
@app.get("/api/user/balance")
async def get_balance(user_id: int = Depends(get_current_user)):
    """Obtiene el balance USD del usuario autenticado"""
    try:
        balance = await get_user_balance(user_id)
        return {
            "success": True,
            "balance": float(balance),
            "currency": "USD",
            "user_id": user_id
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo balance: {str(e)}"
        )

# Páginas de autenticación
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página principal de login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Página de registro"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request, user_id: int = Depends(get_current_user)):
    """Página de trading (requiere autenticación)"""
    return templates.TemplateResponse("trading.html", {"request": request})

@app.get("/paypal-transacc", response_class=HTMLResponse)
async def paypal_transaction_page(request: Request, user_id: int = Depends(get_current_user)):
    """Página de PayPal (requiere autenticación)"""
    return templates.TemplateResponse("paypal-transacc.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: int = Depends(get_current_user)):
    """Dashboard principal (requiere autenticación)"""
    # Obtener información del usuario desde la base de datos
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        user = await conn.fetchrow(
            "SELECT nombre, apellido, correo FROM users WHERE id = $1",
            user_id
        )
    finally:
        await conn.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "user": {
            "nombre": user['nombre'],
            "apellido": user['apellido'],
            "correo": user['correo']
        }
    })

@app.get("/wallet", response_class=HTMLResponse)
async def wallet_page(request: Request, user_id: int = Depends(get_current_user)):
    """Página de wallet (requiere autenticación)"""
    return templates.TemplateResponse("wallet.html", {
        "request": request,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })
    
# endpoint de perfil
# Añade este modelo para la actualización de perfil
class UserUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    correo: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

# Añade este endpoint para la página de perfil
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user_id: int = Depends(get_current_user)):
    """Página de perfil de usuario (requiere autenticación)"""
    # Obtener información del usuario desde la base de datos
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        user = await conn.fetchrow(
            "SELECT nombre, apellido, correo, created_at FROM users WHERE id = $1",
            user_id
        )
        
        # Obtener balances
        usd_balance = await get_user_balance(user_id)
        crypto_balances = await get_all_crypto_balances(user_id)
        
    finally:
        await conn.close()
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": {
            "id": user_id,
            "nombre": user['nombre'],
            "apellido": user['apellido'],
            "correo": user['correo'],
            "created_at": user['created_at']
        },
        "balances": {
            "usd": float(usd_balance),
            "crypto": crypto_balances.get('balances', []) if isinstance(crypto_balances, dict) else []
        }
    })

# Añade este endpoint para actualizar el perfil
@app.post("/api/user/profile/update")
async def update_user_profile(
    request: Request,
    user_id: int = Depends(get_current_user)
):
    """Actualiza el perfil del usuario"""
    try:
        data = await request.json()
        update_data = UserUpdateRequest(**data)
        
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            # Verificar contraseña actual si se quiere cambiar la contraseña
            if update_data.new_password:
                if not update_data.current_password:
                    raise HTTPException(status_code=400, detail="Contraseña actual requerida")
                
                user = await conn.fetchrow(
                    "SELECT password FROM users WHERE id = $1", user_id
                )
                
                if not await verify_password(update_data.current_password, user['password']):
                    raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
                
                # Hashear nueva contraseña
                new_hashed_password = await hash_password(update_data.new_password)
                await conn.execute(
                    "UPDATE users SET password = $1 WHERE id = $2",
                    new_hashed_password, user_id
                )
            
            # Actualizar otros campos
            update_fields = {}
            if update_data.nombre:
                update_fields['nombre'] = update_data.nombre
            if update_data.apellido:
                update_fields['apellido'] = update_data.apellido
            if update_data.correo:
                # Verificar si el nuevo correo ya existe
                existing_user = await conn.fetchrow(
                    "SELECT id FROM users WHERE correo = $1 AND id != $2",
                    update_data.correo, user_id
                )
                if existing_user:
                    raise HTTPException(status_code=400, detail="El correo ya está en uso")
                update_fields['correo'] = update_data.correo
            
            if update_fields:
                set_clause = ", ".join([f"{field} = ${i+1}" for i, field in enumerate(update_fields.keys())])
                values = list(update_fields.values()) + [user_id]
                await conn.execute(
                    f"UPDATE users SET {set_clause} WHERE id = ${len(update_fields) + 1}",
                    *values
                )
            
        finally:
            await conn.close()
        
        return {
            "success": True,
            "message": "Perfil actualizado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando perfil: {str(e)}")

# 🔥🔥🔥 ENDPOINTS DE TRADING MEJORADOS
price_alerts: Dict[str, List[Dict]] = {}
active_monitoring: Dict[str, bool] = {}

@app.get("/api/v1/trading/test", tags=["Trading"])
async def trading_test(user_id: int = Depends(get_current_user)):
    """Endpoint de prueba para trading"""
    return {
        "message": "✅ Trading endpoint is working!", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.get("/api/v1/trading/coins/available", tags=["Trading"])
async def get_available_coins(limit: int = Query(100, ge=1, le=500), user_id: int = Depends(get_current_user)):
    """Obtiene todas las criptomonedas disponibles con paginación"""
    try:
        coins = await trading_service.get_available_coins()
        return {
            "total_coins": len(coins),
            "coins": coins[:limit],
            "limit": limit,
            "page": 1,
            "has_more": len(coins) > limit,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Fallback con monedas populares
        popular_coins = [
            {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap_rank": 1},
            {"id": "ethereum", "symbol": "eth", "name": "Ethereum", "market_cap_rank": 2},
            {"id": "tether", "symbol": "usdt", "name": "Tether", "market_cap_rank": 3},
            {"id": "binancecoin", "symbol": "bnb", "name": "BNB", "market_cap_rank": 4},
            {"id": "solana", "symbol": "sol", "name": "Solana", "market_cap_rank": 5},
            {"id": "ripple", "symbol": "xrp", "name": "XRP", "market_cap_rank": 6},
            {"id": "usd-coin", "symbol": "usdc", "name": "USD Coin", "market_cap_rank": 7},
            {"id": "cardano", "symbol": "ada", "name": "Cardano", "market_cap_rank": 8},
            {"id": "dogecoin", "symbol": "doge", "name": "Dogecoin", "market_cap_rank": 9},
            {"id": "avalanche-2", "symbol": "avax", "name": "Avalanche", "market_cap_rank": 10}
        ]
        return {
            "total_coins": len(popular_coins),
            "coins": popular_coins[:limit],
            "limit": limit,
            "page": 1,
            "has_more": False,
            "timestamp": datetime.now().isoformat(),
            "note": "Using popular coins list (fallback mode)"
        }

@app.get("/api/v1/trading/{coin_id}/price", tags=["Trading"])
async def get_current_price(coin_id: str, user_id: int = Depends(get_current_user)):
    """Obtiene el precio actual de una criptomoneda con información extendida"""
    try:
        price = await trading_service.get_current_price(coin_id)
        if price is None:
            raise HTTPException(status_code=404, detail="Precio no disponible")
        
        # Obtener información adicional del mercado
        market_data = trading_service.client.get_coins_markets(
            vs_currency='usd',
            ids=coin_id,
            per_page=1,
            page=1
        )
        
        market_info = market_data[0] if market_data else {}
        
        return {
            "coin_id": coin_id,
            "name": market_info.get('name', coin_id),
            "symbol": market_info.get('symbol', '').upper(),
            "price_usd": price,
            "price_change_24h": market_info.get('price_change_percentage_24h', 0),
            "market_cap": market_info.get('market_cap', 0),
            "market_cap_rank": market_info.get('market_cap_rank', 0),
            "volume_24h": market_info.get('total_volume', 0),
            "high_24h": market_info.get('high_24h', 0),
            "low_24h": market_info.get('low_24h', 0),
            "timestamp": datetime.now().isoformat(),
            "last_updated": market_info.get('last_updated', datetime.now().isoformat())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo precio: {str(e)}")

@app.get("/api/v1/trading/{coin_id}/signals", tags=["Trading"])  
async def get_trading_signals(
    coin_id: str, 
    time_frame: str = Query("24h", enum=["1h", "24h", "7d", "30d"]),
    user_id: int = Depends(get_current_user)
):
    """Señales de trading para una criptomoneda con análisis real"""
    try:
        # Obtener datos históricos para análisis
        days = 7 if time_frame == "1h" else 30 if time_frame == "24h" else 90
        historical_data = await trading_service.get_historical_data(coin_id, days)
        
        if not historical_data:
            raise HTTPException(status_code=404, detail="Datos históricos no disponibles")
        
        # Calcular métricas
        metrics = trading_service.calculate_metrics(historical_data, time_frame)
        if not metrics:
            raise HTTPException(status_code=404, detail="No se pudieron calcular métricas")
        
        # Generar señales
        signals = trading_service.generate_trading_signals(metrics, time_frame)
        
        # Obtener precio actual
        price_data = await get_current_price(coin_id)
        
        return {
            "signals": signals,
            "metrics": metrics,
            "current_price": price_data["price_usd"],
            "coin_id": coin_id,
            "time_frame": time_frame,
            "timestamp": datetime.now().isoformat(),
            "data_points": len(historical_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando señales: {str(e)}")

@app.get("/api/v1/trading/{coin_id}/metrics", tags=["Trading"])
async def get_trading_metrics(
    coin_id: str, 
    days: int = Query(7, ge=1, le=365),
    time_frame: str = Query("24h", enum=["1h", "24h", "7d"]),
    user_id: int = Depends(get_current_user)
):
    """Métricas de trading detalladas"""
    try:
        historical_data = await trading_service.get_historical_data(coin_id, days)
        
        if not historical_data:
            raise HTTPException(status_code=404, detail="Datos históricos no disponibles")
        
        metrics = trading_service.calculate_metrics(historical_data, time_frame)
        
        if not metrics:
            raise HTTPException(status_code=404, detail="No se pudieron calcular métricas")
        
        # Obtener información de precio actual
        current_price = await trading_service.get_current_price(coin_id)
        
        return {
            "coin_id": coin_id,
            "time_frame": time_frame,
            "days_analyzed": days,
            "current_price": current_price,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
            "data_points": len(historical_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")

@app.get("/api/v1/trading/{coin_id}/calculate", tags=["Trading"])
async def calculate_crypto_value(
    coin_id: str,
    amount: float = Query(..., description="Cantidad a calcular", ge=0.00000001),
    vs_currency: str = Query("usd", description="Moneda para la conversión"),
    user_id: int = Depends(get_current_user)
):
    """Calcula el valor en USD u otra moneda"""
    try:
        price_data = await trading_service.get_current_price(coin_id)
        if price_data is None:
            raise HTTPException(status_code=404, detail="Precio no disponible")
        
        # Si se solicita otra moneda, obtener la conversión
        if vs_currency != "usd":
            try:
                conversion_data = trading_service.client.get_price(
                    ids=coin_id, 
                    vs_currencies=vs_currency
                )
                price = conversion_data.get(coin_id, {}).get(vs_currency, price_data)
            except:
                price = price_data
        else:
            price = price_data
        
        return {
            "coin_id": coin_id,
            "amount": amount,
            "price_per_coin": price,
            "total_value": amount * price,
            "currency": vs_currency.upper(),
            "timestamp": datetime.now().isoformat(),
            "exchange_rate": price
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando valor: {str(e)}")

# 🔥 NUEVOS ENDPOINTS PARA EL DASHBOARD MEJORADO

@app.get("/api/v1/market/performance", tags=["Dashboard"])
async def get_market_performance(user_id: int = Depends(get_current_user)):
    """Obtiene el rendimiento general del mercado"""
    try:
        global_data = trading_service.client.get_global_data()
        
        # Calcular métricas adicionales
        total_market_cap = global_data.get('total_market_cap', {}).get('usd', 0)
        total_volume = global_data.get('total_volume', {}).get('usd', 0)
        
        return {
            "total_market_cap": total_market_cap,
            "total_volume": total_volume,
            "volume_market_cap_ratio": (total_volume / total_market_cap * 100) if total_market_cap > 0 else 0,
            "market_cap_change_24h": global_data.get('market_cap_change_percentage_24h_usd', 0),
            "active_cryptocurrencies": global_data.get('active_cryptocurrencies', 0),
            "upcoming_icos": global_data.get('upcoming_icos', 0),
            "ongoing_icos": global_data.get('ongoing_icos', 0),
            "ended_icos": global_data.get('ended_icos', 0),
            "markets": global_data.get('markets', 0),
            "bitcoin_dominance": global_data.get('market_cap_percentage', {}).get('btc', 0),
            "ethereum_dominance": global_data.get('market_cap_percentage', {}).get('eth', 0),
            "timestamp": datetime.now().isoformat(),
            "last_updated": global_data.get('updated_at', datetime.now().timestamp())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo rendimiento del mercado: {str(e)}")

@app.get("/api/v1/coins/top-gainers", tags=["Dashboard"])
async def get_top_gainers(limit: int = Query(10, ge=1, le=50), user_id: int = Depends(get_current_user)):
    """Obtiene las criptomonedas con mayor ganancia"""
    try:
        market_data = trading_service.client.get_coins_markets(
            vs_currency='usd',
            order='price_change_percentage_24h_desc',
            per_page=limit,
            page=1,
            price_change_percentage='24h'
        )
        
        return {
            "gainers": market_data,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo top gainers: {str(e)}")

@app.get("/api/v1/coins/top-losers", tags=["Dashboard"])
async def get_top_losers(limit: int = Query(10, ge=1, le=50), user_id: int = Depends(get_current_user)):
    """Obtiene las criptomonedas con mayor pérdida"""
    try:
        market_data = trading_service.client.get_coins_markets(
            vs_currency='usd',
            order='price_change_percentage_24h_asc',
            per_page=limit,
            page=1,
            price_change_percentage='24h'
        )
        
        return {
            "losers": market_data,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo top losers: {str(e)}")

@app.get("/api/v1/coins/trending", tags=["Dashboard"])
async def get_trending_coins(limit: int = Query(10, ge=1, le=20), user_id: int = Depends(get_current_user)):
    """Obtiene las criptomonedas trending"""
    try:
        # Usar el endpoint de búsqueda para obtener trending
        trending_data = trading_service.client.get_search_trending()
        
        coins = []
        for item in trending_data.get('coins', [])[:limit]:
            coin_info = item.get('item', {})
            coins.append({
                "id": coin_info.get('id'),
                "name": coin_info.get('name'),
                "symbol": coin_info.get('symbol'),
                "market_cap_rank": coin_info.get('market_cap_rank'),
                "thumb": coin_info.get('thumb'),
                "price_btc": coin_info.get('price_btc')
            })
        
        return {
            "trending": coins,
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo trending coins: {str(e)}")

# 🔥 NUEVO ENDPOINT PARA SIMULACIÓN DE TRADING
@app.get("/simulacion", response_class=HTMLResponse)
async def trading_simulation(request: Request, user_id: int = Depends(get_current_user)):
    """Página de simulación de trading"""
    return templates.TemplateResponse("simulacion.html", {
        "request": request,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })

# 🔥 NUEVO ENDPOINT PARA COMPRA CON PAYPAL - ACTUALIZADO
@app.post("/api/paypal/buy-crypto")
async def buy_crypto_with_paypal(
    request: Request,
    user_id: int = Depends(get_current_user)
):
    """Compra criptomonedas usando PayPal como método de pago"""
    try:
        # Obtener datos de la solicitud
        data = await request.json()
        payment_id = data.get("paymentID")
        payer_id = data.get("payerID")
        amount = decimal.Decimal(str(data.get("amount", 0)))
        coin_id = data.get("coin_id")
        coin_amount = decimal.Decimal(str(data.get("coin_amount", 0)))
        
        # Validar los datos
        if amount <= 0 or coin_amount <= 0:
            raise HTTPException(status_code=400, detail="Monto inválido")
        
        if not coin_id:
            raise HTTPException(status_code=400, detail="Coin ID es requerido")
        
        # Obtener el precio actual de la criptomoneda
        current_price = await trading_service.get_current_price(coin_id)
        if current_price is None:
            raise HTTPException(status_code=404, detail="No se pudo obtener el precio de la criptomoneda")
        
        # Verificar que el monto coincida con el cálculo
        calculated_amount = coin_amount * decimal.Decimal(str(current_price))
        if abs(amount - calculated_amount) > decimal.Decimal('0.01'):
            raise HTTPException(status_code=400, detail="El monto no coincide con el cálculo")
        
        # LÓGICA REAL DE PAYPAL - Ejecutar el pago
        payment = Payment.find(payment_id)
        
        # Verificar que el pago esté aprobado
        if payment.state != 'approved':
            raise HTTPException(status_code=400, detail="El pago no fue aprobado por PayPal")
        
        # Verificar que el monto coincida
        payment_amount = decimal.Decimal(payment.transactions[0].amount.total)
        if payment_amount != amount:
            raise HTTPException(status_code=400, detail="El monto no coincide con la transacción de PayPal")
        
        # Ejecutar el pago
        if payment.execute({"payer_id": payer_id}):
            # Registrar la compra de criptomonedas
            transaction_id = f"paypal_buy_{payment_id}"
            
            # Registrar la transacción
            await record_transaction(
                user_id=user_id,
                transaction_id=transaction_id,
                amount=amount,
                currency="USD",
                status="completed",
                transaction_type="buy_crypto",
                paypal_data={
                    "payment_id": payment_id,
                    "payer_id": payer_id,
                    "coin_id": coin_id,
                    "coin_amount": float(coin_amount),
                    "price_per_coin": float(current_price),
                    "total_amount": float(amount),
                    "payment_state": payment.state,
                    "create_time": payment.create_time,
                    "update_time": payment.update_time
                }
            )
            
            # Actualizar el balance de criptomonedas del usuario
            await update_crypto_balance(user_id, coin_id, coin_amount)
            
            # Obtener información del usuario para el email
            conn = await asyncpg.connect(**DATABASE_CONFIG)
            try:
                user = await conn.fetchrow(
                    "SELECT nombre, apellido, correo FROM users WHERE id = $1",
                    user_id
                )
            finally:
                await conn.close()
            
            # Enviar email de confirmación
            if user:
                send_purchase_confirmation_email(
                    user['correo'],
                    user['nombre'],
                    user['apellido'],
                    coin_id,
                    coin_amount,
                    current_price,
                    amount,
                    transaction_id
                )
            
            return {
                "success": True,
                "message": "Compra realizada exitosamente",
                "transaction_id": transaction_id,
                "coin_id": coin_id,
                "coin_amount": float(coin_amount),
                "price_per_coin": float(current_price),
                "total_amount": float(amount),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Error al ejecutar el pago
            error_details = payment.error if hasattr(payment, 'error') else "Error desconocido"
            raise HTTPException(status_code=400, detail=f"Error al ejecutar el pago: {error_details}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando compra: {str(e)}")

# 🔥 NUEVA FUNCIÓN PARA ACTUALIZAR BALANCE DE CRIPTOMONEDAS
async def update_crypto_balance(user_id: int, coin_id: str, amount: decimal.Decimal):
    """Actualiza el balance de criptomonedas de un usuario"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        # Verificar si existe la tabla de balances de criptomonedas, si no crearla
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS crypto_balances (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                coin_id TEXT NOT NULL,
                balance DECIMAL(20, 8) DEFAULT 0.00000000,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, coin_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Insertar o actualizar el balance
        await conn.execute('''
            INSERT INTO crypto_balances (user_id, coin_id, balance)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, coin_id)
            DO UPDATE SET 
                balance = crypto_balances.balance + EXCLUDED.balance,
                updated_at = CURRENT_TIMESTAMP
        ''', user_id, coin_id, float(amount))
        
    except Exception as e:
        print(f"Error actualizando balance crypto: {e}")
        raise
    finally:
        await conn.close()

# 🔥 NUEVA FUNCIÓN PARA ENVIAR EMAIL DE CONFIRMACIÓN
def send_purchase_confirmation_email(email, nombre, apellido, coin_id, coin_amount, price_per_coin, total_amount, transaction_id):
    """Envía un email de confirmación de compra de criptomonedas"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f'Confirmación de Compra - {coin_id.upper()}'
        msg['From'] = f'{EMAIL_CONFIG["company_name"]} <{EMAIL_CONFIG["email"]}>'
        msg['To'] = email
        
        # Formatear cantidades
        formatted_amount = f"{coin_amount:.8f}".rstrip('0').rstrip('.')
        formatted_price = f"${price_per_coin:,.2f}"
        formatted_total = f"${total_amount:,.2f}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirmación de Compra</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .transaction-details {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #007bff;
                }}
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }}
                .detail-row:last-child {{
                    border-bottom: none;
                }}
                .detail-label {{
                    color: #666;
                    font-weight: 500;
                }}
                .detail-value {{
                    font-weight: 600;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }}
                .crypto-amount {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #007bff;
                    text-align: center;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>¡Compra Confirmada!</h1>
                <p>{EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="content">
                <h2>Hola {nombre} {apellido},</h2>
                
                <p>Tu compra de criptomonedas ha sido procesada exitosamente. 
                Aquí están los detalles de tu transacción:</p>
                
                <div class="transaction-details">
                    <div class="crypto-amount">{formatted_amount} {coin_id.upper()}</div>
                    
                    <div class="detail-row">
                        <span class="detail-label">ID de Transacción:</span>
                        <span class="detail-value">{transaction_id}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">Criptomoneda:</span>
                        <span class="detail-value">{coin_id.upper()}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">Cantidad:</span>
                        <span class="detail-value">{formatted_amount}</span>
                    </div>
                    
                                        <div class="detail-row">
                        <span class="detail-label">Precio por unidad:</span>
                        <span class="detail-value">{formatted_price}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">Total pagado:</span>
                        <span class="detail-value">{formatted_total}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">Fecha y hora:</span>
                        <span class="detail-value">{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</span>
                    </div>
                    
                    <div class="detail-row">
                        <span class="detail-label">Estado:</span>
                        <span class="detail-value" style="color: #28a745;">Completado</span>
                    </div>
                </div>
                
                <p>Los fondos han sido acreditados a tu cuenta y ya están disponibles para operar.</p>
                
                <p>Si tienes alguna pregunta o necesitas asistencia, no dudes en contactarnos 
                en <a href="mailto:{EMAIL_CONFIG["support_email"]}">{EMAIL_CONFIG["support_email"]}</a></p>
                
                <p>¡Gracias por confiar en nosotros!</p>
                
                <p>Atentamente,<br>El equipo de {EMAIL_CONFIG["company_name"]}</p>
            </div>
            
            <div class="footer">
                <p>© {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.</p>
                <p>Este es un mensaje automático, por favor no responda a este correo.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Confirmación de Compra - {EMAIL_CONFIG["company_name"]}
        
        Hola {nombre} {apellido},
        
        Tu compra de criptomonedas ha sido procesada exitosamente.
        
        Detalles de la transacción:
        - ID de Transacción: {transaction_id}
        - Criptomoneda: {coin_id.upper()}
        - Cantidad: {formatted_amount}
        - Precio por unidad: {formatted_price}
        - Total pagado: {formatted_total}
        - Fecha y hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        - Estado: Completado
        
        Los fondos han sido acreditados a tu cuenta y ya están disponibles para operar.
        
        Si tienes alguna pregunta, contacta a soporte: {EMAIL_CONFIG["support_email"]}
        
        Atentamente,
        El equipo de {EMAIL_CONFIG["company_name"]}
        
        © {datetime.now().year} {EMAIL_CONFIG["company_name"]}. Todos los derechos reservados.
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando email de confirmación: {e}")

# 🔥 NUEVO ENDPOINT PARA OBTENER BALANCE DE CRIPTOMONEDAS
@app.get("/api/user/crypto-balance/{coin_id}")
async def get_crypto_balance(coin_id: str, user_id: int = Depends(get_current_user)):
    """Obtiene el balance de una criptomoneda específica para el usuario autenticado"""
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            # Verificar si la tabla existe
            table_exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'crypto_balances'
                )
            ''')
            
            if not table_exists:
                return {"balance": 0.0, "coin_id": coin_id, "user_id": user_id}
            
            # Obtener el balance
            result = await conn.fetchrow(
                "SELECT balance FROM crypto_balances WHERE user_id = $1 AND coin_id = $2",
                user_id, coin_id
            )
            
            balance = decimal.Decimal(str(result['balance'])) if result else decimal.Decimal('0.0')
            
            return {
                "success": True,
                "balance": float(balance),
                "coin_id": coin_id,
                "user_id": user_id
            }
            
        finally:
            await conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo balance de criptomoneda: {str(e)}"
        )

# 🔥 NUEVO ENDPOINT PARA OBTENER TODOS LOS BALANCES DE CRIPTO
@app.get("/api/user/crypto-balances")
async def get_all_crypto_balances(user_id: int = Depends(get_current_user)):
    """Obtiene todos los balances de criptomonedas para el usuario autenticado"""
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        try:
            # Verificar si la tabla existe
            table_exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'crypto_balances'
                )
            ''')
            
            if not table_exists:
                return {"balances": [], "user_id": user_id}
            
            # Obtener todos los balances
            results = await conn.fetch(
                "SELECT coin_id, balance FROM crypto_balances WHERE user_id = $1",
                user_id
            )
            
            balances = []
            for row in results:
                if row['balance'] > 0:
                    balances.append({
                        "coin_id": row['coin_id'],
                        "balance": float(row['balance']),
                        "value_usd": 0.0  # Se puede calcular con los precios actuales
                    })
            
            # Obtener precios actuales para calcular el valor en USD
            for balance in balances:
                try:
                    price = await trading_service.get_current_price(balance['coin_id'])
                    if price:
                        balance['value_usd'] = float(balance['balance'] * decimal.Decimal(str(price)))
                except:
                    balance['value_usd'] = 0.0
            
            return {
                "success": True,
                "balances": balances,
                "user_id": user_id,
                "total_value_usd": sum(b['value_usd'] for b in balances)
            }
            
        finally:
            await conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo balances de criptomonedas: {str(e)}"
        )

# Endpoints de utilidad y debug
@app.get("/api/debug/routes", include_in_schema=False)
async def debug_routes(user_id: int = Depends(get_current_user)):
    """Muestra todas las rutas disponibles"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": getattr(route, "methods", []),
                "name": getattr(route, "name", "Unknown"),
                "tags": getattr(route, "tags", [])
            })
    return {"routes": sorted(routes, key=lambda x: x["path"])}

@app.get("/api/health", tags=["Status"])
async def health_check():
    """Health check del servicio"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "trading": "operational",
            "api": "operational",
            "database": "n/a"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Evento de inicialización"""
    try:
        # Inicializar base de datos
        await init_db()
        print("✅ PostgreSQL database initialized successfully")

        # Inicializar servicio de trading
        await trading_service.initialize()
        print("✅ Trading service initialized successfully")
        
        # Inicializar servicio de Proton Wallet
        await proton_service.initialize()
        print("✅ Proton Wallet service initialized successfully")
        
        print("✅ Dashboard endpoints registered")
        print("✅ API version 2.0.0 is ready")
        print("✅ Simulación disponible en: /simulacion")
        print("✅ Payment processing available via Braintree and PayPal")
        print("✅ Proton Wallet integration ready")
    except Exception as e:
        print(f"⚠️  Error initializing services: {e}")

@app.get("/api", tags=["Info"])
async def api_info():
    """Información de la API"""
    return {
        "message": "Crypto Trading Platform API", 
        "version": "2.0.0",
        "endpoints": {
            "docs": "/api/docs",
            "redoc": "/api/redoc",
            "health": "/api/health",
            "status": "/api/v1/status",
            "dashboard": "/dashboard",
            "wallet": "/wallet",
            "simulacion": "/simulacion",
            "trading": "/api/v1/trading/test",
            "market_data": "/api/v1/market/performance",
            "coins": "/api/v1/trading/coins/available",
            "analysis": "/api/v1/dashboard/analysis/{coin_id}",
            "global_metrics": "/api/v1/dashboard/global-metrics",
            "top_opportunities": "/api/v1/dashboard/top-opportunities",
            "top_gainers": "/api/v1/coins/top-gainers",
            "top_losers": "/api/v1/coins/top-losers",
            "trending": "/api/v1/coins/trending",
            "proton_wallet": {
                "connect": "/api/proton/connect",
                "balance": "/api/proton/balance/{account_name}",
                "transfer": "/api/proton/transfer",
                "tokens": "/api/proton/tokens/{account_name}"
            },
            "payments": {
                "client_token": "/api/braintree/client-token",
                "process_payment": "/api/braintree/process-payment",
                "withdraw": "/api/braintree/withdraw",
                "paypal_payment": "/api/paypal/process-payment",
                "paypal_buy_crypto": "/api/paypal/buy-crypto"
            }
        },
        "timestamp": datetime.now().isoformat()
    }

# Manejo de errores global
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path
        }
    )