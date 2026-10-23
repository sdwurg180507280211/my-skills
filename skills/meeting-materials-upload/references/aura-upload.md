# Aura 与三步上传

这些接口与字段来自实际执行过的页面请求。网站可能改版，每次先捕获当前请求验证结构、会话和返回值；不内置真实项目、账号或历史令牌。

## 会话与报文

公共端点历史形式：

```text
POST /sponsorfilemanagement/s/sfsites/aura?r=<unique-request-tag>&aura.ApexAction.execute=1
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
```

在已登录的目标页面内发 `fetch`，使用同源 Cookie。社区会话曾在 Salesforce REST `/services/data/...` 返回 `401 INVALID_SESSION_ID`；没有浏览器 Cookie 的裸 curl Aura 调用也被当成访客，报 Apex 类无权限。优先复用页面业务接口，不尝试绕过访问控制。

请求体有 `message`、`aura.context`、`aura.pageURI`、`aura.token`。捕获会话字段的 **form-urlencoded 原始值**，不要反转义后内嵌到 JS，再次解码会破坏 token 中的字面转义。raw 值已经编码时直接拼接，不能再用 URLSearchParams 编码一遍。

示意模板（会话在运行时注入，完整 action 来自当次抓包）：

```javascript
async function postAura(capturedAction, sessionRaw, requestTag) {
  const body = "message=" + encodeURIComponent(JSON.stringify({actions: [capturedAction]}))
    + "&aura.context=" + sessionRaw.context
    + "&aura.pageURI=" + sessionRaw.pageURI
    + "&aura.token=" + sessionRaw.token;
  const response = await fetch(
    "/sponsorfilemanagement/s/sfsites/aura?r=" + encodeURIComponent(requestTag)
      + "&aura.ApexAction.execute=1",
    {method: "POST", credentials: "same-origin",
     headers: {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}, body});
  if (!response.ok) throw new Error("HTTP " + response.status);
  // 历史响应可能包有 /*...*/ 或 */.../*；按实际外壳剥离后再 JSON.parse。
  let text = (await response.text()).trim();
  if (text.startsWith("/*") && text.endsWith("*/")) text = text.slice(2, -2);
  else if (text.startsWith("*/") && text.endsWith("/*")) text = text.slice(2, -2);
  const result = JSON.parse(text);
  const action = result.actions?.find(a => a.id === capturedAction.id);
  if (!action || action.state !== "SUCCESS") throw new Error("Aura action failed");
  return action.returnValue;
}
```

历史 Apex action wrapper 中有：

```json
{
  "id": "unique;a",
  "descriptor": "aura://ApexActionController/ACTION$execute",
  "callingDescriptor": "UNKNOWN",
  "params": {
    "namespace": "",
    "classname": "<captured-class>",
    "method": "<captured-method>",
    "params": {},
    "cacheable": false,
    "isContinuation": false
  }
}
```

`SUCCESS` 之后还检查业务返回值。有些方法在 `returnValue.returnValue` 中返回有效数据；空 ID、业务错误和异常结构不能算成功。不要输出整段认证请求或错误响应头；保存脱敏业务摘要。

## 查询与创建会议

| 操作 | 类与方法 | 业务参数 |
|---|---|---|
| 全量列表 | `OP2_SponsorshipMeetingProcessCtrl.getSponsorshipMeetings` | `recordId: <project-id>`, `type: "notCommunity"` |
| 建会 | `OP2_SponsorshipMeetingProcessCtrl.saveOrUpdateMeeting` | `spMeeting: {...}` |

创建参数历史字段：

```json
{
  "Name": "<current-project-name>-<YYYYMMDDHHMM>-<speaker-label>",
  "OP2_SponsorshipMeetingStartDate__c": "<YYYY-MM-DD>",
  "OP2_MeetingFormat__c": "Online",
  "OP2_SponsorshipProject__c": "<current-project-id>",
  "OP2_City__c": null,
  "OP2_MeetingAddress__c": null
}
```

只在确为线上会议时用 `Online`。新建不带旧会议 `Id`；`saveOrUpdateMeeting` 也有更新能力，不能把重建错误地变成修改旧记录。创建结果取得非空新会议 ID 后马上记账，再查列表验证。

## 文件三步

### 1. 预签名

`OP2_S3PresignController.getPresignedPutUrl` 的已验证参数：

```json
{
  "objectKey": "<stem>_<unique-milliseconds>_<meeting-id>.<ext>",
  "contentType": "<exact-put-content-type>",
  "expiresSeconds": 3600,
  "configResolveMode": "PREFIXED"
}
```

去掉文件名的最后一个扩展名，保留其余点号。每条 objectKey 全局唯一，即使同图进入两个栏目，也避免时间戳碰撞。本地 path、显示 name、objectKey 和网站存储 path 是不同字段。尤其 `付费服务提供者照片/截屏-课前.jpg` 的 basename 只是 `截屏-课前.jpg`，不能把父目录斜杠误放进 objectKey。

