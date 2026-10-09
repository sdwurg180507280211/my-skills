---
name: codex-dream-skin-fix
description: 排查并修复 Codex Dream Skin（Codex/ ChatGPT
  桌面端换肤工具）主题"不生效"的问题。当用户说"换肤没反应""主题没应用""Codex Dream Skin 注入失败""verify 报
  installed:false""红绡云梦/自定义主题切换后没显示""切换预设后界面没变"时使用。覆盖端口错位根因、诊断命令、让 Dream Skin 拥有
  CDP 会话的修复流程。
agent_created: true
---

# Codex Dream Skin 主题注入失败排查与修复

Codex Dream Skin（仓库 Fei-Away/Codex-Dream-Skin，装到 `~/.codex/codex-dream-skin-studio`）通过本机回环 CDP（默认端口 **9341**，绑定 `127.0.0.1`）把 CSS/背景注入到 Codex 的 `app://` renderer。常见故障是切换/热应用主题后界面没变。

## 何时用
- 运行 `verify-dream-skin-macos.sh` 后报 `installed:false`、`themeId:null`、`stylePresent:false`。
- 切换预设或自定义主题后，Codex 界面仍是官方外观。
- 状态文件 `state.json` 显示 `session:active`、主题正确，但页面实际无皮肤。

## 根因（关键）
Dream Skin 的设计前提是**它自己拉起 Codex**（`--remote-debugging-address=127.0.0.1 --remote-debugging-port=9341`），这样持久注入器 `injector.mjs --watch` 与渲染器的首次 `load` 事件同步，注入才会"焊死"。

如果 Codex 是被**外部工具**拉起的——如 browser-use / computer-use，或 `codex mcp add chrome-devtools -- --autoConnect --channel=stable`，或任何以 `--remote-debugging-port=9229` 启动的会话——Dream Skin 的 watcher 只能**事后 attach**，会错过渲染器首次 load 的注入窗口。one-shot `--once` 注入即使控制流成功，页面一 reload / 一切路由就丢，最终 `verify` 读到 `installed:false`。文件侧（state.json / 主题目录）全对，仅渲染器无注入标记。

## 诊断（先确认再动手）
```bash
# 1. Codex 实际启动参数与端口
pgrep -fl "Contents/MacOS/ChatGPT"
/usr/sbin/lsof -nP -iTCP:9229 -sTCP:LISTEN -t   # 外部会话常在这
/usr/sbin/lsof -nP -iTCP:9341 -sTCP:LISTEN -t   # Dream Skin 应在这

# 2. 注入器绑定端口（应都是 9341，且由 Dream Skin 自己拉起）
pgrep -fl "injector.mjs --watch"

# 3. state.json 的 port 必须与上面实际监听端口一致
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node \
  -e 'const s=require(require("os").homedir()+"/Library/Application Support/CodexDreamSkinStudio/state.json");console.log(s.port, s.appliedThemeId, s.appliedThemeName)'

# 4. 权威验证（解析 targets[0].result.installed）
~/.codex/codex-dream-skin-studio/scripts/verify-dream-skin-macos.sh --port <PORT> 2>/dev/null > /tmp/verify.json
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node -e 'const r=require("/tmp/verify.json");const t=(Array.isArray(r)?r:r.targets||[])[0];const res=t.result||{};console.log("pass:",res.pass,"installed:",res.installed,"themeId:",res.themeId)'
```
诊断要点：**state.json 的 port、Codex 实际端口、注入器绑定端口三者必须一致且都是 9341**。不一致（尤其 Codex 跑在 9229 而 state 记 9341，或反过来）就是故障信号。

## 修复流程（让 Dream Skin 拥有会话）
```bash
# 1. 暂停抢占 CDP 的 MCP（codex mcp 无 disable 子命令，只能 remove；恢复时重新 add）
codex mcp remove chrome-devtools

# 2. 干净退出 Codex（用 app 的 quit，避免脏退出）
/usr/bin/osascript -e 'tell application id "com.openai.codex" to quit'
for i in $(seq 1 40); do pgrep -f "Contents/MacOS/ChatGPT" >/dev/null 2>&1 || break; sleep 0.5; done
pgrep -f "Contents/MacOS/ChatGPT" >/dev/null 2>&1 && pkill -KILL -f "Contents/MacOS/ChatGPT"

# 3. 清理残留 watcher（旧 watcher 还挂着旧端口，会干扰新会话）
pkill -KILL -f "injector.mjs --watch"

# 4. 让 Dream Skin 自己拉起 Codex 并持有 9341（watcher 与 load 同步注入）
~/.codex/codex-dream-skin-studio/scripts/start-dream-skin-macos.sh --port 9341

# 5.（可选）若想显式切到目标主题；start 会用 state.json 的 appliedTheme 自动应用
#    自定义主题目录名形如 img-<时间戳>-<随机>，state 里 appliedThemeId 形如 custom-<时间戳>
~/.codex/codex-dream-skin-studio/scripts/switch-theme-macos.sh --id <preset-arina-hashimoto | img-xxxx | custom-xxxx>

# 6. 再 verify --port 9341，应 pass:true / installed:true / themeId 匹配
```

## 注意
- `codex mcp remove` 是不可逆的配置删除（无 disable），恢复需重新 `codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --autoConnect --channel=stable`。
- 若后续又用 browser-use / computer-use 类工具拉起 Codex，可能再次以 9229 抢会话，导致 Dream Skin 被覆盖。复发时重复上述修复。
- 切勿事后 attach watcher 到外部 9229 会话来"热应用"——只会得到文件侧成功、渲染器失败的假象。
- 还原官方外观：`restore-dream-skin-macos.sh --restore-base-theme --restart-codex`。
