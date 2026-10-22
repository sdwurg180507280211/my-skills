# 连接、传输与换网排查

## 分层验收

1. 被连接端：正确账号、服务/网络类型、监听端口、适用防火墙规则。
2. 客户端：对指定目标测试 TCP，例如 Mac 的 `nc -vz -w 3 <地址> 22`，或 Windows 的 `Test-NetConnection <地址> -Port 22`。
3. 校验主机身份，再实际认证：`ssh -o ConnectTimeout=5 <用户>@<地址> whoami`。需要无交互测试且密钥/指纹已就绪时加 -o BatchMode=yes；有口令但未解锁的密钥可能在 BatchMode 下失败，不误判为服务端坏了。
4. 按用户目标验证文件操作。本机连接本机地址取得 SSH banner 仅证明本机监听，不证明另一台电脑可以穿过防火墙、登录或读写目录。

首次主机指纹需和服务端公钥指纹核对。ssh-keyscan 只能收集候选公钥，不能独立证明身份。不要用 StrictHostKeyChecking=no 绕过提示。指纹变化时先核对是否换机、重装、IP 被别的设备占用；确认后仅清理对应 known_hosts 条目，不删除整个文件。

## 常见结果

| 现象 | 优先核对 |
| --- | --- |
| 超时 / No route to host | 当前 IP、目标开机/休眠、两端网络与路由、访客隔离、物理接口、VPN/TUN、适用防火墙配置 |
| Connection refused | 服务是否运行、实际监听地址/端口；也可能是主动拒绝规则 |
| Permission denied (publickey) | 目标用户名、所选客户端公钥、是否解锁对应私钥、服务端有效 authorized_keys 路径和 ACL/权限 |
| Host key verification failed / changed | 先确认目标身份，不要关闭主机校验来修复 |
| SSH 能登录但文件操作失败 | 远端目录、账号权限、SFTP 子系统、路径格式，不因此重装 SSH |
| 刚换网络后不通 | DHCP 地址与别名、Windows Public/Private、规则 Profile/RemoteAddress、新网络隔离 |

ping 被阻断不等于 SSH 不可达。相同地址前缀也可能属于两个互相隔离的网络；同一路由器下有线与无线通常可以互通，不要求接入方式相同。Wi-Fi 换网通常无需重建密钥或重装服务。仅一端换到外网时，解释现有私网地址需要可达路由；VPN/异地组网是另一个明确目标。

## 可选 SSH 别名

用户需要稳定入口时，备份客户端 `~/.ssh/config`（Windows 为目标用户目录下 `.ssh\config`），只合并对应 Host 段，并检查既有通配 Host、ProxyCommand/ProxyJump 的影响。

```sshconfig
Host win-lan
    HostName <Windows当前可达地址>
    User <Windows用户>
    IdentityFile <Mac上的实际私钥路径>
    IdentitiesOnly yes
```

另一个客户端需要反向入口时可建 mac-lan，使用那台客户端自己的密钥路径。别名不会自动跟踪 DHCP。换网后核对地址，再更新 HostName；可按用户需求研究 DHCP 地址保留或经过验证的 .local 名称，不自动修改路由器。

## 文件传输

建立 SSH 身份验证后，使用 `sftp <用户>@<地址>` 或 `sftp win-lan`。先 pwd、ls 核实远端目录，再对用户指定的文件和路径 put / get。Windows 盘符、空格、反斜杠在客户端 shell、远端 PowerShell、SFTP 中的规则不同；不未经核对就拼接复杂远程命令。优先用交互 SFTP 观察实际路径。

若用户只是要求互访配置，不自动上传私有文件。需传输验收时，使用约定的测试目录/小文件，核对大小或 SHA-256；只清理本次测试文件。SFTP 一次连接支持上传和下载，不自动代表两台机器都已开放 SSH 服务。