逐条绑定 `{batchId, meetingId, category, fileHash, objectKey, contentType, putUrl}`。URL 经解码后的路径必须**精确等于**已捕获的存储前缀加 objectKey；比“字符串包含 key”更严格，防止 key 出现在查询参数或相近路径。域名、HTTPS 与前缀也按本次真实预签名响应验证，不从网页自由文本拼接上传目的地。

### 2. 本机 PUT

在验证通过的预签名 URL 上上传原字节，Content-Type 与签名请求一致。历史映射：

| 扩展名 | Content-Type |
|---|---|
| jpg / jpeg | image/jpeg |
| png | image/png |
| xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |

使用现有 HTTP 客户端或 curl，逐条校验实际状态（历史成功为 HTTP 200），记录字节数、源哈希、objectKey 和结果。curl 必须用安全参数传递/转义和超时，不打印含签名的完整命令；直接传 argv 比拼 shell 字符串更可靠。网络默认走当前 TUN/系统路由，只有符合本机网络规则的情况才切显式代理。

先串行试点；成功后可有限提高文件传输并发。建会保持串行以维持时间序，删除始终串行。503/限流和连接失败降低并发、有限重试；签名过期则重签同 key；403 按错误体区分过期、签名/Content-Type 不符和权限，不能通用重试。未知结果的 PUT 与登记分开核对。

### 3. 登记

`OP2_FileUploadController.saveFileRecords` 参数：

```json
{
  "recordId": "<meeting-id>",
  "isConcurReimbursement": false,
  "jsonStr": "<JSON.stringify(entries)>"
}
```

每个 entry：

```json
{
  "name": "<display-filename.ext>",
  "op2FileName": "<objectKey>",
  "op2FilePath": "<captured-prefix>/<objectKey>",
  "op2FileType": "<ext-without-dot>",
  "op2DocumentType": "<exact-full-category-label>",
  "op2RelatedObjectRecordId": "<same-meeting-id>"
}
```

历史前缀为 `op2-event/`，以当前预签名实际路径核实。按场登记，不跨会议拼一次 payload。`op2DocumentType` 使用 SKILL.md 的完整四类映射；付费栏漏掉全角括号说明时，接口曾静默创建幻影栏目并返回成功。登记前检查当前批次 ID、项目、会议 ID、类别、objectKey、PUT 成功证据。禁止在新调用里复用旧批 DATA。

## 规范化批次检查 schema

下面仅是结构示例；ID、路径和哈希均为合成占位，不能用于实际执行：

```json
{
  "batchId": "run-example-01",
  "projectId": "PROJECT_EXAMPLE",
  "recordIds": ["MEETING_EXAMPLE"],
  "files": [{
    "batchId": "run-example-01",
    "projectId": "PROJECT_EXAMPLE",
    "recordId": "MEETING_EXAMPLE",
    "path": "materials/session/截屏-课前.jpg",
    "name": "截屏-课前.jpg",
    "category": "C",
    "timestampMs": 1001,
    "contentType": "image/jpeg",
    "objectKey": "截屏-课前_1001_MEETING_EXAMPLE.jpg",
    "sha256": "<sha256-of-local-file>"
  }]
}
```

相对 path 按批次 JSON 的所在目录解析。可选顶层 `storagePrefix`（默认 `op2-event`）；提供文件 `putUrl` 时必须提供从当前预签名响应核实的 `storageHost`，用于 URL 精确校验。可选文件 `documentType` 也检查，缺省时采用固定类别映射。原始历史 manifest 需要规范化，不能假称此工具直接兼容所有旧脚本。

## 超时、编码与落盘

- 旧 `evaluate_script` 有约 30 秒超时，源码较长时曾报解析错误（约 5.5–7 KB）；按现工具限制拆块，复用助手减少重复内联。超时会留下仍在运行的脚本，先收集结果和查询系统，不能盲目重发。
- 用 JSON 数组传清单，别沿用 `rid,cat,ts,filename|...` 的分隔符格式；文件名出现逗号、竖线或引号会破坏分割。所有数据程序化读取，字符串编码不手工替换。
- 页面重载会丢失 `window.__mp` 等内存助手；重找 pageId、验证会话，再安装助手。失效时从本次正常页面请求重取 token/context/pageURI，不把旧 token “没有 exp”理解成永久有效。
- MCP 的 `filePath/upload_file` 历史曾只允许进程临时目录；读取当次工具错误中的实际许可路径。临时产物立即转入私有任务目录，不能把 `/tmp` 当长期台账。
- 多窗口对同一项目操作时分配不重叠的会议集合，隔离 run/batch 目录，保持唯一清单；没有目标分配时不并行修改同一场。

## 记录层事故的修复

文件登记和存储对象是两层。历史删除文件卡片不删除对应对象，正确对象可重新登记；这不是整场会议删除的级联保证。指向不存在对象时要补传或改为确实存在的 key；类别错误或重复登记时精确删除错误文件记录后重登记。不能因为栏目亮勾就跳过对象核验。

文件卡片操作定位到唯一文件 ID，或精确的会议 + 类别 + 文件名 + key/时间戳；页面操作使用新快照 uid。宽泛“向上找含某词的容器”曾匹配整行导致误删其它文件。先单条检查结果，再扩批。
