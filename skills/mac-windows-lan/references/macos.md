# Mac 端

当前 skill 没有实际连接到用户的 Mac。以下步骤按官方说明编写，每次使用时检查 macOS 版本、账号和网络；不能声称已经在这台 Mac 上启用或测试。

## 地址和身份

```sh
whoami
scutil --get LocalHostName
networksetup -listallhardwareports
```

从硬件端口输出确定实际使用的 Wi-Fi/以太网设备，再运行 `ipconfig getifaddr <设备>`。不要固定假设 en0；VPN 开启时默认路由可能指向 utun，需和物理网络、目标路由一起判断。`<LocalHostName>.local` 仅在实际能解析时使用，失败则回到已核对的地址。

## Mac 作为客户端：连接 Windows

无需启用 Mac 的远程登录。检查 ssh -V，确认用户要用的已有密钥路径或 ssh-agent 公钥指纹。已有合适密钥时复用；用户要求新密钥时才在新的文件名下创建，例如 `ssh-keygen -t ed25519 -f <新密钥路径> -C mac-to-windows-lan`，先确保不会覆盖旧文件。口令交给用户本地输入，不作为命令参数或聊天内容。

只把选定 .pub 内容部署到 Windows 对应账号。私钥留在 Mac。检查服务器主机指纹后，从 Mac 运行：

```sh
ssh -i <Mac私钥路径> -o IdentitiesOnly=yes <Windows用户>@<Windows当前地址> whoami
```

若通过 ssh-agent 使用密钥，按实际配置省略 -i 和 IdentitiesOnly；不要凭空猜私钥文件名。

## Mac 作为服务器：接受 Windows 连接

按用户已授权目标，打开“系统设置 → 通用 → 共享 → 远程登录”，启用并只允许目标账号访问。具体 UI 以当前版本为准。普通 SSH/SFTP 不应默认开启“允许远程用户完全访问磁盘”；需要受保护目录时另行明确权限。

在目标 Mac 用户的 `~/.ssh/authorized_keys` 安装 Windows 客户端的选定公钥，保留已有条目并去重。确认文件属于该用户；通常目录权限 700、文件权限 600。不要向别人的主目录写入，也不要把 Windows 私钥传来。Windows → Mac 使用 Windows 自己的客户端密钥；反向连接不是自动建立的授权。

从 Windows 验收：

```powershell
ssh <Mac用户>@<Mac当前地址> whoami
```

需要核验 Mac 主机指纹时，在 Mac 本地读取 `/etc/ssh/ssh_host_ed25519_key.pub` 的 ssh-keygen -lf 结果，与客户端首次连接显示的指纹比较。仅查看公钥文件。

依据：[Apple 远程登录说明](https://support.apple.com/guide/mac-help/allow-a-remote-computer-to-access-your-mac-mchlp1066/mac)。它同时提供 SSH 与 SFTP，无需为了 SFTP 再开启 SMB 文件共享。
