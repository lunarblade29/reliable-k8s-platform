FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
