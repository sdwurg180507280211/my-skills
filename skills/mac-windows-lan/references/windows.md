# Windows 作为被连接端

以下是选择性操作，不是每次全部重跑的安装脚本。先检查现状；变量必须来自本次选定的账号、接口或文件。

## 服务和权限

只读检查：`Get-Service sshd`、`Get-NetTCPConnection -State Listen -LocalPort 22`。服务存在与 Windows 可选组件安装状态是不同证据。

需要首次安装时，在管理员 PowerShell 查询 `Get-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`。仅对缺失状态运行 `Add-WindowsCapability`；已有安装操作时跟踪原任务。安装失败或未结束须明确报告，不依据 sshd.exe 存在认定成功。

组件可用且任务要求接收连接时：

```powershell
Set-Service -Name sshd -StartupType Automatic
Start-Service -Name sshd
```

需要更改默认终端时先读取 `HKLM:\SOFTWARE\OpenSSH` 的 `DefaultShell`，保留原值。用户选择 PowerShell 后，将值设为已存在的 powershell.exe 或 pwsh.exe 完整路径；不要覆盖用户已选的终端。配置文件默认在 `$env:ProgramData\ssh\sshd_config`，修改后用实际安装位置的 `sshd.exe -t` 检查，仅在需要时重启对应服务。

依据：[Microsoft OpenSSH 安装](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)、[Windows 服务端配置](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh-server-configuration)。

## 账号、公钥和 ACL

先确定远程登录的目标 Windows 账号，不使用提权后管理员身份的 `$env:USERPROFILE` 来猜目标用户目录。用户登录 Windows 的 PIN 不等同于 SSH 密码，不要索要 PIN。

查看实际 sshd_config 中的 AuthorizedKeysFile 和 Match。常见默认位置：

| 目标账号 | 生效的公钥文件 |
| --- | --- |
| 普通用户 | 该用户配置目录下 `.ssh\authorized_keys` |
| 属于本机 Administrators 且默认 Match 仍生效 | `$env:ProgramData\ssh\administrators_authorized_keys` |

通常只需写入实际生效的文件，不无条件向两个位置重复添加。处理密钥选项与注释时保留既有行；新公钥按“类型 + base64 数据”识别重复。确保一条公钥占一行、有换行且无 BOM；不要通过 ASCII 重写整个文件损坏原有注释。

管理员公钥文件应只允许 Administrators 与 SYSTEM。用 SID 避免中文/英文组名差异：

```powershell
# $keyFile 已确认是本次目标管理员公钥文件。
icacls.exe $keyFile /inheritance:r /grant:r '*S-1-5-32-544:F' /grant:r '*S-1-5-18:F'
```

该命令不会移除其他显式授权，必须检查最终 ACL；仅针对这个文件修复多余授权，保留变更前 ACL。普通用户文件检查目标用户所有权和写入权限，不套用管理员专用 ACL。

可以比较 .pub 文件指纹，禁止读取主机私钥或用户私钥正文。主机身份指纹示例：

```powershell
ssh-keygen.exe -lf "$env:ProgramData\ssh\ssh_host_ed25519_key.pub"
```

依据：[Microsoft Windows 公钥管理](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement)。

## 网络类型与防火墙

检查实际物理接口的 Get-NetConnectionProfile。换网后地址可能不变，但网络类别可能变为 Public。可信家庭/办公网络已由用户确认时，重新核对接口和网络身份，再按具体索引设置：

```powershell
Set-NetConnectionProfile -InterfaceIndex $selectedIndex -NetworkCategory Private
```

不批量修改所有接口，不把公共/访客网络标为可信。Private 网络类别与 RemoteAddress 是不同条件：规则为 Private 不代表仅本地子网；RemoteAddress=Any 也不代表适用于 Public。

检查选定规则的 Enabled、Direction、Action、Profile、端口和地址过滤条件。安装器可能已创建范围较宽的 OpenSSH-Server-In-TCP。只检查“规则存在”不足以确认符合需求；权限不足须报告未知，不关闭防火墙来测试。

当任务明确要求仅在本地子网、可信专用网络开放 SSH，且选定规则没有其他远程用途时，按已授权范围调整现有规则；不存在才新建：

```powershell
# 修改前保存选定规则和地址过滤器的原值。
Set-NetFirewallRule -Name $selectedRuleName -Enabled True -Profile Private -RemoteAddress LocalSubnet
# 仅在没有适用规则、且获授权配置时使用：
New-NetFirewallRule -Name 'Mac-Windows-LAN-SSH' -DisplayName 'Mac Windows LAN SSH' `
  -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow `
  -Profile Private -RemoteAddress LocalSubnet
```

新增窄规则不会收窄其他既有宽规则。不要悄悄改变服务于其他用户的规则。路由可达但跨子网的设备可能不匹配 LocalSubnet，应按真实路由与用户要求选择指定来源，而非自动扩大到 Any。

## 安装停滞

区分 UAC 未批准、安装运行中、需要重启、安装失败。读取本次进程、任务状态、DISM/CBS 对应时段日志；不要把历史错误当成本次错误。待重启标记本身不能证明 OpenSSH 安装失败。没有新证据时避免密集轮询；若系统维护阻塞，报告实际未完成步骤，保留原任务，不为了绕过等待同时修改同一组件。
