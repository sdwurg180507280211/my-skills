#!/usr/bin/env python3
"""Build an exclusive PCM voice track; optionally replace a video's entire audio."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np


def build(spec_path, output, ffmpeg, overwrite=False):
    spec_path = Path(spec_path).resolve()
    output = Path(output).resolve()
    if output.exists() and not overwrite:
        raise ValueError(f'Output exists: {output}')
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    duration = float(spec['duration_seconds'])
    rate = int(spec.get('sample_rate', 48000))
    if not math.isfinite(duration) or duration <= 0 or rate <= 0:
        raise ValueError('Duration and sample rate must be positive')
    count = round(duration * rate)
    track = np.zeros((count, 2), dtype=np.float32)
    occupied = np.zeros(count, dtype=np.uint8)
    placements = []
    segments = spec['segments']
    if not segments:
        raise ValueError('No speech segments')
    for segment in segments:
        source = (spec_path.parent / segment['file']).resolve()
        if source == output:
            raise ValueError('Output must not replace a source voice file')
        start = float(segment['start'])
        if not math.isfinite(start) or start < 0:
            raise ValueError(f'Invalid start for {source}')
        result = subprocess.run([
            ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(source),
            '-vn', '-af', f'loudnorm=I=-18:TP=-2:LRA=7,aresample={rate}',
            '-ac', '2', '-ar', str(rate), '-f', 'f32le', '-'
        ], stdout=subprocess.PIPE, check=True)
        speech = np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2).copy()
        if len(speech) == 0 or not np.isfinite(speech).all():
            raise ValueError(f'Empty or nonfinite voice data: {source}')
        first = round(start * rate)
        last = first + len(speech)
        if last > count:
            raise ValueError(f'Voice exceeds film duration: {source}')
        if occupied[first:last].any():
            raise ValueError(f'Voice overlap detected: {source}')
        fade_in = min(round(0.012 * rate), len(speech))
        fade_out = min(round(0.05 * rate), len(speech))
        speech[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
        speech[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]
        track[first:last] = speech
        occupied[first:last] = 1
        placements.append({
            'file': segment['file'], 'text': segment.get('text', ''),
            'start': first / rate, 'end': last / rate,
            'sample_start': first, 'sample_end': last,
        })
    peak = float(np.max(np.abs(track)))
    if peak > 0.95:
        track *= 0.95 / peak
    pcm = np.round(track * 32767).astype('<i2')
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), 'wb') as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm.tobytes())
    return {
        'file': str(output), 'duration_seconds': count / rate,
        'sample_rate': rate, 'voice_source': spec.get('voice_source'),
        'original_audio_included': False,
        'max_simultaneous_voice_segments': int(occupied.max()),
        'placements': placements,
        'gap_pcm_peak': int(np.abs(pcm[occupied == 0].astype(np.int32)).max(initial=0)),
        'peak_before_optional_attenuation': peak,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report')
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--video')
    parser.add_argument('--movie-output')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error('FFmpeg is unavailable')
    if bool(args.video) != bool(args.movie_output):
        parser.error('--video and --movie-output must be supplied together')
    outputs = [Path(args.output).resolve()]
    if args.report:
        outputs.append(Path(args.report).resolve())
    if args.movie_output:
        outputs.append(Path(args.movie_output).resolve())
        if Path(args.video).resolve() in outputs:
            parser.error('Movie input and output must differ')
    if len(set(outputs)) != len(outputs) or Path(args.spec).resolve() in outputs:
        parser.error('Inputs and outputs must use distinct paths')
    if not args.overwrite and any(p.exists() for p in outputs):
        parser.error('Output already exists; use a new path or --overwrite')
    try:
        report = build(args.spec, args.output, args.ffmpeg, args.overwrite)
        if args.video:
            movie = Path(args.movie_output).resolve()
            movie.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([
                args.ffmpeg, '-hide_banner', '-loglevel', 'error',
                '-y' if args.overwrite else '-n', '-i', str(Path(args.video).resolve()),
                '-i', str(Path(args.output).resolve()), '-map', '0:v:0', '-map', '1:a:0',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-t', str(report['duration_seconds']), '-map_metadata', '-1',
                '-movflags', '+faststart', str(movie)
            ], check=True)
            report['movie_file'] = str(movie)
        if args.report:
            path = Path(args.report).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
