#!/usr/bin/env python3
"""小团子Java 草稿入口客户端：查询交付状态，或提交一篇文章建草稿并等待结果。

用法：
  deliver_draft.py check   <仓库根> <文章目录>
  deliver_draft.py deliver <仓库根> <文章目录> <article.html> <metadata.json> [--dry-run]

环境变量：PUBLISH_API_BASE（草稿入口地址，以 /publish-api 结尾）、PUBLISH_API_TOKEN。
正文图按 Markdown 出现顺序取 imgs/ 下的图片（不含 cover.png），封面固定 imgs/cover.png。
metadata.json：{"title": ..., "author": "小团子Java", "summary": ...}。入口只建草稿，不发布。
提交后只轮询结果，不重复提交；结果不明时交给人工核对，避免重复建稿。
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request


def article_files(repo, article_dir):
    folder = os.path.join(repo, article_dir)
    mds = [n for n in os.listdir(folder) if n.endswith('.md') and n != '配图需求.md']
    if len(mds) != 1:
        raise SystemExit('expected exactly one article .md in %s, got %s' % (article_dir, mds))
    text = open(os.path.join(folder, mds[0]), encoding='utf-8').read()
    images = [p for p in re.findall(r'!\[[^\]]*\]\((imgs/[^)\s]+)\)', text) if p != 'imgs/cover.png']
    return folder, mds[0], images


def read(folder, rel):
    with open(os.path.join(folder, rel), 'rb') as f:
        return f.read()


def check_payload(repo, article_dir):
    folder, md, images = article_files(repo, article_dir)
    digest = lambda rel: hashlib.sha256(read(folder, rel)).hexdigest()  # noqa: E731
    return {'article_directory': article_dir,
            'body': {'path': md, 'sha256': digest(md)},
            'images': [{'path': p, 'sha256': digest(p)} for p in images],
            'cover': {'path': 'imgs/cover.png', 'sha256': digest('imgs/cover.png')}}


def deliver_payload(repo, article_dir, html_path, meta_path, dry_run=False):
    folder, md, images = article_files(repo, article_dir)
    b64 = lambda rel: base64.b64encode(read(folder, rel)).decode()  # noqa: E731
    commit = subprocess.check_output(['git', '-C', repo, 'rev-parse', 'HEAD']).decode().strip()
    return {'article_directory': article_dir, 'git_commit': commit, 'dry_run': dry_run,
            'body_markdown': {'path': md, 'content_b64': b64(md)},
            'images': [{'path': p, 'content_b64': b64(p)} for p in images],
            'cover': {'path': 'imgs/cover.png', 'content_b64': b64('imgs/cover.png')},
            'metadata': json.load(open(meta_path, encoding='utf-8')),
            'html': open(html_path, encoding='utf-8').read()}


def call(method, path, payload=None):
    base, token = os.environ['PUBLISH_API_BASE'].rstrip('/'), os.environ['PUBLISH_API_TOKEN']
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
        'User-Agent': 'xiaotuanzi-deliver/1'})  # 默认 Python UA 会被 Cloudflare 拦截
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {'error': 'non-JSON response', 'body': raw[:300]}


def main():
    if len(sys.argv) < 4 or sys.argv[1] not in ('check', 'deliver'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'check':
        code, resp = call('POST', '/v1/check', check_payload(sys.argv[2], sys.argv[3]))
        print(json.dumps({'http': code, **resp}, ensure_ascii=False))
        sys.exit(0 if code == 200 else 1)
    repo, article_dir, html_path, meta_path = sys.argv[2:6]
    code, resp = call('POST', '/v1/deliveries',
                      deliver_payload(repo, article_dir, html_path, meta_path, '--dry-run' in sys.argv))
    if code != 202:
        print(json.dumps({'http': code, 'response': resp}, ensure_ascii=False))
        sys.exit(1)
    job = resp['job_id']
    for _ in range(120):  # 最多约 20 分钟
        time.sleep(10)
        code, status = call('GET', '/v1/jobs/' + job)
        if status.get('status') in ('finished', 'failed'):
            print(json.dumps(status, ensure_ascii=False, indent=2))
            sys.exit(0 if status['status'] == 'finished' else 1)
    print(json.dumps({'job_id': job, 'status': 'still_running_check_later'}, ensure_ascii=False))
    sys.exit(2)


if __name__ == '__main__':
    main()
