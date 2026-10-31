<#
把这台 Windows 接入 cloudcli：建立到服务器的反向隧道并授权 cloudcli 公钥。可重复运行。

用法（在管理员 PowerShell 窗口里运行）：
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Server <服务器> -DeviceName <设备名> -CloudcliPubKey "<公钥>"
可选：-Port <端口>、-SetPowerShellDefaultShell
没有传 -Server 时读取环境变量 CLOUDCLI_SERVER。

本文件必须保存为带 BOM 的 UTF-8，否则 Windows PowerShell 5.1 读到的中文是乱码。
#>
[CmdletBinding()]
param(
    [string]$Server = $env:CLOUDCLI_SERVER,
    [string]$DeviceName,
    [string]$CloudcliPubKey,
    [int]$Port = 0,
    [switch]$SetPowerShellDefaultShell
)

$ErrorActionPreference = 'Stop'

$TaskName = 'CloudcliTunnel'
$TunnelHost = 'cloudcli-tunnel'
$ExitAlreadyRegistered = 3
$KeyPattern = '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh\.com|sk-ecdsa-sha2-nistp256@openssh\.com) [A-Za-z0-9+/]+={0,3}( .*)?$'
$SshDir = Join-Path $env:USERPROFILE '.ssh'
$KeyFile = Join-Path $SshDir 'cloudcli_tunnel_ed25519'
$SshConfig = Join-Path $SshDir 'config'
$TunnelScript = Join-Path $env:USERPROFILE 'cloudcli-tunnel.ps1'
$LogFile = Join-Path $env:USERPROFILE 'cloudcli-tunnel.log'
$AddKeyScript = Join-Path $PSScriptRoot '..\server\add-device-key.sh'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Fail([string]$Message) {
    Write-Host "错误：$Message" -ForegroundColor Red
    exit 1
}

