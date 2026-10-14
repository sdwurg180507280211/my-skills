# 客户端联网与新电脑迁移

这里只列 Claude 各客户端要分别验证的点。Claude 分流和固定出口见 [clash-routing.md](clash-routing.md)，出口守护和 CLI 入口见 [fixed-exit.md](fixed-exit.md)，专用浏览器见 [browser-setup.md](browser-setup.md)；通用网络检测用 `china-proxy`。

## 各客户端分别验证

| 客户端 | 核对 |
|---|---|
| 前台 CLI | 实际二进制或 wrapper、有效配置、请求出口 |
| 后台会话与 `/fork` | 后台进程的实际环境，与前台不一定相同 |
| Claude App | 从 Dock 启动时不继承终端环境和 CLI wrapper |
| 专用浏览器 profile | 独立数据目录、桌面启动参数、实际入口与出口、OAuth 本机回调 |
| 手机 | 当前连接的实际出口；用户没用手机就跳过 |

多设备要求同一出口时，逐台查公网 IP；同一订阅或同名节点不代表出口相同。

## 新电脑迁移

1. 安装官方 CLI/App，重新登录；不复制旧电脑的认证文件和钥匙串。
2. 按用户要求恢复 `skills`、hooks、设置，检查其中硬编码的旧路径。
3. 自定义启动器或 wrapper（如 `claude-safe`）不是官方功能，迁移时按新机器重新配置路径和端口。
4. 国内直连等通用 Clash 配置按 `china-proxy` 恢复，Claude 规则、专用 listener 和出口守护按本技能的参考重新配置。
5. 验证登录、本机回调和实际出口，记录已测和未测项。
