---
name: cloudcli-device-onboarding
description: 把新的 Windows 或 Mac 接入 cloudcli：给设备建立到阿里云服务器的反向 SSH 隧道、分配端口、授权 cloudcli 公钥并验证。当用户说"把这台电脑接入 cloudcli""给设备建立到阿里云的反向隧道""cloudcli 新增设备""移除或迁移 cloudcli 设备""cloudcli 隧道连不上"时使用。局域网互访用 mac-windows-lan，应用部署用 github-aliyun-deploy。
---

# 把设备接入 cloudcli

cloudcli 运行在阿里云服务器上，通过 SSH 连接各台设备。设备没有公网地址，所以由设备主动到服务器建反向隧道，cloudcli 再经服务器本机端口连回设备。

本 skill 保存方法，不保存服务器地址、密码、私钥或端口表。服务器地址在运行时询问用户，或读取环境变量 `CLOUDCLI_SERVER`。

## 原理

```text
cloudcli ──ssh──▶ 127.0.0.1:<端口> ═══反向隧道═══▶ 设备:22（设备自己的 sshd）
         └─────── 阿里云服务器 ───────┘
                       ▲
                       └── 设备主动运行 ssh -N -R <端口>:localhost:22，登录用户 tunnel
```

- 隧道统一使用服务器上的专用用户 `tunnel`，它不能登录命令行。
- 每台设备一把专用密钥，`authorized_keys` 限制它只能开自己那一个端口。
- 新设备从 22024 起依次分配。22023 保留给 bjpc-windows，脚本不会分配。
- 服务器的 `/home/tunnel/.ssh/authorized_keys` 是唯一的端口记录，每行末尾的 `cloudcli-tunnel:<端口>:<设备名>` 就是登记表。需要查端口时读这个文件。

## 前置条件

1. 服务器已运行过 `server/init-tunnel-user.sh`。没有运行过时，让用户在自己的终端运行一次（路径相对于本 skill），并处理输出的警告：

   ```bash
   ssh root@<服务器> "bash -s" < server/init-tunnel-user.sh
   ```

2. 阿里云安全组已放行 22 端口。

脚本输出的 `Match User tunnel` 建议段要由用户决定是否加入 `sshd_config`，脚本不会自动修改。不加也能建隧道，但设备密钥可以用 `-L` 访问服务器本机端口，设备睡眠后端口也可能长时间被旧连接占着。

## 执行前询问

已经知道的不重复问：

- **设备名**：字母、数字、点、下划线、连字符，比如 `office-mac`。
- **cloudcli 公钥**：一行 `类型 base64 [注释]`，只是公钥，不是私钥。
- **服务器地址**：本仓库公开，地址不写进任何文件。环境变量 `CLOUDCLI_SERVER` 已设置时可以不问。

端口默认自动分配，只有用户明确要求时才传。

## 必须由用户亲手完成

AI 不能代做这几步，也不能保存或转述密码。只把准备好的命令交给用户，等用户告诉你结果：

- **输入 root 密码**：脚本登记公钥时，用户在自己的终端里输入。不要让用户把密码发到聊天里，不要用 `sshpass`、`expect` 或任何代填方式。
- **确认管理员权限**：Windows 上由用户自己打开管理员 PowerShell，不模拟点击 UAC。
- **在 Mac 上打开远程登录**：系统设置 → 通用 → 共享 → 远程登录。
- **在 cloudcli 里新增设备**：填脚本最后输出的地址、端口、用户名。

安装脚本检测到没有交互式终端时会直接退出。大多数 AI 工具的命令执行环境都不是交互式终端，所以默认让用户把命令粘贴到自己的窗口运行，再把输出发回来。

## 操作流程

两个脚本都可以重复运行，重复运行时密钥、端口、配置都沿用，不会重复添加，但需要再输入一次 root 密码。

运行前保留完整的 skill 目录，脚本要读取 `server/add-device-key.sh`。还没有这个目录时先克隆仓库：

```bash
git clone https://github.com/sdwurg180507280211/my-skills.git
cd my-skills/skills/cloudcli-device-onboarding
```

### Windows