function Write-Step([string]$Message) {
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

# PowerShell 5.1 和 7 传递空字符串、引号参数的规则不同（比如 ssh-keygen -N ""），
# 管道还会改动字节，所以这里直接用 Process，由调用方写好完整的参数字符串。
function Invoke-Native([string]$FilePath, [string]$Arguments, [byte[]]$InputBytes = $null) {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.StandardOutputEncoding = $Utf8NoBom
    $startInfo.RedirectStandardInput = ($null -ne $InputBytes)
    $process = [System.Diagnostics.Process]::Start($startInfo)
    if ($null -ne $InputBytes) {
        # ssh 登录失败时会提前关闭标准输入，写入报错可以忽略，结果看退出码。
        try {
            $process.StandardInput.BaseStream.Write($InputBytes, 0, $InputBytes.Length)
            $process.StandardInput.Close()
        } catch {
        }
    }
    $output = $process.StandardOutput.ReadToEnd()
    $process.WaitForExit()
    return [pscustomobject]@{ ExitCode = $process.ExitCode; Output = $output }
}

function Find-SshTool([string]$Name) {
    # 优先用系统自带的 OpenSSH，避免用到 Git for Windows 带的 ssh，它的家目录和配置路径不同。
    $systemPath = Join-Path $env:WINDIR "System32\OpenSSH\$Name"
    if (Test-Path -LiteralPath $systemPath) { return $systemPath }
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail "找不到 $Name。请先安装 OpenSSH 客户端：Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
}

function Test-Arguments {
    if ([string]::IsNullOrWhiteSpace($Server)) { Fail '缺少服务器地址：请传 -Server 或设置环境变量 CLOUDCLI_SERVER。' }
    if ($Server -cnotmatch '^[A-Za-z0-9.:-]+$') { Fail "服务器地址格式不对：$Server" }
    if ($DeviceName -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$') { Fail '设备名只能包含字母、数字、点、下划线和连字符，且以字母或数字开头。' }
    if ($CloudcliPubKey -match "[\r\n]" -or $CloudcliPubKey -cnotmatch $KeyPattern) { Fail 'cloudcli 公钥格式不对，应为一行“类型 base64 [注释]”。' }
    if ($Port -ne 0 -and ($Port -lt 1024 -or $Port -gt 65535)) { Fail '端口必须是 1024-65535 之间的数字。' }
    if (-not (Test-Path -LiteralPath $AddKeyScript)) { Fail "找不到 $AddKeyScript，请保留完整的 skill 目录。" }
}

function Test-Elevated {
    Write-Step '1/11 检查管理员权限'
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Fail '请右键“以管理员身份运行”打开 PowerShell，再重新运行这条命令。'
    }

    # 用另一个账号提权时，密钥、计划任务和 cloudcli 登录都会落到那个账号名下，
    # 登录桌面的用户注销重登后隧道不会启动。
    $current = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $desktopUser = (Get-CimInstance Win32_ComputerSystem).UserName
    if ($desktopUser -and $desktopUser -ne $current) {
        Fail "当前以 $current 运行，但登录桌面的是 $desktopUser。请用要接入 cloudcli 的账号登录桌面，并让该账号自己以管理员身份运行。"
    }

    if ([Console]::IsInputRedirected) {
        Fail '当前环境没有可交互的终端。请在自己打开的管理员 PowerShell 窗口运行，因为 root 密码必须由你亲手输入。'
    }
    Write-Host '已确认管理员权限。'
}

function Enable-Sshd {
    Write-Step '2/11 检查 sshd 服务'
    if (-not (Get-Service -Name sshd -ErrorAction SilentlyContinue)) {
        Write-Host '未安装 OpenSSH Server，正在安装（可能需要几分钟）...'
        try {
            Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
        } catch {
            Fail "安装 OpenSSH Server 失败：$($_.Exception.Message)"
        }
        if (-not (Get-Service -Name sshd -ErrorAction SilentlyContinue)) {
            Fail '安装命令已结束，但仍找不到 sshd 服务。可能需要重启电脑后再运行。'
        }
    }
    try {
        Set-Service -Name sshd -StartupType Automatic
        Start-Service -Name sshd
    } catch {
        Fail "启动 sshd 服务失败：$($_.Exception.Message)"
    }
    for ($i = 0; $i -lt 10; $i++) {
        if (Get-NetTCPConnection -LocalPort 22 -State Listen -ErrorAction SilentlyContinue) {
            Write-Host 'sshd 已设为自动启动，22 端口正在监听。'
            return
        }
        Start-Sleep -Seconds 1
    }
    Fail 'sshd 已启动，但 22 端口没有在监听。请检查 C:\ProgramData\ssh\sshd_config 里的 Port 设置。'
}

function Get-TunnelPublicKey {
    Write-Step '3/11 准备隧道专用密钥'
    if (-not (Test-Path -LiteralPath $SshDir)) {
        New-Item -ItemType Directory -Path $SshDir | Out-Null
    }
    if (Test-Path -LiteralPath $KeyFile) {
        Write-Host "沿用已有密钥 $KeyFile。"
    } else {
        $result = Invoke-Native $SshKeygenExe "-q -t ed25519 -N `"`" -C `"${TunnelHost}:$DeviceName`" -f `"$KeyFile`""
        if ($result.ExitCode -ne 0) { Fail '生成密钥失败，原因见上面的输出。' }
        Write-Host "已生成 $KeyFile。"
    }
    $result = Invoke-Native $SshKeygenExe "-y -P `"`" -f `"$KeyFile`""
    if ($result.ExitCode -ne 0) {
        Fail "读不出 $KeyFile 的公钥。隧道要无人值守运行，这把密钥不能设口令，并且只有本人和 SYSTEM 能访问。"
    }
    $fields = $result.Output.Trim() -split '\s+'
    $publicKey = "$($fields[0]) $($fields[1])"
    if (-not (Test-Path -LiteralPath "$KeyFile.pub")) {
        [IO.File]::WriteAllText("$KeyFile.pub", "$publicKey`n", $Utf8NoBom)
    }
    return $publicKey
}

function Register-TunnelKey([string]$PublicKey) {
    Write-Step '4/11 在服务器登记公钥'
    Write-Host '接下来请在这个窗口亲手输入 root 密码，密码不会被保存。'
    # 脚本可能被 Git 转成 CRLF，而 bash 不接受 CRLF，这里统一成 LF 后按原始字节发送。
    $text = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $AddKeyScript).Path).Replace("`r`n", "`n")
    $scriptBytes = $Utf8NoBom.GetBytes($text)
    $portArgument = if ($Port -ne 0) { " $Port" } else { '' }
    $remoteCommand = "bash -s -- '$DeviceName' '$PublicKey'$portArgument"
    $result = Invoke-Native $SshExe "root@$Server `"$remoteCommand`"" $scriptBytes
    switch ($result.ExitCode) {
        0 { }
        $ExitAlreadyRegistered { Write-Host '服务器上已有这台设备的登记，沿用原端口。' }
        255 { Fail '连不上服务器或 root 登录失败。请确认服务器地址、root 密码，以及安全组已放行 22 端口。' }
        default { Fail '服务器拒绝登记，原因见上面的输出。' }
    }
    $lines = @($result.Output -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($lines.Count -eq 0 -or $lines[-1] -notmatch '^\d+$') {
        Fail "没有从服务器拿到端口号，实际输出：$($result.Output)"
    }
    Write-Host "隧道端口：$($lines[-1])"
    return [int]$lines[-1]
}

function Get-NormalizedHostBlock([string[]]$Lines) {
    # 统一空白和大小写后按行排序，便于比较。
    $inBlock = $false
    $block = foreach ($line in $Lines) {
        $tokens = @($line.Trim() -split '\s+')
        if ($tokens[0] -eq 'host' -or $tokens[0] -eq 'match') {
            $inBlock = ($tokens[0] -eq 'host') -and ($tokens -contains $TunnelHost)
        }
        if ($inBlock -and $tokens[0] -and -not $tokens[0].StartsWith('#')) {
            ($tokens -join ' ').ToLowerInvariant()
        }
    }
    return (@($block) | Sort-Object) -join "`n"
}

