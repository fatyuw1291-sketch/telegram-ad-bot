FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# اجرای run.py به جای bot.py
CMD ["python", "run.py"]