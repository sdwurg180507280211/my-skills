# 功能开关与会话分叉

## essential-traffic-only

创建云端任务或 Remote Control 时报 `Remote triggers unavailable: essential-traffic-only`，原因是设置或启动脚本里有 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`。先查这个开关，不必重做 GitHub 授权或重新登录。

`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`、`DISABLE_TELEMETRY`、`DISABLE_ERROR_REPORTING` 只要非空就生效，写成 `0` 或 `false` 也一样。要关闭就删除这个键。`DISABLE_GROWTHBOOK` 等其他开关有各自的取值规则。

处理步骤：

1. 用 `scripts/audit_settings.py` 和 shell 配置检查，找出所有来源（含启动脚本模板，它可能重新写入）。
2. 删除需要解除的键，其他隐私开关按用户意愿保留。
3. 新开进程，用 `claude doctor` 或一次最小请求验证；需要时再实际创建云端任务确认。

解除本地开关后，云端任务仍可能因 GitHub 权限、套餐或组织策略失败，需分别排查。

## 会话分叉方式

| 入口 | 作用 |
|---|---|
| `--resume <ID> --fork-session` | 加载已有历史，生成新会话 ID，在新终端独立聊天 |
| `/branch [name]` | 当前终端切换到对话分支，原对话保留 |
| `/fork [prompt]` | Agent View 开启时复制为独立后台会话；带 prompt 会立即开始工作 |
| `--cloud` / 云端会话 | 任务在云端执行，不继承本机代理和设置 |

这些方式都不隔离项目文件；需要独立工作区时另用 worktree。后台会话可能有独立的启动环境，前台验证通过不代表后台也走同一代理。命令以当前版本的 `/help` 和官方 [命令表](https://code.claude.com/docs/en/commands) 为准。