function Set-SshConfig {
    Write-Step '5/11 配置 ~/.ssh/config'
    $expectedLines = @(
        "Host $TunnelHost",
        "    HostName $Server",
        '    User tunnel',
        '    IdentityFile ~/.ssh/cloudcli_tunnel_ed25519',
        '    IdentitiesOnly yes',
        '    ServerAliveInterval 30',
        '    ServerAliveCountMax 3',
        '    ExitOnForwardFailure yes',
        '    StrictHostKeyChecking accept-new'
    )
    $expected = Get-NormalizedHostBlock $expectedLines
    $existingLines = @()
    if (Test-Path -LiteralPath $SshConfig) { $existingLines = @([IO.File]::ReadAllLines($SshConfig)) }
    $existing = Get-NormalizedHostBlock $existingLines

    if ($existing -eq $expected) {
        Write-Host "Host $TunnelHost 段已存在且内容一致。"
    } elseif ($existing) {
        Write-Host "$SshConfig 里已有 Host $TunnelHost 段，但内容和预期不同。" -ForegroundColor Yellow
        Write-Host "现有内容：`n$existing`n`n预期内容：`n$($expectedLines -join "`n")"
        Fail '不会覆盖已有配置。请人工确认并修改后重新运行。'
    } else {
        # 不用 Add-Content：5.1 的编码选项会写入 BOM 或 ANSI，ssh 读不了带 BOM 的配置。
        $separator = if ($existingLines.Count -gt 0) { "`n" } else { '' }
        [IO.File]::AppendAllText($SshConfig, $separator + ($expectedLines -join "`n") + "`n", $Utf8NoBom)
        Write-Host "已追加 Host $TunnelHost 段。"
    }

    # ssh 配置先出现的值优先，靠前的 Host * 可能盖掉这里的设置。这一步只解析配置，不连接。
    $result = Invoke-Native $SshExe "-G $TunnelHost"
    if ($result.ExitCode -ne 0) { Fail "ssh 无法解析 $SshConfig，请检查配置语法。" }
    $effective = @($result.Output -split "`r?`n")
    foreach ($item in @('user tunnel', "hostname $Server", 'exitonforwardfailure yes')) {
        if ($effective -notcontains $item) {
            Fail "$TunnelHost 实际生效的配置里没有“$item”，请检查 $SshConfig 靠前的 Host * 或 Match 段。"
        }
    }
}

