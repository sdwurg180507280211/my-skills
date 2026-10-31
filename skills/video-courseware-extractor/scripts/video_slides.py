#!/usr/bin/env python3
"""Generate review candidates and capture original frames; never auto-delete slides."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'sha256': digest.hexdigest(), 'bytes': Path(path).stat().st_size}


def run_json(cmd):
    return json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout)


def probe(video):
    video = Path(video).resolve(strict=True)
    data = run_json([os.getenv('FFPROBE_BIN', 'ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)])
    stream = next((s for s in data['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
    if stream is None:
        raise ValueError('No video stream')
    rotation = float(stream.get('tags', {}).get('rotate', 0))
    for side in stream.get('side_data_list', []):
        rotation = float(side.get('rotation', rotation))
    return dict(video=str(video), stream_index=stream['index'], width=int(stream['width']), height=int(stream['height']),
                duration=float(data['format'].get('duration') or stream.get('duration')),
                sample_aspect_ratio=stream.get('sample_aspect_ratio', '1:1'), rotation=rotation,
                frame_rate=stream.get('avg_frame_rate'), fingerprint=fingerprint(video))


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: expected finite number')
    return value


def box(value, width, height, normalized=False):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('crop/ignore region requires [x,y,width,height]')
    x, y, w, h = [number(v, 'box') for v in value]
    if not normalized and any(int(v) != v for v in value):
        raise ValueError('crop must use whole pixels')
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > width+1e-9 or y+h > height+1e-9:
        raise ValueError('crop/ignore region outside frame')
    return [x, y, w, h]


def safe_name(name):
    if not isinstance(name, str) or not name.strip() or name in ('.', '..') or any(c in name for c in '/\\\0'):
        raise ValueError('output_name must be a filename without directories')
    if not name.endswith('.pptx'):
        raise ValueError('output_name must end with .pptx')
    return name


def validate_plan(plan, info):
    if plan.get('schema_version') != 1:
        raise ValueError('schema_version must be 1')
    if info['rotation'] % 360 or info['sample_aspect_ratio'] not in ('1:1', 'N/A', '0:1'):
        raise ValueError('Normalize rotation/sample aspect ratio before selecting crop coordinates')
    for k, default in [('sample_fps', 1), ('stable_seconds', 2), ('mean_threshold', 2.1),
                       ('changed_fraction_threshold', .017), ('pixel_threshold', 25)]:
        v = number(plan.get(k, default), k)
        if v <= 0:
            raise ValueError(f'{k} must be positive')
        plan[k] = v
    if plan['sample_fps'] > 30 or plan['changed_fraction_threshold'] > 1 or plan['pixel_threshold'] > 255:
        raise ValueError('fps or threshold exceeds supported range')
    segments = plan.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValueError('segments must be a non-empty list')
    previous_end = 0; ids = set(); speakers = {}; owners = {}
    for s in segments:
        if not isinstance(s.get('id'), str) or not s['id'] or s['id'] in ids:
            raise ValueError('segment ids must be unique non-empty strings')
        ids.add(s['id'])
        if not isinstance(s.get('speaker'), str) or not s['speaker'].strip():
            raise ValueError('speaker is required')
        start = number(s['start'], 'start'); end = number(s['end'], 'end')
        if start < previous_end or end <= start or end > info['duration'] + .01:
            raise ValueError('segments must be ordered, non-overlapping and within duration')
        previous_end = end
        box(s['crop'], info['width'], info['height'])
        for region in s.get('ignore_regions', []):
            box(region, 1, 1, True)
        name = safe_name(s.get('output_name', s['speaker']+'.pptx'))
        if speakers.get(s['speaker'], name) != name or owners.get(name.casefold(), s['speaker']) != s['speaker']:
            raise ValueError('Each speaker needs one distinct output_name')
        speakers[s['speaker']] = name; owners[name.casefold()] = s['speaker']; s['output_name'] = name
    return plan


def save_new(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_segment(video, segment, plan, info):
    import numpy as np
    x, y, w, h = segment['crop']; width = min(480, w); height = max(1, round(width*h/w))
    fps = plan['sample_fps']; start = segment['start']; end = segment['end']
    filters = f'crop={w}:{h}:{x}:{y},setpts=PTS-STARTPTS,fps={fps}:start_time=0,scale={width}:{height}'
    cmd = [os.getenv('FFMPEG_BIN', 'ffmpeg'), '-v', 'error', '-nostdin', '-threads', '2', '-ss', str(start),
           '-i', str(video), '-t', str(end-start), '-map', f"0:{info['stream_index']}", '-an', '-vf', filters,
           '-pix_fmt', 'gray', '-threads', '2', '-f', 'rawvideo', 'pipe:1']
    # stderr is a temporary file: avoid a full pipe deadlocking a long decode.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors)
        intervals = []; reference = None; begin_index = 0; count = 0
        try:
            while True:
                payload = bytearray()
                while len(payload) < width*height:
                    chunk = process.stdout.read(width*height-len(payload))
                    if not chunk:
                        break
                    payload.extend(chunk)
                if not payload:
                    break
                if len(payload) != width*height:
                    raise ValueError('Incomplete raw frame')
                frame = np.frombuffer(payload, dtype=np.uint8).reshape(height, width).copy()
                for rx, ry, rw, rh in segment.get('ignore_regions', []):
                    frame[math.floor(ry*height):math.ceil((ry+rh)*height), math.floor(rx*width):math.ceil((rx+rw)*width)] = 255
                if reference is not None:
                    delta = np.abs(frame.astype(np.int16)-reference.astype(np.int16))
                    if float(delta.mean()) > plan['mean_threshold'] and float((delta > plan['pixel_threshold']).mean()) > plan['changed_fraction_threshold']:
                        intervals.append((begin_index, count))
                        begin_index = count; reference = frame
                else:
                    reference = frame
                count += 1
            if process.wait(timeout=30):
                errors.seek(0); raise RuntimeError(errors.read().decode(errors='replace')[-3000:])
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
            process.stdout.close()
    if count == 0:
        raise ValueError(f"No frames decoded in {segment['id']}")
    intervals.append((begin_index, count))
    result = []
    for i, (left, right) in enumerate(intervals, 1):
        begin = min(end, start+left/fps); finish = min(end, start+right/fps)
        if begin >= finish:
            continue
        time = start+(left+(right-left-1)//2)/fps
        result.append(dict(candidate_id=f"{segment['id']}-{i:04d}", segment_id=segment['id'], speaker=segment['speaker'],
                           output_name=segment['output_name'], begin=begin, end=finish, time=min(time, finish-1e-6),
                           stable=(finish-begin >= plan['stable_seconds']), crop=segment['crop'], keep=None, reason=''))
    return result


def validate_selection(data, info):
    if data.get('source', {}).get('fingerprint') != info['fingerprint']:
        raise ValueError('Source changed; do not reuse old selection')
    plan = validate_plan(data['plan'], info)
    segments = {s['id']:s for s in plan['segments']}; seen = set(); selected = []
    for c in data['candidates']:
        if c.get('candidate_id') in seen or not c.get('candidate_id'):
            raise ValueError('Candidate ids must be unique')
        seen.add(c['candidate_id'])
        if type(c.get('keep')) is not bool or not isinstance(c.get('reason'), str) or not c['reason'].strip():
            raise ValueError('Every candidate requires keep true/false and a review reason')
        s = segments[c['segment_id']]
        if c['speaker'] != s['speaker'] or c['output_name'] != s['output_name']:
            raise ValueError('Candidate speaker/output differs from source segment')
        begin = number(c['begin'], 'begin'); end = number(c['end'], 'end'); t = number(c['time'], 'time')
        if not s['start'] <= begin <= t < end <= s['end']:
            raise ValueError('Candidate time/interval outside segment')
        box(c['crop'], info['width'], info['height'])
        if c['keep']:
            selected.append(c)
    if not selected:
        raise ValueError('No kept pages')
    selected.sort(key=lambda c:c['time'])
    if len({c['time'] for c in selected}) != len(selected):
        raise ValueError('Multiple kept pages selected from the same time')
    expected = {s['speaker'] for s in plan['segments']}
    if {c['speaker'] for c in selected} != expected:
        raise ValueError('A speaker has no selected pages; resolve before capture')
    return selected


def capture(selection, outdir, review_only=False):
    data = json.loads(Path(selection).read_text(encoding='utf-8')); info = probe(data['source']['video'])
    if review_only:
        for candidate in data['candidates']:
            candidate.update(keep=True, reason='PREVIEW ONLY: not reviewed')
    selected = validate_selection(data, info); outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=False)
    decks = {}
    for index, c in enumerate(selected, 1):
        target = outdir/f'frame-{index:04d}.png'
        subprocess.run([os.getenv('FFMPEG_BIN', 'ffmpeg'), '-v', 'error', '-nostdin', '-threads', '2',
                        '-ss', str(c['time']), '-i', info['video'], '-map', f"0:{info['stream_index']}",
                        '-frames:v', '1', '-threads', '2', '-n', str(target)], check=True, timeout=120)
        if not target.is_file() or target.stat().st_size == 0:
            raise ValueError('Frame was not captured')
        deck = decks.setdefault(c['speaker'], dict(speaker=c['speaker'], output_name=c['output_name'], pages=[]))
        deck['pages'].append(dict(page=len(deck['pages'])+1, frame=target.name,
                                  frame_size=[info['width'], info['height']], crop=c['crop'], time=c['time'],
                                  candidate_id=c['candidate_id'], reason=c['reason']))
    save_new(outdir/'manifest.json', dict(schema_version=1, review_only=review_only, source=info, decks=list(decks.values())))
    return outdir/'manifest.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('probe'); p.add_argument('--video', required=True)
    s = sub.add_parser('scan'); s.add_argument('--plan', required=True); s.add_argument('--out', required=True)
    for command in ('capture', 'preview'):
        c = sub.add_parser(command); c.add_argument('--selection', required=True); c.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    if args.command == 'probe':
        print(json.dumps(probe(args.video), ensure_ascii=False, indent=2))
    elif args.command == 'scan':
        if Path(args.out).exists():
            raise FileExistsError(args.out)
        plan_path = Path(args.plan).resolve(); plan = json.loads(plan_path.read_text(encoding='utf-8'))
        video = (plan_path.parent/plan['video']).resolve(); info = probe(video); validate_plan(plan, info)
        candidates = []
        for segment in plan['segments']:
            found = scan_segment(video, segment, plan, info); candidates.extend(found)
            print(f"{segment['id']}: {len(found)} candidates; all need visual review", flush=True)
        save_new(args.out, dict(schema_version=1, source=info, plan=plan, candidates=candidates))
    else:
        print(capture(args.selection, args.out_dir, review_only=args.command == 'preview'))


if __name__ == '__main__':
    main()
