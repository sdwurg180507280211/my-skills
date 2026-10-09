---
name: github-aliyun-deploy
description: 把任意项目配成「本地/手机改代码 → push GitHub main → 阿里云 ECS 自托管 Runner 自动 Docker 部署」的闭环。当用户说"自动部署到阿里云""GitHub Actions 自托管 Runner""本地改代码自动上线""帮我把 XX 项目配成云端自动部署""手机 Codex 改完自动发布""搭一个测试环境""develop 测试 main 生产"时使用。涵盖 Docker 化、deploy.yml、ECS 初始化、同机多环境（测试/生产）隔离、nginx 按域名反代、certbot HTTPS（SAN 证书 + 自动续期）与已知踩坑。
---

# 本地 → GitHub → 阿里云 ECS 自动部署

一套通用方法论：GitHub 自托管 Runner 在服务器上**主动拉代码**执行部署，不需要 GitHub 反向 SSH 进服务器，因此 22 端口可长期关闭。

## 何时用
- 用户要把某个本地项目做成「push 即部署」到阿里云。
- 用户有阿里云 ECS，希望手机/电脑改完代码自动上线。
- 用户已有一套这样的项目，想用相同套路套到另一个项目。

## 核心约定（自动部署稳定的前提）
- 服务名、容器端口（默认 8080）、健康检查路由 `/api/health` **固定不变**。
- 凭据只放服务器 `/opt/{{PROJECT}}/.env`（`chmod 600`），仓库只提交 `.env.example`。
- `runs-on: self-hosted` 才能用服务器上的 Runner。

## 执行流程（按需跳步，已存在的产物跳过）

### 1. 容器化（本地）
- `Dockerfile`：基础镜像按语言选，`USER` 非 root，`EXPOSE 8080`，`CMD` 启动服务。
  - **Node 轻量项目**（无原生编译依赖）：`node:20-alpine`。
  - **Node 含原生模块**（如 `better-sqlite3`、需 python/make/g++ 编译）：改用 `node:*-bookworm-slim`，`npm install` 走国内源 `registry.npmmirror.com`（见踩坑 C）。
  - **Python 后端**用 `python:3.13-slim` + `uvicorn` 起 `:8000`；**务必在 `pip install` 加阿里云 PyPI 镜像源**（`-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`），否则 ECS 直连 PyPI 会卡死。
- `docker-compose.yml`：服务名 = `{{PROJECT}}`，`ports: "${BIND_ADDR:-127.0.0.1:8080}:8080"`（只绑内网，由 nginx 反代），`restart: unless-stopped`，挂载 `./data`。
- `.dockerignore`：排除 `node_modules dist .git .github docs scripts .env* data/* .DS_Store *.log`。
- `.env.example`：只放占位（如 `ADMIN_TOKEN=__强随机值__`）。

### 2. GitHub 仓库 + Actions
- `gh repo create {{OWNER}}/{{PROJECT}} --public --source=. --remote=origin --push`
- `.github/workflows/deploy.yml`（见下方模板）：on push main，job `runs-on: self-hosted`，步骤 checkout → `docker compose --env-file /opt/{{PROJECT}}/.env up -d --build` → 健康检查 `curl -fsS http://127.0.0.1:8080/api/health`。

### 3. 阿里云 ECS 一次性初始化（只在服务器做这一次）
- 临时放开安全组 22 给当前出口 IP，用完收紧。
- 建 `deployer` 用户并加入 `docker` 组。
- 装 Docker + compose 插件：
  - Ubuntu/Debian：`apt install -y git docker.io docker-compose-plugin`
  - Alibaba Cloud Linux/CentOS：先加阿里云 docker-ce 源再 `yum install -y docker-ce docker-compose-plugin`（避免 compose 插件缺失）。
- **踩坑 A — Docker 起不来（socket activation）**：`systemctl enable --now docker.socket` 再 `systemctl restart docker`。
- **踩坑 B — 拉镜像超时**：写 `/etc/docker/daemon.json` 配 `registry-mirrors`（daocloud / 163 / baidu），`systemctl restart docker`。
- **踩坑 C — 构建阶段卡死（npm / apt 在 ECS 直连慢）**：
  - **npm 重依赖项目**（如 Next.js）：`RUN npm install` 直连 `registry.npmjs.org` 在 ECS 上极慢（实测 8s/请求），几百个包基本跑不完。解决：Dockerfile 加 `--registry https://registry.npmmirror.com` + BuildKit 缓存挂载（`RUN --mount=type=cache,target=/root/.npm npm install --registry https://registry.npmmirror.com`）。
  - **Debian/Ubuntu 基础镜像 `apt-get update`**：Dockerfile 里若有 `apt-get install`（如给 `better-sqlite3` 装 `python3 make g++`），默认源 `deb.debian.org` 在 ECS 构建容器内常卡死。解决：先 `sed -i 's@deb.debian.org@mirrors.aliyun.com@g'` 再 `apt-get update`，并加 apt 缓存挂载。
  - **关键提醒：构建发生在 ECS 上，不是本地。** Runner 在服务器本地 `docker compose build`，所以**重应用首构建无缓存会跑 10–20 分钟，属正常、不是卡死**；中途不要 `docker buildx prune -f`，否则清空缓存强制全量重建，反而暴露网络问题。