function Write-TunnelScript([int]$TunnelPort) {
    Write-Step '6/11 生成隧道脚本'
    # ssh -E 把标准错误追加写到日志。PowerShell 5.1 的 2>> 会把日志写成 UTF-16 并混入错误记录。
    $content = @'
# Generated by cloudcli-device-onboarding/windows/setup.ps1. Re-run setup.ps1 to change it.
$log = Join-Path $env:USERPROFILE 'cloudcli-tunnel.log'
while ($true) {
    Add-Content -LiteralPath $log -Encoding Ascii -ErrorAction SilentlyContinue -Value "[$(Get-Date -Format s)] connecting"
    & '__SSH_EXE__' -N -E $log -R __PORT__:localhost:22 -o BatchMode=yes __TUNNEL_HOST__
    Add-Content -LiteralPath $log -Encoding Ascii -ErrorAction SilentlyContinue -Value "[$(Get-Date -Format s)] ssh exited with code $LASTEXITCODE, retrying in 10 seconds"
    Start-Sleep -Seconds 10
}
'@
    $content = $content.Replace('__SSH_EXE__', $SshExe.Replace("'", "''")).Replace('__PORT__', "$TunnelPort").Replace('__TUNNEL_HOST__', $TunnelHost)
    [IO.File]::WriteAllText($TunnelScript, $content.Replace("`r`n", "`n"), (New-Object System.Text.UTF8Encoding($true)))
    Write-Host "已生成 $TunnelScript。"
}

function Get-TunnelProcessId([int]$TunnelPort) {
    $processes = Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" | Where-Object {
        $_.CommandLine -like "*-R ${TunnelPort}:localhost:22*" -and $_.CommandLine -like "*$TunnelHost*"
    }
    return @($processes | ForEach-Object { $_.ProcessId })
}

function Stop-OldTunnel([int]$TunnelPort) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }
    # 结束任务不一定带走 ssh 子进程，遗留的进程会占着服务器上的端口。
    foreach ($processId in @(Get-TunnelProcessId $TunnelPort)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

function Register-TunnelTask {
    Write-Step '7/11 注册计划任务'
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$TunnelScript`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
        Start-ScheduledTask -TaskName $TaskName
    } catch {
        Fail "注册或启动计划任务失败：$($_.Exception.Message)"
    }
    Write-Host "已注册并启动计划任务 $TaskName。"
}

function Add-UniqueKey([string]$Path, [string]$PublicKey) {
    $body = ($PublicKey -split '\s+')[1]
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        # ReadAllLines 能识别 BOM。之前用 >> 写过的文件是 UTF-16，sshd 读不了，追加时会一起改回 UTF-8。
        $lines = @([IO.File]::ReadAllLines($Path))
        foreach ($line in $lines) {
            if (($line.Trim() -split '\s+') -contains $body) {
                Write-Host "cloudcli 公钥已在 $Path 中，不重复添加。"
                return
            }
        }
    }
    $text = (@($lines) + $PublicKey) -join "`n"
    [IO.File]::WriteAllText($Path, "$text`n", $Utf8NoBom)
    Write-Host "已把 cloudcli 公钥写入 $Path。"
}

function Set-CloudcliKey {
    Write-Step '8/11 授权 cloudcli 公钥'
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $path = 'C:\ProgramData\ssh\administrators_authorized_keys'
        Add-UniqueKey $path $CloudcliPubKey
        & icacls $path /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail "设置 $path 的权限失败。" }
    } else {
        Add-UniqueKey (Join-Path $SshDir 'authorized_keys') $CloudcliPubKey
    }
}

