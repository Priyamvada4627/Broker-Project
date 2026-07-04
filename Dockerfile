# ---- Backend Dockerfile ----
# Build context should be the "backend" folder (the one containing this
# Dockerfile, requirements.txt, and the "backend" python package).

FROM python:3.11-slim

# System deps needed to build psycopg2 / xgboost / scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code (the "backend" python package)
COPY backend ./backend

EXPOSE 8000

# Runs "backend.main:app" because the package folder is named "backend"
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
