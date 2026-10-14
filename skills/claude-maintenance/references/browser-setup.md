# Claude 专用 Chrome

专用 Chrome 由 `scripts/exit_guard.py browser` 启动：独立 profile，所有请求经出口守护走固定出口。守护、配置和 CLI 入口见 [出口守护与 CLI 入口](fixed-exit.md)，各平台路径与桌面入口见 [平台差异](platforms.md)。

只需要独立登录、不要求固定出口时，用普通 Chrome 加 `--user-data-dir=<专用目录>` 即可，网络沿用 TUN 规则。

## 一、确定参数

先发现已有的守护配置、启动器和 profile，能复用就复用；只询问缺失且影响实施的参数。

| 参数 | 取得方式 |
|---|---|
| Chrome 可执行文件 | 本机安装位置；路径可能含空格。未安装时从官方渠道安装 |
| 专用 profile 目录 | 现有启动器中的 `--user-data-dir`，或用户选定的新目录，与普通 Chrome 分开 |
| 守护端口与上游 | 守护配置的 `listen_port`；上游是 [Claude 分流](clash-routing.md) 的专用 listener |
| 期望出口与落地节点 | 用户确认的值，与 Clash 生成配置核对 |
| 桌面入口名称和位置 | 用户选定 |

## 二、首次启动

1. 确认 Clash 专用 listener 可用，守护配置写好后运行 `exit_guard.py status`；守护未运行时会提示，运行 `exit_guard.py browser` 启动。
2. 守护先做链路和出口检查，通过后才打开 Chrome，起始页是守护状态页（显示是否已确认指定出口）。
3. 在 `chrome://version` 核对 Profile Path 和命令行参数。

守护给 Chrome 的参数：

- `--user-data-dir` 隔离登录与站点数据。
- `--proxy-server` 指向守护；守护或 listener 不可用时请求失败，不会直连。
- `--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;[::1]` 只放行字面 loopback，供 CLI 的 OAuth 本机回调使用。
- `--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost` 让域名全部交给代理解析。
- `--disable-quic`、`--force-webrtc-ip-handling-policy=disable_non_proxied_udp` 关闭不经代理的 UDP。
- `--disable-background-networking`、`--disable-sync` 关闭后台更新和账号同步。

专用 profile 已有 Chrome 实例时，新启动会复用旧进程。守护发现旧实例的代理参数不同会提示并停止；保存工作后完整退出专用实例再打开，普通 Chrome 不受影响。

## 三、桌面入口

桌面入口只调用 `exit_guard.py --config <配置> browser`，参数都从配置文件读取，不依赖终端环境变量。macOS 用 `.app`，Windows 用 `.lnk` 快捷方式，做法见 [平台差异](platforms.md)。系统默认浏览器保持不变。

## 四、验收

| 项目 | 通过条件 |
|---|---|
| 独立环境 | 普通 Chrome 与专用 profile 的目录不同，各自保留登录状态 |
| 启动入口 | 终端和桌面入口打开的是同一配置，路径带空格也能启动 |
| 网络 | 状态页显示已确认指定出口；Clash 连接记录里专用浏览器的新请求进入专用 listener |
| OAuth | CLI 登录能用专用浏览器打开并回调成功 |
| 入口故障 | 保存工作后让前置或落地暂时不可用，新请求停止；恢复后重新连接 |

更换前置、更新订阅或改落地后重新核对。撤销时把启动器和 profile 移入废纸篓或回收站中带时间戳的目录。
