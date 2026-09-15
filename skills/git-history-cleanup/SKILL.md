---
name: git-history-cleanup
description: 安全整理并重写 Git 分支历史，在最终仓库 Tree 完全不变的前提下保留真实有效的功能、修复、回退与演进记录，只删除明确无价值的临时、占位、误操作和即时修补噪声。用户明确要求“整理最近提交”“清理 Git 历史”“删除无效提交”“合并刚提交错又立即修正的碎片提交”“重写历史但代码不能变”时使用；不用于普通代码修改，也不得在未获授权时强推共享分支。
---

# Git 历史整理

目标不是“把提交数量压到最少”，也不是“让日志看起来整齐”，而是：

> **保留项目真实演进，删除无价值的操作过程。**

默认策略是保守整理：**正常有效提交不动；只有能够明确证明存在问题的提交才删除、合并或改写。**

## 两个核心不变量

历史整理必须同时满足两个维度。

### 1. 最终仓库状态完全一致

```text
OLD_HEAD^{tree} == NEW_HEAD^{tree}
```

Git Tree SHA 相同意味着最终目录结构、文件内容、文件模式、子树与 gitlink 等 Git 记录完全一致。

只要最终 Tree SHA 不相同，就不得把整理后的历史写回目标分支。

### 2. 有价值的历史信息不能被过度压缩

Tree 相同只能证明“代码没变”，不能证明“历史整理得对”。

还必须检查：

- 独立功能提交是否仍然可见。
- 独立缺陷修复是否仍然可见。
- 有真实决策意义的 revert 是否仍然可见。
- 不相关改动是否被错误合并到同一个大提交。
- 原来已经清晰、有效的提交是否被无理由重写。

如果一次整理把几十条真实功能和修复压成几个“模块级大提交”，即使 Tree 完全相同，也属于**过度整理**。

## 第一原则：默认保留，明确有问题才处理

不要先问“这个提交能不能删”，而要先问：

1. 这个提交是否代表一个独立、完整、可解释的开发事件？
2. 删除它以后，会不会让后来的人误解项目为什么变成现在这样？
3. 它是否只是敲代码过程中的临时状态、误操作或紧邻补救？

无法明确证明没有历史价值时，**保留**。

### 推荐判定表

| 情况 | 默认动作 | 说明 |
| --- | --- | --- |
| 正常有效的独立功能提交 | 保留 | 不为了整齐而合并 |
| 正常有效的独立修复提交 | 保留 | `fix` 不是噪声 |
| 提交信息不规范，但代码有效 | reword | 不因 message 差而删除代码 |
| 手滑、错文件、调试日志、临时检查、占位文件 | 删除 | 没有独立历史价值 |
| 一个功能刚提交就发现遗漏，下一条立即补齐 | 合并 | 属于同一次实现过程 |
| 一个提交同时包含有效和错误改动 | 拆分 | 保留有效部分，丢弃错误部分 |
| 功能稳定存在一段时间后发现真实缺陷 | 保留 feature + fix | 这是项目真实演进 |
| 新增后当天立即完整撤销，且只是实验/误操作 | 可删除整链 | 必须有充分证据 |
| 已发布/使用过，后来因业务决策回退 | 保留新增 + revert | 回退本身有历史意义 |
| merge 只是无额外内容的包装 | 可去掉 merge 包装 | 保留分支内真实提交 |
| merge 拓扑有协作、发布、审计价值 | 保留 merge | 不机械线性化 |

## “错误提交”如何理解

不要把“错误提交”简单等同于 `fix`、`revert` 或“最终净效果为零”。

### 可以删除的错误过程

典型特征：

- `tmp`
- 临时检查文件
- 错误标记文件
- 占位文件
- 调试日志
- 测试上传文件
- 刚创建立刻删除的无业务文件
- 为了探测分支/权限/API 而制造的无意义提交

这类提交即使有独立 SHA，也没有项目演进价值。

### 应该合并的即时补救

例如：

```text
feat(系统设置): 增加登录验证码
fix(系统设置): 修复刚提交的验证码参数错误
fix(系统设置): 补充遗漏的验证码字段
```

如果三条连续发生、第一条在当时并未形成完整可用能力，后两条只是把同一次实现补完整，可以整理为一条完整功能提交。

### 应该保留的真实缺陷修复

例如：

```text
2026-07-10 feat(系统设置): 增加登录验证码
...
2026-07-25 fix(系统设置): 修复验证码过期后无法刷新问题
```

