#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${IMAGE_TAG:-iyou-poly:latest}"

cd "$(dirname "$0")/.."

echo "==> Building ${IMAGE_TAG} ..."
docker build \
    --tag "${IMAGE_TAG}" \
    --file Dockerfile \
    .

echo "==> Done: ${IMAGE_TAG}"
