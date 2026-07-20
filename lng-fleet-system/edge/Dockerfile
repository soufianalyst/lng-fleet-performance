# =============================================================================
# Stage 1: Build the edge gateway binary
# =============================================================================
FROM rust:1.77-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy manifests first for dependency caching
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true

# Copy actual source
COPY src/ ./src/
COPY config/ ./config/

# Force rebuild of actual source
RUN cargo build --release

# =============================================================================
# Stage 2: Minimal runtime image
# =============================================================================
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /build/target/release/lng-edge-gateway /app/lng-edge-gateway
COPY --from=builder /build/config/ /app/config/

EXPOSE 1883

ENTRYPOINT ["/app/lng-edge-gateway"]
