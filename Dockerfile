# Dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8080

ENV PORT=8080 \
    MONGO_URI=mongodb://mongo:27017 \
    MONGO_DB=daystore \
    SVC_USERNAME=service_bot \
    SVC_PASSWORD=service_bot_secret

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
