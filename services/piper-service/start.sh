#!/usr/bin/env sh
set -e

VOICE="${PIPER_VOICE:-en_US-lessac-medium}"
PORT="${PIPER_PORT:-5000}"
DATA_DIR="/models"

mkdir -p "$DATA_DIR"

MODEL_PATH="${DATA_DIR}/${VOICE}.onnx"
CONFIG_PATH="${DATA_DIR}/${VOICE}.onnx.json"

download_file () {
  URL="$1"
  OUT="$2"
  python - <<PY
import urllib.request
url = "${URL}"
out = "${OUT}"
urllib.request.urlretrieve(url, out)
print("downloaded ->", out)
PY
}

# Eğer model yoksa indir
if [ ! -f "$MODEL_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
  echo "[piper] voice files not found, downloading: $VOICE"

  # VOICE formatı: tr_TR-fahrettin-medium
  LOCALE="$(echo "$VOICE" | cut -d'-' -f1)"        # tr_TR
  QUALITY="$(echo "$VOICE" | rev | cut -d'-' -f1 | rev)"  # medium
  SPEAKER="$(echo "$VOICE" | cut -d'-' -f2)"       # fahrettin
  LANG="$(echo "$LOCALE" | cut -d'_' -f1)"         # tr

  # HuggingFace v1.0.0 resolve URL'leri (resmi piper-voices yapısı)
  MODEL_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/${LANG}/${LOCALE}/${SPEAKER}/${QUALITY}/${VOICE}.onnx?download=true"
  CONFIG_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/${LANG}/${LOCALE}/${SPEAKER}/${QUALITY}/${VOICE}.onnx.json?download=true"

  download_file "$MODEL_URL" "$MODEL_PATH"
  download_file "$CONFIG_URL" "$CONFIG_PATH"
fi

echo "[piper] starting http server on :${PORT} with ${VOICE}"
python -m piper.http_server -m "${VOICE}" --data-dir "$DATA_DIR" --host 0.0.0.0 --port "${PORT}"