# Fase 1: Builder
FROM python:3.12-slim as Builder

# Working directory
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependences file and install it
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Etapa 2: Final runtime (mínima y segura)
FROM python:3.12-slim AS runtime

# Create user and group witout privilege
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Working directory
WORKDIR /app

# Copy packages from builder step
COPY --from=Builder /root/.local /home/appuser/.local
COPY src/ /app/src/

# Configure enviroment variables and path
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Change to user without root permiss
USER 10001

# Copy the app code in the container
COPY src/ /app/src/

# Port
EXPOSE 8000

# Healthcheck of the container
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000" ]