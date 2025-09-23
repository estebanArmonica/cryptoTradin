## Crypto Trading 🌱💻

Este es un proyecto de una página web en el cual podra realizar compra y venta de criptomonedas
con la API de coingecko

## Tecnologías

- Python 3.12.6
- FastAPI 0.116.1
- HTML5
- CSS3
- JavaScripts
- Bootstrap 5.0.2
- PostgreSQL 17

## Entorno Local

Lo primero que tienes que hacer para poder ejecutar el proyecto es clonar el repositorio en tu computadora:

```bash
git clone https://github.com/estebanArmonica/cryptoTradin.git
cd src
```

Ahora que clonamos el repositorio, tenemos que crear un entorno virtual de Python para la instalación de dependencias del proyecto:

```bash
python -m virtualenv venv

# Windows
venv\Scripts\activate

# Linux o Mac
source venv/bin/activate
```

> [!NOTE]
> Si quieres utilizar virtualenv, tienes que instalarlo con pip `pip install virtualenv`.

### Instalación de Dependencias

Con el entorno virtual de Python activado y configurado, instalamos las dependencias del proyecto:

    pip install -r requirements.txt

Opcional también puede instalar las dependencias de node

    npm install -g requirementsnpm.txt

### Variables de Entorno

Ahora tenemos que configurar las variables de entorno, en la carpeta del proyecto debera crear un `.env` para utilizar y llamar a esas variables de entorno en python:

### Migraciones

Con las variables de entorno configuradas, tenemos que levantar el proyecto una vez dentro de la carpeta src:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Ejecución

Listo!!, si todo salio bien ya tienes el proyecto corriento en tu computadora de manera local
