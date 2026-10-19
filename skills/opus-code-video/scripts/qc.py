"""成片检查：python3 qc.py <成片.mp4> [--duration 60]

报时长、分辨率、帧率、帧数、有无音轨、整体响度、峰值、意外黑帧。峰值超过 -1 dBFS 时给出修正命令
（压成 AAC 后峰值常比 WAV 高零点几 dB，降一点音量重新封装即可，画面不用重渲）。
"""
import argparse
import re
import subprocess
import sys

PEAK_MAX = -1.0


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate,nb_frames',
                        '-of', 'compact', str(path)], capture_output=True, text=True, check=True)
    return parse_probe(r.stdout)


def parse_probe(text):
    info = {'audio': False}
    for line in text.splitlines():
        kv = dict(p.split('=', 1) for p in line.split('|')[1:] if '=' in p)
        if line.startswith('stream') and kv.get('codec_type') == 'video':
            num, den = kv['r_frame_rate'].split('/')
            info.update(width=int(kv['width']), height=int(kv['height']), fps=round(int(num) / int(den), 3), frames=int(kv.get('nb_frames') or 0))
        elif line.startswith('stream') and kv.get('codec_type') == 'audio':
            info['audio'] = True
        elif line.startswith('format'):
            info['duration'] = round(float(kv['duration']), 3)
    return info


def parse_loudness(stderr):
    """ffmpeg ebur128=peak=true 的汇总：返回 (整体响度 LUFS, 峰值 dBFS)。"""
    lufs = re.findall(r'I:\s+(-?[\d.]+) LUFS', stderr)
    peak = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', stderr)
    return (float(lufs[-1]) if lufs else None, float(peak[-1]) if peak and peak[-1] != '-inf' else None)


def parse_black(stderr):
    return [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', stderr)]


def main(argv=None):
    ap = argparse.ArgumentParser(description='成片检查')
    ap.add_argument('video')
    ap.add_argument('--duration', type=float, help='期望时长（秒）')
    a = ap.parse_args(argv)
    info = probe(a.video)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', a.video, '-af', 'ebur128=peak=true', '-vf', 'blackdetect=d=0.1:pix_th=0.1',
                        '-f', 'null', '-'], capture_output=True, text=True)
    lufs, peak = parse_loudness(r.stderr)
    black = parse_black(r.stderr)
    print(f"{info.get('width')}×{info.get('height')}  {info.get('fps')} fps  {info.get('frames')} 帧  {info.get('duration')} 秒  "
          f"音轨 {'有' if info['audio'] else '无'}  响度 {lufs} LUFS  峰值 {peak} dBFS  黑帧 {black or '无'}")
    ok = info['audio'] and not black
    if a.duration and abs(info['duration'] - a.duration) > 1 / (info.get('fps') or 30):
        print(f'时长不对：期望 {a.duration} 秒'); ok = False
    if peak is not None and peak > PEAK_MAX:
        drop = round(peak - PEAK_MAX + .2, 1)
        print(f'峰值超过 {PEAK_MAX} dBFS，降 {drop} dB 重新封装：\n  ffmpeg -i {a.video} -i film/out/audio.wav -map 0:v -map 1:a -c:v copy '
              f'-af volume=-{drop}dB -c:a aac -b:a 320k -ar 48000 -movflags +faststart 成片.mp4')
        ok = False
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
