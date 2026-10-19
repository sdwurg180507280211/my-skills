# 按下回车之后的 1 秒 — 配乐和音效，全部按 cues.json 的时间点合成
# 配乐：mgaudio 的 explainer（马林巴科技解说风），音效：UI 点击、贴纸、印章、嗖声；高潮前抽空再砸下
import sys, os, json
D = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.insert(0, os.path.join(D, '..', 'lib', 'audio'))
import mgaudio as mg
from mgaudio import recipes, sfx

C = json.load(open(D + 'cues.json'))
E = C['ev']
DUR = C['duration']

# 第 1 章开始时进入正式段落，结尾字卡出现时收尾
m = recipes.explainer(duration=DUR, key='D', drop=E['fly1'][1], outro=E['end_title'])
print('bpm', round(m.form.bpm, 2), 'tracks', list(m.tracks))
S = m.sfx
key_note = lambda t, i=0, up=12: m.form.chord_at(t)[i % len(m.form.chord_at(t))] + up

# ---- 钩子：回车键砸下，片名两下 ----
S(sfx.swish(dur=.3, seed=1), at=.28, gain=-8, pan=.4)
S(sfx.impact(kind='punch', size=.8), at=E['enter_land'], gain=-2, pan=.3)
S(sfx.click('hard'), at=E['enter_land'] + .02, gain=-2, pan=.3)
S(sfx.boom(dur=1.2, f0=52), at=E['enter_land'], gain=-8)
S(sfx.text_hit('slam'), at=E['title1'], gain=-3)
S(sfx.text_hit('slam', seed=2), at=E['title2'], gain=-1)
S(sfx.pen('marker', dur=.4, seed=3), at=E['title2'] + .35, gain=-12, pan=-.2)
S(sfx.swish(dur=.24, seed=4), at=E['sub'] + .1, gain=-12, pan=-.3)
S(sfx.pop('bubble', pitch=1.2), at=E['packet_out'], gain=-6, pan=.4)

# ---- 场景之间的飞行：嗖声峰值放在飞行中点 ----
for i, k in enumerate(['fly1', 'fly2', 'fly3', 'fly4', 'fly5', 'fly6']):
    a, b = E[k]
    S(sfx.whoosh(dur=b - a + .2, kind='swish', direction=1 if i % 2 == 0 else -1, peak=.5, seed=10 + i), at=(a + b) / 2, gain=-5)

# ---- 章节标签：弹出 + 记号笔下划线 ----
for i, k in enumerate(['ch1_tag', 'ch2_tag', 'ch3_tag', 'ch4_tag', 'ch5_tag', 'ch6_tag']):
    S(sfx.pop('mouth', pitch=1.0 + .05 * i), at=E[k] + .05, gain=-5)
    S(sfx.pen('marker', dur=.4, seed=20 + i), at=E[k] + .42, gain=-14, pan=-.2)

# ---- ① 读懂网址 ----
S(sfx.blip(note=key_note(E['https'], 0), kind='sine'), at=E['https'] + .1, gain=-8)
S(sfx.blip(note=key_note(E['https'], 2), kind='sine'), at=E['https'] + .25, gain=-9)
for i, t in enumerate(E['cache']):
    S(sfx.sticker_slap(seed=30 + i), at=t + .08, gain=-6, pan=-.25 + .5 * i)
for i, t in enumerate(E['cross']):
    S(sfx.stamp('rubber', seed=35 + i), at=t + .02, gain=-3, pan=-.25 + .5 * i)

# ---- ② DNS：每条消息出发一声、到达一声，回答的音高往上走 ----
for i, (a, b) in enumerate(E['dns']):
    S(sfx.swish(dur=.3, seed=40 + i), at=(a + b) / 2, gain=-15, pan=(-.3 if i % 2 else .3))
    S(sfx.blip(note=key_note(b, i, 12 + (12 if i % 2 else 0)), kind='sine'), at=b, gain=-9)
S(sfx.sticker_slap(seed=48), at=E['ip_land'], gain=-3, pan=-.3)
S(sfx.ding(note=key_note(E['ip_land'], 2, 24)), at=E['ip_land'], gain=-6, pan=-.3)

# ---- ③ TCP 三次握手：三下，越来越高，最后确认 ----
for i, (a, b) in enumerate(E['tcp']):
    S(sfx.swish(dur=.4, direction=(1 if i != 1 else -1), seed=50 + i), at=(a + b) / 2, gain=-12, pan=(.3 if i != 1 else -.3))
    S(sfx.blip(note=key_note(b, i, 24), kind='tri'), at=b, gain=-6, pan=(.4 if i != 1 else -.4))
