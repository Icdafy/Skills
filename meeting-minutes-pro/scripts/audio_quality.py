"""Streaming PCM diagnostics; signal measurements are not speech/ASR confidence."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave


SILENCE_DBFS = -50.0
WINDOW_SECONDS = 0.1
NEAR_FULL_SCALE = 32760


class _ReadOnlyPipe:
    # Some Windows pipe handles report tell()/seek() success despite not
    # supporting WAV seeks. Expose only streaming reads to the WAV reader.
    def __init__(self, stream):
        self.stream = stream

    def read(self, size=-1):
        return self.stream.read(size)


class _StreamingPCM:
    """Use WAV metadata but read raw frames to EOF, beyond RIFF's 4 GiB limit."""
    def __init__(self, stream, header):
        self.stream = stream
        self.channels = header.getnchannels()
        self.rate = header.getframerate()

    def getsampwidth(self):
        return 2

    def getcomptype(self):
        return 'NONE'

    def getnchannels(self):
        return self.channels

    def getframerate(self):
        return self.rate

    def readframes(self, count):
        return self.stream.read(count * self.channels * 2)


def _dbfs(value: float) -> float | None:
    return round(20 * math.log10(value), 2) if value > 0 else None


def inspect_pcm16(handle: wave.Wave_read) -> dict:
    """Read bounded windows until EOF, including WAV streams with unknown length."""
    if handle.getsampwidth() != 2 or handle.getcomptype() != 'NONE':
        raise ValueError('Audio diagnostics require uncompressed PCM16')
    channels, rate = handle.getnchannels(), handle.getframerate()
    if channels < 1 or rate < 1:
        raise ValueError('Invalid WAV channel count or sample rate')
    # NumPy is optional here: ASR runtimes have it, standalone checks need not.
    try:
        import numpy as np
    except ImportError:
        np = None
    totals = [dict(squares=0, peak=0, near_full_scale=0, silent_frames=0,
                   zero_samples=0) for _ in range(channels)]
    frames = 0
    while True:
        data = handle.readframes(max(1, int(rate * WINDOW_SECONDS)))
        if not data:
            break
        if len(data) % (2 * channels):
            raise ValueError('Truncated PCM frame in audio diagnostics')
        count = len(data) // (2 * channels)
        if np is not None:
            samples = np.frombuffer(data, dtype='<i2').astype(np.int64).reshape(-1, channels)
        else:
            samples = array('h')
            samples.frombytes(data)
            if sys.byteorder != 'little':
                samples.byteswap()
        for index, total in enumerate(totals):
            if np is not None:
                values = samples[:, index]
                absolute = np.abs(values)
                squares = int(np.sum(values * values))
                peak = int(np.max(absolute))
                near = int(np.count_nonzero(absolute >= NEAR_FULL_SCALE))
                zero = int(np.count_nonzero(values == 0))
            else:
                values = samples[index::channels]
                squares = sum(value * value for value in values)
                peak = max(abs(value) for value in values)
                near = sum(abs(value) >= NEAR_FULL_SCALE for value in values)
                zero = values.count(0)
            total['squares'] += squares
            total['peak'] = max(total['peak'], peak)
            total['near_full_scale'] += near
            total['zero_samples'] += zero
            if math.sqrt(squares / count) / 32768 <= 10 ** (SILENCE_DBFS / 20):
                total['silent_frames'] += count
        frames += count
    summaries = []
    for index, total in enumerate(totals):
        rms = math.sqrt(total['squares'] / frames) / 32768 if frames else 0.0
        peak = total['peak'] / 32768
        summaries.append({
            'channel_index': index, 'rms': round(rms, 8), 'rms_dbfs': _dbfs(rms),
            'peak': round(peak, 8), 'peak_dbfs': _dbfs(peak),
            'near_full_scale_fraction': round(total['near_full_scale'] / frames, 6) if frames else 0,
            'silent_window_fraction': round(total['silent_frames'] / frames, 6) if frames else 0,
            'zero_fraction': round(total['zero_samples'] / frames, 6) if frames else 0,
        })
    return {'status': 'measured', 'sample_format': 'decoded_pcm_s16le',
            'sample_rate_hz': rate, 'channel_count': channels,
            'frames_measured': frames, 'duration_seconds': round(frames / rate, 3),
            'window_seconds': WINDOW_SECONDS, 'silence_threshold_dbfs': SILENCE_DBFS,
            'near_full_scale_threshold_pcm16': NEAR_FULL_SCALE, 'channels': summaries,
            'interpretation': 'Signal energy and possible clipping only; not speech detection or transcription accuracy.'}


