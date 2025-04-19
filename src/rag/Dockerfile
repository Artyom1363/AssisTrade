FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

RUN mkdir -p /app/data/index /app/data/persist_dir /app/data/metamask_data

# Expose port
EXPOSE 8001

# Run application
CMD ["python", "main.py", "--vector-data-dir", "/app/data/index", "--persist-dir", "/app/data/persist_dir", "--data-dir", "/app/data/metamask_data", "--collection-name", "documentation", "--host", "0.0.0.0", "--port", "8001"]