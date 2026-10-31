#!/usr/bin/env bash
# 把这台 Mac 接入 cloudcli：建立到服务器的反向隧道并授权 cloudcli 公钥。可重复运行。
#
# 分两次运行：
#   第一次不传 --port：生成隧道密钥，输出公钥和登记命令，退出码 2，这时还没有接入。
#   由有服务器管理权限的一方登记、拿到端口后，加 --port 再运行一次，完成安装和本机验证。
#
# 用法：
#   bash setup.sh --server <服务器> --device-name <设备名> --cloudcli-pubkey "<公钥>" [--port <端口>]
# 没有传 --server 时读取环境变量 CLOUDCLI_SERVER。
# shellcheck disable=SC1111,SC2094  # 中文弯引号有意保留；只是追加前检查文件
set -euo pipefail

LABEL=com.cloudcli.tunnel
TUNNEL_HOST=cloudcli-tunnel
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_FILE="$HOME/Library/Logs/cloudcli-tunnel.log"
SSH_DIR="$HOME/.ssh"
KEY_FILE="$SSH_DIR/cloudcli_tunnel_ed25519"
SSH_CONFIG="$SSH_DIR/config"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"
KEY_RE='^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh\.com|sk-ecdsa-sha2-nistp256@openssh\.com) [A-Za-z0-9+/]+={0,3}( .*)?$'
EXIT_NEEDS_REGISTRATION=2

SERVER="${CLOUDCLI_SERVER:-}"
DEVICE_NAME=""
CLOUDCLI_PUBKEY=""
PORT=""
TUNNEL_PUBKEY=""

die() { printf '错误：%s\n' "$*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

usage() {
  cat >&2 <<'EOF'
用法：bash setup.sh --server <服务器> --device-name <设备名> --cloudcli-pubkey "<公钥>" [--port <端口>]
没有传 --server 时读取环境变量 CLOUDCLI_SERVER。
EOF
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --server|--device-name|--cloudcli-pubkey|--port)
        [ "$#" -ge 2 ] || { usage; die "$1 缺少取值。"; }
        case "$1" in
          --server) SERVER=$2 ;;
          --device-name) DEVICE_NAME=$2 ;;
          --cloudcli-pubkey) CLOUDCLI_PUBKEY=$2 ;;
          --port) PORT=$2 ;;
        esac
        shift 2
        ;;
      *) usage; die "不认识的参数：$1" ;;
    esac
  done
}

