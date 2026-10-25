# System Chromium keeps VFS disk use bounded; Playwright itself is pinned.
FROM node:24-bookworm-slim
WORKDIR /tools
RUN --mount=type=secret,id=proxy_ca,required=true \
    apt-get update && apt-get install -y --no-install-recommends chromium fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm install --no-audit --no-fund playwright@1.56.1
ENV PLAYWRIGHT_MODULE=/tools/node_modules/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium
WORKDIR /repo
CMD ["sleep", "infinity"]
