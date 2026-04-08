# VMAnalytic App — Flask + Gunicorn
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Matplotlib / NumPy wheels are manylinux; no compiler needed for typical installs.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir 'gunicorn>=22.0.0'

COPY web/ web/
COPY vm_analysis/ vm_analysis/
COPY helper_files/ helper_files/

# Runtime output dirs (sessions write under data/uploads)
RUN mkdir -p data/uploads saved_csv_files \
    && chmod -R u+rwX data saved_csv_files

EXPOSE 5000

# Long timeout: analysis can run several minutes on large inventories
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "600", "web.app:app"]
