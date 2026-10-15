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
- `--lang=en-US`、`--accept-lang=en-US,en`：界面语言和网页看到的语言默认英文，由配置 `chrome_lang` 控制，设为空字符串则不加。

专用 profile 已有 Chrome 实例时，新启动会复用旧进程。守护发现旧实例的代理参数不同会提示并停止；保存工作后完整退出专用实例再打开，普通 Chrome 不受影响。

## 三、英文环境

守护默认用英文启动，新建的 profile 一开始就是英文界面。已有 profile 或手动调整时，逐项核对：

| 项目 | 位置 | 目标 |
|---|---|---|
| 界面语言 | `chrome://settings/languages` 的显示语言；Windows 存在 `Local State` 的 `intl.app_locale` | English |
| 网页语言 | 同一页面的语言列表；`Preferences` 的 `intl.accept_languages` | 只留 English |
| 拼写检查 | `Preferences` 的 `spellcheck.dictionaries` | 空或 `en-US` |
| 翻译 | 设置里关闭翻译提示 | 关闭 |
| 默认搜索引擎 | `chrome://settings/search` | 非中文引擎 |
| profile 名称 | `chrome://settings/manageProfile` | 英文名；用中文界面建的 profile 会叫"您的 Chrome" |

- macOS 上 Chrome 忽略 `--lang`，界面语言和网页 `Intl` 默认语言跟随该应用的 `AppleLanguages`（系统「语言与地区 → 应用程序」），同一应用的所有 profile 共用；`--accept-lang` 仍然生效，且会覆盖 profile 里存的语言。实测把 `-AppleLanguages (en-US)` 当启动参数能切换界面，但 Chrome 会把 `(en-US)` 当网址多开一个标签页，不采用。
- 只想让专用浏览器英文、普通 Chrome 保持中文时，专用浏览器改用官方 Chrome Beta（应用标识 `com.google.Chrome.beta`，与正式版分开）：安装后 `defaults write com.google.Chrome.beta AppleLanguages -array en-US`，守护配置的 `chrome` 指向 `/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta`。旧 profile 可直接沿用，但会被升级到 Beta 的版本，之后不宜再用正式版打开。下载地址用 `https://dl.google.com/chrome/mac/universal/beta/googlechromebeta.dmg`（不带 `universal` 的旧地址返回的是过期版本）；从 DMG 复制后若严格签名校验报 `detritus`，用 `xattr -cr` 清掉 Finder 扩展属性再校验。
- 切换浏览器前完整退出专用实例：同一 profile 不能被两个 Chrome 同时打开，旧守护也只按配置里的路径识别进程。
- Chrome 运行时会覆盖 `Preferences`，改文件前先完整退出专用实例；在设置页里改则不用。
- 系统时区、区域格式和字体不属于浏览器语言设置，这里不改。

## 四、桌面入口

桌面入口只调用 `exit_guard.py --config <配置> browser`，参数都从配置文件读取，不依赖终端环境变量。macOS 用 `.app`，Windows 用 `.lnk` 快捷方式，做法见 [平台差异](platforms.md)。系统默认浏览器保持不变。

## 五、验收

| 项目 | 通过条件 |
|---|---|
| 独立环境 | 普通 Chrome 与专用 profile 的目录不同，各自保留登录状态 |
| 启动入口 | 终端和桌面入口打开的是同一配置，路径带空格也能启动 |
| 网络 | 状态页显示已确认指定出口；Clash 连接记录里专用浏览器的新请求进入专用 listener |
| OAuth | CLI 登录能用专用浏览器打开并回调成功 |
| 入口故障 | 保存工作后让前置或落地暂时不可用，新请求停止；恢复后重新连接 |

更换前置、更新订阅或改落地后重新核对。撤销时把启动器和 profile 移入废纸篓或回收站中带时间戳的目录。
