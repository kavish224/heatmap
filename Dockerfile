FROM python:3.11-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

COPY crontab.txt /etc/cron.d/heatmap-cron
RUN chmod 0644 /etc/cron.d/heatmap-cron && crontab /etc/cron.d/heatmap-cron

RUN touch /var/log/cron.log

EXPOSE 5005

CMD ["sh", "-c", "cron && python smart_api.py && python app.py"]
