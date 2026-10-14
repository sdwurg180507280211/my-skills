# Claude 本地数据清理与恢复

适用于 macOS 和 Windows。下文路径以 macOS 写法为例，Windows 对应路径和命令见 [平台差异](platforms.md)。

## 一、发现与分类

先确认用户要的是释放空间、清缓存、移除旧登录、删除历史，还是完整重置。配置根目录默认 `~/.claude`，设置了 `CLAUDE_CONFIG_DIR` 时以它为准。

按目录统计占用（命令见 [平台差异](platforms.md)），再按下表分类。目录名随版本变化，不存在的如实报告。

| 数据 | 常见位置 | 风险 | 处置 |
|---|---|---|---|
| 已结束任务的临时文件 | `jobs/<id>/tmp`（`state.json` 中 `state` 为 `done`） | 低 | 确认一次后移走；先看里面有没有用户要留的成品 |
| 缓存和临时快照 | `cache`、`paste-cache`、`shell-snapshots`、`telemetry` | 低 | 确认一次后移走 |
| 会话与编辑历史 | `projects/<项目>/*.jsonl`、`file-history`、`history.jsonl` | 中 | 按项目或时间列清单确认；移走后无法 `--resume` |
| 插件缓存 | `plugins/cache` | 中 | 移走后需重新安装或同步插件 |
| 配置与扩展 | `settings*.json`、`~/.claude.json`、`CLAUDE.md`、`skills`、`agents`、`hooks`、memory | 高 | 默认保留；只改确认冲突的键 |
| CLI 认证 | 官方登录状态；macOS 钥匙串，Windows `.claude\.credentials.json` | 高 | 用官方退出流程，单独确认 |
| 桌面 App 数据 | `~/Library/Application Support/Claude` 及对应 Caches | 高 | 缓存与登录分开确认 |

已知旧 `org_id` 时，只在 Claude 的存储目录内搜索，报告命中的文件类别和数量，不输出标识本身；逐个确认用途后再处理。

## 二、清单与备份

给出清单：路径、大小、动作、恢复方式。目标必须是解析后的具体路径，拒绝 `~`、`~/.claude` 整体、项目根目录等宽泛目标和未展开的变量。

- 低风险项：移入废纸篓即视为备份，不另做副本。
- 会话历史、配置：移走前备份到私有目录（权限 700），确认备份可读后再执行。
- 完整重置：整体备份 `~/.claude` 和 `~/.claude.json`；`skills` 下的软链接只备份链接本身，不复制链接目标。
- 凭据不做备份：macOS 钥匙串不在文件备份范围内；Windows 的 `.credentials.json` 备份时排除。删除后靠重新登录恢复。
- 清理会话或配置前，请用户退出相关 CLI/App 会话，避免文件被重新写入。只清已结束任务的临时文件和缓存时不需要。

## 三、执行

普通文件移到废纸篓中的 `claude-cleanup-<时间戳>/`（Windows 移入回收站，做法见 [平台差异](platforms.md)），保留源路径到目标路径的对照，不覆盖同名文件、不清空废纸篓或回收站。移动失败时停下报告，不改用永久删除。逐项记录成功或失败。

## 四、凭据与登录

先用 `/logout` 或 `claude auth logout` 退出，再查是否还有残留。macOS 查钥匙串，常见服务名是 `Claude Code-credentials`；Windows 查 `%USERPROFILE%\.claude\.credentials.json` 是否已被移除，不读取或输出其内容。不调用 `security ... -w`/`-g` 输出密码，不批量删除所有含 Claude 的条目；确需删除时针对核实过的单个条目。

重新登录后用 `claude auth status` 或 `/status` 核对认证方式和账号，账号信息留在本机。

## 五、恢复与验收

按对照表把文件从废纸篓或回收站移回；目标位置已有新文件时先比较，不整目录覆盖。验收：目标已移走、空间已释放，`skills`、hooks、设置仍可用，CLI 和 App 正常启动，认证方式正确。
