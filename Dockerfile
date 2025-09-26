# --- Build stage -------------------------------------------------------------
FROM golang:1.22 AS build
WORKDIR /app

# OS deps for CGO (sqlite3 driver) + useful certs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates tzdata \
  && rm -rf /var/lib/apt/lists/*

# Enable CGO so mattn/go-sqlite3 can compile
ENV CGO_ENABLED=1
# (optional) keep linux/amd64 unless you want to cross-compile
ENV GOOS=linux GOARCH=amd64

# Modules first (better caching)
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# If you want to build without sqlite, you could use tags to skip it, but by default this builds both.
# Build the binary
RUN go build -trimpath -ldflags="-s -w" -o /bin/raalisence ./cmd/raalisence

# --- Runtime stage -----------------------------------------------------------
# Distroless base includes libc & libstdc++ needed for CGO with sqlite.
FROM gcr.io/distroless/base-debian12:nonroot
WORKDIR /app

# Binary
COPY --from=build /bin/raalisence /app/raalisence

# Static assets (and templates if you have them)
COPY --from=build /app/static /app/static
# COPY --from=build /app/templates /app/templates

# If your app needs to know the static dir:
# ENV RA_STATIC_DIR=/app/static

EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/app/raalisence"]