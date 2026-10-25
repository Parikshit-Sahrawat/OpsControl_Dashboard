FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements*.txt ./
RUN --mount=type=secret,id=proxy_ca,required=true PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements-providers.txt -r requirements-hosts.txt
COPY backend/ /app/
COPY tests/ /tests/
COPY agent/ /agent/
COPY deploy/fixtures/ /fixtures/