这类 `fix` 代表真实缺陷发现和修复，应单独保留。

判断重点不是时间间隔本身，而是：前一个版本是否已经作为一个独立、可解释的状态存在过。

## revert 不能按“净效果为零”机械删除

### 可以删除整条 add → revert 链

只有当能够明确证明：

- 这是短暂实验、误提交或当天即时撤销；
- 没有发布、没有形成其他依赖；
- 中间过程本身没有审计、协作或决策价值；
- 删除整链不会让人误解项目演进。

### 应保留 add + revert

如果功能曾经真实存在，后来因为：

- 产品需求变化
- 风险控制
- 上线后发现问题
- 架构决策改变
- 临时下线

而正式撤销，那么新增和 revert 都是有价值历史。

> “从来没做过”与“做过，后来正式撤销”是两种完全不同的项目历史。

因此：**最终净效果为零，只是删除候选信号，不是删除依据。**

## merge 的处理原则

不要一看到 merge 就拉平。

### 可以去掉纯包装 merge

如果 merge：

- 自身没有额外冲突解决内容；
- 只是把一个短分支中的若干真实提交带回主线；
- 分支拓扑没有发布、审计或协作价值；

可以保留分支内真实提交，去掉 merge 包装。

### 应保留 merge

如果 merge：

- 包含有意义的冲突解决；
- 表达一次正式版本集成；
- 关联多人协作边界；
- 关联发布/审计/合规流程；

则保留。

## 阶段 0：读取仓库规则

在生成任何新 commit 之前，先检查：

- `AGENTS.md`
- `CLAUDE.md`
- `CONTRIBUTING.md`
- `git-commit-convention.md`
- `.github/` 中的 CI / branch policy

如果仓库定义了 commit message 规范，所有新生成或 reword 的提交都必须遵守。

如果多个旧作者身份可能属于同一个人，只有在用户明确确认后才合并身份；不要擅自把其他人的提交归到当前用户。

## 阶段 1：冻结目标分支，并建立恢复点

分析完成后，真正写操作前重新读取目标分支：

```bash
TARGET=master
git fetch origin
OLD_HEAD=$(git rev-parse "origin/$TARGET")
OLD_TREE=$(git rev-parse "$OLD_HEAD^{tree}")
```

建立原始历史备份：

```bash
BACKUP="backup/history-before-$(date +%Y%m%d)"
git branch "$BACKUP" "$OLD_HEAD"
git push origin "$BACKUP"
```

必须记录：

```text
TARGET
BASE
OLD_HEAD
OLD_TREE
BACKUP
```

### 如果目标分支已经被整理过一次

不要覆盖旧恢复点。

推荐保留两层备份：

```text
backup/history-original-YYYYMMDD
backup/history-v1-before-YYYYMMDD
```

第一条保存最原始历史，第二条保存上一版整理结果。这样既能回到最初状态，也能回到最近一个可用整理版本。

如果分析期间目标分支新增了提交，必须把这些新增提交视为真实新工作重新纳入计划；不能用旧快照覆盖。

## 阶段 2：确定整理基线 BASE

BASE 是整理窗口之前最后一个保持不动的提交。

```bash
git log --graph --decorate --oneline <BASE>..<OLD_HEAD>
```

不要为了“减少提交数”向前扩大范围。

BASE 越早：

- 失效的旧 SHA 越多；
- 本地 clone 分叉越严重；
- 审计与回溯成本越高。

## 阶段 3：逐条审提交，不按模块粗分组

先建立提交清单，并查看每条提交的真实 diff，而不是只看 message：

```bash
git log --reverse --format='%H %P %s' <BASE>..<OLD_HEAD>
git show --stat --summary <sha>
git show <sha> --
```

对每条提交记录：

```text
SHA
message
parent(s)
changed paths
是否独立可解释
是否后来被修复/回退
是否只是即时补救
动作：KEEP / REWORD / SQUASH / DROP / SPLIT
证据
```

### 最重要的保守规则

- **正常有效提交默认 KEEP。**
- 不按“系统设置”“工作台”“测试计划”等模块把十几条独立提交压成一条。
- 不因为同一个功能相关，就自动 squash。
- 不因为最终代码里某功能不存在，就自动删除它的历史。
- 无法确定时 KEEP，而不是 DROP。

## 阶段 4：选择重写方式

### 策略 A：交互式 rebase

适合：

- 本地 Git 可用；
- 历史基本线性；
- 需要处理的 DROP/SQUASH 很少；
- 大部分提交保持原样。

