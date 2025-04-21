FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run python needed commands. Probably should change for a bash script
RUN python manage.py migrate
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Comamand to run on server
 CMD ["gunicorn", "--bind", "0.0.0.0:8000", "arriendos.wsgi:application"]
