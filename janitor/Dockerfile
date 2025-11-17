FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV JANITOR_INTERVAL_SECONDS=30
CMD ["python", "janitor.py"]
