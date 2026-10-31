#!/usr/bin/env bash
# 在 cloudcli 服务器上以 root 运行：创建隧道专用用户 tunnel 并检查 sshd 配置。
# 可重复运行。只检查和提示，不修改 sshd_config。
#
# 用法（服务器通常禁止 root 密码登录，所以二选一）：
#   已有 root 密钥的电脑：ssh root@<服务器> "bash -s" < init-tunnel-user.sh
#   已经在服务器上：sudo bash init-tunnel-user.sh
set -euo pipefail
# 非登录式 ssh 会话的 PATH 可能不含 sbin，而 useradd、sshd、nologin 都在那里。
export PATH="/usr/local/sbin:/usr/sbin:/sbin:$PATH"

TUNNEL_USER=tunnel
TUNNEL_HOME=/home/tunnel
SSH_DIR="$TUNNEL_HOME/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"
WARNINGS=0

die() { printf '错误：%s\n' "$*" >&2; exit 1; }
warn() { WARNINGS=$((WARNINGS + 1)); printf '警告：%s\n' "$*"; }

config_value() { awk -v k="$1" '$1 == k { print $2; exit }' <<<"$2"; }

ensure_user() {
  if id "$TUNNEL_USER" >/dev/null 2>&1; then
    echo "用户 $TUNNEL_USER 已存在，沿用。"
  else
    local nologin_path
    nologin_path=$(command -v nologin) || die "找不到 nologin，无法创建不能登录命令行的用户。"
    useradd -m -s "$nologin_path" "$TUNNEL_USER" || die "创建用户 $TUNNEL_USER 失败。"
    echo "已创建用户 ${TUNNEL_USER}。"
  fi

  local home shell
  home=$(getent passwd "$TUNNEL_USER" | cut -d: -f6)
  shell=$(getent passwd "$TUNNEL_USER" | cut -d: -f7)
  [ "$home" = "$TUNNEL_HOME" ] || die "用户 $TUNNEL_USER 的家目录是 ${home}，不是 ${TUNNEL_HOME}，请先人工核对。"
  case "$shell" in
    */nologin|*/false) ;;
    *) warn "用户 $TUNNEL_USER 的登录 shell 是 ${shell}，应改为 nologin：usermod -s \"$(command -v nologin)\" $TUNNEL_USER" ;;
  esac
}

ensure_key_file() {
  local group
  group=$(id -gn "$TUNNEL_USER")
  install -d -m 700 -o "$TUNNEL_USER" -g "$group" "$SSH_DIR" || die "创建 $SSH_DIR 失败。"
  if [ -e "$AUTH_KEYS" ]; then
    # 不能再用 install 处理已有文件：它会用空文件覆盖，清掉所有已登记设备。
    chown "$TUNNEL_USER:$group" "$AUTH_KEYS" || die "修正 $AUTH_KEYS 的属主失败。"
    chmod 600 "$AUTH_KEYS" || die "修正 $AUTH_KEYS 的权限失败。"
    echo "$AUTH_KEYS 已存在，保留原内容（当前 $(grep -c 'cloudcli-tunnel:' "$AUTH_KEYS" || true) 台设备）。"
  else
    install -m 600 -o "$TUNNEL_USER" -g "$group" /dev/null "$AUTH_KEYS" || die "创建 $AUTH_KEYS 失败。"
    echo "已创建 ${AUTH_KEYS}。"
  fi
  if command -v restorecon >/dev/null 2>&1; then
    restorecon -R "$SSH_DIR" || warn "restorecon 执行失败；SELinux 开启时可能导致公钥登录被拒。"
  fi
}

