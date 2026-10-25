FROM node:24-bookworm-slim
WORKDIR /app
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca,required=true NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci --no-audit --no-fund
COPY frontend/ ./
ENV VITE_API_BASE_URL=http://api:8000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
