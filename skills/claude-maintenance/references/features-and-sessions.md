# 功能开关与会话分叉

## 减少额外上报，优先保留云端任务

用户要保留云端任务或远程功能时，按功能分别关闭，不默认启用总开关。合并到原有 `env`，保留代理、模型和其他设置：

```json
{
  "env": {
    "DISABLE_ERROR_REPORTING": "1",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1"
  }
}
```

| 开关 | 影响 |
|---|---|
| `DISABLE_ERROR_REPORTING` | 单独关闭错误报告，不关闭功能开关获取 |
| `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | 单独关闭会话满意度调查 |
| `DISABLE_TELEMETRY` | 关闭使用指标，也关闭功能开关获取，可能影响远程功能；不是无副作用的指标开关 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 启用仅必要流量模式，可能直接阻断云端任务管理接口，报 `essential-traffic-only` |
| `DISABLE_GROWTHBOOK`、`DO_NOT_TRACK` | 按各自取值规则关闭功能开关获取，也要检查来源 |

处理时先备份，确认总开关及功能开关获取限制没有被 shell、项目设置或 wrapper 重新注入；不为了减少上报删除有效专用代理。改完比较非目标配置不变，再新启动 CLI。文件校验不等于真实云端任务验收；未创建/查询任务就标记未实测。

区分执行位置：本机 CLI 管理云端 routines 可能受本机开关影响；已保存的云端任务不因修改本机文件就自动暂停，浏览器也不读取 CLI 的 `settings.json`。云端 `/schedule`、本地 `/loop` 和桌面本地定时任务分别核对，不混称同一功能。

依据：官方 [Data usage](https://code.claude.com/docs/en/data-usage#telemetry-services)、[环境变量及功能开关获取](https://code.claude.com/docs/en/env-vars#features-that-need-feature-flag-fetching)、[Routines](https://code.claude.com/docs/en/routines)。这组区别于 2026-10-15 核对；维护时以当前版本和官方说明为准。

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
