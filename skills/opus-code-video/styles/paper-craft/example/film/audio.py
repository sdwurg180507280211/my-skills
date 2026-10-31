# 纸艺立体示例的配乐和音效，时间点全部来自节拍表：lofi boombap + 钢琴，纸声、胶带、剪刀、纸箱、橡皮章
# 输出 film/out/bed.wav；有旁白时再跑 scripts/mix_voice.py
import sys, os, json
D = os.path.dirname(os.path.abspath(__file__)) + '/'
sys.path.insert(0, os.path.join(D, '..', 'lib', 'audio'))
import mgaudio as mg
from mgaudio import recipes, sfx

from mgaudio import samples as SM
_avail = SM.available
SM.available = lambda name: name != 'kalimba' and _avail(name)    # 本地样本库缺一个拇指琴音（D4），改用 FM 合成的

C = json.load(open(D + ('cues.json' if os.path.exists(D + 'cues.json') else 'cues_base.json')))
E = C['ev']
DUR = C['duration']

m = recipes.lofi(duration=DUR, key='F', flavor='boombap', keys='piano', drop=E['tear1'], outro=DUR - 1.2)
S = m.sfx
note = lambda t, i=0, up=12: m.form.chord_at(t)[i % len(m.form.chord_at(t))] + up

S(sfx.sticker_slap(seed=1), at=E['full'], gain=-4)
S(sfx.paper('rustle', dur=.5, seed=2), at=E['full'] + .02, gain=-12)
S(sfx.pop('mouth', pitch=1.0), at=E['what'], gain=-8, pan=.5)
S(sfx.scissors(seed=3), at=E['cut'][0] + .15, gain=-7, pan=.2)
S(sfx.scissors(seed=4), at=E['cut'][0] + .45, gain=-8, pan=-.1)
S(sfx.tape_rip(dur=.4, seed=5), at=E['tear1'] - .05, gain=-6, pan=-.2)
S(sfx.paper('flip', dur=.9, seed=6), at=E['tear1'] + .2, gain=-10, pan=-.4)
S(sfx.paper('crumple', dur=.35, seed=7), at=E['tear1'] + 1.22, gain=-9, pan=-.5)
S(sfx.paper('slide', dur=.5, seed=8), at=E['slide'][0], gain=-11)
for k, t in enumerate([E['new1'], E['new2']]):
    S(sfx.sticker_slap(seed=10 + k), at=t, gain=-7, pan=.1)
S(sfx.whoosh(dur=.9, kind='cloth', direction=-1, peak=.5, seed=12), at=sum(E['focus']) / 2, gain=-12)
S(sfx.paper('slide', dur=.6, seed=13), at=E['cil'] - .25, gain=-10, pan=-.3)
S(sfx.impact('thud', size=.6, seed=14), at=E['push'] - .05, gain=-8, pan=-.3)
S(sfx.paper('rustle', dur=.4, seed=15), at=E['push'], gain=-11, pan=-.3)
S(sfx.whoosh(dur=1.0, kind='cloth', direction=1, peak=.5, seed=16), at=sum(E['pull']) / 2, gain=-12)
S(sfx.pop('mouth', pitch=1.15), at=10.75, gain=-10, pan=.5)
S(sfx.paper('slide', dur=1.1, seed=17), at=E['scan'][0] + .1, gain=-14)
S(sfx.stamp('rubber', seed=18), at=E['unseen'], gain=-5, pan=-.4)
S(sfx.pop('mouth', pitch=.9), at=E['huh'], gain=-8, pan=.5)

SPEECH = [v['speech'] for v in C.get('voice', [])]


def duck(t, depth=-8, pre=.15, post=.25, ramp=.12):
    g = 0
    for x0, x1 in SPEECH:
        x0, x1 = x0 - pre, x1 + post
        if x0 - ramp <= t <= x1 + ramp:
            k = min(1, (t - (x0 - ramp)) / ramp, ((x1 + ramp) - t) / ramp)
            g = min(g, depth * max(0, k))
    return g


m.group('music').automate('gain', [(round(t * .02, 3), round(duck(t * .02), 2)) for t in range(int(DUR / .02) + 1)])
os.makedirs(D + 'out', exist_ok=True)
res = m.export(D + 'out/bed.wav', lufs=-16, tp=-2)
print('bpm', round(m.form.bpm, 1))
