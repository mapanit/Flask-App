FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY main.py .
COPY templates/ templates/

# Создаем директорию для загрузок
RUN mkdir -p uploads

# Открываем порт
EXPOSE 5012

# Команда запуска
CMD ["python", "main.py"]
