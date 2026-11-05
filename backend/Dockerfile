FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY backend /srv/backend
COPY config /srv/config
COPY materials /srv/materials

WORKDIR /srv/backend
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir weasyprint

ENV SUBJECTS_CONFIG=/srv/config/subjects.yaml
ENV MATERIALS_ROOT=/srv/materials
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