S(sfx.ui('confirm'), at=E['tcp_ok'], gain=-4)

# ---- ④ TLS：证书检查、盖章、两把钥匙合成、锁扣上 ----
for i, (a, b) in enumerate(E['tls']):
    S(sfx.swish(dur=.4, direction=(1 if i == 0 else -1), seed=60 + i), at=(a + b) / 2, gain=-12, pan=(.3 if i == 0 else -.3))
    S(sfx.blip(note=key_note(b, i, 24), kind='tri'), at=b, gain=-6)
S(sfx.sticker_slap(seed=63), at=E['tls'][1][1], gain=-8, pan=-.3)
S(sfx.hud_scan(dur=.6, seed=64), at=E['cert_check'] + .1, gain=-14, pan=-.3)
S(sfx.stamp('seal', seed=65), at=E['cert_ok'] + .02, gain=-2, pan=-.3)
S(sfx.swish(dur=.5, seed=66), at=E['keys'] - .25, gain=-10)
S(sfx.shimmer_hit(note=key_note(E['keys'], 0, 12)), at=E['keys'], gain=-5)
S(sfx.click('switch'), at=E['lock'], gain=-2, pan=.35)
S(sfx.impact(kind='metal', size=.4), at=E['lock'], gain=-9, pan=.35)

# ---- ⑤ 请求与响应：齿轮转动时滴答 ----
a, b = E['req']
S(sfx.swish(dur=.5, seed=70), at=(a + b) / 2, gain=-11, pan=.2)
S(sfx.blip(note=key_note(b, 0, 24), kind='tri'), at=b, gain=-6, pan=.4)
w0, w1 = E['work']
n = int((w1 - w0) / .15)
for i in range(n):
    S(sfx.tick('clock'), at=w0 + i * .15, gain=-16 + 4 * i / max(1, n - 1), pan=.4)
a, b = E['resp']
S(sfx.swish(dur=.6, direction=-1, seed=71), at=(a + b) / 2, gain=-10, pan=-.2)
S(sfx.sticker_slap(seed=72), at=b, gain=-3, pan=-.4)
S(sfx.ding(note=key_note(b, 1, 24)), at=b, gain=-8, pan=-.4)

