# UI Frontend

Bu klasor, mevcut websocket TTS backend'ine baglanan React + TypeScript + Vite arayuzudur. Backend contract'ina dokunmaz; mevcut `append`, `flush`, `stop` ve binary PCM akisini kullanir.

## Ozellikler

- explicit connection lifecycle: `disconnected`, `connecting`, `idle`, `streaming`, `stopping`, `error`
- merkezi request takibi ve stale message filtering
- stale binary frame / metadata mismatch drop korumasi
- deterministic audio reset ve disconnect cleanup
- env tabanli WebSocket URL konfigurasyonu
- debug log paneli
- backend bagimsiz testler

## Klasor Yapisi

```text
ui/
  public/
    audio-stream-processor.js
  src/
    components/
      ControlBar.tsx
      LogPanel.tsx
      StatusBadge.tsx
    hooks/
      useAudioPlayer.ts
      useTtsWebSocket.ts
    lib/
      config.ts
      PcmStreamPlayer.ts
      wsProtocol.ts
    test/
      mocks.ts
      setupTests.ts
    App.tsx
    App.test.tsx
```

## Kurulum

```bash
cd ui
npm install
```

## Env / Config

`.env.example` dosyasini referans al:

```env
VITE_TTS_WS_URL=ws://127.0.0.1:8000/ws/tts
VITE_ENABLE_DEV_SEED=true
```

`VITE_TTS_WS_URL` verilmezse frontend default olarak `ws://127.0.0.1:8000/ws/tts` kullanir.
`VITE_ENABLE_DEV_SEED=false` yapilirsa gelistirme ortamindaki ornek metin/log seed'i kapatilabilir.

## Gelistirme

```bash
npm run dev
```

## Production Build

```bash
npm run build
```

## Testler

```bash
npm run test
```

Testler backend gerektirmez. Mock edilenler:

- `WebSocket`
- `AudioContext`
- `AudioWorkletNode`
- `crypto.randomUUID`

Kapsanan temel senaryolar:

1. `connect -> speak -> stop`
2. stop sonrasi stale message / stale audio ignore edilmesi
3. yeni request baslayinca eski request etkisinin kesilmesi
4. disconnect cleanup
5. bos text engelleme
6. websocket acik degilken speak engeli

## Backend Olmadan Test Etme

Bu frontend, websocket contract'i frontend testleri icinde mock eder. Gercek backend olmadan UI lifecycle, stale request filtering ve audio queue davranisi dogrulanabilir.

## Demo Notlari

- Gelistirme modunda acilista ornek metin ve debug log seed'i otomatik yuklenir.
- once `Connect`
- sonra `Speak`
- debug panelden request akisini izle
- `Stop` ile stale audio'nun drop edildigini gorebilirsin
- `Disconnect` ile queue ve player state sifirlanir
