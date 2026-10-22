#!/usr/bin/env bash
# 新建一个代码动画工程：bash new_project.sh <工程目录> [风格，默认 sticker-explainer]
#
# 做的事：
#   1. 稀疏克隆 mg-styles-15（MIT，只取渲染器、配乐工具和提示词）到 $MG_STYLES_DIR（默认 ~/.cache/mg-styles-15）
#   2. 工程里复制渲染器 harness/（附许可证），lib/ 软链接到克隆的配乐工具
#   3. 复制所选风格的示例片（film/、voice/、cover.py）
#   4. npm 装 puppeteer-core；建 .venv 装配乐依赖（Intel Mac 用 numba 0.60 + llvmlite 0.43 + numpy<2.1，新版没有 x86 安装包）
#   5. 下载 OFL 字体 Noto Sans SC / Inter / JetBrains Mono 到 assets/fonts/
# 已存在的东西不覆盖。联网请求按本机网络规则走系统路由。
set -euo pipefail
PROJ="${1:?用法：bash new_project.sh <工程目录> [风格]}"
STYLE="${2:-sticker-explainer}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
MG="${MG_STYLES_DIR:-$HOME/.cache/mg-styles-15}"
EX="$SKILL/styles/$STYLE/example"
[ -d "$EX" ] || { echo "没有这个风格：$STYLE（看 $SKILL/styles/）"; exit 2; }

if [ ! -d "$MG/.git" ]; then
  mkdir -p "$(dirname "$MG")"
  git clone --filter=blob:none --sparse https://github.com/Vincentwei1021/mg-styles-15.git "$MG"
  git -C "$MG" sparse-checkout set harness lib prompts
fi

mkdir -p "$PROJ"/{harness,assets/fonts,film/out,voice/lines}
cd "$PROJ"
[ -f harness/render.mjs ] || cp "$MG/harness/render.mjs" "$MG/harness/preview.html" harness/
[ -f harness/LICENSE-mg-styles-15 ] || cp "$MG/LICENSE" harness/LICENSE-mg-styles-15
[ -e lib ] || ln -s "$MG/lib" lib
for f in film/index.html film/cues_base.json film/audio.py voice/旁白.txt cover.py; do
  [ -e "$f" ] || cp "$EX/$f" "$f"
done
[ -f package.json ] || cat > package.json <<'EOF'
{ "private": true, "type": "module", "scripts": { "render": "node harness/render.mjs film" },
  "dependencies": { "puppeteer-core": "25.12.0" } }
EOF
[ -d node_modules ] || npm install --registry=https://registry.npmjs.org/ --no-audit --no-fund

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  if [ "$(uname -s)-$(uname -m)" = "Darwin-x86_64" ]; then
    .venv/bin/pip install -q --only-binary=:all: "numba==0.60.0" "llvmlite==0.43.0" "numpy<2.1" scipy soundfile pedalboard pyloudnorm matplotlib librosa pillow
  else
    .venv/bin/pip install -q numba numpy scipy soundfile pedalboard pyloudnorm matplotlib librosa pillow
  fi
fi

G=https://raw.githubusercontent.com/google/fonts/main/ofl
fetch() { [ -s "assets/fonts/$2" ] || curl -sSL --retry 3 --max-time 600 -C - -o "assets/fonts/$2" "$G/$1"; }
fetch 'notosanssc/NotoSansSC%5Bwght%5D.ttf' NotoSansSC-VF.ttf
fetch 'inter/Inter%5Bopsz,wght%5D.ttf' Inter-VF.ttf
fetch 'jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf' JetBrainsMono-VF.ttf
fetch notosanssc/OFL.txt OFL-NotoSansSC.txt
fetch inter/OFL.txt OFL-Inter.txt
fetch jetbrainsmono/OFL.txt OFL-JetBrainsMono.txt
echo "工程就绪：${PROJ}（风格 ${STYLE}）。先出关键帧：node harness/render.mjs film --stills 1,5,10"