# ---- ⑥ 画出页面：敲代码、节点逐个弹出（上行音阶）、上色、盖章 ----
S(sfx.typing(n_keys=8, rate=14, kind='typewriter', seed=80), at=E['html'], gain=-12, pan=-.4)
d0, d1 = E['dom']
for i in range(6):
    t = d0 + i * (d1 - d0) / 6
    S(sfx.blip(note=key_note(t, i, 12 + 12 * (i // 3)), kind='sine'), at=t + .05, gain=-9, pan=-.1 + .05 * i)
S(sfx.pop('bubble', pitch=1.1), at=E['css'] + .05, gain=-7)
l0, l1 = E['layout']
for i in range(6):
    S(sfx.click('soft'), at=l0 + i * (l1 - l0) / 6 + .03, gain=-14, pan=.35)
p0, p1 = E['paint']
for i in range(6):
    S(sfx.pop('bubble', pitch=.9 + .08 * i), at=p0 + i * (p1 - p0) / 6 + .03, gain=-11, pan=.35)
S(sfx.stamp('rubber', seed=85), at=E['page_done'] + .02, gain=-2, pan=.35)
S(sfx.ding(note=key_note(E['page_done'], 0, 24)), at=E['page_done'], gain=-7, pan=.35)

# ---- 拉远看全程：大嗖声，数据包经过每一站时叮一下 ----
a, b = E['pull']
S(sfx.whoosh(dur=b - a + .3, kind='air', direction=0, peak=.45, seed=90), at=a + (b - a) * .45, gain=-3)
r0, r1 = E['replay']
# 和画面一样按 inOutCubic 推进，算出经过 6 站的时刻
import math
def inv_inout(y):        # inOutCubic 的反函数
    return (y / 4) ** (1 / 3) if y < .5 else 1 - ((2 - 2 * y) ** (1 / 3)) / 2
# 线路和 index.html 里的 routePts 一致；各站在线路上的位置 = 到该站的长度 / 总长
ST = [(1190, 382), (2400, 372), (4790, 372), (4790, 1872), (2490, 1872), (290, 1872)]
route = [ST[0], (1190, 200), (2400, 200), ST[1], (2400, 200), (4790, 200), ST[2], (4790, 200), (6700, 200), (6700, 1700),
         (4790, 1700), ST[3], (4790, 1700), (2490, 1700), ST[4], (2490, 1700), (290, 1700), ST[5]]
cum = [0.0]
for p_, q_ in zip(route, route[1:]):
    cum.append(cum[-1] + math.dist(p_, q_))
st = [cum[i] / cum[-1] for i in (0, 3, 6, 11, 14, 17)]
for i, f in enumerate(st):
    t = r0 + (r1 - r0) * inv_inout(f)
    S(sfx.ding(note=key_note(t, i, 24), dur=.5), at=t, gain=-10, pan=-.5 + .2 * i)
a, b = E['fly7']
S(sfx.whoosh(dur=b - a + .2, kind='swish', direction=-1, peak=.5, seed=91), at=(a + b) / 2, gain=-5)

# ---- 高潮：耗时条扫过，越扫越密的滴答；抽空 3 帧后砸下 441 ----
s0, s1 = E['sweep']
for i in range(24):
    f = (i + 1) / 24
    t = s0 + (s1 - s0) * inv_inout(f)
    S(sfx.tick('hi'), at=t, gain=-14 + 6 * f, pan=-.6 + 1.2 * f)
tot = E['total']
S(sfx.riser(dur=1.6, kind='hybrid', end='cut'), at=tot - .1, gain=-6)
S(sfx.impact(kind='punch', size=1.0), at=tot, gain=2)
S(sfx.boom(dur=1.8), at=tot, gain=-2)
S(sfx.sticker_slap(seed=95), at=tot, gain=-2)
S(sfx.click('soft'), at=E['note'] + .05, gain=-14)
# 配乐增益曲线 = 高潮前的抽空 和 旁白让路（说话时压低 8 dB）取较低的那个
def suck(t):
    pts = [(0, 0), (tot - .9, 0), (tot - .5, -8), (tot - .11, -8), (tot - .1, -40), (tot - .004, -40), (tot, 0), (DUR, 0)]
    for (a, ga), (b, gb) in zip(pts, pts[1:]):
        if a <= t <= b:
            return ga + (gb - ga) * (t - a) / max(b - a, 1e-6)
    return 0
SPEECH = [v['speech'] for v in C.get('voice', [])]
def duck(t, depth=-8, pre=.15, post=.25, ramp=.12):
    g = 0
    for a, b in SPEECH:
        a, b = a - pre, b + post
        if a - ramp <= t <= b + ramp:
            k = min(1, (t - (a - ramp)) / ramp, ((b + ramp) - t) / ramp)
            g = min(g, depth * max(0, k))
    return g
m.group('music').automate('gain', [(round(t * .02, 3), round(min(suck(t * .02), duck(t * .02)), 2)) for t in range(int(DUR / .02) + 1)])

# ---- 结尾 ----
a, b = E['fly8']
S(sfx.whoosh(dur=b - a + .2, kind='air', direction=0, peak=.5, seed=96), at=(a + b) / 2, gain=-6)
S(sfx.text_hit('slam', seed=97), at=E['end_title'] + .05, gain=-5)
S(sfx.swish(dur=.3, seed=98), at=E['end_sub'] + .1, gain=-14)
S(sfx.ding(note=key_note(E['sign'], 0, 24)), at=E['sign'], gain=-7)
t = E['sign'] + .1
while t < DUR - .4:                     # 结尾回车键每 2 秒轻按一下
    S(sfx.click('hard'), at=t, gain=-18, pan=0)
    t += 2

m.master_kw.update(tilt=.4)
os.makedirs(D + 'out', exist_ok=True)
res = m.export(D + 'out/bed.wav', lufs=-16, tp=-2, spectrogram=D + 'out/qc_audio_spec.png')
print({k: v for k, v in res.items() if k not in ('spectrum', 'onsets')} if isinstance(res, dict) else res)
print(mg.hit_alignment(D + 'out/bed.wav', [E['enter_land'], E['title2'], E['ip_land'], E['tcp_ok'], E['lock'], E['page_done'], E['total']]))

# 旁白由 opus-code-video 的 scripts/mix_voice.py 叠上去（读 out/bed.wav 和 cues.json 的 voice，写 out/audio.wav）
