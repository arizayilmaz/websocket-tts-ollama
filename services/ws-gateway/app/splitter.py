import re
from dataclasses import dataclass

@dataclass
class SplitterConfig:
    MAX_BUFFER_CHARS: int = 10_000
    WAITING_THRESHOLD_CHARS: int = 500
    FALLBACK_TARGET_CHARS: int = 50
    MAX_SEGMENT_CHARS: int = 350

class Splitter:
    # TR kısaltmalar 
    ABBREV = {"Dr.", "Prof.", "Doç.", "Sn.", "No.", "T.C.", "vb.", "vs."}

    SENT_END = {".", "!", "?"}
    PAUSE_CHARS = {",", ";", ":"}

    def __init__(self, cfg: SplitterConfig | None = None):
        self.cfg = cfg or SplitterConfig()

    def pop_ready_segments(self, buffer: str):
        """Primary: cümle sonu var mı? yoksa WAITING_THRESHOLD_CHARS sonrası fallback."""
        if len(buffer) > self.cfg.MAX_BUFFER_CHARS:
            buffer = buffer[:self.cfg.MAX_BUFFER_CHARS]

        segments = []

        # 1) Cümle sonuna göre çıkar
        while True:
            idx = self._find_sentence_end(buffer)
            if idx is None:
                break
            seg = buffer[:idx].strip()
            buffer = buffer[idx:].lstrip()
            if seg:
                segments.extend(self._enforce_max(seg))

        # 2) Nokta yok ama buffer büyüdüyse fallback üret
        if not segments and len(buffer) >= self.cfg.WAITING_THRESHOLD_CHARS:
            seg, buffer = self._fallback_split(buffer)
            if seg:
                segments.extend(self._enforce_max(seg))

        return segments, buffer

    def flush_all(self, buffer: str):
        """Buffer’daki her şeyi (fallback dahil) segmentlere çevir."""
        segments = []
        buffer = buffer.strip()
        while buffer:
            idx = self._find_sentence_end(buffer)
            if idx is not None:
                seg = buffer[:idx].strip()
                buffer = buffer[idx:].lstrip()
                if seg:
                    segments.extend(self._enforce_max(seg))
                continue

            seg, buffer = self._fallback_split(buffer)
            if seg:
                segments.extend(self._enforce_max(seg))

        return segments, ""

    def _find_sentence_end(self, s: str):
        # .,!,? bul ama kısaltma sonrası nokta ise sayma
        for m in re.finditer(r"[.!?]", s):
            i = m.end()  # segment bitişi
            candidate = s[:i].strip()

            # Son kelime kısaltma mı?
            last_token = candidate.split()[-1] if candidate.split() else ""
            if last_token in self.ABBREV:
                continue

            return i
        return None

    def _fallback_split(self, s: str):
        target = min(len(s), max(self.cfg.FALLBACK_TARGET_CHARS, 1))
        window = s[:max(target, 1)]

        # 1) durak karakteri
        for j in range(len(window) - 1, -1, -1):
            if window[j] in self.PAUSE_CHARS:
                cut = j + 1
                return s[:cut].strip(), s[cut:].lstrip()

        # 2) son boşluk
        k = window.rfind(" ")
        if k != -1:
            cut = k + 1
            return s[:cut].strip(), s[cut:].lstrip()

        # 3) hard fallback
        cut = target
        return s[:cut].strip(), s[cut:].lstrip()

    def _enforce_max(self, seg: str):
        # segment çok uzunsa (MAX_SEGMENT_CHARS) kelime bozmadan böl
        if len(seg) <= self.cfg.MAX_SEGMENT_CHARS:
            return [seg]

        out = []
        rest = seg
        while len(rest) > self.cfg.MAX_SEGMENT_CHARS:
            chunk = rest[:self.cfg.MAX_SEGMENT_CHARS]
            k = chunk.rfind(" ")
            cut = k if k > 0 else self.cfg.MAX_SEGMENT_CHARS
            out.append(rest[:cut].strip())
            rest = rest[cut:].lstrip()

        if rest:
            out.append(rest.strip())
        return out