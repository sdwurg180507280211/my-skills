"""火山方舟 API 公共部分：读取密钥、直连（不走环境代理）、带重试的 JSON 请求。"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://ark.cn-beijing.volces.com/api/v3"
KEY_FILE = Path("~/.config/volc-ark/api-key").expanduser()

# 方舟服务在国内。会话环境若设了 HTTP(S)_PROXY（例如给 AI 工具用的专用出口），国内请求会绕路：
# 实测 600 KB 上传直连约 1 秒，走代理 35~75 秒并常被 SSL 断开。因此固定直连，交给系统路由（含 TUN）。
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))


class ArkError(Exception):
    """接口返回了错误（4xx/5xx）。这类请求没有建成任务，不收费。"""


def load_key():
    key = os.environ.get("ARK_API_KEY", "").strip()
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text().strip()
    if not key:
        raise ArkError(f"缺少方舟 API Key：设置环境变量 ARK_API_KEY，或写入 {KEY_FILE}（权限 600）")
    return key


def request(method, path, body=None, tries=5):
    """GET 遇到网络错误自动重试。POST 只在 429 限流时重试：网络中断时任务可能已经建成，
    由调用方先查任务列表再决定，避免重复扣费。"""
    headers = {"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    timeout = 300 if method == "POST" else 120
    for i in range(tries):
        req = urllib.request.Request(BASE + path, method=method, headers=headers, data=data)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read()[:800].decode(errors="replace")
            if e.code == 429 and i < tries - 1:
                time.sleep(20 * (i + 1))
                continue
            raise ArkError(f"HTTP {e.code}: {msg}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if method == "POST" or i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def download(url, out, tries=5):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    for i in range(tries):
        try:
            urllib.request.urlretrieve(url, out)
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if i == tries - 1:
                raise
            time.sleep(5)
