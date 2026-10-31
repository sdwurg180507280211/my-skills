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
- 新设备从 22024 起分配。22023 保留给 bjpc-windows，脚本不会分配。
- 分配时跳过所有用户 `authorized_keys` 的 `permitlisten`、`sshd_config` 的 `PermitListen` 和正在监听的端口，所以其他设备离线时，它的端口也不会被分出去。
- `/home/tunnel/.ssh/authorized_keys` 记录走 `tunnel` 用户的设备，每行末尾的 `cloudcli-tunnel:<端口>:<设备名>` 就是登记表。早期设备可能用单独的隧道用户，要查全部端口时再看 `sshd_config` 的 `Match User` 段。

## 前置条件

1. 服务器已运行过 `server/init-tunnel-user.sh`。没有运行过时，由已有管理权限的一方运行一次（路径相对于本 skill），并处理输出的警告：

   ```bash
   ssh root@<服务器> "bash -s" < server/init-tunnel-user.sh   # 已有 root 密钥的电脑
   sudo bash server/init-tunnel-user.sh                       # 已经在服务器上
   ```

2. 阿里云安全组已放行 22 端口。

脚本输出的 `Match User tunnel` 建议段要由用户决定是否加入 `sshd_config`，脚本不会自动修改。不加也能建隧道，但设备密钥可以用 `-L` 访问服务器本机端口，设备睡眠后端口也可能长时间被旧连接占着。

## 执行前询问

已经知道的不重复问：

- **设备名**：字母、数字、点、下划线、连字符，比如 `office-mac`。
- **cloudcli 公钥**：一行 `类型 base64 [注释]`，只是公钥，不是私钥。
- **服务器地址**：本仓库公开，地址不写进任何文件。环境变量 `CLOUDCLI_SERVER` 已设置时可以不问。

端口默认自动分配，只有用户明确要求时才传。

## 登记权限

服务器通常设置了 `PermitRootLogin prohibit-password` 和 `PasswordAuthentication no`，新设备不能用 root 密码登录。不要为了接入设备重新打开密码登录，也不要把 root 私钥复制到新设备。

所以新设备只负责生成密钥和输出公钥，登记由已有服务器管理权限的一方完成：已有 root 密钥的电脑，或者服务器上有 sudo 权限的会话。当前 AI 有这个权限时可以直接登记，先告诉用户要写入的设备名和公钥。

## 必须由用户亲手完成

AI 不能代做这几步，只把准备好的内容交给用户，等用户告诉你结果。不要向用户要密码或私钥：

- **确认管理员权限**：Windows 上由用户自己打开管理员 PowerShell，不模拟点击 UAC。
- **在 Mac 上打开远程登录**：系统设置 → 通用 → 共享 → 远程登录。
- **在 cloudcli 里新增设备**：填脚本最后输出的地址、端口、用户名。

## 操作流程

接入分三步，脚本都可以重复运行，密钥和配置都沿用，不会重复添加：

1. **在设备上运行安装脚本，不传端口**。它生成隧道密钥，输出公钥和登记命令，退出码是 2。这时还没有接入。
2. **登记公钥**。有管理权限的一方运行输出的命令，最后一行就是端口。同一设备名和公钥重复登记时，退出码是 3，并输出原端口，不会新增记录。
3. **在设备上加端口再运行一次**，完成安装和本机验证。

服务器给 cloudcli 服务配了出站防火墙白名单时，第 2 步登记后还要把新端口加进去，否则 cloudcli 连不上。用户已授权这一步，由有服务器管理权限的一方直接完成，只加这台新设备的端口：

1. 用 `systemctl list-units | grep -i firewall` 找到防火墙服务，看它的 `ExecStart` 脚本。
2. 备份脚本，把端口加进每个 cloudcli 账号的白名单列表，然后用 sudo 重新运行脚本。
3. 用 cloudcli 账号（不用 root）按“如何验证”第 3 层的命令读版本行，确认放行。

还没有 skill 目录时先克隆仓库：

```bash
git clone https://github.com/sdwurg180507280211/my-skills.git
cd my-skills/skills/cloudcli-device-onboarding
```

### Windows

