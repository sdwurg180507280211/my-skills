"""以配音为准重排节拍表：python3 retime.py <项目目录>

读 film/cues_base.json（没有配音时的节拍）里的 narration 配置和 voice/lines/NN.mp3.json（豆包返回的逐字时间戳），
把每一段拉长到装得下这一句（够长的段不动），段内事件按比例平移，写出 film/cues.json，
并加上 voice（每句音频放在哪、说话区间）和 subs（按标点切好的字幕及起止时间）。

narration 配置示例（段落边界写事件名，"pull.0" 表示 ev.pull[0]，"duration" 是片尾）：
  "narration": {
    "lines": "voice/旁白.txt",
    "bounds": [0, "ch1_tag", "ch2_tag", "total", "end_title", "duration"],
    "place": [{"seg": 0, "lead": 0.55}, {"seg": 1, "lead": 0.15},
              {"seg": 2, "anchor_word": "四", "pre": 0.25}, {"seg": 4, "lead": 0.3}],
    "tail": 0.5, "end_hold": 1.2, "show": {"点 com": ".com"}
  }
place 按句子顺序一一对应。普通句子放在第 seg 段开头往后 lead 秒；带 anchor_word 的句子让这个字正好落在第 seg 段的结尾
（例如数字砸下的那一刻），第 seg 段要装得下这个字之前的话，下一段要装得下之后的话。
"""
import json
import re
import sys
from pathlib import Path

PUNCT = '，。：？、！；'
AFTER_ANCHOR = .4          # 锚点字之后的话说完，再留多少秒
MERGE_GAP = .35            # 相邻字幕空隙小于这个值就接上，避免闪烁


def resolve(ev, duration, ref):
    """段落边界：数字原样；"name" 取 ev[name]；"name.0" 取 ev[name][0]；"duration" 是片长。"""
    if isinstance(ref, (int, float)):
        return float(ref)
    if ref == 'duration':
        return float(duration)
    name, _, idx = ref.partition('.')
    v = ev[name]
    return float(v[int(idx)] if idx else v)


def speech_span(words):
    return words[0]['startTime'], words[-1]['endTime']


def segment_needs(bounds, place, words, tail=.5, end_hold=1.2):
    """每段至少要多长。words[i] 是第 i 句的逐字时间戳。"""
    need = [0.0] * (len(bounds) - 1)
    last = len(need) - 1
    for i, p in enumerate(place):
        s0, s1 = speech_span(words[i])
        k = p['seg']
        if 'anchor_word' in p:
            w = anchor_time(words[i], p['anchor_word'])
            need[k] = max(need[k], p.get('pre', .25) + (w - s0))
            if k + 1 <= last:
                need[k + 1] = max(need[k + 1], (s1 - w) + AFTER_ANCHOR)
        else:
            need[k] = max(need[k], p.get('lead', .3) + (s1 - s0) + (end_hold if k == last else tail))
    return need


def anchor_time(words, ch):
    for w in words:
        if w['word'].startswith(ch):
            return w['startTime']
    raise ValueError(f'句子里找不到锚点字 {ch!r}')


def build_warp(bounds, need):
    """返回 (新的段落边界, warp 函数)。段长 = max(原长, 需要的长度)，段内线性拉伸。"""
    new_len = [max(b - a, n) for a, b, n in zip(bounds, bounds[1:], need)]
    nb = [bounds[0]]
    for L in new_len:
        nb.append(nb[-1] + L)

    def warp(t):
        for k in range(len(bounds) - 1):
            if t <= bounds[k + 1] or k == len(bounds) - 2:
                return round(nb[k] + (t - bounds[k]) * new_len[k] / (bounds[k + 1] - bounds[k]), 3)
    return nb, warp


def warp_all(x, warp):
    if isinstance(x, list):
        return [warp_all(v, warp) for v in x]
    return warp(x)


