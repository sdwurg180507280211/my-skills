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

## 二、固定出口组

- `Claude固定出口` 直接指向确认的落地，或只含该落地的专用策略；不含其他出口、DIRECT、自动测速、故障回退或负载均衡。
- 链路是「客户端 → 普通前置 → 固定落地 → Claude」。固定的是最后出口；前置由用户在 Clash 可视化链式页面更换，保存后核对 `dialer-proxy` 关系和公网出口。
- 落地或前置失效时 Claude 连接失败，不改用普通海外兜底。出口 IP 变化时由用户确认新的期望值，不把探针结果自动写入配置。

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