```bash
git rebase -i <BASE>
```

优先：

- `pick`：正常有效提交
- `reword`：只修提交信息
- `fixup` / `squash`：只用于明确的即时补救
- `drop`：只用于明确无价值噪声

存在重要 merge 时使用保留 merge 的方式。

### 策略 B：按原提交粒度精细重放

适合：

- 原始历史复杂；
- 本地 Git 不可用，只能使用 Git 托管 API；
- 需要去掉部分 merge 包装或噪声提交；
- 必须最大限度保留有效提交明细。

核心不是“从最终 Tree 重新按模块造几个大提交”，而是：

> **从原始历史逐条读取真实改动，只对被判定为 DROP/SQUASH 的提交动手，其余有效提交按原粒度重放。**

推荐流程：

```text
parent = BASE

for original_commit in original_history_in_order:
    decision = classify(original_commit)

    if decision == DROP:
        continue

    if decision == SQUASH:
        accumulate_patch_into_target_commit()
        continue

    if decision == KEEP or REWORD:
        new_tree = replay_exact_effect(original_commit, parent)
        new_commit = create_commit(new_tree, parent, normalized_message)
        parent = new_commit

assert parent.tree == OLD_TREE
```

### 不要滥用“最终 Tree 驱动重建”

最终 Tree 很适合做**等价校验**，但如果直接按最终模块 subtree 重建历史，极易产生过度合并：

```text
几十条真实提交
→ 系统设置一个大提交
→ 缺陷管理一个大提交
→ 工作台一个大提交
```

这会丢掉真实演进明细。

如果确实需要低层 tree API：

1. 仍然先按原始 commit 粒度分类。
2. KEEP 的提交尽量重放其真实差异。
3. 只有明确 SQUASH 的小段才合并 tree 变化。
4. 最终 OLD_TREE 只作为硬校验，不作为“如何分组”的唯一依据。

### Tree API 的细节

- 优先复用已有 blob/subtree SHA。
- 不要提前把整个模块替换成最终 subtree，否则会提前吸收后续提交。
- 每个新提交都要确认 tree 与父提交不同，避免 no-op commit。
- 如果仓库要求 signed commits，低层 API 创建的 unsigned commit 不合格，应改用支持签名的正常 Git 流程。

## 阶段 5：提交信息处理

### 原 message 已合规

尽量保留，不为了统一措辞无意义 reword。

### 原 message 不合规，但提交有效

只 reword，不改变提交粒度。

例如：

```text
feature:登录页增加验证码功能
```

可规范为：

```text
feat(系统设置): 增加登录验证码功能
```

### 无意义 message

如：

```text
tmp
修改
错误
不使用
```

先判断代码是否有历史价值：

- 没有价值 → DROP。
- 有价值 → KEEP 代码并重新生成合规 message。

## 阶段 6：候选历史完成后的双重校验

### A. 最终代码等价

```bash
NEW_TREE=$(git rev-parse "$NEW_HEAD^{tree}")
test "$OLD_TREE" = "$NEW_TREE"
git diff --exit-code "$OLD_HEAD" "$NEW_HEAD" --
git diff --summary "$OLD_HEAD" "$NEW_HEAD"
```

### B. 历史粒度审计

重新查看：

```bash
git log --reverse --oneline <BASE>..<NEW_HEAD>
```

逐项确认：

- 原本正常有效的功能提交仍然可识别。
- 原本独立的真实 fix 没有被吃进大提交。
- 有价值的 add + revert 仍然存在。
- 只删除了有证据支持的噪声。
- 没有按模块粗暴聚合。
- 没有 no-op commit。

建议记录数量：

```text
原提交数
KEEP 数
REWORD 数
SQUASH 数
DROP 数
新提交数
```

新提交数变少不是目标，只是清理后的结果。

## 阶段 7：先发布清理分支，再执行 HEAD Guard

复杂整理先发布：

```text
refactor/clean-history-v2-YYYYMMDD
```

检查：

- 清理分支 HEAD = 计划 NEW_HEAD。
- 清理分支 Tree = OLD_TREE。
- 原始备份仍然存在。
- 上一版备份仍然存在（如果有）。
- BASE → 清理分支的提交数量与分类记录一致。

然后重新读取目标分支：

```text
current_target_head == OLD_HEAD
```

只有成立，才能更新目标分支。

本地 Git：

