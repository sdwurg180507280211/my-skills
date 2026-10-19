"""把旁白叠到底乐上：python3 mix_voice.py <项目目录>（用项目的 .venv 跑，需要 numpy、soundfile、pyloudnorm）

读 film/out/bed.wav（audio.py 按节拍表合成的配乐和音效，已经在说话处压低）和 film/cues.json 的 voice，
每句先统一到 -16 LUFS，放到节拍表给的位置；整体归一到 -14 LUFS，再用 alimiter 把采样峰值压在 -1.8 dBFS，
写出 film/out/audio.wav（渲染器会自动用它）。压成 AAC 后峰值会再冒一点，成片要用 qc.py 复查。
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

VOICE_LUFS, TARGET_LUFS, LIMIT = -16.0, -14.0, 0.81      # 0.81 ≈ -1.8 dBFS


def placement(at, n_voice, n_mix, sr):
    """音频放在 at 秒处：返回 (mix 起点, 片段起点, 长度)。at 为负时裁掉片段开头多出的静音。"""
    i0 = int(round(at * sr))
    skip = max(0, -i0)
    i0 = max(0, i0)
    return i0, skip, max(0, min(n_mix - i0, n_voice - skip))


def main(argv=None):
    import numpy as np
    import soundfile as sf
    import pyloudnorm as pyln
    proj = Path((argv or sys.argv[1:] or ['.'])[0]).resolve()
    cues = json.loads((proj / 'film/cues.json').read_text(encoding='utf-8'))
    mix, sr = sf.read(proj / 'film/out/bed.wav', always_2d=True)
    meter = pyln.Meter(sr)
    with tempfile.TemporaryDirectory() as td:
        for v in cues.get('voice', []):
            wav = f"{td}/{v['i']:02d}.wav"
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(proj / v['file']), '-ac', '2', '-ar', str(sr),
                            '-af', 'highpass=f=90,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120', wav], check=True)
            x, _ = sf.read(wav, always_2d=True)
            x = x * 10 ** ((VOICE_LUFS - meter.integrated_loudness(x)) / 20)
            i0, skip, n = placement(v['at'], len(x), len(mix), sr)
            mix[i0:i0 + n] += x[skip:skip + n]
        mix *= 10 ** ((TARGET_LUFS - meter.integrated_loudness(mix)) / 20)
        pre = f'{td}/pre.wav'
        sf.write(pre, mix, sr, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', pre, '-af', f'alimiter=limit={LIMIT}:attack=3:release=60:level=disabled',
                        '-c:a', 'pcm_s24le', str(proj / 'film/out/audio.wav')], check=True)
    out, _ = sf.read(proj / 'film/out/audio.wav', always_2d=True)
    print(f"含旁白 {len(out) / sr:.2f} 秒  {meter.integrated_loudness(out):.2f} LUFS  峰值 {20 * np.log10(np.abs(out).max()):.2f} dBFS")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