def subtitles(line, words, t0, show=None):
    """按标点把一句切成几条字幕，时间取每条第一个字的开始和最后一个字的结束（加上音频放置位置 t0）。"""
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if w['word'] and w['word'][-1] in PUNCT:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    text = line
    for a, b in (show or {}).items():
        text = text.replace(a, b)
    parts = [p.strip() for p in re.split(f'[{PUNCT}]', text) if p.strip()]
    marks = re.findall(f'[{PUNCT}]', text)
    if len(parts) != len(chunks):
        raise ValueError(f'字幕切分对不上：{parts} vs {["".join(w["word"] for w in c) for c in chunks]}')
    return [{'t': [round(t0 + c[0]['startTime'], 3), round(t0 + c[-1]['endTime'], 3)],
             'text': p + ('？' if k < len(marks) and marks[k] == '？' else '')}
            for k, (p, c) in enumerate(zip(parts, chunks))]


def merge_gaps(subs, gap=MERGE_GAP):
    for a, b in zip(subs, subs[1:]):
        if 0 < b['t'][0] - a['t'][1] < gap:
            a['t'][1] = b['t'][0]
    return subs


def retime(base, lines, words):
    """base: cues_base.json 的内容；lines: 每句原文；words: 每句的逐字时间戳。返回新的 cues。"""
    cfg = base['narration']
    ev0 = base['ev']
    bounds = [resolve(ev0, base['duration'], r) for r in cfg['bounds']]
    place = cfg['place']
    if len(place) != len(lines):
        raise ValueError(f'narration.place 有 {len(place)} 项，旁白有 {len(lines)} 句')
    need = segment_needs(bounds, place, words, cfg.get('tail', .5), cfg.get('end_hold', 1.2))
    nb, warp = build_warp(bounds, need)
    ev = {k: warp_all(v, warp) for k, v in ev0.items()}
    voice, subs = [], []
    for i, p in enumerate(place):
        s0, s1 = speech_span(words[i])
        if 'anchor_word' in p:
            start = nb[p['seg'] + 1] - (anchor_time(words[i], p['anchor_word']) - s0)
        else:
            start = nb[p['seg']] + p.get('lead', .3)
        t0 = round(start - s0, 3)                      # 音频文件开头有一小段静音，文件要比说话早放
        voice.append({'i': i, 'file': f'voice/lines/{i:02d}.mp3', 'at': t0, 'speech': [round(t0 + s0, 3), round(t0 + s1, 3)]})
        subs += subtitles(lines[i], words[i], t0, cfg.get('show'))
    out = dict(base, duration=round(nb[-1], 3), ev=ev, voice=voice, subs=merge_gaps(subs))
    out['note'] = '由 retime.py 从 cues_base.json 和配音时间戳生成，不要手改；改节拍请改 cues_base.json'
    return out, bounds, nb


def load_words(path):
    q = json.loads(Path(path).read_text(encoding='utf-8'))
    return [w for s in q['data']['sentences'] for w in s['words']]


def main(argv=None):
    proj = Path((argv or sys.argv[1:] or ['.'])[0]).resolve()
    base = json.loads((proj / 'film/cues_base.json').read_text(encoding='utf-8'))
    lines = (proj / base['narration'].get('lines', 'voice/旁白.txt')).read_text(encoding='utf-8').strip().split('\n')
    words = [load_words(proj / f'voice/lines/{i:02d}.mp3.json') for i in range(len(lines))]
    out, bounds, nb = retime(base, lines, words)
    (proj / 'film/cues.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"时长 {base['duration']} → {out['duration']} 秒，字幕 {len(out['subs'])} 条")
    for k in range(len(bounds) - 1):
        if nb[k + 1] - nb[k] > bounds[k + 1] - bounds[k] + 1e-6:
            print(f'  第 {k} 段 {bounds[k]:g}–{bounds[k + 1]:g}：{bounds[k + 1] - bounds[k]:.2f} → {nb[k + 1] - nb[k]:.2f} 秒')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
