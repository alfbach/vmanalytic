# VMAnalytic — Flask + Gunicorn (production-style container)
#
# OpenShift helper (o-i-creator): set OIC_STATIC_ROOT to a directory that contains
# the static export (index.html + assets/). Example bind-mount at run time:
#   docker run ... -v /path/to/o-i-creator/static:/app/oic-static:ro -e OIC_STATIC_ROOT=/app/oic-static ...
#
# SPDX-License-Identifier: GPL-2.0-only

FROM python:3.12-slim-bookworm

# OpenShift/Podman: arbitrary UID is typically in group 0; keep caches on /app/data.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    OIC_STATIC_ROOT=/app/oic-static \
    TMPDIR=/app/data/tmp \
    MPLCONFIGDIR=/app/data/.mplconfig \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir 'gunicorn>=22.0.0'

COPY web/ web/
COPY vm_analysis/ vm_analysis/
COPY helper_files/ helper_files/

# Writable dirs (upload sessions, temp uploads, matplotlib cache, optional CSV cache).
# Group 0 + g=u: OpenShift arbitrary UIDs (and rootless Podman) can write via root group.
RUN mkdir -p data/uploads data/tmp data/.mplconfig saved_csv_files oic-static \
    && useradd --create-home --uid 1000 --shell /bin/bash vmanalytic \
    && chown -R 1000:0 /app \
    && chmod -R g=u /app

USER 1000

EXPOSE 5000

# Long timeout: analysis can run several minutes on large inventories
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "600", "web.app:app"]