validate_args() {
  [ "$(uname -s)" = "Darwin" ] || die "这个脚本只用于 macOS。"
  [ -n "$SERVER" ] || { usage; die "缺少服务器地址：请传 --server 或设置 CLOUDCLI_SERVER。"; }
  [[ $SERVER =~ ^[A-Za-z0-9.:-]+$ ]] || die "服务器地址格式不对：$SERVER"
  [[ $DEVICE_NAME =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$ ]] || die "设备名只能包含字母、数字、点、下划线和连字符，且以字母或数字开头。"
  [[ $CLOUDCLI_PUBKEY != *$'\n'* && $CLOUDCLI_PUBKEY =~ $KEY_RE ]] || die "cloudcli 公钥格式不对，应为一行“类型 base64 [注释]”。"
  if [ -n "$PORT" ]; then
    if ! [[ $PORT =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
      die "端口必须是 1024-65535 之间的数字。"
    fi
  fi
  launchctl print "gui/$(id -u)" >/dev/null 2>&1 || die "当前用户没有图形登录会话，无法加载 LaunchAgent。请先在这台 Mac 上登录桌面，再从那里的终端运行。"
}

check_remote_login() {
  step "1/7 检查远程登录"
  nc -z localhost 22 >/dev/null 2>&1 || die "22 端口没有在监听。请到“系统设置 → 通用 → 共享 → 远程登录”打开它，然后重新运行。"
  echo "22 端口正在监听。"
}

ensure_tunnel_key() {
  step "2/7 准备隧道专用密钥"
  install -d -m 700 "$SSH_DIR" || die "创建 $SSH_DIR 失败。"
  chmod 700 "$SSH_DIR" || die "设置 $SSH_DIR 权限失败。"
  if [ -f "$KEY_FILE" ]; then
    echo "沿用已有密钥 ${KEY_FILE}。"
  else
    ssh-keygen -q -t ed25519 -N "" -C "$TUNNEL_HOST:$DEVICE_NAME" -f "$KEY_FILE" </dev/null || die "生成密钥失败。"
    echo "已生成 ${KEY_FILE}。"
  fi
  TUNNEL_PUBKEY=$(ssh-keygen -y -P "" -f "$KEY_FILE" </dev/null) \
    || die "读不出 $KEY_FILE 的公钥。隧道要无人值守运行，这把密钥不能设口令，权限也必须是 600。"
  TUNNEL_PUBKEY=$(awk '{ print $1, $2 }' <<<"$TUNNEL_PUBKEY")
  [ -f "$KEY_FILE.pub" ] || printf '%s\n' "$TUNNEL_PUBKEY" >"$KEY_FILE.pub"
}

request_registration() {
  cat <<EOF

还没有接入：这把隧道公钥要先在服务器登记。服务器通常禁止 root 密码登录，所以由已有管理权限的一方操作。

设备名：$DEVICE_NAME
隧道公钥：$TUNNEL_PUBKEY

在 skill 目录下运行，二选一，输出的最后一行就是端口：
  已有 root 密钥的电脑：ssh root@$SERVER "bash -s -- '$DEVICE_NAME' '$TUNNEL_PUBKEY'" < server/add-device-key.sh
  已经在服务器上：sudo bash server/add-device-key.sh $DEVICE_NAME '$TUNNEL_PUBKEY'

拿到端口后，在这台 Mac 上加 --port <端口> 重新运行这条命令。
EOF
  exit "$EXIT_NEEDS_REGISTRATION"
}

expected_host_block() {
  cat <<EOF
Host $TUNNEL_HOST
    HostName $SERVER
    User tunnel
    IdentityFile ~/.ssh/cloudcli_tunnel_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ExitOnForwardFailure yes
    StrictHostKeyChecking accept-new
EOF
}

# 输出配置里 Host cloudcli-tunnel 段的内容，统一空白和大小写后按行排序，便于比较。
normalized_host_block() {
  awk -v host="$TUNNEL_HOST" '
    { first = tolower($1) }
    first == "host" || first == "match" {
      in_block = 0
      if (first == "host") for (i = 2; i <= NF; i++) if ($i == host) in_block = 1
    }
    in_block && NF && $1 !~ /^#/ { $1 = $1; print tolower($0) }
  ' | sort
}

ensure_ssh_config() {
  step "3/7 配置 ~/.ssh/config"
  local existing expected
  expected=$(expected_host_block | normalized_host_block)
  existing=""
  if [ -f "$SSH_CONFIG" ]; then
    existing=$(normalized_host_block <"$SSH_CONFIG")
  fi
  if [ "$existing" = "$expected" ]; then
    echo "Host $TUNNEL_HOST 段已存在且内容一致。"
  elif [ -n "$existing" ]; then
    printf '%s 里已有 Host %s 段，但内容和预期不同。\n现有内容：\n%s\n\n预期内容：\n' "$SSH_CONFIG" "$TUNNEL_HOST" "$existing" >&2
    expected_host_block >&2
    die "不会覆盖已有配置。请人工确认并修改后重新运行。"
  else
    if [ ! -e "$SSH_CONFIG" ]; then
      install -m 600 /dev/null "$SSH_CONFIG" || die "创建 $SSH_CONFIG 失败。"
    fi
    {
      if [ -s "$SSH_CONFIG" ]; then
        printf '\n'
      fi
      expected_host_block
    } >>"$SSH_CONFIG" || die "写入 $SSH_CONFIG 失败。"
    echo "已追加 Host $TUNNEL_HOST 段。"
  fi

  # ssh 配置先出现的值优先，靠前的 Host * 可能盖掉这里的设置。这一步只解析配置，不连接。
  local effective
  effective=$(ssh -G "$TUNNEL_HOST") || die "ssh 无法解析 ${SSH_CONFIG}，请检查配置语法。"
  grep -qixF "user tunnel" <<<"$effective" || die "$TUNNEL_HOST 实际生效的用户不是 tunnel，请检查 $SSH_CONFIG 靠前的 Host * 或 Match 段。"
  grep -qixF "hostname $SERVER" <<<"$effective" || die "$TUNNEL_HOST 实际生效的地址不是 ${SERVER}，请检查 $SSH_CONFIG 靠前的 Host * 或 Match 段。"
  grep -qixF "exitonforwardfailure yes" <<<"$effective" || die "$TUNNEL_HOST 的 ExitOnForwardFailure 没有生效，请检查 $SSH_CONFIG 靠前的 Host * 或 Match 段。"
}

xml_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<<"$1"; }

write_plist() {
  local tmp log_xml
  log_xml=$(xml_escape "$LOG_FILE")
  install -d "$(dirname "$PLIST")" "$(dirname "$LOG_FILE")" || die "创建 LaunchAgents 或 Logs 目录失败。"
  tmp=$(mktemp "$PLIST.XXXXXX") || die "无法在 $(dirname "$PLIST") 创建临时文件。"
  cat >"$tmp" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-N</string>
        <string>-R</string>
        <string>$PORT:localhost:22</string>
        <string>-o</string>
        <string>BatchMode=yes</string>
        <string>$TUNNEL_HOST</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>$log_xml</string>
    <key>StandardErrorPath</key>
    <string>$log_xml</string>
</dict>
</plist>
EOF
  if ! plutil -lint "$tmp" >/dev/null; then
    rm -f "$tmp"
    die "生成的 plist 没有通过 plutil 检查。"
  fi
  chmod 644 "$tmp"
  mv "$tmp" "$PLIST" || die "写入 $PLIST 失败。"
}

load_agent() {
  step "4/7 配置 LaunchAgent"
  local domain
  domain="gui/$(id -u)"
  write_plist
  launchctl bootout "$domain/$LABEL" >/dev/null 2>&1 || true
  # bootout 刚返回时服务可能还在退出，这时 bootstrap 会报 Input/output error，需要重试。
  for _ in 1 2 3 4 5; do
    if launchctl bootstrap "$domain" "$PLIST" 2>/dev/null; then
      echo "已加载 ${LABEL}。"
      return 0
    fi
    sleep 2
  done
  launchctl bootstrap "$domain" "$PLIST" || die "launchctl bootstrap 失败。"
}

authorize_cloudcli_key() {
  step "5/7 授权 cloudcli 公钥"
  local key_body
  key_body=$(awk '{ print $2 }' <<<"$CLOUDCLI_PUBKEY")
  if [ ! -e "$AUTHORIZED_KEYS" ]; then
    install -m 600 /dev/null "$AUTHORIZED_KEYS" || die "创建 $AUTHORIZED_KEYS 失败。"
  fi
  chmod 600 "$AUTHORIZED_KEYS" || die "设置 $AUTHORIZED_KEYS 权限失败。"
  if awk -v body="$key_body" '{ for (i = 1; i <= NF; i++) if ($i == body) found = 1 } END { exit !found }' "$AUTHORIZED_KEYS"; then
    echo "cloudcli 公钥已存在，不重复添加。"
    return 0
  fi
  {
    if [ -s "$AUTHORIZED_KEYS" ] && [ -n "$(tail -c 1 "$AUTHORIZED_KEYS")" ]; then
      printf '\n'
    fi
    printf '%s\n' "$CLOUDCLI_PUBKEY"
  } >>"$AUTHORIZED_KEYS" || die "写入 $AUTHORIZED_KEYS 失败。"
  echo "已添加 cloudcli 公钥。"
}

tunnel_pid() {
  # 服务不存在时 launchctl 返回非零，这里只要“没有 PID”的结果，不能让 set -e 中止脚本。
  { launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null || true; } | awk '$1 == "pid" && $2 == "=" { print $3; exit }'
}

log_size() {
  if [ -f "$LOG_FILE" ]; then
    wc -c <"$LOG_FILE" | tr -d ' '
  else
    echo 0
  fi
}

verify_tunnel() {
  step "6/7 本机验证（约 15 秒）"
  local log_offset=$1 first_pid second_pid new_log
  sleep 5
  first_pid=$(tunnel_pid)
  sleep 10
  second_pid=$(tunnel_pid)
  # 旧日志里的失败记录不算数，只看这次启动后新增的内容。
  new_log=""
  if [ -f "$LOG_FILE" ]; then
    new_log=$(tail -c "+$((log_offset + 1))" "$LOG_FILE")
  fi

  # launchd 会自动重启失败的 ssh，只看进程在不在分不出来，所以比较前后两次的 PID。
  if [ -z "$first_pid" ] || [ "$first_pid" != "$second_pid" ]; then
    printf '%s\n' "$new_log" | tail -n 20 >&2
    die "隧道进程没有稳定运行（PID：${first_pid:-无} → ${second_pid:-无}）。日志里有 Permission denied 时，通常是公钥还没登记。日志：$LOG_FILE"
  fi
  if grep -q "remote port forwarding failed" <<<"$new_log"; then
    die "日志出现 remote port forwarding failed：端口 $PORT 被占用，或不符合服务器上的限制。日志：$LOG_FILE"
  fi
  if ! lsof -nP -a -p "$second_pid" -iTCP -sTCP:ESTABLISHED >/dev/null 2>&1; then
    die "隧道进程还在，但没有和服务器建立连接。请检查网络和安全组。日志：$LOG_FILE"
  fi
  echo "隧道进程运行正常（PID ${second_pid}），日志没有端口转发失败。"
}

print_summary() {
  step "7/7 完成"
  cat <<EOF
设备名：$DEVICE_NAME
Mac 用户名：$(id -un)
隧道端口：$PORT

请在 cloudcli 里新增设备，填写：
  地址：127.0.0.1
  端口：$PORT
  用户名：$(id -un)

提醒：Mac 睡眠时隧道会断开。如需随时可连，请到“系统设置 → 电池/能源”关闭自动睡眠。
EOF
}

main() {
  parse_args "$@"
  validate_args
  check_remote_login
  ensure_tunnel_key
  [ -n "$PORT" ] || request_registration
  ensure_ssh_config
  local log_offset
  log_offset=$(log_size)
  load_agent
  authorize_cloudcli_key
  verify_tunnel "$log_offset"
  print_summary
}

main "$@"
