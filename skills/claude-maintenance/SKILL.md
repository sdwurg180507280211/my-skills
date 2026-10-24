---
name: claude-maintenance
description: 在 macOS 和 Windows 上清理、维护或卸载 Claude Code、Claude App 与专用 Chrome：处理缓存与历史、并存安装、登录凭据、认证/接口/代理冲突、essential-traffic-only、Clash 分流与固定出口、出口守护和 OAuth 回调。用户要求删除 Claude 软件及残留、清理 Claude、检查 Claude 配置或网络出口、建立专用浏览器时使用；通用网络和 Clash 问题使用 china-proxy，普通编程任务使用对应开发技能。
---

# Claude 环境清理与配置维护

支持 macOS 和 Windows。主文档的步骤与平台无关，路径、命令、shell 约定和 Windows 安装做法见 [平台差异](references/platforms.md)，涉及具体命令时先读它。

本地清理只处理本机数据，不会清除服务器上的账号记录，也不影响账号资格。

## 选择资料

- 删除程序和残留、合规卸载或停止使用：读取 [完整卸载](references/uninstall.md)。它与保留程序可用性的维护清理有不同验收标准。
- 清空间、缓存、历史会话、旧组织资料、桌面登录或钥匙串：读取 [清理与恢复](references/cleanup-and-recovery.md)。
- 官方订阅登录、第三方 API、shell/项目设置覆盖、代理残留、登录报错：读取 [认证与配置](references/auth-and-config.md)。
- 减少额外上报并保留云端任务、`essential-traffic-only`、非必要流量开关、`/fork` 与会话分叉：读取 [功能开关与会话](references/features-and-sessions.md)。
- 创建或调整 Claude 专用 Chrome、桌面启动入口：读取 [专用 Chrome](references/browser-setup.md)。
- Claude 域名分流、固定出口组、Claude DNS 策略、专用 listener：读取 [Claude 分流与固定出口](references/clash-routing.md)；国内直连名单、通用 DNS、链式代理和网络模式检测使用 `china-proxy`。
- 出口守护、`claude-safe` 受保护 CLI 入口、OAuth 回调失败、经受保护入口升级模型：读取 [出口守护与 CLI 入口](references/fixed-exit.md)，实现是 `scripts/exit_guard.py`。
- 新电脑迁移、多客户端联网验证：读取 [客户端与迁移](references/clients-and-migration.md)。

## 安全底线

1. 不打印凭据、完整环境变量、完整设置文件、org_id、邮箱、Cookie 或 OAuth 回调参数，只报告键名、类别和状态。
2. 修改前明确路径、大小、动作和恢复影响；已有具体清单且用户授权执行时，沿用该授权。用户明确覆盖配置、历史和指定凭据后，不再逐项询问；新发现超出授权的目标另行处理。
3. 维护清理默认将普通文件移入带时间戳的废纸篓/回收站。用户明确授权永久删除列明目标时，执行精确删除，不另留完整程序或令牌备份；凭据删除后只能重新认证。权限不足须如实处理，不以挪动或改名冒充删除。
4. 不移走当前会话正在使用的文件（本会话的 `projects` 记录、运行中任务的 `jobs` 目录）；不跟随 `skills` 软链接进入技能仓库。
5. 只改本次要修的键，改完开新进程验证，其他设置和认证保持不变。

## 脚本

`scripts/audit_settings.py` 只读审计：读取指定的 JSON 设置文件（可选加上当前进程环境），只输出相关键名、类别和开关状态，不输出值、不联网、不改文件。Windows 上把 `python3` 换成 `py -3`，路径换成 `%USERPROFILE%\.claude\settings.json`。

```bash
python3 scripts/audit_settings.py --settings ~/.claude/settings.json --settings <项目>/.claude/settings.local.json
python3 scripts/audit_settings.py --include-process-env
```

结果是逐个文件的内容，不是 Claude 合并后的有效配置。

`scripts/exit_guard.py` 是跨平台出口守护、专用 Chrome 启动器、受保护 CLI 入口和 OAuth helper，用法见 [出口守护](references/fixed-exit.md)。

## 交付

说明发现的问题、已做的修改、备份位置和恢复方法，以及哪些已验证、哪些未验证。运行结果和备份留在本机私有目录，不进入公开仓库。