在管理员 PowerShell 里，进入本 skill 目录后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1 -Server <服务器> -DeviceName <设备名> -CloudcliPubKey "<cloudcli 公钥>"
```

登记后加 `-Port <端口>` 再运行一次。

用户希望 SSH 登录后进入 PowerShell 时，加 `-SetPowerShellDefaultShell`。

脚本依次完成：检查管理员权限 → 安装并启动 sshd → 准备 `~\.ssh\cloudcli_tunnel_ed25519`（不动 `id_ed25519`）→ 没有端口时输出登记命令并退出 → 追加 `Host cloudcli-tunnel` → 生成 `~\cloudcli-tunnel.ps1` → 注册并启动计划任务 `CloudcliTunnel` → 授权 cloudcli 公钥 → 本机验证 → 输出汇总。

计划任务在用户登录时启动，所以电脑重启后要登录这个账号，隧道才会恢复。

运行脚本的账号就是 cloudcli 登录的账号。必须由这个账号登录桌面、自己以管理员身份运行；标准账号用别的管理员账号提权时，脚本会报错退出。

### Mac

在 Mac 自己的“终端”窗口，进入本 skill 目录后运行：

```bash
bash mac/setup.sh --server <服务器> --device-name <设备名> --cloudcli-pubkey "<cloudcli 公钥>"
```

登记后加 `--port <端口>` 再运行一次。

脚本依次完成：检查 22 端口（没开时报错，让用户打开远程登录后重新运行）→ 准备 `~/.ssh/cloudcli_tunnel_ed25519` → 没有端口时输出登记命令并退出 → 追加 `Host cloudcli-tunnel` → 写入并加载 `~/Library/LaunchAgents/com.cloudcli.tunnel.plist` → 授权 cloudcli 公钥 → 本机验证 → 输出汇总。

Mac 睡眠时隧道会断开。需要随时可连时，让用户到“系统设置 → 电池/能源”关闭自动睡眠。

## 如何验证

按顺序验证，前一层不通过就不要宣称后一层成功。安装脚本只验证到第 1 层，后面几层要在服务器和 cloudcli 上确认：

1. **设备本机**：脚本结尾没有报错。它确认了 ssh 进程 10 秒内 PID 不变、已和服务器建立连接，这次启动后的日志里也没有 `remote port forwarding failed`。
2. **服务器上端口在监听，且只绑定本机**。地址应为 `127.0.0.1` 或 `[::1]`，不能是 `0.0.0.0`：

   ```bash
   ss -tln | grep ':<端口> '
   ```

3. **服务器上能连到设备的 sshd**。用 root 或 sudo 运行，能看到 SSH 版本行就说明隧道通了。cloudcli 的账号可能受出站白名单限制，它的失败不代表隧道不通：

   ```bash
   timeout 5 bash -c 'exec 3<>/dev/tcp/127.0.0.1/<端口>; head -n 1 <&3'
   ```

4. **cloudcli 新增设备后能连接**，运行 `whoami`，核对返回的用户名。报 `Connection refused` 而第 2、3 层都正常时，查服务器的出站白名单：`sudo iptables -S | grep -E 'owner|:<端口>|dport'`。

需要确认限制是否生效时，在设备上试下面两条，都应该失败：

```bash
ssh cloudcli-tunnel                                      # 没有命令行
ssh -N -R 22999:localhost:22 -o BatchMode=yes cloudcli-tunnel   # 报 remote port forwarding failed
```

日志位置：Windows 是 `%USERPROFILE%\cloudcli-tunnel.log`，Mac 是 `~/Library/Logs/cloudcli-tunnel.log`。Windows 的 ssh 运行时独占日志，读取报“文件被占用”说明 ssh 正在运行；要看内容时先 `Stop-ScheduledTask CloudcliTunnel`，看完再 `Start-ScheduledTask CloudcliTunnel`。

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 登记时报端口已被声明或正在被监听 | 指定的端口已被占用 | 不传端口，让脚本自动分配 |
| `ssh root@<服务器>` 报 `Permission denied` | 服务器禁止 root 密码登录，这台电脑没有 root 密钥 | 换到已有 root 密钥的电脑或服务器上的 sudo 会话登记，不要打开密码登录 |
| 日志出现 `remote port forwarding failed` | 服务器上旧连接还占着端口（常见于睡眠、断网后），或端口和 `permitlisten` 不一致 | 在服务器运行 `ss -tlnp \| grep ':<端口> '` 查占用进程；确认是这台设备的旧连接后结束它。长期解决：配置 `ClientAliveInterval`（见前置条件）。不一致时核对 `authorized_keys` 那一行和设备上的端口 |
| 日志出现 `Permission denied (publickey)` | 公钥还没登记，`AllowUsers` 或 `AllowGroups` 没有包含 `tunnel`，设备已被移除，或 `/home/tunnel/.ssh` 权限不对 | 重新运行 `init-tunnel-user.sh` 看警告。`AllowUsers` 要把 `tunnel` 加到现有行末尾并保留 root，改完 `sshd -t && systemctl reload sshd` |
| `UsePAM no` 时 `tunnel` 公钥登录被拒 | 账号被视为锁定 | 按 `init-tunnel-user.sh` 的提示运行 `usermod -p '*' tunnel` |
| `UNPROTECTED PRIVATE KEY FILE` 或 `Bad permissions` | 私钥权限过宽 | Mac：`chmod 600 ~/.ssh/cloudcli_tunnel_ed25519`。Windows：在 PowerShell 里运行 `icacls <私钥> /inheritance:r /grant "${env:USERNAME}:F" /grant "SYSTEM:F"` |
| 第 2、3 层正常，cloudcli 连端口报 `Connection refused` | 服务器的出站防火墙只放行白名单端口，新端口不在其中 | 用 `systemctl list-units \| grep -i firewall` 找到防火墙服务，看它的 `ExecStart` 脚本。按“操作流程”里的步骤把端口加入白名单 |
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

然后手动删除设备 `~/.ssh/config` 里的 `Host cloudcli-tunnel` 段，并在 cloudcli 里删除设备。

授权文件里的 cloudcli 公钥只在接入前没有这把公钥时才删。接入前就有的不要删，否则这台设备现有的 cloudcli 连接也会失效。

## 迁移旧设备

**先确认是否需要迁移。** 用 root 跑隧道的设备才要迁移。已经用专用用户并限制了单端口的设备（比如 bjpc-windows 的 22023）符合安全规则，不要动。在服务器上核对：

```bash
ss -tlnp | grep ':<端口> '                    # 端口在线时，看占用它的是 sshd: root 还是专用用户
grep -n -A8 '^Match User' /etc/ssh/sshd_config   # 查哪个专用用户声明了这个端口
```

确实在用 root 时，全程由用户在设备本机窗口操作：第 3 步会断开经这条隧道的所有连接，第 3 步到第 5 步之间 cloudcli 连不上这台设备。下面以 Windows 为例，Mac 换成 `mac/setup.sh` 对应的参数。

1. 运行一次 `setup.ps1`，不传端口，拿到隧道公钥。
2. 在服务器上手动登记，端口沿用原来的。脚本不接受已被占用的端口，所以这一行要人工添加，只保留公钥的类型和 base64 两段：

   ```bash
   cd /home/tunnel/.ssh && cp -p authorized_keys authorized_keys.bak
   printf '%s\n' 'restrict,port-forwarding,permitlisten="localhost:<端口>" <类型> <base64> cloudcli-tunnel:<端口>:<设备名>' >> authorized_keys
   ```

3. 在设备上找到旧隧道及其启动方式，先停用启动方式（计划任务、服务或启动项），再结束进程。否则它会重连并继续占着端口：

   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" | Where-Object { $_.CommandLine -like '*<端口>*' } | Select-Object ProcessId, ParentProcessId, CommandLine
   ```

   然后在服务器确认 `ss -tln | grep ':<端口> '` 已经没有输出。

