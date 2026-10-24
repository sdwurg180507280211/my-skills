# Claude 分流与固定出口

这里只维护 Claude 专属的 Clash 约定：Claude 域名规则、固定出口组、Claude 的 DNS 策略和专用入口。国内直连名单、规则集转换、通用 DNS、链式代理、持久化和故障测试方法见 [china-proxy 的 Clash 参考](../../china-proxy/references/clash-routing-and-chain.md)。

修改前按 china-proxy 的流程找到真正参与生成的持久化扩展并备份，不只改运行 YAML。

## 一、规则位置

```yaml
rules:
  - DOMAIN-SUFFIX,claude.ai,Claude固定出口
  - DOMAIN-SUFFIX,anthropic.com,Claude固定出口
  - DOMAIN-SUFFIX,claude.com,Claude固定出口
  # 之后是原有局域网规则、国内域名/IP 直连规则，最后 MATCH 到海外默认组
```

- Claude 规则放在国内域名/IP 判断之前。三个域名是起点，登录、资源和工具依赖从实际连接记录补齐。
- 组名替换为本机已确认的名称。
- 规则扩展的 `prepend` 以 MATCH 结尾时，订阅自带规则永远不会命中，兜底组也可能含 DIRECT。用每个订阅自己的 Script 清理，见 [china-proxy：订阅自带规则与兜底组](../../china-proxy/references/clash-routing-and-chain.md)。

## 二、固定出口组与前置节点池

- `Claude固定出口` 直接指向确认的落地，或只含该落地的专用策略；不含其他出口、DIRECT、自动测速、故障回退或负载均衡。
- 链路是「客户端 → 普通前置 → 固定落地 → Claude」。固定的是最后出口；落地或前置失效时 Claude 连接失败，不改用普通海外兜底。出口 IP 变化时由用户确认新的期望值，不把探针结果自动写入配置。

### 1. 多节点前置代理池与自动优选设计

单前置节点一旦发生高延迟（>300ms）、丢包或维护，会导致专用浏览器登录超时（如 GitHub/Claude 登录报 `SSLEOFError` / 504）或 CLI 挂起。**Mihomo 内核原生支持将代理组（Selector 或 URLTest）作为落地节点的 `dialer-proxy`**。

最佳实践是在 Clash Verge 的 Profile 增强（`groups` 扩展的 `prepend`）中定义前置选择组和自动优选组，并将固定落地节点的 `dialer-proxy` 绑定到该组：

```yaml
# 1. 在 groups 增强中定义前置组与自动优选组
prepend:
  - name: Claude前置选择
    type: select
    proxies:
      - 🇺🇸United States 02
      - 🇺🇸United States 03
      - 🇸🇬Singapore 02
      - 🇯🇵Japan 01
      - 🇭🇰Hong Kong 03
      - Claude前置自动优选
  - name: Claude前置自动优选
    type: url-test
    url: https://cp.cloudflare.com/generate_204
    interval: 120
    tolerance: 50
    proxies:
      - 🇺🇸United States 02
      - 🇺🇸United States 03
      - 🇸🇬Singapore 02
      - 🇯🇵Japan 01
      - 🇭🇰Hong Kong 03

# 2. 在 proxies 增强中绑定前置组
prepend:
  - name: Claude出口-209.200.250.178
    type: socks5
    server: <落地服务器>
    port: <落地端口>
    username: <账号>
    password: <密码>
    dialer-proxy: Claude前置选择
```

- **交互体验**：用户在 Clash Verge GUI 的「代理」页面中，可在 `Claude前置选择` 组下随时一键切换当前订阅中的任意高速节点；也可以选择 `Claude前置自动优选` 由核心周期性选路。
- **界面静默纯净模式（Zero-UI Background Mode）**：若用户希望 Clash Verge 界面 100% 保持订阅原样（供日常个人浏览），不希望看到任何 Claude 相关分组或节点：
  - 在 `Claude前置自动优选` 组和 `Claude出口` 节点上声明 `hidden: true`，Mihomo 与 Clash Verge GUI 会将其从所有可视化列表中完全隐藏。
  - 在订阅脚本（`Script.js`）中将普通代理组（如 `节点选择`、`GLOBAL`）中的 Claude 节点过滤剔除。
  - 固定出口节点直接以 `dialer-proxy: Claude前置自动优选` 在后台持续自动选路，前置优选完全静默进行，客户端界面 0 干扰。
- **出口安全**：无论前置节点如何切换，落地节点出口保持不变，出口守卫（`exit_guard.py`）持续核验公网出口 IP，兼顾了灵活性与 fail-closed 安全底线。

### 2. 多订阅环境下的节点池隔离

