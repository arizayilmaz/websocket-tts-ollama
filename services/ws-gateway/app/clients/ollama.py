import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: httpx.Timeout, retries: int = 1):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def normalize(self, text: str) -> str:
        payload = {
            "model": self.model,
            "prompt": (
                "Metni TTS için normalize et: noktalama düzelt, "
                "gereksiz boşlukları temizle, sayıları okunur yap. "
                "Sadece düzeltilmiş metni döndür.\n\n"
                f"METIN:\n{text}"
            ),
            "stream": False,
        }

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                r = await self._client.post(f"{self.base_url}/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return (data.get("response") or "").strip()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise

        raise RuntimeError("Ollama normalize failed unexpectedly") from last_error
