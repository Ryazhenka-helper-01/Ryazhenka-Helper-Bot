FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Команда запуска бота
CMD ["python", "main.py"]
