#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-orchflow:dev}"
CONTAINER="${CONTAINER:-orchflow-dev}"
HOST_PORT="${HOST_PORT:-8765}"
APP_PORT="${APP_PORT:-8765}"

require() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: $1 not found" >&2
        exit 1
    fi
}

wsl_ip() {
    hostname -I 2>/dev/null | awk '{print $1}'
}

print_urls() {
    local port="${1}"
    echo "UI available at:"
    echo "  http://127.0.0.1:${port}/"
    if grep -qi microsoft /proc/version 2>/dev/null; then
        local ip
        ip="$(wsl_ip)"
        if [[ -n "${ip}" ]]; then
            echo "  http://${ip}:${port}/  (use this from Windows if localhost fails)"
        fi
    fi
}

wait_for_ready() {
    local port="${1}"
    for _ in $(seq 1 30); do
        if curl -sf "http://127.0.0.1:${port}/" >/dev/null; then
            return 0
        fi
        sleep 0.2
    done
    echo "error: server did not become ready on port ${port}" >&2
    docker logs "${CONTAINER}" >&2 || true
    return 1
}

build() {
    require docker
    docker build \
        -f "${ROOT}/dockerfile" \
        --target prod \
        -t "${IMAGE}" \
        "${ROOT}"
    echo "built ${IMAGE}"
}

run() {
    require docker
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true

    local -a run_args=(--rm -d --name "${CONTAINER}")
    local listen_port="${APP_PORT}"

    if [[ "$(uname -s)" == Linux ]]; then
        run_args+=(--network host)
    else
        run_args+=(-p "${HOST_PORT}:${APP_PORT}")
        listen_port="${HOST_PORT}"
    fi

    docker run "${run_args[@]}" \
        "${IMAGE}" \
        python -m uvicorn src.ui.app:app --host 0.0.0.0 --port "${APP_PORT}"

    wait_for_ready "${listen_port}"
    print_urls "${listen_port}"
    echo "logs: docker logs -f ${CONTAINER}"
    echo "stop: $(basename "$0") stop"
}

stop() {
    require docker
    docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
    echo "stopped ${CONTAINER}"
}

logs() {
    require docker
    docker logs -f "${CONTAINER}"
}

usage() {
    cat <<EOF
usage: $(basename "$0") <build|run|up|stop|logs>

  build   build the prod image (${IMAGE})
  run     start the UI container in the background
  up      build, then run
  stop    stop and remove the container
  logs    follow container logs

env: IMAGE, CONTAINER, HOST_PORT, APP_PORT
EOF
}

case "${1:-}" in
    build) build ;;
    run) run ;;
    up) build; run ;;
    stop) stop ;;
    logs) logs ;;
    *)
        usage
        exit 1
        ;;
esac
