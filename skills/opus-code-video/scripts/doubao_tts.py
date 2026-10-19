"""豆包语音合成 2.0（火山引擎新版控制台 API Key）

  一句：python3 doubao_tts.py one <音色ID> <输出.mp3> "文本" [--rate 0]
  整稿：python3 doubao_tts.py lines <音色ID> <项目目录> [--rate 0]   读 voice/旁白.txt，每行一句 → voice/lines/NN.mp3

用异步接口：先提交，再轮询，下载音频，并把完整查询结果（含逐字时间戳 sentences[].words[]）存成 <输出>.json，
字幕和节拍都按它对时。Key 读环境变量 DOUBAO_SPEECH_API_KEY，或 ~/.config/volc-speech/api-key，不打印。
火山引擎是国内服务，固定直连，不走会话代理。
"""
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SUBMIT = 'https://openspeech.bytedance.com/api/v3/tts/submit'
QUERY = 'https://openspeech.bytedance.com/api/v3/tts/query'
RESOURCE = 'seed-tts-2.0'          # 豆包语音合成模型 2.0 的音色（ID 以 _uranus_bigtts 结尾）
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HINT = {
    'load grant: requested grant not found': '密钥类型或请求头不对：新版控制台的 API Key 只用 X-Api-Key，不要再带 App-Id/Access-Key',
    'speaker permission denied': '音色 ID 不对，或这个音色不属于 seed-tts-2.0',
    'quota exceeded': '额度用完或超并发',
}


def api_key():
    k = os.environ.get('DOUBAO_SPEECH_API_KEY', '').strip()
    if not k:
        f = Path.home() / '.config/volc-speech/api-key'
        k = f.read_text().strip() if f.exists() else ''
    if not k:
        raise SystemExit('没有豆包语音的 API Key：请用户在豆包语音控制台创建后存到 ~/.config/volc-speech/api-key（权限 600）')
    return k


def headers(key):
    return {'X-Api-Key': key, 'X-Api-Resource-Id': RESOURCE, 'X-Api-Request-Id': str(uuid.uuid4()),
            'Content-Type': 'application/json', 'X-Control-Require-Usage-Tokens-Return': 'true'}


def submit_body(text, voice, rate=0, uid='opus-code-video'):
    return {'user': {'uid': uid}, 'unique_id': str(uuid.uuid4()), 'req_params': {
        'text': text, 'speaker': voice,
        'audio_params': {'format': 'mp3', 'sample_rate': 24000, 'speech_rate': rate, 'enable_timestamp': True}}}


def explain(data):
    msg = data.get('message', '')
    hint = next((v for k, v in HINT.items() if k in msg), '')
    return f"豆包语音报错：code {data.get('code')} {msg}" + (f'（{hint}）' if hint else '')


def post(url, body, key):
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method='POST', headers=headers(key))
    try:
        with OPENER.open(req, timeout=60) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read() or b'{}')
    if data.get('code') != 20000000:
        raise RuntimeError(explain(data))
    return data


def synth(text, voice, out, rate=0, key=None):
    key = key or api_key()
    task = post(SUBMIT, submit_body(text, voice, rate), key)['data']['task_id']
    for _ in range(120):
        time.sleep(1.5)
        q = post(QUERY, {'task_id': task}, key)
        st = q.get('data', {}).get('task_status')
        if st == 2:
            break
        if st == 3:
            raise RuntimeError(f"合成失败：{q.get('message')}")
    else:
        raise RuntimeError('等了 3 分钟还没合成完')
    with OPENER.open(q['data']['audio_url'], timeout=120) as r:
        Path(out).write_bytes(r.read())
    Path(f'{out}.json').write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')
    return q


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    rate = 0
    if '--rate' in a:
        i = a.index('--rate')
        rate = int(a[i + 1])
        del a[i:i + 2]
    if len(a) == 4 and a[0] == 'one':
        _, voice, out, text = a
        synth(text, voice, out, rate)
        print(f'{out}  {len(text)} 字')
    elif len(a) == 3 and a[0] == 'lines':
        _, voice, proj = a
        proj = Path(proj)
        lines = (proj / 'voice/旁白.txt').read_text(encoding='utf-8').strip().split('\n')
        (proj / 'voice/lines').mkdir(parents=True, exist_ok=True)
        key = api_key()
        with cf.ThreadPoolExecutor(4) as ex:
            jobs = {ex.submit(synth, s, voice, proj / f'voice/lines/{i:02d}.mp3', rate, key): i for i, s in enumerate(lines)}
            for j in cf.as_completed(jobs):
                j.result()
        print(f'{len(lines)} 句，共 {sum(len(s) for s in lines)} 字 → {proj / "voice/lines"}')
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
