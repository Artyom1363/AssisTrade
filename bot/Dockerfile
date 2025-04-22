FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код бота
COPY main.py .
COPY models.py .

# Запускаем бота
CMD ["python", "main.py"]
