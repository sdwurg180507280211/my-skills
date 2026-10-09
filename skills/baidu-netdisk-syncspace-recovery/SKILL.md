---
name: baidu-netdisk-syncspace-recovery
description: 排查百度网盘「同步空间」目录在 macOS 本地丢失/多出文件的问题。当用户说"同步空间/百度网盘同步目录里的文件丢了""帮我看看网盘同步哪里不对""本地和云端不一致"时使用。通过解析客户端本地 SQLite（SyncHistory / sync_flux / sync_status / sync_revision / filecache.file_meta）与云端 API 双向对账，定位差异并给出可执行的恢复路径。
agent_created: true
---

# 百度网盘同步空间丢文件排查（macOS）

## 触发场景
用户报告「同步空间里某个文件夹/文件不见了」「本地和网盘不一致」「帮我找回同步空间丢失的文件」。

## 第一原则
**只读排查，不动用户文件。** 所有数据库先 `cp` 到 `/tmp/<name>_inspect/` 再读，避免锁住正在运行的客户端。
删除/还原动作一律交给用户或先取得明确确认。

## Step 1 定位同步空间
```bash
ls -d ~/Desktop/同步空间 ~/百度网盘* ~/BaiduNetdisk* 2>/dev/null
ls -la ~/Library/CloudStorage 2>/dev/null
```
`同步空间` 通常是软链接，`readlink` 拿到真实目录。真实目录里会有 `.cache/` 和 0 字节的 `Icon` —— 这两个是**百度网盘同步空间的指纹**，可据此确认。

## Step 2 确认云端映射路径
同步空间的云端路径前缀是 **`/_pcs_.workspace/`**，不是网盘根。用 baidu-netdisk MCP 验证：
```
file_list(dir="/_pcs_.workspace")            # 一级：其它 / 工作 / ...
file_list(dir="/_pcs_.workspace/其它/审核")   # 每页 10 条，翻 page=1,2,3...
```
`file_list(dir="/")` **看不到** `_pcs_.workspace`，不要因此以为同步空间不存在。

## Step 3 解析客户端数据库（核心）
```bash
APP=~/Library/Application\ Support/com.baidu.BaiduNetdisk-mac
ls "$APP"                                    # 找 32 位 hex 用户目录
ls "$APP/AppData"                            # at_trche（加密二进制，读不出，跳过）
D="$APP/<32位hash>"; mkdir -p /tmp/bd_inspect
cp "$D"/SyncHistory.db* "$D"/F*.db "$D"/S*.db "$D"/R*.db "$D"/filecache.db* /tmp/bd_inspect/ 2>/dev/null
cd /tmp/bd_inspect
for f in SyncHistory.db F*.db S*.db R*.db filecache.db; do
  echo "== $f"; sqlite3 "$f" ".tables"; sqlite3 "$f" ".schema" | head -20
done
```
已知表结构（v2.x 客户端）：

| 文件 | 表 | 关键列 | 用途 |
|---|---|---|---|
| `SyncHistory.db` | `sync_history` | `type, is_dir, server_path, local_path, end_time, error_code` | 每次同步流水；`server_path` 前缀 `/_pcs_.workspace/` |
| `F*.db` | `sync_flux` | `relative_path, type` | 待同步/队列（`type=10` 常见） |
| `S*.db` | `sync_status` | `file_name, is_dir` | 文件名级状态 |
| `R*.db` | `sync_revision` | `relative_path, is_dir, revision, local_mtime` | 同步快照；`relative_path` 以 `~/` 开头代表同步根 |
| `filecache.db` | **`file_meta`** | `parent_path, server_filename, isdir, server_mtime, fid` | **客户端缓存的云端全量索引，最有用** |

`file_meta` 的 `parent_path` 是云端绝对路径（如 `/_pcs_.workspace/其它/审核/`），且 `isdir=1` 标目录 —— 用它可直接重建云端树。

## Step 4 双向对账（决定性步骤）
```bash
cd /tmp/bd_inspect && python3 - <<'EOF'
import os, sqlite3
root = os.path.realpath(os.path.expanduser("~/Desktop/同步空间"))  # 换成 readlink 得到的真实路径
con = sqlite3.connect("filecache.db")
rows = con.execute("select parent_path, server_filename, isdir from file_meta "
                   "where parent_path like '/_pcs_.workspace%'").fetchall()
miss_d, miss_f = [], []
for pp, name, isdir in rows:
    rel = pp[len("/_pcs_.workspace/"):] + name
    if not os.path.exists(os.path.join(root, rel)):
        (miss_d if isdir else miss_f).append(rel)
print("云端有/本地缺 目录:", len(miss_d))
for x in sorted(miss_d): print("  [DIR ]", x)
print("云端有/本地缺 文件:", len(miss_f))
for x in sorted(miss_f)[:60]: print("  [FILE]", x)
EOF
```
反向查（本地应有）：用 `sync_revision.relative_path` 去掉 `~/` 前缀后同样 `os.path.exists` 检查。

注意：**`file_meta` 是缓存，可能有陈旧条目**。对关键结论务必用 MCP `file_list` 实时复核一次再下结论。

## Step 5 定向搜索用户提到的名字
```bash
# 路径段恰好是某名字（目录）
sqlite3 filecache.db "select parent_path||server_filename from file_meta where isdir=1 and server_filename glob '2025*';"
# 某子树下所有含关键词的目录
sqlite3 filecache.db "select parent_path||server_filename from file_meta where isdir=1 and parent_path like '/_pcs_.workspace/其它%' and server_filename like '%2025%';"
sqlite3 SyncHistory.db "select * from sync_history where server_path like '%/2025/%';"
```

## Step 6 回收站 —— 能力边界（必须如实告知用户）
- **百度网盘云端回收站：MCP 连接器没有接口。** 现有方法仅 `file_copy / file_list / file_keyword_search / file_meta / file_move / file_rename / file_sharelink_set / file_upload_by_* / file_doc_list / file_image_list / file_video_list / file_semantics_search / get_quota / make_dir / user_info`。**读不到也还原不了**，必须让用户在网盘客户端「回收站」或 pan.baidu.com 左侧「回收站」自行还原。
- 本地 macOS 废纸篓：`ls -1 ~/.Trash | grep -i <关键词>`
- Time Machine：`tmutil listlocalsnapshots /`；若为空且 `tmutil destinationinfo` 报 `No destinations configured`，则**无本地快照可回滚**。

## 常见误判
- 把「云端有、本地无」当成文件丢失 —— 同步空间是**选择性同步**，云端大量目录本来就不镜像到本地。只有用户确认过「这些本来在本地」才算真丢失。
- 只查 `~/.Trash` 就下结论 —— 同步空间的删除走网盘回收站，不走 macOS 废纸篓。
- 用 `file_list("/")` 找同步空间 —— 找不到，必须用 `/_pcs_.workspace`。

## 输出建议
给用户三块：① 结论（有/没有）；② 已查过的数据源清单（用表格）；③ 用户能自己做的下一步（云端回收站入口、要补充的信息）。不要给长篇 runbook。
