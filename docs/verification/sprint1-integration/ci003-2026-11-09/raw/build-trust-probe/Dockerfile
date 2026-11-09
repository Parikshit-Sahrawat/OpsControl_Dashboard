FROM python:3.12-alpine
RUN --network=none --mount=type=secret,id=proxy_ca,required=true python -c "import ssl; c=ssl.create_default_context(cafile='/run/secrets/proxy_ca'); assert c.verify_mode == ssl.CERT_REQUIRED and c.check_hostname; print('TLS trust mount verified')"