4. 在设备上加 `-Port <端口>` 再运行一次 `setup.ps1`。
5. 按“如何验证”逐层确认，并确认 cloudcli 能正常连接。
6. 全部通过后，才从 `/root/.ssh/authorized_keys` 删除旧隧道用的那把公钥。先用 `ssh-keygen -lf` 核对指纹，确认它只用于这条隧道；操作时另外保留一个已登录的 root 会话。

**回滚**：第 5 步失败时，运行 `Unregister-ScheduledTask -TaskName CloudcliTunnel -Confirm:$false` 并结束新的 ssh 进程，恢复第 3 步停用的启动方式。旧的 root 公钥此时还没删，隧道可以恢复。

## 安全规则

- 不用 root 跑隧道。
- 不为接入设备打开 root 密码登录。登记由已有管理权限的一方完成。
- 不开启 `GatewayPorts`。隧道端口只绑定服务器本机。
- 安全组不放行 220xx 端口，只放行 22。
- 私钥不离开生成它的设备。登记时只传公钥，不复制、不上传私钥。
- 任何地方都不能出现密码：仓库、日志、聊天、命令行参数、脚本、环境变量都不行。
- 每台设备一把专用密钥。不复用 `id_ed25519`，也不让多台设备共用。
- 不把服务器地址写进本仓库。仓库是公开的。
- 脚本不自动修改 `sshd_config`。改之前先让用户确认，改完先运行 `sshd -t`，并保留一个已登录的会话。
