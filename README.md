# websocket-tts-ollama

FastAPI tabanli WebSocket gateway, gelen metni segmentlere ayirir, opsiyonel olarak Ollama ile normalize eder, Piper ile WAV uretir ve sesi PCM chunk olarak stream eder.

## Durum
Bu repo artik temel urunlesme kontrollerine sahip:

- request lifecycle websocket baglantisi icinde netlestirildi
- `stop` ve yeni request aktif segment taskini gercekten iptal ediyor
- stale audio eski request icin cliente gitmiyor
- bounded queue ile backpressure eklendi
- config validation, timeout, retry ve structured logging eklendi
- `/health` ve dependency-aware `/ready` ayrimi eklendi
- websocket loglarinda `connection_id` korelasyonu eklendi

## Mimari
- `ws-gateway`
  - endpoint: `ws://localhost:8000/ws/tts`
  - sorumluluk: websocket IO, request session lifecycle, segment queue orchestration
- `ollama`
  - opsiyonel text normalization
- `piper`
  - HTTP uzerinden WAV uretimi
- `ollama-pull`
  - model warm-up/init container

Gateway akisi:

`append/flush/end/stop` -> `ConnectionSession` -> bounded segment queue -> Ollama normalize -> Piper WAV -> PCM chunk stream

## Proje Yapisi
```text
websocket-tts-ollama/
  docker-compose.yml
  README.md
  services/
    ws-gateway/
      requirements.txt
      app/
        config.py
        logging_utils.py
        main.py
        session.py
        ws_handler.py
        protocol.py
        splitter.py
        audio_chunker.py
        clients/
          ollama.py
          piper_http.py
      tests/
        test_config.py
        test_session.py
    piper-service/
      Dockerfile
      start.sh
```

## Konfigurasyon
Root `.env` dosyasi:

```env
CHUNK_MS=100
USE_OLLAMA=true
OLLAMA_BASE_URL=http://ollama:11434/api
PIPER_BASE_URL=http://piper:5000
OLLAMA_MODEL=gemma3
SEGMENT_QUEUE_SIZE=8
REQUEST_TIMEOUT_SECONDS=30
CONNECT_TIMEOUT_SECONDS=5
PIPER_RETRIES=1
OLLAMA_RETRIES=1
LOG_LEVEL=INFO
PIPER_VOICE=en_US-lessac-medium
PIPER_PORT=5000
```

Validation kurallari:
- `CHUNK_MS`: `20-1000`
- `SEGMENT_QUEUE_SIZE`: `1-128`
- timeout ve retry degerleri pozitif olmali
- `LOG_LEVEL`: `DEBUG|INFO|WARNING|ERROR|CRITICAL`

Gecersiz config ile servis startup'ta fail eder.

## WebSocket Protokolu
Client -> Server:
- `{"type":"append","request_id":"r1","text":"..."}`
- `{"type":"flush","request_id":"r1"}`
- `{"type":"end","request_id":"r1"}`
- `{"type":"stop","request_id":"r1"}`

Server -> Client:
- `audio_format`
- `buffer_status`
- `segment_ready`
- `audio_start`
- `audio_chunk`
- `audio_end`
- `warning`
- `error`

Kurallar:
- Her `audio_chunk` JSON mesajini hemen bir binary PCM frame takip eder.
- Yeni `request_id` geldiyse eski aktif request iptal edilir.
- `stop` sonrasinda kuyruktaki segmentler bosaltilir ve aktif segment taski iptal edilir.
- Queue dolarsa request hata ile iptal edilir.

## Calistirma
```bash
docker compose up --build
```

Health:
```bash
curl http://localhost:8000/health
```

Beklenen response artik queue bilgisini de icerir:
```json
{
  "ok": true,
  "segment_queue_size": 8
}
```

Readiness:
```bash
curl http://localhost:8000/ready
```

Beklenen response:
```json
{
  "ok": true,
  "dependencies": {
    "piper": true,
    "ollama": true
  }
}
```

## Testler
Python testleri:

```bash
cd services/ws-gateway
pytest
```

Kapsanan temel senaryolar:
- config validation
- `stop` ile aktif request iptali
- yeni request gelince eski request iptali
- queue full durumunda backpressure hata akisi
- websocket endpoint uzerinden JSON/binary frame sirasi
- invalid websocket payload rejection
- readiness endpoint dependency durumu

## Operasyonel Notlar
- Logging JSON formatinda stdout'a yazar.
- WebSocket connection loglarinda `connection_id` bulunur.
- Ollama ve Piper clientlari reuse edilen `httpx.AsyncClient` kullanir.
- Timeout ve retry sinirlari env ile yonetilir.
- Docker Compose servislerinde healthcheck ve `restart: unless-stopped` tanimlidir.

## Troubleshooting
`/ws/tts` bir HTTP endpoint degildir; browserda 404 gormen normaldir.

Piper container Windows tarafinda restart ediyorsa once `services/piper-service/start.sh` dosyasinin LF formatinda oldugunu kontrol et.