- 建 `/opt/{{PROJECT}}/.env`（真实凭据，`chmod 600`）。
- **注册 Runner（核心）**：仓库 `Settings → Actions → Runners → New self-hosted runner → Linux x64`，复制命令在 ECS 以 `deployer` 执行。
  - **优先在 ECS 上直接 `curl` 下载 Runner 包**；必须本机传的话用 `rsync -P --partial`（scp 大包会截断）。
  - **衍生坑：ECS 直连 GitHub releases 下载也可能被墙**（返回 "Not Found" 错误页而非包）。若服务器上已缓存**同版本** Runner 包（如另一项目目录下的 `actions-runner-linux-x64-<ver>.tar.gz`），直接 `cp` 复用即可，省去联网。
  - `./config.sh --url ... --token ...` → `sudo ./svc.sh install` → `sudo ./svc.sh start`。
  - 验证 GitHub Runners 页显示 **Idle / Online**。
- nginx 反代 `127.0.0.1:8080`（`listen 80`），`systemctl enable --now nginx`。安全组 80/443 对 `0.0.0.0/0` 开放（**80 通不等于 443 通，443 要单独放行，见踩坑 I**）。
- HTTPS（有域名再做）：见下方「HTTPS 完整落地」章节（webroot 签 SAN 证书 + 80 保留 ACME、其余 301 + HSTS + 续期钩子）。

### 4. 验证
- 本地/手机 push main → 看仓库 Actions 跑绿 → 公网访问域名/IP 看到更新。

## 进阶 A：同机多环境（develop→测试 / main→生产）

在**同一台 ECS**上零成本再跑一套测试环境，形成 `本地 → push develop → 自动部署测试 → 人工验收 → 合并 main → 自动部署生产` 的发布链路。核心是**两套环境每个维度都物理隔离**：

| 维度 | 生产 | 测试 |
|---|---|---|
| 触发分支 | `main` | `develop` |
| 目录 | `/opt/{{PROJECT}}` | `/opt/{{PROJECT}}-test` |
| 容器名 | `{{PROJECT}}` | `{{PROJECT}}-test` |
| 镜像名 | `{{PROJECT}}:latest` | `{{PROJECT}}-test:latest` |
| 端口（回环） | `127.0.0.1:8080` | `127.0.0.1:8081` |
| 数据卷 | `/opt/{{PROJECT}}/data` | `/opt/{{PROJECT}}-test/data` |
| `.env` | `/opt/{{PROJECT}}/.env` | `/opt/{{PROJECT}}-test/.env`（独立密码/SESSION_SECRET） |
| concurrency group | `{{PROJECT}}-production` | `{{PROJECT}}-test` |
| **compose project** | 默认 | **`-p {{PROJECT}}-test`（必须显式，见踩坑 D）** |

落地要点：
- **CI 要覆盖 develop**：`on.push.branches: [main, develop]`，否则 develop 推送不触发 CI，测试部署的 `workflow_run` 事件不会来。
- **deploy 用 `workflow_run` 按分支分流**：`deploy` job `if: workflow_run.head_branch == 'main'`；`deploy-test` job `if: workflow_run.head_branch == 'develop'`。
- 测试用独立 `docker-compose.test.yml`（容器名/镜像/端口/数据目录全改），部署命令一律带 `-p {{PROJECT}}-test`。
- 公网暴露走 nginx 按 `server_name` 分流（见「HTTPS 完整落地」），容器继续只绑回环。

- **踩坑 D（严重：误删另一环境容器）**：同一 Runner 工作目录下两个 compose 文件，docker compose 默认 project name 都推导自**目录名**（相同）。测试部署执行 `docker compose up -d --remove-orphans` 时，会把同 project 下的**生产容器当孤儿删掉**，导致生产瞬间中断。修复：测试环境所有 compose 命令（配置检查、`up`、回滚）**统一显式加 `-p {{PROJECT}}-test`**，与生产从 compose 层彻底隔离。
- **踩坑 E（手动部署误伤生产）**：若 `deploy` 和 `deploy-test` 两个 job 的 `if` 都裸含 `github.event_name == 'workflow_dispatch'`，在 GitHub 点「Run workflow」会**同时触发生产+测试**。修复：`workflow_dispatch` 加一个 **required 的 `inputs.environment`（choice: `test`/`production`）**，每个 job 再 `&& inputs.environment == '...'` 守卫；手动测试部署时 checkout 要显式指定 `ref: develop`（否则默认拉 main）。

