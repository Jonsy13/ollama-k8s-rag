# ---- Base Image ----
FROM python:3.11-slim

# ---- Install dependencies ----
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy app ----
COPY src/ ./src/

# ---- Configure ----
EXPOSE 8000

# ---- Start command ----
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