function Set-DefaultShell {
    if (-not $SetPowerShellDefaultShell) { return }
    Write-Step '9/11 设置 SSH 默认 shell'
    $shell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path -LiteralPath 'HKLM:\SOFTWARE\OpenSSH')) {
        New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
    }
    New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value $shell -PropertyType String -Force | Out-Null
    Write-Host "SSH 默认 shell 已设为 $shell。"
}

function Get-LogSize {
    if (Test-Path -LiteralPath $LogFile) { return (Get-Item -LiteralPath $LogFile).Length }
    return 0
}

function Read-LogFrom([long]$Offset) {
    if (-not (Test-Path -LiteralPath $LogFile)) { return '' }
    # ssh 正在追加这个文件，必须允许共享读写。
    $stream = New-Object IO.FileStream($LogFile, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try {
        [void]$stream.Seek($Offset, [IO.SeekOrigin]::Begin)
        $reader = New-Object IO.StreamReader($stream, $Utf8NoBom)
        return $reader.ReadToEnd()
    } finally {
        $stream.Dispose()
    }
}

function Test-Tunnel([int]$TunnelPort, [long]$LogOffset) {
    Write-Step '10/11 本机验证（约 15 秒）'
    Start-Sleep -Seconds 5
    $firstPid = @(Get-TunnelProcessId $TunnelPort)
    Start-Sleep -Seconds 10
    $secondPid = @(Get-TunnelProcessId $TunnelPort)
    # 旧日志里的失败记录不算数，只看这次启动后新增的内容。
    $newLog = Read-LogFrom $LogOffset

    # 循环脚本 10 秒后会重连，只看进程在不在分不出来，所以比较前后两次的 PID。
    if ($firstPid.Count -ne 1 -or $secondPid.Count -ne 1 -or $firstPid[0] -ne $secondPid[0]) {
        Write-Host $newLog
        Fail "隧道进程没有稳定运行（PID：$($firstPid -join ',') → $($secondPid -join ',')）。日志：$LogFile"
    }
    if ($newLog -match 'remote port forwarding failed') {
        Fail "日志出现 remote port forwarding failed：端口 $TunnelPort 被占用，或不符合服务器上的限制。日志：$LogFile"
    }
    if (-not (Get-NetTCPConnection -OwningProcess $secondPid[0] -State Established -ErrorAction SilentlyContinue)) {
        Fail "隧道进程还在，但没有和服务器建立连接。请检查网络和安全组。日志：$LogFile"
    }
    Write-Host "隧道进程运行正常（PID $($secondPid[0])），日志没有端口转发失败。"
}

function Write-Summary([int]$TunnelPort) {
    Write-Step '11/11 完成'
    Write-Host "设备名：$DeviceName"
    Write-Host "Windows 用户名：$env:USERNAME"
    Write-Host "隧道端口：$TunnelPort"
    Write-Host ''
    Write-Host '请在 cloudcli 里新增设备，填写：'
    Write-Host '  地址：127.0.0.1'
    Write-Host "  端口：$TunnelPort"
    Write-Host "  用户名：$env:USERNAME"
    Write-Host ''
    Write-Host '提醒：计划任务在用户登录时启动，电脑重启后要登录这个账号，隧道才会恢复。'
}

try {
    [Console]::OutputEncoding = $Utf8NoBom
} catch {
}

try {
    Test-Arguments
    Test-Elevated
    Enable-Sshd
    $SshExe = Find-SshTool 'ssh.exe'
    $SshKeygenExe = Find-SshTool 'ssh-keygen.exe'
    $tunnelPublicKey = Get-TunnelPublicKey
    $assignedPort = Register-TunnelKey $tunnelPublicKey
    Set-SshConfig
    Write-TunnelScript $assignedPort
    Stop-OldTunnel $assignedPort
    $logOffset = Get-LogSize
    Register-TunnelTask
    Set-CloudcliKey
    Set-DefaultShell
    Test-Tunnel $assignedPort $logOffset
    Write-Summary $assignedPort
} catch {
    Fail "执行中断：$($_.Exception.Message)"
}
