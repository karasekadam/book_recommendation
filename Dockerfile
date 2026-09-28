FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY archive/*.csv archive/
COPY database.py recommender_model.py app.py serve.py ./
COPY --from=frontend /frontend/dist frontend/dist

ENV DB_PATH=/data/books.db
VOLUME /data
EXPOSE 8000

CMD ["sh", "-c", "[ -f \"$DB_PATH\" ] || python database.py; exec gunicorn serve:application --bind 0.0.0.0:8000 --workers 1 --threads 8 --timeout 300"]