```bash
git push \
  --force-with-lease="$TARGET:$OLD_HEAD" \
  origin "$NEW_HEAD:refs/heads/$TARGET"
```

API `update_ref(force=true)` 也必须手工实现相同 lease 保护。

如果目标分支已经移动：

```text
停止
→ 获取新增提交
→ 重放到候选历史尾部
→ 更新 OLD_HEAD / OLD_TREE
→ 重新验证
→ 再做 HEAD Guard
```

禁止覆盖新增工作。

## 阶段 8：更新目标分支后复核

```bash
git fetch origin
FINAL_HEAD=$(git rev-parse "origin/$TARGET")
FINAL_TREE=$(git rev-parse "$FINAL_HEAD^{tree}")

test "$FINAL_HEAD" = "$NEW_HEAD"
test "$FINAL_TREE" = "$OLD_TREE"
```

再确认：

- 清理分支与目标分支 identical。
- 原始备份仍精确指向旧历史。
- 上一版备份仍可恢复。
- 提交数量正确。
- CI / workflow / required checks 已查看。

### Tree 相同不等于新 SHA 的 CI 已通过

历史重写会产生新 commit SHA。

旧 SHA 的 CI 不能自动继承到新 SHA。

如果新 SHA 没有 workflow/status：

```text
代码 Tree 已证明完全一致；当前新提交没有可确认的 CI 运行，因此不宣称测试已通过。
```

## 本地 clone 如何同步

历史重写后，旧本地分支通常已经与远端分叉。

### 没有未提交工作，也没有本地独有 commit

不要直接 `git pull`，推荐：

```bash
git fetch origin
git checkout <target>
git reset --hard origin/<target>
```

然后确认：

```bash
git status
git rev-parse HEAD
git rev-parse origin/<target>
```

两个 SHA 应一致。

### 有未提交修改

先保存：

```bash
git stash push -u -m "同步历史重写前本地修改"
git fetch origin
git checkout <target>
git reset --hard origin/<target>
git stash pop
```

如有冲突，人工解决。

### 有本地独有 commit

不要直接 hard reset。

```bash
git checkout <target>
git branch backup/local-before-history-sync
git fetch origin
git reset --hard origin/<target>
git log --oneline origin/<target>..backup/local-before-history-sync
```

再把确实需要的本地提交 `cherry-pick` / rebase 到新历史上。

## 回滚

备份分支不是临时垃圾，不要整理结束就删除。

需要回滚时：

1. 检查目标分支整理后是否有新提交。
2. 检查原始备份仍精确指向旧 HEAD。
3. 如果还保留上一版整理备份，可先比较哪一版更适合作为恢复点。
4. 使用 `--force-with-lease` 或 API 等价机制恢复。
5. 再验证 HEAD / Tree。

如果整理后已经有新工作，先保护新工作，禁止直接把目标分支粗暴回退到旧备份。

## 最终报告必须包含

至少报告：

- 整理前 HEAD / Tree。
- 整理后 HEAD / Tree。
- Tree 是否完全一致。
- BASE。
- 原提交数与新提交数。
- KEEP / REWORD / SQUASH / DROP 的数量或关键明细。
- 明确删除了哪些“无价值噪声”类型。
- 哪些真实 feature / fix / revert 被保留。
- 原始备份分支。
- 上一版备份分支（如果有）。
- 清理分支与目标分支是否 identical。
- 新 SHA 的实际 CI / workflow 状态。
- 本地 clone 同步方式。

不要只说“代码没变”，也不要只说“提交从 78 条变成 8 条”。

应该同时证明：

```text
代码没变
+
有效历史没有被过度压缩
```

## 禁止事项

- 未经明确授权强推共享分支。
- 没有备份就开始破坏性重写。
- 只看 commit message，不看真实 diff。
- 只看最终净效果就删除 add + revert。
- 把所有 `fix` 当成实现噪声。
- 按模块把多个独立功能/修复压成一个大提交。
- 为了减少 commit 数量而扩大整理范围。
- 无法确定是否有历史价值时擅自 DROP。
- 最终 Tree 不相同仍继续 force push。
- 目标分支冻结后移动，却仍覆盖旧快照。
- 把其他作者的提交改成当前用户，除非身份已明确确认。
- 因为 Tree 一样就宣称新 SHA 的 CI 已通过。
- 整理完成后立即删除唯一恢复分支。
- 对有未提交工作或本地独有提交的 clone 直接执行 `reset --hard`。
- 历史重写后建议用户直接 `git pull` 解决分叉。