def inspect_wav(path: Path) -> dict:
    with wave.open(str(path), 'rb') as handle:
        return inspect_pcm16(handle)


def inspect_media(source: Path, ffmpeg: str, clip_start: float = 0.0,
                  clip_duration: float | None = None) -> dict:
    """Decode the selected interval without downmixing or loading it into RAM."""
    command = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error']
    if clip_start > 0:
        command += ['-ss', str(clip_start)]
    command += ['-i', str(source), '-map', '0:a:0', '-vn']
    if clip_duration is not None:
        command += ['-t', str(clip_duration)]
    # bitexact suppresses optional LIST metadata chunks, which Python's WAV
    # reader may otherwise attempt to seek over on an unseekable pipe.
    command += ['-c:a', 'pcm_s16le', '-bitexact', '-f', 'wav', 'pipe:1']
    # A temporary stderr file avoids both pipe deadlocks and unbounded logs.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        try:
            with wave.open(_ReadOnlyPipe(process.stdout), 'rb') as handle:
                if handle.getsampwidth() != 2 or handle.getcomptype() != 'NONE':
                    raise ValueError('FFmpeg did not produce PCM16')
                result = inspect_pcm16(_StreamingPCM(process.stdout, handle))
            returncode = process.wait()
            if returncode:
                errors.seek(0)
                raise RuntimeError('FFmpeg diagnostics failed: ' + errors.read(4096).decode('utf-8', errors='replace'))
            return result
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()


def quality_flags(source: dict, processed: dict, channel: str, text: str) -> list[dict]:
    """Return observable signal cautions, never an invented accuracy score."""
    flags = []
    if source.get('status') != 'measured':
        flags.append({'code': 'source_diagnostics_unavailable', 'severity': 'warning',
                      'message': 'Source-channel measurements could not be completed; no source quality conclusion is available.'})
    for item in source.get('channels', []):
        selected = (channel == 'mix' or item['channel_index'] == (0 if channel == 'left' else 1))
        if selected and item['near_full_scale_fraction'] >= 0.001:
            flags.append({'code': 'possible_clipping', 'severity': 'warning',
                          'channel_index': item['channel_index'],
                          'near_full_scale_fraction': item['near_full_scale_fraction'],
                          'message': 'Near-full-scale decoded samples; inspect for clipping, not proof of distorted speech.'})
        if item['silent_window_fraction'] >= 0.99 and item['peak'] < 0.01:
            flags.append({'code': 'near_silent_channel', 'severity': 'info',
                          'channel_index': item['channel_index'],
                          'message': 'This source channel is near silent under the stated energy threshold.'})
    mono = processed.get('channels', [{}])[0]
    source_rms = max((item['rms'] for item in source.get('channels', [])), default=0)
    if (channel == 'mix' and source.get('channel_count', 0) > 1 and source_rms >= 0.01
            and mono.get('rms', 0) <= source_rms * 0.1):
        flags.append({'code': 'downmix_energy_drop', 'severity': 'warning',
                      'message': 'Mono energy is at least 20 dB below the strongest source channel; inspect downmix cancellation or explicit preprocessing.'})
    if not text.strip() and mono.get('rms', 0) > 10 ** (SILENCE_DBFS / 20):
        flags.append({'code': 'non_silent_audio_without_text', 'severity': 'warning',
                      'message': 'Measured audio energy with empty ASR text; may be noise or missed speech and needs review.'})
    if text.strip() and mono.get('peak') == 0 and processed.get('frames_measured', 0) > 0:
        flags.append({'code': 'text_on_digital_silence', 'severity': 'warning',
                      'message': 'ASR emitted text although every measured processed sample is zero; review before use.'})
    return flags


def boundary_windows(boundaries: list[float], duration: float, padding: float = 3.0) -> list[dict]:
    return [{'start': round(max(0.0, point - padding), 3),
             'end': round(min(duration, point + padding), 3),
             'boundary_seconds': round(point, 3), 'reason': 'chunk_boundary',
             'time_basis': 'processed_audio'}
            for point in boundaries if math.isfinite(point) and 0 < point < duration]
