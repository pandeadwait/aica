#!/bin/sh
set -eu

ollama serve &

sleep 5

if [ "${OLLAMA_PULL_ON_START:-false}" = "true" ]; then
  ollama pull "${OLLAMA_MODEL}"
fi

wait
