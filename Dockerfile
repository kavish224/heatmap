# heatmap/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5005

CMD ["bash", "-c", "python smart_api.py && python app.py"]