## 进阶 B：HTTPS 完整落地（webroot + SAN 证书 + 自动续期）

比 `certbot --nginx` 更可控的标准做法，尤其适合**多域名/多环境同机**：

1. **签 SAN 合并证书（一张覆盖多个域名，统一续期）**：
   `certbot certonly --webroot -w /var/www/letsencrypt -d www.{{域名}} -d test.{{域名}} --non-interactive --agree-tos --email admin@{{域名}}`
2. **nginx 结构**：
   - 80 端口 server：保留 `location /.well-known/acme-challenge/ { root /var/www/letsencrypt; }`（续期必需），其余 `return 301 https://$host$request_uri;`。
   - 443 端口 server：按 `server_name` 分流，`ssl_certificate .../fullchain.pem`，`proxy_pass http://127.0.0.1:{8080|8081}`。
3. **应用侧配套**（改完 `.env` 需**重建容器**才生效）：`COOKIE_SECURE=1`、`NEXT_PUBLIC_SITE_URL=https://...`。
4. **HSTS（第一阶段稳妥值）**：`add_header Strict-Transport-Security "max-age=31536000" always;`。**先不加 `includeSubDomains` / `preload`**——一旦加，全子域必须长期支持 HTTPS，撤销困难；等所有子域 HTTPS 稳定后再考虑。
5. **续期后自动 reload nginx**（否则续期成功但 nginx 仍用旧证书）：
   `/etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh` 内容 `#!/bin/bash` + `systemctl reload nginx`，`chmod +x`。certbot 续期成功后自动执行。
6. **验证续期链路**：`certbot renew --dry-run`；定时器 `systemctl list-timers | grep certbot`（certbot 2.x 默认已 enable，"Run certbot twice daily"，无需再 `enable --now`）。

- **踩坑 F（安全组放行 8081 无效）**：容器端口绑 `127.0.0.1` 时，回环端口外部根本到不了，**单纯在安全组放行 8081/8080 毫无作用**。公网访问必须靠 nginx（80/443）反代到回环端口。这是 feature 不是 bug——回环绑定 + nginx 才是安全的正确姿势。
- **踩坑 G（ECS 自连公网 IP 被拦，误判服务挂了）**：在 ECS 上用**自己的公网 IP** 访问自身端口（如 `curl https://{{ECS公网IP}}/`）会被安全组/路由回流（hairpin）拦住，**即使服务完全正常也会超时/失败**。自测一律用 `curl -k -H 'Host: 域名' https://127.0.0.1/...`；判断外部可达性用外部工具或让用户浏览器实测。
- **踩坑 H（dry-run 像"卡死"其实是随机延迟）**：`certbot renew --dry-run` 非交互模式续期前会 `Non-interactive renewal: random delay`，**随机 sleep 最长 ~8 分钟**（实测 440s）。设短超时（如 280s）会被掐断，误判成网络卡死。快速验证加 `--no-random-sleep-on-renew` 跳过。
- **踩坑 I（80 通≠443 通）**：新开 443 时，安全组入方向要**单独加 443/TCP（0.0.0.0/0）**规则，不要以为 80 开了 443 就自动通。判据：ECS 上 `bash -c 'cat</dev/null>/dev/tcp/IP/443'` 若 `443 blocked` 而 `80 reachable`，且 nginx 已 `listen 0.0.0.0:443`、证书正常，即为安全组未放行 443。

## 复用模板

### deploy.yml
```yaml
name: Deploy to Aliyun ECS
on:
  push: { branches: [main] }
  workflow_dispatch:
jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: |
          set -euo pipefail
          docker compose --env-file /opt/{{PROJECT}}/.env down || true
          docker compose --env-file /opt/{{PROJECT}}/.env up -d --build
          docker image prune -f
      - run: |
          sleep 3
          curl -fsS http://127.0.0.1:8080/api/health || exit 1
```

