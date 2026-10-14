---
name: claude-maintenance
description: 清理和维护 Claude Code、Claude App 与专用 Chrome：释放 ~/.claude 空间、清理会话和缓存、排查认证/接口/代理冲突、修复 essential-traffic-only，配置 Claude 的 Clash 分流与固定出口、出口守护、CLI 受保护入口和 OAuth 回调，以及创建、迁移和检查 Claude 专用浏览器。用户要求清理 Claude、检查 Claude 配置或网络出口、建立专用浏览器时使用；通用网络和 Clash 问题使用 china-proxy，普通编程任务使用对应开发技能。
---

# Claude 环境清理与配置维护

本地清理只处理本机数据，不会清除服务器上的账号记录，也不影响账号资格。

## 选择资料

- 清空间、缓存、历史会话、旧组织资料、桌面登录或钥匙串：读取 [清理与恢复](references/cleanup-and-recovery.md)。
- 官方订阅登录、第三方 API、shell/项目设置覆盖、代理残留、登录报错：读取 [认证与配置](references/auth-and-config.md)。
- `essential-traffic-only`、非必要流量开关、云端任务、`/fork` 与会话分叉：读取 [功能开关与会话](references/features-and-sessions.md)。
- 创建或调整 Claude 专用 Chrome、桌面启动入口、CLI 登录浏览器：读取 [专用浏览器创建流程](references/browser-setup.md)。
- Claude 域名分流、固定出口组、Claude DNS 策略、专用 listener：读取 [Claude 分流与固定出口](references/clash-routing.md)；国内直连名单、通用 DNS、链式代理和网络模式检测使用 `china-proxy`。
- 出口守护、`claude-safe` 等受保护 CLI 入口、OAuth 回调失败、经受保护入口升级模型：读取 [出口守护与 CLI 入口](references/fixed-exit.md)。
- 新电脑迁移、多客户端联网验证：读取 [客户端与迁移](references/clients-and-migration.md)。

## 安全底线

1. 不打印凭据、完整环境变量、完整设置文件、org_id、邮箱、Cookie 或 OAuth 回调参数，只报告键名、类别和状态。
2. 修改或移走前给出清单（路径、大小、动作、恢复方式），用户确认后执行；低风险的缓存和已结束任务临时文件确认一次即可，认证、钥匙串和完整重置逐项确认。
3. 普通文件移到废纸篓中带时间戳的目录，不用 `rm`；钥匙串删除后只能重新登录恢复，事先说明。
4. 不移走当前会话正在使用的文件（本会话的 `projects` 记录、运行中任务的 `jobs` 目录）；不跟随 `skills` 软链接进入技能仓库。
5. 只改本次要修的键，改完开新进程验证，其他设置和认证保持不变。

## 只读设置审计

`scripts/audit_settings.py` 读取指定的 JSON 设置文件（可选加上当前进程环境），只输出相关键名、类别和开关状态，不输出值、不联网、不改文件。

```bash
python3 scripts/audit_settings.py --settings ~/.claude/settings.json --settings <项目>/.claude/settings.local.json
python3 scripts/audit_settings.py --include-process-env
```

结果是逐个文件的内容，不是 Claude 合并后的有效配置。

## 交付

说明发现的问题、已做的修改、备份位置和恢复方法，以及哪些已验证、哪些未验证。运行结果和备份留在本机私有目录，不进入公开仓库。
