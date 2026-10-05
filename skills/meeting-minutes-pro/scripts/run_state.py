"""Content-bound checkpoints, atomic JSON writes and explicit offline loading."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(source: Path, configuration: dict) -> str:
    data = {'source_sha256': file_hash(source), 'configuration': configuration}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    default=str).encode('utf-8')).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def read_checkpoint(path: Path, identity: str, start: float, end: float) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data.get('identity') == identity and data.get('start') == start
                and data.get('end') == end and isinstance(data.get('text'), str)):
            return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def enable_offline() -> None:
    """Fail closed for Python networking in this CLI process, including ModelScope.

    Call only from CLI entrypoints; never install the guard merely by importing.
    This is a process guard, not a machine firewall or a promise about native code.
    """
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1')
    def denied(*args, **kwargs):
        raise OSError('offline mode: network access is disabled')
    socket.create_connection = denied
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.getaddrinfo = denied


def local_model(model: str, hub: str, offline: bool) -> str:
    if not offline:
        return model
    if Path(model).is_dir():
        return str(Path(model).resolve())
    try:
        if hub == 'hf':
            from huggingface_hub import snapshot_download
        else:
            from modelscope.hub.snapshot_download import snapshot_download
            from funasr.download.name_maps_from_hub import name_maps_ms
            model = name_maps_ms.get(model, model)
        return str(snapshot_download(model, local_files_only=True))
    except Exception as exc:
        raise RuntimeError(f'离线缓存不完整：{model}；请先联网安装完整模型或指定本地目录。') from exc


def covered_seconds(ranges: list[tuple[float, float]]) -> float:
    total = 0.0
    frontier = 0.0
    for start, end in sorted(ranges):
        total += max(0.0, end - max(start, frontier))
        frontier = max(frontier, end)
    return total
