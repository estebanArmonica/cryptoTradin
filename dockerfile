# Usaremos una imagen de Python 3.12.6 en su version 'slim' lo cual es más ligera que la completa
FROM python:3.12.6-slim

# Realizamos manejo de variables de entorno
# ARG: Nos define una variable que se puede pasar al construir la imagen
# ENV: Establece una variable de entorno dentro del contenedor
ARG NODE_ENV
ENV NODE_ENV=$NODE_ENV

# Creamos un directorio de trabajo y cambiamos el directorio dentro del contenedor '/src'
# Primero actualizamos la lista de dependencias 'apt-get update'
# Segundo instala librerias necesarias para PostgreSQL y compilaciones
# Tercero el default-libmysqlclient-dev gcc pkg-config son necesarios para paquetes de Python que requieren compilación
RUN apt-get update && \
  apt-get install -y default-libmysqlclient-dev gcc pkg-config

# Copiamos todo lo que esta en el requirements.txt
# Luego instalamos todos los paquetes listados del requirements.txt 
COPY requirements.txt .

# El --no-cache-dir evita que guarde caceh para reducir el tamaño de la imagem
RUN pip install --no-cache-dir -r requirements.txt

# Ahora copiamos todo el contenido  del directorio actual (host) al directorio de trabajo del contenedor
COPY . .

# Configuramos las variables de entorno especificadas anteriormente
# ubicada dentro de la aplicación
COPY .env src/.env

# Realizamos debugging
# pwd: mostramos el directorio actual
# ls -lha: listamos los archivos con detalles
RUN pwd
RUN ls -lha

# Expone el puerto (indicamos en donde escuchara, esto no lo abre de forma automatica)
EXPOSE 8000

# Le brindamos permisos de ejecución al script 
RUN chmod +x ./start.sh

# Ejecutamos el script que iniciara el servidor cuando el contenedor este listo
CMD ["./start.sh"]

