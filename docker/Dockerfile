# syntax=docker/dockerfile:1.4

# Python version as build argument
ARG PYTHON_VERSION=3.13

# Build stage - export dependencies
FROM python:${PYTHON_VERSION}-alpine AS deps-export

# Install poetry
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /build

# Copy only dependency files for better caching
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements format (faster installation)
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes --without dev,test,docs

# Build stage - install dependencies
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine AS builder

WORKDIR /build

# Copy exported requirements
COPY --from=deps-export /build/requirements.txt .

# Install dependencies in a virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -U pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Final runtime stage
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine

# Build metadata arguments
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

# Add metadata labels
LABEL org.opencontainers.image.title="credproxy" \
    org.opencontainers.image.description="Service to provide AWS IAM authentication via container endpoint URLs or credential files" \
    org.opencontainers.image.vendor="John Preston" \
    org.opencontainers.image.licenses="MPL-2.0" \
    org.opencontainers.image.sbom="sbom.json"

# Install runtime dependencies (if any needed - currently none for alpine python)
# RUN apk add --no-cache ca-certificates

# Create non-root user with specific IDs
RUN addgroup -g 1338 credproxy && \
    adduser -D -u 1338 -G credproxy -s /bin/sh -h /credproxy credproxy

# Set work directory
WORKDIR /credproxy

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code with proper ownership
COPY --chown=credproxy:credproxy credproxy/ ./credproxy/
COPY --chown=credproxy:credproxy sbom.json ./

# Generate build info file with git commit and build date
RUN printf '"""Build-time information."""\n\n__version__ = "0.1.0"\n__git_commit__ = "%s"\n__build_date__ = "%s"\n' \
    "${GIT_COMMIT}" "${BUILD_DATE}" > /credproxy/credproxy/_build_info.py && \
    chown credproxy:credproxy /credproxy/credproxy/_build_info.py

# Copy and prepare entrypoint scripts
COPY docker/entrypoint.sh docker/init_secrets.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/init_secrets.sh

# Download lprobe for health checks with proper architecture detection
ARG LPROBE_VERSION=v0.1.6
ARG TARGETPLATFORM
RUN --mount=type=cache,target=/tmp/lprobe \
    case ${TARGETPLATFORM} in \
    "linux/amd64")  LPROBE_ARCH=amd64  ;; \
    "linux/arm64")  LPROBE_ARCH=arm64  ;; \
    *) echo "Unsupported platform: ${TARGETPLATFORM}" && exit 1 ;; \
    esac && \
    wget -qO /bin/lprobe https://github.com/fivexl/lprobe/releases/download/${LPROBE_VERSION}/lprobe-linux-${LPROBE_ARCH} && \
    chmod +x /bin/lprobe && \
    chown credproxy:credproxy /bin/lprobe

# Set PATH to include virtual environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER credproxy

# Health check (adjust port and path as needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["/bin/lprobe", "--port", "8080"]

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
