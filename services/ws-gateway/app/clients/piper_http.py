import httpx

class PiperHttpClient:
    def __init__(self, base_url: str, timeout: httpx.Timeout, retries: int = 1):
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def synthesize_wav(self, text: str) -> bytes:
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                r = await self._client.post(
                    f"{self.base_url}/",
                    json={"text": text},
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                return r.content
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise

        raise RuntimeError("Piper synthesis failed unexpectedly") from last_error
