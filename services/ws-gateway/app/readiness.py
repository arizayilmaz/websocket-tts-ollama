import asyncio
from urllib.parse import urlparse


async def tcp_ready(url: str, timeout_seconds: float) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port

    if not host or not port:
        return False

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout_seconds,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False
