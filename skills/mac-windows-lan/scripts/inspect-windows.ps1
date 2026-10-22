[CmdletBinding()]
param(
    [string]$TargetHost,
    [ValidateRange(1,65535)][int]$Port = 22,
    [ValidateRange(1,15)][int]$TimeoutSeconds = 3
)

# Read-only inspection. Does not read key bodies or change system configuration.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
if ($env:OS -ne 'Windows_NT') { throw 'This inspector requires Windows.' }
$issues = [System.Collections.Generic.List[object]]::new()
$report = [ordered]@{
    captured_at = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    username = $env:USERNAME
    elevated = $false
    networks = @()
    ssh_service = $null
    default_shell = $null
    listening_port = $Port
    listeners = @()
    firewall_rule_scope = 'Named SSH inbound rules only; not a complete effective-policy evaluation'
    firewall_rules = @()
    target_probe = $null
    authentication_verified = $false
    errors = @()
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$report.elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

try {
    $report.networks = @(Get-NetIPConfiguration | Where-Object { $_.NetAdapter.Status -eq 'Up' } | ForEach-Object {
        $configuration = $_
        [pscustomobject]@{
            interface_index = $configuration.InterfaceIndex
            interface_alias = $configuration.InterfaceAlias
            description = $configuration.InterfaceDescription
            hardware_interface = $configuration.NetAdapter.HardwareInterface
            network_category = if ($configuration.NetProfile) { [string]$configuration.NetProfile.NetworkCategory } else { $null }
            ipv4 = @($configuration.IPv4Address | ForEach-Object {
                [pscustomobject]@{address=$_.IPAddress;prefix_length=$_.PrefixLength}
            })
            ipv4_gateway = @($configuration.IPv4DefaultGateway | ForEach-Object { $_.NextHop })
        }
    })
} catch {
    [void]$issues.Add([pscustomobject]@{section='networks';message=$_.Exception.Message})
}

try {
    $service = Get-Service -Name sshd -ErrorAction Stop
    $report.ssh_service = [pscustomobject]@{
        exists=$true;status=[string]$service.Status;startup_type=[string]$service.StartType
    }
} catch {
    if ($_.CategoryInfo.Category -eq 'ObjectNotFound') {
        $report.ssh_service = [pscustomobject]@{exists=$false;status=$null;startup_type=$null}
    } else {
        [void]$issues.Add([pscustomobject]@{section='ssh_service';message=$_.Exception.Message})
    }
}

try {
    $registryPath = 'HKLM:\SOFTWARE\OpenSSH'
    if (Test-Path -LiteralPath $registryPath) {
        $properties = Get-ItemProperty -LiteralPath $registryPath
        if ($properties.PSObject.Properties.Name -contains 'DefaultShell') {
            $report.default_shell = $properties.DefaultShell
        }
    }
} catch {
    [void]$issues.Add([pscustomobject]@{section='default_shell';message=$_.Exception.Message})
}

try {
    $report.listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -eq $Port } |
        Select-Object LocalAddress,LocalPort,OwningProcess)
} catch {
    [void]$issues.Add([pscustomobject]@{section='listeners';message=$_.Exception.Message})
}

try {
    $rules = @(Get-NetFirewallRule -Name '*ssh*' -ErrorAction Stop |
        Where-Object { $_.Direction -eq 'Inbound' })
    $report.firewall_rules = @($rules | ForEach-Object {
        $rule = $_
        $addressFilter = $null
        $portFilter = $null
        try {
            $addressFilter = $rule | Get-NetFirewallAddressFilter
            $portFilter = $rule | Get-NetFirewallPortFilter
        } catch {
            [void]$issues.Add([pscustomobject]@{section='firewall_filter';rule=$rule.Name;message=$_.Exception.Message})
        }
        [pscustomobject]@{
            name=$rule.Name;enabled=[string]$rule.Enabled;action=[string]$rule.Action
            profile=[string]$rule.Profile;remote_addresses=@($addressFilter.RemoteAddress)
            protocol=$portFilter.Protocol;local_ports=@($portFilter.LocalPort)
        }
    })
} catch {
    [void]$issues.Add([pscustomobject]@{section='firewall_rules';message=$_.Exception.Message})
}

if ($TargetHost) {
    $probe = [ordered]@{target=$TargetHost;port=$Port;tcp_connected=$false;ssh_banner_observed=$false;banner=$null;error=$null}
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync($TargetHost,$Port)
        if (-not $connection.Wait($TimeoutSeconds * 1000)) { throw 'TCP connection timed out.' }
        if (-not $client.Connected) { throw 'TCP connection did not succeed.' }
        $probe.tcp_connected = $true
        $stream = $client.GetStream()
        $stream.ReadTimeout = $TimeoutSeconds * 1000
        $buffer = New-Object byte[] 256
        $count = $stream.Read($buffer,0,$buffer.Length)
        $banner = [Text.Encoding]::ASCII.GetString($buffer,0,$count).Trim()
        $probe.banner = $banner
        $probe.ssh_banner_observed = $banner.StartsWith('SSH-')
    } catch {
        $probe.error = $_.Exception.Message
    } finally {
        $client.Dispose()
    }
    $report.target_probe = [pscustomobject]$probe
}
$report.errors = @($issues.ToArray())
$report | ConvertTo-Json -Depth 8
