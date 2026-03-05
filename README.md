# websocket-tts-ollama

FastAPI + Uvicorn WebSocket gateway üzerinden gelen metni (opsiyonel) **Ollama** ile normalize eder, **Piper** ile TTS üretir ve sesi **~100ms PCM (pcm_s16le) binary chunk**’lar halinde WebSocket üzerinden stream eder.

---

## Mimari (Docker Compose)
- **ws-gateway** (FastAPI WebSocket)
  - WS endpoint: `ws://localhost:8000/ws/tts`
  - Akış: `append/flush/end/stop` → segmentleme → (ops) Ollama normalize → Piper TTS → PCM chunk stream
- **ollama** (LLM)
  - Normalize için kullanılır
- **piper** (TTS)
  - HTTP üzerinden WAV üretir, gateway PCM chunk’lara çevirip WS üzerinden yollar
- **ollama-pull** (init job)
  - Modeli indirir, tamamlayınca kapanır (Exited normal)

---

## Proje Yapısı
```
websocket-tts-ollama/
  docker-compose.yml
  .env
  services/
    ws-gateway/
      Dockerfile
      requirements.txt
      app/
        main.py
        protocol.py
        splitter.py
        audio_chunker.py
        clients/
          ollama.py
          piper_http.py
    piper-service/
      Dockerfile
      start.sh
```

---

## Gereksinimler
- Docker Desktop
- Portlar boş olmalı:
  - `8000` (ws-gateway)
  - `5000` (piper)
  - `11434` (ollama)

---

## .env Dosyası
Proje root dizinine `.env` oluştur ve aşağıdaki gibi doldur:

```env
# ws-gateway
CHUNK_MS=100
USE_OLLAMA=true

# Docker network içinde servis isimleri
OLLAMA_BASE_URL=http://ollama:11434/api
PIPER_BASE_URL=http://piper:5000

# Ollama
OLLAMA_MODEL=gemma3

# Piper
PIPER_VOICE=en_US-lessac-medium
PIPER_PORT=5000
```

---

## Çalıştırma
Proje root dizininde:

```bash
docker compose up --build
```

Durum kontrol:
```bash
docker compose ps
```

Beklenen:
- `ws-gateway` → Up
- `ollama` → Up
- `piper` → Up
- `ollama-pull` → `Exited(0)` olabilir (model indirip kapanması normal)

---

## Hızlı Testler

### 1) Gateway health
Tarayıcı:
- `http://localhost:8000/health`

Beklenen:
```json
{"ok": true}
```

### 2) Piper HTTP testi (WAV)
Postman:
- **POST** `http://localhost:5000/`
- Body (raw JSON):
```json
{"text":"Merhaba! Piper HTTP test."}
```
Response binary gelir → “Save Response” ile `.wav` kaydedip dinleyebilirsin.

Curl:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{ "text": "Merhaba! Piper HTTP test." }' \
  -o test.wav http://localhost:5000/
```

### 3) WebSocket TTS testi (Postman)
> Postman ses çalmaz, sadece JSON + Binary frame’leri gösterir.

Postman → New → **WebSocket Request**  
URL: `ws://localhost:8000/ws/tts`

Bağlanınca ilk mesaj:
- `audio_format`

Gönder:
```json
{"type":"append","text":"Merhaba! WebSocket üzerinden TTS testi."}
```
Ardından:
```json
{"type":"flush"}
```

Beklenen akış:
- `segment_ready`
- `audio_start`
- birden fazla `audio_chunk` + her chunk sonrası **Binary**
- `audio_end`

---

## WebSocket Protokol Özeti
Client → Server (JSON):
- `{"type":"append","text":"..."}`
- `{"type":"flush"}`
- `{"type":"end"}`
- `{"type":"stop"}`

Server → Client (JSON):
- `audio_format`
- `buffer_status`
- `segment_ready`
- `audio_start`
- `audio_chunk`
- `audio_end`
- `error`

**Kural:** Her `audio_chunk` JSON mesajını **takiben** bir **binary frame** gelir.  
Binary içerik: **PCM s16le** chunk bytes (CHUNK_MS=100 ise 100ms).

---

## Troubleshooting
### `/ws/tts` 404
`/ws/tts` bir HTTP endpoint değil **WebSocket endpoint**. Tarayıcıda açarsan 404 normaldir. Postman WebSocket veya WS client kullan.

### Piper container restart ediyor
Log:
```bash
docker compose logs -f piper
```
Windows’ta sık sebep: `start.sh` CRLF → dosyayı LF’ye çevir (VS Code: CRLF → LF).