在管理员 PowerShell 里，进入本 skill 目录后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1 -Server <服务器> -DeviceName <设备名> -CloudcliPubKey "<cloudcli 公钥>"
```

用户希望 SSH 登录后进入 PowerShell 时，加 `-SetPowerShellDefaultShell`。

脚本依次完成：检查管理员权限 → 安装并启动 sshd → 准备 `~\.ssh\cloudcli_tunnel_ed25519`（不动 `id_ed25519`）→ 登记公钥拿到端口 → 追加 `Host cloudcli-tunnel` → 生成 `~\cloudcli-tunnel.ps1` → 注册并启动计划任务 `CloudcliTunnel` → 授权 cloudcli 公钥 → 本机验证 → 输出汇总。

计划任务在用户登录时启动，所以电脑重启后要登录这个账号，隧道才会恢复。

运行脚本的账号就是 cloudcli 登录的账号。必须由这个账号登录桌面、自己以管理员身份运行；标准账号用别的管理员账号提权时，脚本会报错退出。

### Mac

在 Mac 自己的“终端”窗口，进入本 skill 目录后运行：

```bash
bash mac/setup.sh --server <服务器> --device-name <设备名> --cloudcli-pubkey "<cloudcli 公钥>"
```

脚本依次完成：检查 22 端口（没开时提示用户打开远程登录并等待）→ 准备 `~/.ssh/cloudcli_tunnel_ed25519` → 登记公钥拿到端口 → 追加 `Host cloudcli-tunnel` → 写入并加载 `~/Library/LaunchAgents/com.cloudcli.tunnel.plist` → 授权 cloudcli 公钥 → 本机验证 → 输出汇总。

Mac 睡眠时隧道会断开。需要随时可连时，让用户到“系统设置 → 电池/能源”关闭自动睡眠。

## 如何验证

按顺序验证，前一层不通过就不要宣称后一层成功。安装脚本只验证到第 1 层，后面几层要在服务器和 cloudcli 上确认：

1. **设备本机**：脚本结尾没有报错。它确认了 ssh 进程 10 秒内 PID 不变、已和服务器建立连接，这次启动后的日志里也没有 `remote port forwarding failed`。
2. **服务器上端口在监听，且只绑定本机**。地址应为 `127.0.0.1` 或 `[::1]`，不能是 `0.0.0.0`：

   ```bash
   ss -tln | grep ':<端口> '
   ```

3. **服务器上能连到设备的 sshd**。能看到 SSH 版本行就说明隧道通了：

   ```bash
   timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/<端口>; head -n 1 <&3'
   ```

4. **cloudcli 新增设备后能连接**，运行 `whoami`，核对返回的用户名。

需要确认限制是否生效时，在设备上试下面两条，都应该失败：

```bash
ssh cloudcli-tunnel                                      # 没有命令行
ssh -N -R 22999:localhost:22 -o BatchMode=yes cloudcli-tunnel   # 报 remote port forwarding failed
```

日志位置：Windows 是 `%USERPROFILE%\cloudcli-tunnel.log`，Mac 是 `~/Library/Logs/cloudcli-tunnel.log`。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 登记时报端口被其他设备登记或正在被监听 | 指定的端口已被占用 | 不传端口，让脚本自动分配 |
| 日志出现 `remote port forwarding failed` | 服务器上旧连接还占着端口（常见于睡眠、断网后），或端口和 `permitlisten` 不一致 | 在服务器运行 `ss -tlnp \| grep ':<端口> '` 查占用进程；确认是这台设备的旧连接后结束它。长期解决：配置 `ClientAliveInterval`（见前置条件）。不一致时核对 `authorized_keys` 那一行和设备上的端口 |
| 日志出现 `Permission denied (publickey)` | `AllowUsers` 或 `AllowGroups` 没有包含 `tunnel`，设备已被移除，或 `/home/tunnel/.ssh` 权限不对 | 重新运行 `init-tunnel-user.sh` 看警告。`AllowUsers` 要把 `tunnel` 加到现有行末尾并保留 root，改完 `sshd -t && systemctl reload sshd` |
| `UsePAM no` 时 `tunnel` 公钥登录被拒 | 账号被视为锁定 | 按 `init-tunnel-user.sh` 的提示运行 `usermod -p '*' tunnel` |
| `UNPROTECTED PRIVATE KEY FILE` 或 `Bad permissions` | 私钥权限过宽 | Mac：`chmod 600 ~/.ssh/cloudcli_tunnel_ed25519`。Windows：在 PowerShell 里运行 `icacls <私钥> /inheritance:r /grant "${env:USERNAME}:F" /grant "SYSTEM:F"` |
| 隧道通了，但 cloudcli 登录 Windows 被拒 | 管理员账号的公钥位置、权限或编码不对 | 公钥必须在 `C:\ProgramData\ssh\administrators_authorized_keys`，权限只有 Administrators 和 SYSTEM，编码不能是 UTF-16。重新运行 `setup.ps1` 可以修正。还要确认 `C:\ProgramData\ssh\sshd_config` 里 `Match Group administrators` 段没有被注释 |
| 隧道通了，但 cloudcli 登录 Mac 被拒 | `~/.ssh` 或 `authorized_keys` 权限不对，或远程登录限制了用户 | 目录 700、文件 600；在“远程登录”里确认当前用户被允许访问 |
| Mac 过一会儿就连不上 | Mac 睡眠导致隧道断开 | 关闭自动睡眠。唤醒后 launchd 会自动重连；如果重连报 `remote port forwarding failed`，按上面第二行处理 |
| 报 `Host cloudcli-tunnel` 配置不同 | 配置里已有同名段，脚本不覆盖 | 对比脚本输出的现有内容和预期内容，由用户决定后手动修改 |
| 报实际生效的配置不对 | `ssh` 配置先出现的值优先，靠前的 `Host *` 盖掉了设置 | 把 `Host cloudcli-tunnel` 段移到这些段之前 |
| `launchctl bootstrap` 报没有图形会话 | 从 SSH 运行且用户没有登录桌面 | 登录桌面后，在本机终端运行 |

## 移除设备

如果当前 AI 正是通过这条隧道连到这台设备，停掉隧道会断开自己。这时把设备端的命令交给用户在本机运行。

**服务器**：先核对，再删除对应的那一行：

```bash
cd /home/tunnel/.ssh
grep ' cloudcli-tunnel:<端口>:<设备名>$' authorized_keys
cp -p authorized_keys authorized_keys.bak
sed -i '/ cloudcli-tunnel:<端口>:<设备名>$/d' authorized_keys
ss -tlnp | grep ':<端口> '   # 已有的连接不会因删 key 断开，查到进程后结束它
```

**Windows**：

```powershell
Unregister-ScheduledTask -TaskName CloudcliTunnel -Confirm:$false
Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" | Where-Object { $_.CommandLine -like '*cloudcli-tunnel*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Remove-Item "$env:USERPROFILE\cloudcli-tunnel.ps1", "$env:USERPROFILE\cloudcli-tunnel.log"
Remove-Item "$env:USERPROFILE\.ssh\cloudcli_tunnel_ed25519", "$env:USERPROFILE\.ssh\cloudcli_tunnel_ed25519.pub"
```

**Mac**：

```bash
launchctl bootout "gui/$(id -u)/com.cloudcli.tunnel"
rm ~/Library/LaunchAgents/com.cloudcli.tunnel.plist ~/Library/Logs/cloudcli-tunnel.log
rm ~/.ssh/cloudcli_tunnel_ed25519 ~/.ssh/cloudcli_tunnel_ed25519.pub
```

然后手动删除设备 `~/.ssh/config` 里的 `Host cloudcli-tunnel` 段和授权文件里的 cloudcli 公钥，并在 cloudcli 里删除设备。

## 迁移 bjpc-windows

bjpc-windows 目前用 root 跑隧道，端口 22023。迁移后端口不变，cloudcli 里的设备配置不用改。

**尚未执行。** 用户明确要求迁移时才做，并且全程由用户在 bjpc-windows 本机窗口操作：第 3 步会断开经这条隧道的所有连接。第 4 步要输入 root 密码，第 3 步到第 5 步之间 cloudcli 连不上这台设备。

1. 在 bjpc-windows 的管理员 PowerShell 里生成专用密钥，提示输入口令时直接按两次回车（隧道要无人值守运行，不能设口令），然后查看公钥：

   ```powershell
   ssh-keygen -t ed25519 -C cloudcli-tunnel:bjpc-windows -f "$env:USERPROFILE\.ssh\cloudcli_tunnel_ed25519"
   Get-Content "$env:USERPROFILE\.ssh\cloudcli_tunnel_ed25519.pub"
   ```

2. 在服务器上手动登记。`add-device-key.sh` 不分配 22023，所以这一行要人工添加。只保留公钥的类型和 base64 两段：

   ```bash
   cd /home/tunnel/.ssh && cp -p authorized_keys authorized_keys.bak
   printf '%s\n' 'restrict,port-forwarding,permitlisten="localhost:22023" <类型> <base64> cloudcli-tunnel:22023:bjpc-windows' >> authorized_keys
   ```

3. 在 bjpc-windows 上找到旧隧道及其启动方式，先停用启动方式（计划任务、服务或启动项），再结束进程。否则它会重连并继续占着 22023：

   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" | Where-Object { $_.CommandLine -like '*22023*' } | Select-Object ProcessId, ParentProcessId, CommandLine
   ```

   然后在服务器确认 `ss -tln | grep ':22023 '` 已经没有输出。

