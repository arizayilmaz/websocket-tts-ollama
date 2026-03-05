import httpx

class PiperHttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def synthesize_wav(self, text: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{self.base_url}/",
                json={"text": text},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.content