### docker-compose.yml
```yaml
services:
  {{PROJECT}}:
    build: { context: . }
    image: {{PROJECT}}:latest
    container_name: {{PROJECT}}
    restart: unless-stopped
    environment:
      NODE_ENV: production
      PORT: 8080
      ADMIN_TOKEN: ${ADMIN_TOKEN:-replace-with-a-strong-token}
    ports:
      # 若 ports 直接等于 BIND_ADDR 变量（不拼容器端口），则 BIND_ADDR 必须写全三段：
      # 宿主机IP:宿主机端口:容器端口，如 0.0.0.0:8090:8081，否则 compose 报 invalid hostPort
      - "${BIND_ADDR:-127.0.0.1:8080}:8080"
    volumes:
      - ./data:/app/data
```

## 排错速查
| 现象 | 原因 | 解决 |
|---|---|---|
| 任务排队 | `runs-on` 错 / Runner 离线 | 确认 `self-hosted`；`su - deployer && sudo ./svc.sh status` |
| Docker 起不来 | socket activation | `enable --now docker.socket` 后 `restart docker` |
| 拉镜像超时 | 国内直连慢 | 配 `registry-mirrors` 后 `restart docker` |
| 502 | 容器未起/端口错 | `docker compose --env-file /opt/{{PROJECT}}/.env logs` |
| 健康检查失败 | 无 `/api/health` | 代码加该路由返回 200 |
| 换凭据 | .env 未生效 | 改 `/opt/{{PROJECT}}/.env` 再 push 触发重部署 |
| 构建阶段 pip 卡死 | ECS 直连 PyPI 超时 | Dockerfile `pip install` 加阿里云源 `-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com` |
| 构建阶段 npm 卡死 | ECS 直连 registry.npmjs.org 慢 | Dockerfile `npm install` 加 `--registry https://registry.npmmirror.com` + npm 缓存挂载（见踩坑 C） |
| 构建阶段 apt-get 卡死 | Debian 基础镜像直连 deb.debian.org | Dockerfile apt 步骤 `sed` 换 `mirrors.aliyun.com`（见踩坑 C） |
| 首次构建极慢（10+ 分钟） | 无缓存 + ECS 小机器 | 正常；构建在 ECS 本地跑，别中途 `docker buildx prune -f` |
| compose 报 `invalid hostPort` | BIND_ADDR 缺容器端口 | 变量写全三段 `0.0.0.0:宿主端口:容器端口`（如 `0.0.0.0:8090:8081`） |
| 部署测试却把生产容器删了 | 两 compose 共用默认 project，`--remove-orphans` 误删 | 测试命令统一加 `-p {{PROJECT}}-test`（踩坑 D） |
| 手动 Run workflow 同时部署生产+测试 | 两 job 都裸判 `workflow_dispatch` | 加 required `inputs.environment`（test/production）守卫（踩坑 E） |
| 放行安全组 8081 仍访问不了测试 | 容器绑 127.0.0.1，回环端口外部到不了 | 走 nginx 按 `server_name` 反代，别指望开端口（踩坑 F） |
| 浏览器打不开 HTTPS、80 却正常 | 安全组未放行 443 | 入方向单独加 443/TCP 0.0.0.0/0（踩坑 I） |
| ECS 自测公网 IP 端口超时 | hairpin 回流被拦 | 用 `127.0.0.1` + `-H 'Host: 域名'` 自测（踩坑 G） |
| `certbot renew --dry-run` 像卡死 | 非交互随机延迟最长 ~8 分钟 | 加 `--no-random-sleep-on-renew`（踩坑 H） |
| 推送后网页毫无变化、deploy 运行显示 failure | 手动 `docker run --name X` 起的容器无 compose 标签，后续 `docker compose up` 因同名 `Conflict` 失败并回滚 | 在 `up` 前先 `docker rm -f {{PROJECT}}`（及 `{{PROJECT}}-test`）清掉可能的遗留手动容器（踩坑 J） |
| 部署瞬间 502 数秒后恢复 | 单台自托管 Runner 上生产/测试部署时间重叠，`docker rm -f` 删旧容器到 `up` 重建之间有窗口 | 属正常短暂中断；要零停机可改蓝绿（先起新容器再停旧） |

## 给手机端 AI 的提示词模板
```
你正在维护 GitHub 仓库 {{PROJECT}}（{{说明}}）。
项目现状（沿用，勿推翻）：技术栈{{...}}；已具备 Docker 部署与 deploy.yml 自动部署；关键字段/钩子{{...}}；设计风格{{...}}。
本次任务：{{具体任务}}
硬性约束：1) 凭据走环境变量，不写死代码，只提交 .env.example；2) 保持最少依赖；3) 不改 docker-compose 服务名与 8080 端口。
交付：创建 PR（目标 main），写清改动、本地验证、部署方式、访问地址。
```

## 完整图文版
详见本目录 `PLAYBOOK.md`（所有占位符与踩坑细节都在那里）。
