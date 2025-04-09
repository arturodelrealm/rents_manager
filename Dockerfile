# Usamos Python 3.11 como base
FROM python:3.12

# Configuramos el directorio de trabajo
WORKDIR /app

# Copiamos y actualizamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código fuente
COPY . .

# Definimos el puerto de ejecución
EXPOSE 8000

# Comando por defecto para correr el servidor
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "arriendos.wsgi:application"]

# Command to run locally
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]