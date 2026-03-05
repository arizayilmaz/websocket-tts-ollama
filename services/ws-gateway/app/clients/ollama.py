import httpx

class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def normalize(self, text: str) -> str:
        # /api/generate (streaming endpoint; POC'ta stream:false ile tek response al)
        payload = {
            "model": "gemma3",
            "prompt": (
                "Metni TTS için normalize et: noktalama düzelt, "
                "gereksiz boşlukları temizle, sayıları okunur yap. "
                "Sadece düzeltilmiş metni döndür.\n\n"
                f"METIN:\n{text}"
            ),
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self.base_url}/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("response") or "").strip()