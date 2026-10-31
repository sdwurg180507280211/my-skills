#!/usr/bin/env bash
# 在 cloudcli 服务器上以 root 运行：登记设备公钥并分配隧道端口。
# 服务器上的 authorized_keys 是唯一的端口记录，每行末尾注释就是登记表。
#
# 用法：ssh root@<服务器> "bash -s -- <设备名> '<公钥>' [端口]" < add-device-key.sh
#
# 标准输出只有最后一行端口号，其余信息都走标准错误。退出码：
#   0  新登记成功
#   1  出错，或公钥/设备名已被别的登记占用
#   3  同一设备名和同一公钥已登记：不重复添加，仍输出已有端口，供安装脚本重复运行时沿用
# shellcheck disable=SC1111  # 中文提示里的弯引号是有意的
set -euo pipefail
export PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"

AUTH_KEYS=/home/tunnel/.ssh/authorized_keys
LOCK_FILE=/run/cloudcli-tunnel-keys.lock
RESERVED_PORT=22023
FIRST_PORT=22024
LAST_PORT=22999
EXIT_ALREADY_REGISTERED=3
KEY_RE='^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh\.com|sk-ecdsa-sha2-nistp256@openssh\.com) [A-Za-z0-9+/]+={0,3}$'

die() { printf '错误：%s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*" >&2; }

# 这个脚本可能由 bash -s 从标准输入读取，下面的命令都不能读标准输入，否则会吞掉脚本内容。

registered_ports() {
  { grep -Eo '(permitlisten="[^"]*:|cloudcli-tunnel:)[0-9]+' "$AUTH_KEYS" || true; } | grep -Eo '[0-9]+$' || true
}

listening_ports() {
  ss -tln | awk 'NR > 1 { n = split($4, a, ":"); print a[n] }'
}

line_with_key() {
  awk -v body="$1" '{ for (i = 1; i <= NF; i++) if ($i == body) { print; exit } }' "$AUTH_KEYS"
}

line_with_device() {
  awk -v name="$1" 'split($NF, a, ":") == 3 && a[1] == "cloudcli-tunnel" && a[3] == name { print; exit }' "$AUTH_KEYS"
}

validate_public_key() {
  local tmp rc=0
  [[ $1 =~ $KEY_RE ]] || die "公钥格式不对，应为一行“类型 base64”，且不能带任何选项。"
  tmp=$(mktemp)
  printf '%s\n' "$1" >"$tmp"
  ssh-keygen -l -f "$tmp" >/dev/null 2>&1 || rc=$?
  rm -f "$tmp"
  [ "$rc" -eq 0 ] || die "ssh-keygen 无法解析这个公钥，请确认复制完整。"
}

report_existing() {
  local device=$1 port=$2 key_line=$3 device_line=$4 existing_port
  if [ -n "$key_line" ] && [ "$key_line" = "$device_line" ]; then
    existing_port=$(awk '{ split($NF, a, ":"); print a[2] }' <<<"$key_line")
    if [ -n "$port" ] && [ "$port" != "$existing_port" ]; then
      die "设备 $device 已登记在端口 ${existing_port}，与指定的端口 $port 不一致。要换端口请先按 SKILL.md 移除设备。"
    fi
    say "设备 $device 已用同一公钥登记在端口 ${existing_port}，不重复添加。"
    printf '%s\n' "$existing_port"
    exit "$EXIT_ALREADY_REGISTERED"
  fi
  [ -z "$key_line" ] || die "这个公钥已经登记过（${key_line##* }），不重复添加。"
  [ -z "$device_line" ] || die "设备名 $device 已被另一个公钥占用（${device_line##* }），不重复添加。"
}

choose_port() {
  local requested=$1 registered listening candidate
  registered=$(registered_ports)
  listening=$(listening_ports) || die "ss -tln 执行失败，无法判断端口是否空闲。"

  if [ -n "$requested" ]; then
    if grep -qx "$requested" <<<"$registered"; then
      die "端口 $requested 已被其他设备登记。"
    fi
    if grep -qx "$requested" <<<"$listening"; then
      die "端口 $requested 正在被监听，不是空闲端口。"
    fi
    printf '%s\n' "$requested"
    return 0
  fi

  for ((candidate = FIRST_PORT; candidate <= LAST_PORT; candidate++)); do
    if ! grep -qx "$candidate" <<<"$registered" && ! grep -qx "$candidate" <<<"$listening"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  die "$FIRST_PORT-$LAST_PORT 已没有空闲端口。"
}

main() {
  if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    die "用法：add-device-key.sh <设备名> \"<公钥>\" [端口]"
  fi
  local device=$1 raw_key=$2 port=${3:-} key_type key_body public_key
  local key_line device_line entry

  [ "$(id -u)" -eq 0 ] || die "请用 root 运行。"
  [[ $device =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$ ]] || die "设备名只能包含字母、数字、点、下划线和连字符，且以字母或数字开头。"
  [[ $raw_key != *$'\n'* ]] || die "公钥只能有一行。"
  read -r key_type key_body _ <<<"$raw_key"
  public_key="$key_type $key_body"
  validate_public_key "$public_key"
  if [ -n "$port" ]; then
    if ! [[ $port =~ ^[0-9]+$ ]] || [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
      die "端口必须是 1024-65535 之间的数字。"
    fi
  fi
  [ -f "$AUTH_KEYS" ] || die "$AUTH_KEYS 不存在，请先运行 init-tunnel-user.sh。"

  # 两台设备同时接入时，避免分到同一个端口。
  exec 9>"$LOCK_FILE" || die "无法创建锁文件 ${LOCK_FILE}。"
  flock -w 30 9 || die "等待其他登记操作超时，请稍后重试。"

  key_line=$(line_with_key "$key_body")
  device_line=$(line_with_device "$device")
  report_existing "$device" "$port" "$key_line" "$device_line"

  # 22023 永远不分配：放在已登记检查之后，迁移旧设备时人工加好的那一行才能被重复运行沿用。
  [ "$port" != "$RESERVED_PORT" ] || die "端口 $RESERVED_PORT 保留给 bjpc-windows，不分配。迁移步骤见 SKILL.md。"
  port=$(choose_port "$port")

  entry="restrict,port-forwarding,permitlisten=\"localhost:$port\" $public_key cloudcli-tunnel:$port:$device"
  if [ -s "$AUTH_KEYS" ] && [ -n "$(tail -c 1 "$AUTH_KEYS")" ]; then
    printf '\n' >>"$AUTH_KEYS"
  fi
  printf '%s\n' "$entry" >>"$AUTH_KEYS" || die "写入 $AUTH_KEYS 失败。"
  grep -qxF -- "$entry" "$AUTH_KEYS" || die "写入后没有在 $AUTH_KEYS 中找到新记录。"

  say "已登记设备 ${device}，端口 ${port}。"
  printf '%s\n' "$port"
}

main "$@"