Clash Verge 的配置增强（`groups` / `proxies` / `merge`）是与订阅 Profile 绑定的。
- **不可跨订阅混填**：每个订阅的 `groups` 扩展中填入的节点名称，必须完全属于该订阅本身的节点池。若将订阅 A 的节点名写入订阅 B 的 `Claude前置选择`，Mihomo 启动校验时会报错（`proxy group: 'xxx' not found`）导致配置加载失败。
- **切换订阅适配**：若拥有多个订阅（如良心云、Kitty、equaldcdn），需为每个订阅分别配置其专属的 `groups` 增强文件，均命名为 `Claude前置选择` 和 `Claude前置自动优选`。这样切换活动订阅后，出口节点始终能对齐当前生效的前置组。

### 3. Fake-IP 下 NTP 时钟同步与 VLESS Reality 握手

VLESS Reality 协议等现代代理协议对客户端与服务端的时钟偏移有极高敏感度（容差通常在几秒以内）。
- 若开启了 Fake-IP 模式，且未将 Apple/系统 NTP 域名加入排除名单，macOS 的时间同步服务（`timed`）可能会解析到虚假 IP（如 `198.18.0.x`）导致同步失败，时钟漂移累积后会导致 Reality 节点批量报 `REALITY authentication failed`。
- 必须在 merge 配置或订阅 DNS 设置的 `fake-ip-filter` 中加入：
  ```yaml
  dns:
    fake-ip-filter:
      - time.apple.com
      - "*.apple.com"
      - "time.*.com"
      - "*.pool.ntp.org"
  ```

### 4. Clash Verge Rev 服务模式与双进程排查

- 当 Clash Verge Rev 开启「服务模式（Service Mode）」时，内核由特权进程 `clash-verge-service` 以 root 运行，实际配置位于 `/Library/Application Support/clash-verge-service/users/<uid>/runtime/config.yaml`。
- **严禁在终端手动用普通用户重复启动 `verge-mihomo`**，否则会导致多进程争抢端口（7890/17891）并使 GUI 状态与实际网络行为割裂。
- 自动化或脚本运维应通过 Unix Socket（`/var/run/clash-verge-service/users/<uid>/verge-mihomo.sock`）直接与运行中的核心通信：
  - 查询状态/节点：`curl -s --unix-socket ... http://localhost/proxies`
  - 切换节点：`curl -X PUT --unix-socket ... http://localhost/proxies/Claude%E5%89%8D%E7%BD%AE%E9%80%89%E6%8B%A9 -d '{"name":"xxx"}'`
  - 热重载配置：`curl -X PUT --unix-socket ... "http://localhost/configs?force=true" -d '{"path":"/Library/Application Support/clash-verge-service/users/501/runtime/config.yaml"}'`

## 三、Claude 的 DNS 策略

在现有 DNS 配置上增加 Claude 域名的解析线路，其余部分按 china-proxy 的通用 DNS 设计：

```yaml
dns:
  nameserver-policy:
    "+.claude.ai":
      - "https://1.1.1.1/dns-query#Claude固定出口"
    "+.claude.com":
      - "https://1.1.1.1/dns-query#Claude固定出口"
    "+.anthropic.com":
      - "https://1.1.1.1/dns-query#Claude固定出口"
```

DNS 地址是公开解析服务，不是出口参数。字段以当前 [Mihomo DNS 文档](https://wiki.metacubex.one/config/dns/) 为准。

## 四、专用入口

需要不受普通组切换影响的固定入口时，在持久化扩展里建立只监听 loopback 的 HTTP listener，直接绑定固定出口组。端口从实际配置读取或选未占用值，下面的端口只是示例：

```yaml
listeners:
  - name: claude-dedicated
    type: http
    listen: 127.0.0.1
    port: 17891
    proxy: Claude固定出口
```

CLI 和专用浏览器使用这个本地 HTTP 入口，`NO_PROXY` 保留 `localhost,127.0.0.1,::1`。需要公网 IP 校验时在它前面加出口守护，见 [出口守护与 CLI 入口](fixed-exit.md)；浏览器配置见 [专用浏览器](browser-setup.md)。

## 五、验证

用新请求的连接记录核对，浏览器、CLI、后台会话和 App 分别验证：

1. Claude 请求命中固定出口，同一入口两项出口查询都符合期望 IP。普通 IP 检测网页可能走另一条规则，不代替 Claude 请求记录。
2. 国内网站仍直连，普通海外流量走海外默认组。
3. 让前置或落地暂时不可用（先保存工作并记录原选择）：Claude 新请求失败且没有换出口，国内访问正常；恢复后复测。
4. Clash 整体退出单独测试：显式入口会让使用它的客户端报错；只靠 TUN 的客户端（如 Claude App）此时可能恢复直连。

未做的测试标明未测。订阅更新、换前置、换落地或升级客户端后重新检查。恢复时还原本次改动的源扩展和必要的链式选择，重新加载后验证。
