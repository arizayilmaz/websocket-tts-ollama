import re
from dataclasses import dataclass


@dataclass
class SplitterConfig:
    MAX_BUFFER_CHARS: int = 10_000
    WAITING_THRESHOLD_CHARS: int = 160
    FALLBACK_TARGET_CHARS: int = 140
    MAX_SEGMENT_CHARS: int = 220
    MIN_SEGMENT_CHARS: int = 80


class Splitter:
    ABBREV = {"Dr.", "Prof.", "Doç.", "Sn.", "No.", "T.C.", "vb.", "vs."}
    SENT_END = {".", "!", "?"}
    PAUSE_CHARS = {",", ";", ":"}

    def __init__(self, cfg: SplitterConfig | None = None):
        self.cfg = cfg or SplitterConfig()

    def pop_ready_segments(self, buffer: str):
        if len(buffer) > self.cfg.MAX_BUFFER_CHARS:
            buffer = buffer[:self.cfg.MAX_BUFFER_CHARS]

        raw_segments = []

        while True:
            idx = self._find_sentence_end(buffer)
            if idx is None:
                break

            seg = buffer[:idx].strip()
            buffer = buffer[idx:].lstrip()

            if seg:
                raw_segments.extend(self._enforce_max(seg))

        if not raw_segments and len(buffer) >= self.cfg.WAITING_THRESHOLD_CHARS:
            seg, buffer = self._fallback_split(buffer)
            if seg:
                raw_segments.extend(self._enforce_max(seg))

        return self._merge_small_segments(raw_segments), buffer

    def flush_all(self, buffer: str):
        raw_segments = []
        buffer = buffer.strip()

        while buffer:
            idx = self._find_sentence_end(buffer)

            if idx is not None:
                seg = buffer[:idx].strip()
                buffer = buffer[idx:].lstrip()
                if seg:
                    raw_segments.extend(self._enforce_max(seg))
                continue

            seg, buffer = self._fallback_split(buffer)
            if seg:
                raw_segments.extend(self._enforce_max(seg))

        return self._merge_small_segments(raw_segments), ""

    def _find_sentence_end(self, s: str):
        for m in re.finditer(r"[.!?]", s):
            i = m.end()
            candidate = s[:i].strip()

            parts = candidate.split()
            last_token = parts[-1] if parts else ""

            if last_token in self.ABBREV:
                continue

            return i

        return None

    def _fallback_split(self, s: str):
        target = min(len(s), max(self.cfg.FALLBACK_TARGET_CHARS, 1))
        window = s[:target]

        for j in range(len(window) - 1, -1, -1):
            if window[j] in self.PAUSE_CHARS:
                cut = j + 1
                return s[:cut].strip(), s[cut:].lstrip()

        k = window.rfind(" ")
        if k != -1:
            cut = k + 1
            return s[:cut].strip(), s[cut:].lstrip()

        cut = target
        return s[:cut].strip(), s[cut:].lstrip()

    def _enforce_max(self, seg: str):
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

    def _merge_small_segments(self, segments: list[str]):
        if not segments:
            return []

        merged = []
        current = segments[0]

        for seg in segments[1:]:
            candidate = f"{current} {seg}"

            if (
                len(current) < self.cfg.MIN_SEGMENT_CHARS
                and len(candidate) <= self.cfg.MAX_SEGMENT_CHARS
            ):
                current = candidate
            else:
                merged.append(current)
                current = seg

        if current:
            merged.append(current)

        return merged