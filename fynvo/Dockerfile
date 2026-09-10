ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.12-alpine3.20
ARG BUILD_VERSION=1.22.0
ARG BUILD_ARCH=aarch64
ARG BUILD_REVISION=unknown
ARG BUILD_CREATED=unknown

FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json ./package-lock.json
RUN npm ci
COPY frontend ./
RUN npm run build

FROM ${BUILD_FROM}

ARG BUILD_VERSION
ARG BUILD_ARCH
ARG BUILD_REVISION
ARG BUILD_CREATED

LABEL \
  org.opencontainers.image.title="Fynvo" \
  org.opencontainers.image.description="Household financial planning and cash-flow forecasting" \
  org.opencontainers.image.source="https://github.com/stunwill/fynvo-home-assistant" \
  org.opencontainers.image.version="${BUILD_VERSION}" \
  org.opencontainers.image.revision="${BUILD_REVISION}" \
  org.opencontainers.image.created="${BUILD_CREATED}" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.name="Fynvo" \
  io.hass.arch="${BUILD_ARCH}"

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

ENV PYTHONUNBUFFERED=1
ENV FYNVO_DATA_DIR=/data
ENV FYNVO_VERSION=${BUILD_VERSION}
ENV FYNVO_BUILD_REVISION=${BUILD_REVISION}
ENV FYNVO_BUILD_CREATED=${BUILD_CREATED}
ENV FYNVO_ARCH=${BUILD_ARCH}

EXPOSE 8097

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8097"]