4. 在 bjpc-windows 上运行安装脚本。服务器发现同名同钥的登记后，沿用 22023：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1 -Server <服务器> -DeviceName bjpc-windows -Port 22023 -CloudcliPubKey "<cloudcli 公钥>"
   ```

5. 按“如何验证”逐层确认，并确认 cloudcli 能正常连接。

6. 全部通过后，才从 `/root/.ssh/authorized_keys` 删除这台设备旧隧道用的那把公钥。先用 `ssh-keygen -lf` 核对指纹，确认它只用于这条隧道；操作时另外保留一个已登录的 root 会话。

**回滚**：第 5 步失败时，运行 `Unregister-ScheduledTask -TaskName CloudcliTunnel -Confirm:$false` 并结束新的 ssh 进程，恢复第 3 步停用的启动方式。旧的 root 公钥此时还没删，隧道可以恢复。

## 安全规则

- 不用 root 跑隧道。bjpc-windows 是待迁移的遗留情况，不能作为先例。
- 不开启 `GatewayPorts`。隧道端口只绑定服务器本机。
- 安全组不放行 220xx 端口，只放行 22。
- 私钥不离开生成它的设备。登记时只传公钥，不复制、不上传私钥。
- 任何地方都不能出现密码：仓库、日志、聊天、命令行参数、脚本、环境变量都不行。
- 每台设备一把专用密钥。不复用 `id_ed25519`，也不让多台设备共用。
- 不把服务器地址写进本仓库。仓库是公开的。
- 脚本不自动修改 `sshd_config`。改之前先让用户确认，改完先运行 `sshd -t`，并保留一个已登录的会话。