check_openssh_version() {
  local version major minor
  version=$(sshd -V 2>&1 | grep -oE 'OpenSSH_[0-9]+\.[0-9]+' | head -n 1 || true)
  [ -n "$version" ] || die "读取不到 OpenSSH 版本，无法确认是否支持 permitlisten。"
  major=${version#OpenSSH_}
  minor=${major#*.}
  major=${major%%.*}
  echo "OpenSSH 版本：${version#OpenSSH_}（要求 ≥ 7.8）"
  if [ "$major" -lt 7 ] || { [ "$major" -eq 7 ] && [ "$minor" -lt 8 ]; }; then
    die "OpenSSH 低于 7.8，不支持 permitlisten，设备密钥无法限定端口。请先升级 openssh-server。"
  fi
}

check_allow_users() {
  local allow_users pattern
  allow_users=$(awk '$1 == "allowusers" { print $2 }' <<<"$1")
  if [ -z "$allow_users" ]; then
    echo "AllowUsers：未设置（不限制）"
    return 0
  fi
  echo "AllowUsers：$(tr '\n' ' ' <<<"$allow_users")"
  while IFS= read -r pattern; do
    # AllowUsers 支持通配符和 user@host，这里要的就是通配匹配。
    # shellcheck disable=SC2053
    if [[ $TUNNEL_USER == ${pattern%%@*} ]]; then
      return 0
    fi
  done <<<"$allow_users"
  warn "AllowUsers 里没有 ${TUNNEL_USER}，隧道会登录失败。请把 $TUNNEL_USER 加到 /etc/ssh/sshd_config 现有的 AllowUsers 行末尾（保留 root，否则会把自己锁在外面），然后运行：sshd -t && systemctl reload sshd（Debian/Ubuntu 的服务名是 ssh）。"
}

check_sshd_config() {
  local config effective value group_list use_pam password_field
  config=$(sshd -T 2>/dev/null) || die "sshd -T 执行失败，请运行 sshd -t 查看配置错误。"
  # 带上连接条件才能看到 Match User tunnel 生效后的值。
  effective=$(sshd -T -C "user=$TUNNEL_USER,host=localhost,addr=127.0.0.1" 2>/dev/null) || effective=$config

  echo "AllowTcpForwarding：全局 $(config_value allowtcpforwarding "$config")，对 $TUNNEL_USER 生效的值 $(config_value allowtcpforwarding "$effective")"
  check_allow_users "$config"

  group_list=$(awk '$1 == "allowgroups" { print $2 }' <<<"$config" | tr '\n' ' ')
  [ -z "$group_list" ] || warn "设置了 AllowGroups（${group_list}），请确认 $TUNNEL_USER 所在的组在其中。"

  value=$(config_value allowtcpforwarding "$effective")
  case "$value" in
    no|local) warn "对 $TUNNEL_USER 生效的 AllowTcpForwarding 是 ${value}，反向隧道无法建立，需要 remote 或 yes。" ;;
    yes) warn "对 $TUNNEL_USER 生效的 AllowTcpForwarding 是 yes：authorized_keys 里的 port-forwarding 同时放开了 -L，设备密钥可以访问服务器本机的端口。建议用下面的 Match 段收紧为 remote。" ;;
  esac

  value=$(config_value gatewayports "$effective")
  [ "$value" = "no" ] || warn "GatewayPorts 是 ${value}，隧道端口可能暴露到公网。应设为 no。"

  value=$(config_value clientaliveinterval "$effective")
  if [ "${value:-0}" = "0" ]; then
    warn "对 $TUNNEL_USER 没有设置 ClientAliveInterval：设备睡眠或断网后，服务器上的旧连接可能长时间占着端口，重连时会报 remote port forwarding failed。"
  fi

  use_pam=$(config_value usepam "$config")
  password_field=$(getent shadow "$TUNNEL_USER" | cut -d: -f2 || true)
  if [ "$use_pam" = "no" ] && [ "${password_field#!}" != "$password_field" ]; then
    warn "UsePAM 是 no 且账号处于锁定状态（密码字段以 ! 开头），sshd 会拒绝公钥登录。可运行：usermod -p '*' ${TUNNEL_USER}（仍然不能用密码登录）。"
  fi

  cat <<EOF

建议在 /etc/ssh/sshd_config 末尾加上下面这段（脚本不会自动修改）：

    Match User $TUNNEL_USER
        AllowTcpForwarding remote
        ClientAliveInterval 30
        ClientAliveCountMax 3

改完运行：sshd -t && systemctl reload sshd（Debian/Ubuntu 的服务名是 ssh）。
EOF
}

main() {
  [ "$(id -u)" -eq 0 ] || die "请用 root 运行。"
  check_openssh_version
  ensure_user
  ensure_key_file
  check_sshd_config
  echo
  echo "完成，共 $WARNINGS 条警告。"
}

main "$@"
