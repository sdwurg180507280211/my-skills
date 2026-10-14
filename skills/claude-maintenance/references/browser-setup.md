# 创建 Claude 专用 Chrome

本流程负责独立浏览器环境、启动入口、CLI 登录配合和验收。Clash listener、链式代理、DNS 和出口守护采用 [china-proxy](../../china-proxy/SKILL.md) 的流程。

## 一、确定本机参数

先发现 Chrome 可执行文件、已有专用启动器及 profile，再填写参数表。已有环境可复用；要新建时选择一个与普通 Chrome 分开的 user-data-dir。

Chrome 尚未安装时，从官方渠道安装适配系统与架构的版本；已安装时直接复用。启动后在 `chrome://version` 核对版本及实际 Profile Path。

| 参数 | 取得方式 |
|---|---|
| Chrome 可执行文件 | 本机安装位置和版本；路径可能含空格 |
| 专用 profile 目录 | 现有启动器中的 user-data-dir，或用户选定的新目录 |
| 浏览器网络模式 | 沿用已有方案：普通 TUN 路由，或显式专用入口 |
| 专用代理入口 | 从实际 listener/guard 配置读取协议、主机、端口 |
| 期望出口与落地 | 使用用户确认的值，与当前运行配置核对 |
| 桌面入口 | 用户选定名称及安装位置 |
| 登录配合 | 是否让 CLI 用此浏览器打开本次授权页面 |

沿用已确认的节点、端口和目录；只询问缺失且影响实施的参数。启动器、profile 和当前配置记录在本机私有目录。

## 二、准备网络入口

显式专用模式先核对入口，再创建浏览器：

1. 找到运行中的 Clash 配置与专用 listener，核对它指向的落地及前置。
2. 已有出口守护时，浏览器使用守护入口，先检查服务身份和健康状态；守护上游仍是专用 listener。
3. 仅有 listener 时使用该入口，记录当前是固定链式模式。要增加公网 IP 校验，按 `china-proxy` 另行建立守护。
4. 通过选定入口做有超时的出口查询，并核对当前节点链。

普通 TUN 模式沿用系统路由，不添加下面的显式代理参数。用户要求固定入口及入口失效时停止访问时，使用显式专用模式，启动器只配置这一入口。

## 三、创建独立环境并首次启动

为选定的 profile 创建独立目录，使用当前用户权限，目录权限设为 700。新环境首次启动由 Chrome 生成数据；保留普通 Chrome 的原 profile。语言和同步选项采用用户选择，时区沿用系统设置。

下面是显式专用模式的参数化启动命令。先将三个变量赋为本机已确认值；变量只用于这次命令。OAuth URL 作为位置参数传入时会直接交给同一浏览器。

```bash
#!/bin/sh
set -eu
: "${CLAUDE_CHROME_BIN:?填写 Chrome 可执行文件}"
: "${CLAUDE_CHROME_PROFILE:?填写专用 profile 目录}"
: "${CLAUDE_CHROME_PROXY:?填写已确认的专用 HTTP 入口}"

if [ "$#" -eq 0 ]; then
  set -- 'https://claude.ai/'
fi

exec "$CLAUDE_CHROME_BIN" \
  --user-data-dir="$CLAUDE_CHROME_PROFILE" \
  --proxy-server="$CLAUDE_CHROME_PROXY" \
  '--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;[::1]' \
  --disable-quic \
  --force-webrtc-ip-handling-policy=disable_non_proxied_udp \
  --no-first-run \
  --no-default-browser-check \
  --new-window "$@"
```

- `--user-data-dir` 隔离登录与站点数据，路径和 URL 按独立参数传入。
- `--proxy-server` 指向实际 HTTP 入口；入口连接失败时停止请求。
- bypass 仅列字面 loopback，供 CLI 的本机回调使用。
- QUIC/WebRTC 参数控制对应的 UDP 行为，验收时检查当前 Chrome 版本的实际效果。
- 需要约束额外域名解析时，沿用当前 `china-proxy` 的 DNS/连接识别方案。已有 `host-resolver-rules` 启动参数需保留实际代理主机和 localhost 的解析例外。

profile 已有 Chrome 实例时，新启动通常会复用它。改变参数前保存工作并完整退出该专用实例，再启动；普通 Chrome 保持运行。

## 四、生成可见、可调整的桌面入口

首次启动验证完成后，按确认参数生成持久启动器：

1. 将 Chrome 路径、profile、入口和启动页写入私有配置；参数可独立修改，启动时从该配置读取。
2. macOS 可创建用户选定名称的 `.app`，使用 `Contents/Info.plist`、`Contents/MacOS/<启动文件>` 与 `Contents/Resources/<配置>`。设置可执行权限，并通过 Finder 打开验证。
3. Dock/Finder 启动时也能读取这些配置；不要依赖仅存在于某个终端的环境变量。由现有 guard 管理浏览器时，桌面入口调用它并共用这份参数。
4. 给出启动器路径、profile 路径、配置文件位置、日常启动方法及更改入口的方法。系统默认浏览器保持现状。

创建过程仅写已选定的浏览器目录与入口。Clash 原生链式配置仍由用户在可视化页面调整。

## 五、配合 Claude CLI 登录

需要 CLI 使用专用浏览器时：

1. 核对实际 CLI/wrapper，复用已有的 OAuth browser helper；新环境则让 helper 将当前授权 URL 作为参数交给上述启动入口。
2. 为该 CLI 子进程设置 `BROWSER`，保留其已有专用代理环境；`NO_PROXY` 包含 `localhost,127.0.0.1,::1`。
3. 先用临时本机 HTTP 服务和合成参数测试 localhost/127.0.0.1 回调；IPv6 loopback 按实际支持测试并记录。
4. 保持认证终端运行，由本次 CLI 登录生成新的授权页面。成功后只核对登录状态、认证方式和 provider。

回调失败先查 listener 是否仍在、浏览器 bypass、DNS 例外和当前认证状态。具体检查方法见 [OAuth 回调维护](../../china-proxy/references/claude-fixed-exit.md)。

## 六、验收与日常调整

| 项目 | 通过条件 |
|---|---|
| 独立环境 | 普通 Chrome 与专用 profile 的实际目录不同，各自保留登录状态 |
| 启动入口 | 终端和 Finder/Dock 使用同一配置，路径带空格也能正常启动 |
| 网络 | 专用浏览器的新请求进入选定 inbound/链，同入口两项出口查询符合约定 |
| OAuth | 合成本机回调成功，实际 CLI 登录完成 |
| 参数更新 | 完整退出专用实例后重启，新的参数生效 |
| 入口故障 | 保存工作后，按用户确认的故障测试范围核对新请求停止；恢复入口后重新连接 |

更换前置、更新订阅或改落地后重新核对链与出口；profile 和登录状态可继续使用。迁移电脑时重新绑定路径、入口和启动器，按 [客户端迁移](clients-and-migration.md) 验收。

## 七、恢复

修改已有启动器前保存旧参数与受影响文件。回退时恢复这次修改的配置，再完整退出专用实例并重启。新建环境撤销时，将本次创建的启动器及 profile 移入带时间戳的废纸篓目录，保留恢复对照；共享的 Chrome、CLI 和 Clash 继续使用原配置。
