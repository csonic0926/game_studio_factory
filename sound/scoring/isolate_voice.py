"""Pull narration off a finished video mix with ElevenLabs Voice Isolator (paid call — ask first).

    python3 score.py isolate --in original_audio.mp3 --out vo.mp3

Prefer the original VO recording when the video's owner has it; isolation is the fallback.
Stdlib only (multipart built by hand); key via pipeline.credentials.
"""
from __future__ import annotations

import pathlib, sys, urllib.error, urllib.request, uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline import credentials  # noqa: E402

URL = "https://api.elevenlabs.io/v1/audio-isolation"


def isolate(in_path: str, out_path: str, timeout: int = 600) -> int:
    key = credentials.get_elevenlabs_key()
    data = pathlib.Path(in_path).read_bytes(); boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"{pathlib.Path(in_path).name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ElevenLabs audio-isolation HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from None
    pathlib.Path(out_path).write_bytes(out)
    return len(out)
