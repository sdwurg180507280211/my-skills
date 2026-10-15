# 平台差异：macOS 与 Windows

主文档的步骤与平台无关；这里集中放路径、命令和安装做法。Windows 上标注「待实机验证」的项，第一次在 Windows 上使用时实测并回写本文件。

## 执行命令的 shell

- Windows 原生 Claude Code 装了 [Git for Windows](https://git-scm.com/downloads/win) 后，Bash 工具走 Git Bash，PowerShell 工具同时可用（claude.ai 账号默认开启）；没装 Git 时只有 PowerShell。建议安装 Git for Windows。
- 约定：通用步骤在 zsh/Git Bash 下执行；Windows 系统操作（环境变量、快捷方式、回收站、端口、进程、路由）用 PowerShell，在 Git Bash 里用 `powershell.exe -NoProfile -Command '...'` 调用。
- Python：macOS `python3`，Windows `py -3`（无窗口运行用 `pythonw.exe`）。

## 路径

| 项目 | macOS | Windows |
|---|---|---|
| Claude 配置根目录 | `~/.claude` | `%USERPROFILE%\.claude` |
| 根配置 | `~/.claude.json` | `%USERPROFILE%\.claude.json` |
| CLI 凭据 | 钥匙串（写入失败时 `~/.claude/.credentials.json`） | `%USERPROFILE%\.claude\.credentials.json` |
| 官方 CLI | `~/.local/bin/claude` | `%USERPROFILE%\.local\bin\claude.exe` |
| Claude App 数据 | `~/Library/Application Support/Claude` | `%APPDATA%\Claude`（待实机验证） |
| 守护配置 | `~/Library/Application Support/Claude Dedicated Guard/config.json` | `%APPDATA%\Claude Dedicated Guard\config.json` |
| Clash Verge 数据 | `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev` | `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev` |
| Chrome | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| 废纸篓 | `~/.Trash` | 各盘的回收站 |

Windows 的凭据是普通文件：清理或备份时按敏感文件处理（权限受限的私有目录），不放进仓库或聊天；恢复靠重新 `/login`，不从备份复制凭据。

## 常用命令

| 用途 | macOS | Windows PowerShell |
|---|---|---|
| 目录占用 | `du -sh ~/.claude/* \| sort -rh` | `Get-ChildItem "$env:USERPROFILE\.claude" -Directory -Force \| ForEach-Object { [pscustomobject]@{Name=$_.Name; MB=[math]::Round(((Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue \| Measure-Object Length -Sum).Sum)/1MB,1)} } \| Sort-Object MB -Descending` |
| 移入回收站 | `mv <路径> ~/.Trash/claude-cleanup-<时间戳>/` | `Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory('<路径>','OnlyErrorDialogs','SendToRecycleBin')`（文件用 `DeleteFile`） |
| 命令来源 | `type claude` | `Get-Command claude -All` |
| 监听端口 | `lsof -nP -iTCP -sTCP:LISTEN` | `Get-NetTCPConnection -State Listen` |
| 用户环境变量 | `~/.zshrc`、`~/.zprofile` 等 | `[Environment]::GetEnvironmentVariable('HTTPS_PROXY','User')`，系统级用 `'Machine'`；另查 `$PROFILE` 和 Git Bash 的 `~/.bashrc` |
| 目标路由 | `route -n get <IP>` | `Find-NetRoute -RemoteIPAddress <IP>` |
| 系统代理 | `scutil --proxy` | `Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'`（看 `ProxyEnable`、`ProxyServer`） |

回收站没有逐项的命令行恢复，移入前在私有目录记下原路径对照；需要可脚本恢复时改为移到 `%USERPROFILE%\claude-cleanup-<时间戳>\` 隔离目录（事先说明）。

## 安装出口守护

### macOS

1. 系统 Python 没有 PyYAML 时：`python3 -m pip install --user pyyaml`。
2. 写守护配置（键见 [出口守护](fixed-exit.md)）。
3. `python3 <技能目录>/scripts/exit_guard.py install-wrappers --bin-dir <PATH 中的目录>`，把生成的 `claude-oauth-browser` 完整路径写入配置的 `browser_helper`。目标位置已有同名文件时先备份。
4. 需要直接敲 `claude` 时，在 `~/.zshrc` 加 `claude() { claude-safe "$@"; }`。
5. 桌面入口：建 `<名称>.app/Contents/MacOS/launch`（内容 `#!/bin/sh` 加 `exec /usr/bin/python3 '<exit_guard.py>' --config '<config.json>' browser`，加执行权限）和 `Contents/Info.plist`（`CFBundleExecutable` 为 `launch`），在 Finder 打开验证。

### Windows

1. 安装 Python 3（python.org 或 `winget install Python.Python.3.12`），再 `py -3 -m pip install --user pyyaml`。
2. 脚本引用技能目录里的 `exit_guard.py`；技能目录可能移动时，复制到 `%LOCALAPPDATA%\Claude Dedicated Guard\` 并记下来源版本。
3. 写配置到 `%APPDATA%\Claude Dedicated Guard\config.json`，JSON 里的反斜杠写成 `\\`。`clash_config` 指向 Clash Verge 数据目录下的 `clash-verge.yaml`，`claude_bin` 指向 `claude.exe`。
4. 生成 wrapper 并加入用户 PATH：

   ```powershell
   py -3 "<exit_guard.py>" install-wrappers --bin-dir "$env:USERPROFILE\bin"
   $p = [Environment]::GetEnvironmentVariable('Path', 'User')
   if ($p -notlike "*$env:USERPROFILE\bin*") { [Environment]::SetEnvironmentVariable('Path', "$p;$env:USERPROFILE\bin", 'User') }
   ```

   把 `claude-oauth-browser.cmd` 的完整路径写入配置的 `browser_helper`。新开终端后生效。
5. 简写：PowerShell `$PROFILE` 加 `function claude { claude-safe.cmd @args }`；Git Bash `~/.bashrc` 加 `claude() { claude-safe.cmd "$@"; }`。
6. 桌面快捷方式（用 `pythonw.exe`，不弹控制台窗口）：

   ```powershell
   $pyw = Join-Path (Split-Path (py -3 -c "import sys; print(sys.executable)")) 'pythonw.exe'
   $s = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:USERPROFILE\Desktop\Claude 专用.lnk")
   $s.TargetPath = $pyw
   $s.Arguments = '"<exit_guard.py>" --config "<config.json>" browser'
   $s.IconLocation = 'C:\Program Files\Google\Chrome\Application\chrome.exe,0'
   $s.Save()
   ```

7. 验证：`claude-safe --version`；`py -3 "<exit_guard.py>" status`；双击快捷方式打开状态页显示已确认出口。

### Windows 上脚本已处理的差异

- 判断进程是否存活用系统 API；Windows 的 `os.kill(pid, 0)` 会结束目标进程，不能用。
- 端口用独占绑定（`SO_EXCLUSIVEADDRUSE`），防止另一个程序绑定同一端口。
- 文件锁用 `msvcrt`，提示框用 `MessageBoxW`，查 Chrome 进程用 PowerShell CIM（结果缓存 5 秒，跳过带 `--type=` 的子进程）。
- 守护由 `pythonw` 运行、没有控制台，调用 PowerShell 时必须带 `CREATE_NO_WINDOW`，否则每 5 秒弹出一个命令行窗口（实测出现过）。
- 没有 SIGHUP：直接关掉终端窗口时 `claude-safe` 可能来不及删租约，守护按进程是否存活清理。

### Windows 实测（2026-10-15，Anaconda Python 3.9 + PyYAML 6.0，Clash Verge TUN）

- 已验证：链路检查读取 `clash-verge.yaml`（含中文和 emoji 节点名）、两个探针确认出口、经守护转发、停止后释放端口；TUN 开启时守护到 listener 的 loopback 连接正常；PowerShell CIM 查 Chrome 进程约 0.8 秒。
- 已验证：china-proxy 的 `detect_network.py` 判定 `mode: tun`，TUN 网卡名为 `Meta`，耗时约 3 秒。
- 待验证：Windows 版 Claude Code 是否调用 `BROWSER`（不调用时，登录页按 `c` 复制授权链接到专用 Chrome 打开）；提示框；双击快捷方式打开窗口（SSH 会话里看不到桌面窗口，需要用户在桌面上确认）。

### Windows 排查经验

- 快捷方式双击没反应：先用 `Test-Path` 检查快捷方式的目标和参数里的脚本是否存在；`pythonw.exe` 不显示报错，把同一条命令换成 `python.exe` 在终端里运行看错误。曾遇到别的工具建了快捷方式、却从未把程序装到它指向的目录。
- 守护检查失败时，分别用 `curl.exe -x http://127.0.0.1:7890` 测普通海外、`-x http://127.0.0.1:17891` 测专用 listener：两者都 502 说明 Clash 节点不可用；只有 17891 失败多半是落地节点没配前置（`dialer-proxy` 为空）。
- 不经代理访问 HTTPS 报 `CRYPT_E_REVOCATION_OFFLINE`、要等几十秒：是证书吊销检查访问海外失败，先修海外连通性；单次诊断可加 `--ssl-no-revoke`。
- 远程替换守护后要在用户桌面会话里重启：SSH 会话里启动的进程看不到也活不久。用一次性计划任务（`Register-ScheduledTask` 配 `-LogonType Interactive`，运行后 `Unregister-ScheduledTask`）启动 `exit_guard.py serve`；不要用 PowerShell 5.1 调 `schtasks /TR`，带空格的路径会被拆开。
- 执行策略默认是 Restricted，`$PROFILE` 不会加载（里面的 `claude` 函数也不生效）：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`。

### 从 Mac 远程排查 Windows

1. Windows 管理员 PowerShell：`Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`，`Set-Service sshd -StartupType Automatic; Start-Service sshd`；把默认 shell 设为 PowerShell（注册表 `HKLM:\SOFTWARE\OpenSSH` 的 `DefaultShell`）。
2. 为这台机器单独生成密钥；管理员账户的公钥写入 `%ProgramData%\ssh\administrators_authorized_keys` 并限制为 Administrators 和 SYSTEM 可访问；防火墙只放行局域网的 22 端口。
3. 远程命令用 `powershell -NoProfile -NonInteractive -OutputFormat Text -EncodedCommand <UTF-16LE base64>` 执行，避免引号转义、profile 报错和 CLIXML 输出；脚本里先设 `[Console]::OutputEncoding=[Text.Encoding]::UTF8`。Windows 自带的是 PowerShell 5.1，`foreach` 语句后不能直接接管道。
4. 大文件用 `scp` 传到用户目录再移动；编码命令受 32K 命令行长度限制。
5. SSH 会话里启动的程序不显示在用户桌面，GUI 结果由用户确认；递归遍历浏览器 profile 很慢，搜索时限制深度或目录。

## Clash Verge 在 Windows

- TUN 需要在设置里启用服务模式（或以管理员运行），开启后用 `Get-NetAdapter` 确认 Mihomo 的 TUN 网卡已启用，再用 `Find-NetRoute` 核对目标路由。
- 订阅脚本、规则扩展、listener 的做法与 macOS 相同，见 [Claude 分流](clash-routing.md) 和 china-proxy 的 Clash 参考。
- 用 china-proxy 的 `py -3 scripts/detect_network.py` 判断 TUN；它在 Windows 上读 `tasklist`、注册表和 `Find-NetRoute`，实测 TUN 网卡名为 `Meta`。
