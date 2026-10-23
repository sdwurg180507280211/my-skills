# SSH 登录后的 Windows 远程维护

已验证身份后，再按用户本次任务执行远程命令。查看一台机器不等于授权修改其应用；仅编写 skill 时使用已有记录或只读检查，不重新部署配置。

## PowerShell 与字符编码

Windows OpenSSH 的默认 shell 可能是 cmd、Windows PowerShell 或 pwsh。优先显式调用已存在的 PowerShell，不为了执行一次任务永久修改 DefaultShell：

```text
powershell.exe -NoProfile -NonInteractive -OutputFormat Text -EncodedCommand <UTF-16LE-base64>
```

- Mac 上将 PowerShell 脚本按 UTF-16LE 编码，再 Base64；用参数数组调用 `ssh`，为 SSH 和整个子进程分别设置超时。
- 脚本开头设置 `[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)`，Mac 端按 UTF-8 解码。节点名可能含中文和 emoji，不能依赖远程控制台默认代码页。
- `-NoProfile` 避免用户 profile 副作用；`-NonInteractive` 避免在后台等待输入；`-OutputFormat Text` 配合 `ConvertTo-Json` 输出结构化检查结果。
- Windows PowerShell 5.1 的 `foreach (...) { ... }` 语句不能直接接管道；先赋值、用 `@(...)` 收集或改用 `ForEach-Object`。用 `@(...)` 保持空列表/单元素数组形状。
- EncodedCommand 是转义手段，不是加密。凭据放私有文件或受控 stdin，不嵌进命令行、打印的脚本、异常或版本库。

如果远程有 Python，先确认实际解释器和依赖，再选择它。通过 `python -` 从 SSH stdin 发送脚本时，脚本先用 `sys.stdout.reconfigure(encoding='utf-8')`；Mac 收集输出仍指定 UTF-8。否则中文/emoji 可能触发 `gbk` 编码异常，命令执行过但 JSON 没有成功返回。缺少依赖先报告，不因临时检查自动换全局 Python 或安装整套运行时。

只输出所需键名和脱敏摘要。`capture_output=True` 后失败时也检查 stdout 和 stderr：包装层只看 stderr 可能丢掉内层子进程的实际错误。完整含配置的日志只留私有备份，聊天中给类别、返回码和日志路径。

## 路径与文件传输

通过 `$env:APPDATA`、`$env:LOCALAPPDATA`、`$env:ProgramData`、目标用户目录和进程参数发现路径。Mac 的 Application Support 不等于 Windows 的 Roaming；已有源文件不能证明它正在生效。

优先 SFTP，或已验证可用的现代 `scp`：

```sh
scp -i '<已确认的本机密钥>' -o BatchMode=yes \
  '<本机暂存文件>' '<用户>@<地址>:C:/Users/<目标用户>/<私有暂存目录>/payload.zip'
```

示例的反斜杠转换只针对 Windows SFTP 路径；远程 PowerShell 里的字面路径按它自己的规则处理。遇到盘符/空格解释问题回到交互 SFTP 的 `pwd`、`ls`、`put/get`，不要不断增加 shell 转义。传输后比对 SHA-256；解压自己创建的包时核对成员位于预期相对目录，外来包拒绝绝对路径和 `..` 越界。

## 私有备份与有限范围写入

1. 找到应用实际读写的配置源、生成文件、当前选择和服务运行文件。源配置、GUI 状态与内核运行状态分别记录。
2. 在远端用户私有目录建立唯一时间戳备份，保留原始字节；记录原路径、备份相对路径、SHA-256、拟修改项和恢复动作。含认证的文件使用仅目标用户与必要系统身份可读的 ACL；检查最终 ACL，不只看 `icacls` 成功。
3. 首次写入前报告备份位置和变更范围。可另下载到 Mac 权限受限目录；真实地址、节点凭据、配置、探针记录和备份包不进公开 skill 仓库。
4. 在本机暂存副本上按工作区要求编辑，保留原文件格式；传输到远端私有暂存目录。写前比较目标哈希与备份，用户/应用已修改时暂停覆盖，重新核对差异。
5. 先通过应用/内核校验，再替换本次清单内的文件，并通过该应用实际支持的方式加载。跟踪原始选择；失败时只恢复本次文件及选择，保留其他业务。
6. 交付针对清单的恢复命令或 `restore.cmd`，写明是否需要重新加载应用、重新打开浏览器或重启保护进程。备份不是永久自动重写配置的服务。

不覆盖整份用户配置目录来同步少量字段。原生可视化链式配置由用户维护时，保留对应来源，不新增定时脚本与 GUI 争写。

## SSH 会话与桌面会话

SSH 中启动了 GUI/pythonw，不代表用户桌面窗口已经出现，或 SSH 退出后进程会持续存在。先区分服务进程、SSH 会话进程、登录用户桌面进程；`SessionId` 和进程参数可用于定位，报告时隐藏敏感参数。

用户已授权重启桌面辅助程序时，可在目标用户交互会话用一次性计划任务启动，验证后注销任务；不要按进程名批量结束所有 Python/Chrome，也不通过重装应用处理会话隔离。配置已改但运行进程只在启动时读取配置时，要重启那个精确进程，或明确标注“下次启动生效”。SSH 无法确认的窗口状态请用户在桌面核对。
