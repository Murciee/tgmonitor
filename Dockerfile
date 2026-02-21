FROM python:3.9-slim

WORKDIR /app

RUN pip install telethon

COPY main.py .

CMD ["python", "main.py"]
