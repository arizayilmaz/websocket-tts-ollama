#!/usr/bin/env sh
set -e

VOICE="${PIPER_VOICE:-en_US-lessac-medium}"
PORT="${PIPER_PORT:-5000}"

mkdir -p /models
cd /models

# Daha önce indirildiyse tekrar indirme
# (Piper bazı sürümlerde klasör, bazı sürümlerde .onnx dosyası bırakabiliyor)
if [ ! -d "$VOICE" ] && [ ! -f "${VOICE}.onnx" ]; then
  echo "[piper] downloading voice: ${VOICE}"
  python -m piper.download_voices "${VOICE}"
fi

echo "[piper] starting http server on :${PORT} with ${VOICE}"
python -m piper.http_server -m "${VOICE}" --data-dir /models --host 0.0.0.0 --port "${PORT}"