# PRD: Mem0 Self-Hosted Plugin for Codex

## 1. Product Summary

Mem0 Self-Hosted Plugin for Codex 是一个面向所有自部署 Mem0 用户的 Codex 插件产品。

它的目标不是只服务某一台腾讯云服务器，也不是一个个人脚本，而是提供一个通用插件，让用户可以把 Codex、Claude Code、Cursor 等 AI coding agent 的长期记忆能力连接到自己的 Mem0 self-hosted server。

一句话描述：

```text
让使用自部署 Mem0 的团队，也能获得官方 Mem0 Codex 插件的 MCP tools、skills、hooks、自动记忆和上下文召回能力。
```

## 2. Problem

官方 Mem0 插件目前主要面向 Mem0 Cloud：

- MCP 默认连接 `https://mcp.mem0.ai/mcp`
- hooks 默认调用 `https://api.mem0.ai/v3`
- 用户需要 Mem0 Cloud API key

但一类用户更希望自部署 Mem0：

- 不想把代码上下文、个人记忆、团队知识上传到外部 SaaS
- 已经在内网、云服务器、企业环境部署了 Mem0
- 想统一管理多台电脑、多种 AI coding tool 的记忆数据
- 希望 memory 数据留在自己的 Postgres/pgvector 中

目前这些用户面临的问题：

- 官方插件不能直接指向 self-hosted Mem0 REST API
- self-hosted REST API 与 Mem0 Cloud API/MCP 语义不完全一致
- 用户要么只能手工 patch 插件 cache，要么只能使用低配 direct MCP
- 插件升级会覆盖本地改动
- 多电脑复用配置成本高
- 不知道哪些官方能力在 self-host 环境下完整可用，哪些需要降级

## 3. Target Users

### 3.1 Individual Power Users

典型用户：

- 使用 Codex/Claude Code/Cursor 进行日常开发
- 有自己的 VPS/云服务器
- 希望跨项目、跨设备保留 AI agent 记忆
- 能接受配置 API key、URL、环境变量

核心诉求：

- 简单配置自己的 Mem0 endpoint
- 不想每台电脑重复迁移记忆
- 保留自动记忆和上下文召回

### 3.2 Engineering Teams

典型用户：

- 团队内部部署 Mem0
- 多个开发者使用 AI coding tools
- 需要统一 memory backend
- 对数据边界、审计、权限更敏感

核心诉求：

- 数据不出组织边界
- 有标准安装脚本
- 支持团队默认配置
- 可审计、可升级、可维护

### 3.3 Enterprise / Private Deployment Users

典型用户：

- 内网或专有云环境
- 无法访问外部 SaaS
- 有内部 HTTPS endpoint、SSO、网关、API key 管理

核心诉求：

- 不依赖 Mem0 Cloud
- 支持自定义 base URL
- 插件行为可预测
- Cloud-only 能力有明确边界说明

## 4. Product Goals

### 4.0 Primary Product Constraint

本产品的第一约束是：

```text
基于官方 mem0ai/mem0 插件 fork 开发，并且未来官方插件更新时，可以低成本 merge/rebase 到 self-host 分支。
```

因此本产品不是重新实现一个 Mem0 插件，也不是复制官方插件后长期独立分叉。正确方向是 upstream-first fork：

- 官方插件能力层保持原样
- 自部署能力作为最小 overlay
- 所有 self-host 差异集中在少数 adapter/bridge 文件
- 每次官方升级后可以通过自动测试确认兼容性
- fork diff 必须可审计、可解释、可持续缩小

### 4.1 Functional Goals

- 支持连接任意 self-hosted Mem0 REST endpoint
- 保留官方 Mem0 Codex 插件的大部分用户体验：
  - MCP memory tools
  - skills
  - lifecycle hooks
  - auto-capture
  - auto-import
  - session summary
  - session timeline
  - project/user identity resolution
- 支持多电脑连接同一个 Mem0 backend
- 支持 cloud 与 self-host 两种 provider 模式
- 提供清晰的安装、配置、升级、排障流程

### 4.2 Maintenance Goals

- 不再 patch `~/.codex/plugins/cache/...`
- 基于官方 `mem0ai/mem0` fork 维护，并持续跟随 upstream
- 自部署差异集中在 adapter 和 bridge 层
- 官方升级时冲突面小
- 每个 self-host release 都能追溯到明确的官方 commit/tag
- 可逐步向官方 upstream 提 PR

### 4.3 Productization Goals

- 插件可以作为独立产品被其他用户安装
- 配置不绑定某个用户、某台服务器、某个云厂商
- 支持文档化的 self-host compatibility matrix
- 有 smoke test 验证安装结果
- 有明确的安全模式说明：
  - demo HTTP
  - HTTPS public endpoint
  - SSH tunnel / private endpoint

## 5. Non-Goals

本产品不做：

- 不提供 Mem0 server 托管服务
- 不重写 Mem0 server
- 不保证 100% 复刻 Mem0 Cloud 的所有后端能力
- 不实现复杂企业权限系统
- 不替代用户自己的 API gateway、HTTPS、SSO、WAF
- 不把任何用户 API key 写入仓库

## 6. Product Positioning

### 6.1 Name

暂定：

```text
Mem0 Self-Hosted Plugin for Codex
```

可选名称：

- `mem0-selfhost-codex`
- `codex-mem0-selfhost`
- `Mem0 Self-Hosted Connector`

### 6.2 Relationship with Official Mem0 Plugin

产品定位不是重新发明 Mem0 插件，而是官方插件的 self-host distribution。

原则：

```text
上游能力尽量跟随官方。
自部署兼容集中在 provider adapter。
```

如果未来官方插件原生支持 self-host endpoint，本产品可以收敛为：

- 配置模板
- 安装脚本
- migration guide
- compatibility test suite

具体原则：

- 官方新增 skill：默认自动继承
- 官方修改 hook 编排：默认自动继承
- 官方调整 MCP tool schema：self-host bridge 跟随 schema，而不是让 skill 适配 bridge
- 官方修复 auto-capture/auto-import：self-host fork 不应因大面积改写而难以合并
- fork 只承担“如何连接 self-host backend”的职责

## 7. User Experience

### 7.1 Ideal Setup Flow

用户已经有一个 self-hosted Mem0 API：

```text
https://mem0.example.com
```

用户安装插件：

```bash
git clone https://github.com/<org>/mem0-selfhost-codex.git
cd mem0-selfhost-codex
./scripts/install.sh
```

安装脚本询问：

```text
Mem0 endpoint: https://mem0.example.com
API key file: ~/.mem0/selfhost-api-key
User ID: giming
Default app/project scope: auto-detect
Transport mode: direct-http
```

安装后用户重启 Codex。

Codex 中自动可用：

- `add_memory`
- `search_memories`
- `get_memory`
- `update_memory`
- `delete_memory`
- project context auto-search
- session auto-capture
- compact/session summary capture

### 7.2 Minimal Manual Configuration

用户也可以手动配置：

```bash
export MEM0_PROVIDER=selfhost
export MEM0_SELFHOST_API_URL=https://mem0.example.com
export MEM0_SELFHOST_API_KEY_FILE=$HOME/.mem0/selfhost-api-key
export MEM0_USER_ID=<user>
```

API key 文件：

```bash
mkdir -p ~/.mem0
chmod 700 ~/.mem0
echo "<api-key>" > ~/.mem0/selfhost-api-key
chmod 600 ~/.mem0/selfhost-api-key
```

### 7.3 Transport Modes

产品支持三种连接模式。

#### Mode A: Direct HTTPS

推荐生产方式：

```text
Codex -> HTTPS -> self-hosted Mem0
```

配置：

```bash
MEM0_SELFHOST_TRANSPORT=http
MEM0_SELFHOST_API_URL=https://mem0.example.com
```

#### Mode B: Direct HTTP

demo / 私人测试方式：

```text
Codex -> HTTP -> self-hosted Mem0
```

配置：

```bash
MEM0_SELFHOST_TRANSPORT=http
MEM0_SELFHOST_API_URL=http://host:8888
```

提示：

```text
HTTP 会明文传输 X-API-Key，只建议 demo 或可信网络使用。
```

#### Mode C: SSH Tunnel / SSH Curl

适合不想暴露公网 API 的用户：

```text
Codex -> local bridge -> ssh -> remote localhost Mem0
```

配置：

```bash
MEM0_SELFHOST_TRANSPORT=ssh
MEM0_SELFHOST_SSH_HOST=tencent
MEM0_SELFHOST_API_URL=http://127.0.0.1:8888
```

## 8. Functional Requirements

### 8.1 MCP Tools

插件应暴露与官方 Mem0 MCP 尽量一致的工具名：

- `add_memory`
- `search_memories`
- `get_memories`
- `get_memory`
- `update_memory`
- `delete_memory`
- `delete_all_memories`
- `list_entities`
- `delete_entities`
- `list_events`
- `get_event_status`

不同 self-host server 版本可能不支持所有工具。产品必须提供 compatibility matrix。

### 8.2 Lifecycle Hooks

应保留官方 Codex plugin hook 体验：

- SessionStart: 加载相关 memory context
- UserPromptSubmit: 检查 memory relevance
- PreToolUse: metadata/scope enforcement
- PostToolUse: 统计和记录 memory tool 使用
- Stop: session summary capture
- PreCompact: pre-compaction summary capture

hooks 不应直接调用 `api.mem0.ai`。

hooks 应统一走：

```text
Mem0Client -> provider adapter
```

### 8.3 Skills

尽量不修改官方 skills：

- remember
- peek
- forget
- stats
- tour
- health
- import/export
- switch-project
- context-loader

如果 skill 文案需要补充 self-host 说明，应作为附加章节，而不是重写官方行为。

### 8.4 Auto-Capture

自动捕获用户/助手对话时：

- 保留官方抽取策略
- 保留 metadata 分类
- 写入 self-host 时强制注入：
  - `user_id`
  - `app_id`
  - `project_id`
  - `source`
  - `session_id`
  - `branch`
  - `type`

### 8.5 Auto-Import

自动导入项目文件：

- `AGENTS.md`
- `CLAUDE.md`
- `.cursorrules`
- `.windsurfrules`
- `mem0.md`

导入时：

- 继续使用官方 chunking 策略
- self-host 写入时将 file/source/type 等 metadata 展平成兼容字段
- 查询是否已导入时不要依赖 Cloud nested metadata filter

### 8.6 Session Timeline

SessionStart 应能从 self-host 读取最近 memory。

由于 self-host filter 能力较弱，应采用：

1. 远端按 `user_id` 粗筛
2. 本地按 `app_id/project_id/type/source` 后筛
3. 生成 timeline

## 9. Compatibility Requirements

### 9.1 Search

self-host `/search` 通常要求 filter 中包含：

```text
user_id
agent_id
run_id
```

产品必须保证：

- 所有 search 请求至少带 `user_id`
- `app_id` 和 metadata filter 不直接传给不兼容的 self-host API
- 本地后筛后再返回给 Codex

### 9.2 Metadata

产品应定义统一 metadata schema：

```json
{
  "user_id": "giming",
  "app_id": "ai_work_space",
  "project_id": "ai_work_space",
  "workspace_root": "/path/to/project",
  "type": "task_outcome",
  "topic": "mem0-selfhost",
  "source": "auto_capture",
  "session_id": "...",
  "branch": "main"
}
```

读取时兼容：

- Cloud: `result.metadata.type`
- Self-host: `result.type` or `result.metadata.type`

### 9.3 Memory Type

self-host 不一定支持官方 Cloud 的 `memory_type` 语义。

规则：

- `fact`、`preference`、`task_outcome`、`task_learning`、`decision` 放入 metadata `type`
- 不作为 REST `memory_type` 传给 self-host
- 只有 server 明确支持的 `procedural_memory` 才透传

### 9.4 Event Status

self-host REST 多数接口是同步返回。

如果没有 async event，adapter 返回 shim：

```json
{
  "status": "completed",
  "event_id": null,
  "backend": "selfhost"
}
```

## 10. Product Configuration

### 10.1 Environment Variables

```bash
MEM0_PROVIDER=cloud|selfhost
MEM0_SELFHOST_TRANSPORT=http|ssh
MEM0_SELFHOST_API_URL=https://mem0.example.com
MEM0_SELFHOST_API_KEY_FILE=~/.mem0/selfhost-api-key
MEM0_SELFHOST_API_KEY=<optional>
MEM0_SELFHOST_SSH_HOST=<optional>
MEM0_USER_ID=<user>
MEM0_PROJECT_ID=<project>
MEM0_GLOBAL_SEARCH=false
MEM0_DEBUG=false
```

### 10.2 Config File

可选支持：

```json
{
  "provider": "selfhost",
  "transport": "http",
  "api_url": "https://mem0.example.com",
  "api_key_file": "~/.mem0/selfhost-api-key",
  "user_id": "giming",
  "default_app_id": "auto"
}
```

### 10.3 Secrets

禁止：

- 将 API key 写入 git repo
- 将 API key 写入 plugin manifest
- 在 debug log 中打印完整 key

允许：

- `~/.mem0/selfhost-api-key`
- system keychain
- environment variable
- CI secret

## 11. Distribution

### 11.1 Upstream-First Fork Repository

推荐 fork 完整官方仓库，而不是只复制 `mem0-plugin` 子目录：

```text
github.com/<org>/mem0
```

分支：

```text
upstream/main        # 官方 mem0ai/mem0，只同步不改
main                 # 可选，跟踪 upstream 或作为默认说明分支
selfhost/main        # 长期 self-host 开发分支
selfhost/release     # Codex 安装使用的稳定分支
release/*            # 发布 tag 或 release branch
```

tag：

```text
codex-mem0-0.2.9-selfhost.1
codex-mem0-0.2.10-selfhost.1
```

版本规则：

```text
<official-plugin-version>-selfhost.<patch>
```

示例：

```text
官方插件 0.2.9 之上的第一个 self-host 版本:
codex-mem0-0.2.9-selfhost.1

官方插件 0.2.10 合并后的第二个 self-host patch:
codex-mem0-0.2.10-selfhost.2
```

这样用户和维护者可以明确知道当前 self-host 插件基于哪个官方版本。

### 11.2 Overlay Rules

self-host fork 只能在少数文件或目录中形成长期差异。

允许长期保留差异：

```text
mem0-plugin/scripts/_mem0_client.py
mem0-plugin/scripts/_selfhost.py
mem0-plugin/mcp/selfhost-server.* 或 codex-selfhost/bridge/*
codex-selfhost/*
配置模板和安装脚本
self-host compatibility tests
```

尽量不改，除非官方结构要求：

```text
mem0-plugin/skills/*
mem0-plugin/hooks/*.json
mem0-plugin/scripts/auto_capture.py
mem0-plugin/scripts/auto_import.py
mem0-plugin/scripts/capture_session_summary.py
mem0-plugin/scripts/capture_compact_summary.py
mem0-plugin/scripts/session_timeline.py
```

如果这些 hook 脚本必须改，改动原则是：

```text
只把最终 HTTP/API 调用替换为 Mem0Client 调用。
不要改内容抽取、chunking、summary 构造、project identity、user identity 逻辑。
```

禁止长期保留差异：

```text
~/.codex/plugins/cache/...
个人服务器 IP
个人 API key
个人路径
```

### 11.3 Plugin Packaging

产品可以提供两种安装方式：

#### Sideload Plugin

适合高级用户：

```bash
codex plugin marketplace add ~/codex-plugins/mem0-selfhost
```

#### Install Script

适合大多数用户：

```bash
curl -fsSL https://example.com/install.sh | bash
```

脚本做：

- 检查 Codex
- 检查 Node.js / Python
- 安装 bridge dependency
- 写入配置
- 检测重复 MCP registration
- 运行 smoke test

## 12. Upgrade and Maintenance

### 12.1 Upgrade Flow

标准升级流程：

```bash
git fetch upstream
git checkout selfhost/main
git rebase upstream/main
./codex-selfhost/scripts/test.sh
./codex-selfhost/scripts/smoke-test.sh
git tag codex-mem0-<official-version>-selfhost.<n>
```

如果官方插件使用 release tag，而不是只跟 `main`，则优先 rebase 到官方 plugin 对应 tag：

```bash
git fetch upstream --tags
git checkout selfhost/main
git rebase <official-plugin-tag>
./codex-selfhost/scripts/test.sh
./codex-selfhost/scripts/smoke-test.sh
git tag codex-mem0-<official-version>-selfhost.<n>
```

每次升级必须产出：

- official base commit/tag
- self-host release tag
- compatibility matrix 更新
- smoke test 输出
- 已知差异和降级说明

### 12.2 Conflict Reduction Rules

必须遵守：

- 不改官方 skills，除非添加 self-host 说明
- 不改 hook 编排，除非路径必须变
- 不改 MCP tool schema，除非官方 upstream 变了
- 不在多个 hook 脚本里重复写 HTTP 调用
- 所有后端差异集中在 adapter
- 不在 repo 里写具体用户的 IP、路径、API key

遇到 rebase/merge 冲突时，处理顺序：

1. 优先保留官方 capability 层、skills、hooks 编排和 tool schema。
2. 重新连接 self-host adapter，而不是把旧逻辑强行覆盖回官方文件。
3. 如果官方已经实现同类功能，删除 self-host fork 中的重复实现。
4. 跑 adapter 单测，验证 filter translation、metadata post-filter、memory_type handling。
5. 跑真实 self-host smoke test，验证 add/search/session context。
6. 更新 compatibility matrix 和 release note。

### 12.3 Upstream Merge Readiness Checklist

每次合并官方更新前，维护者需要确认：

- self-host 长期 diff 仍集中在 `codex-selfhost/*` 和少数 adapter 文件
- 官方新增 skill 可以不改代码直接继承
- 官方新增 hook 不会绕过 `Mem0Client`
- 官方 MCP tool schema 变化已经同步到 bridge
- Cloud provider 模式仍能使用官方默认 endpoint
- self-host provider 模式不会调用 `api.mem0.ai` 或 `mcp.mem0.ai`
- installer 不会写入个人 IP、个人路径或明文 key
- smoke test 覆盖 direct HTTP、direct HTTPS、SSH tunnel 中至少一种模式

如果 checklist 失败，本次 release 不应发布，只能作为 experimental branch。

### 12.4 Upstream PR Strategy

可向官方拆分 PR：

PR 1:

```text
Support configurable Mem0 base URL in Codex plugin
```

PR 2:

```text
Document self-hosted Mem0 endpoint configuration for Codex
```

PR 3:

```text
Add self-host compatibility tests for filters and memory_type
```

## 13. Security Modes

### 13.1 Demo Mode

```text
HTTP public endpoint + X-API-Key
```

适合：

- 个人 demo
- 临时验证
- 可信网络

风险：

- API key 明文传输

### 13.2 Production Public Mode

```text
HTTPS public endpoint + X-API-Key
```

推荐：

- Caddy/Nginx/Cloudflare
- key rotation
- request log
- rate limit

### 13.3 Private Mode

```text
localhost Mem0 + SSH tunnel
```

适合：

- 内网
- 不开放公网
- 高安全要求

## 14. Observability

插件应提供 health command：

```text
mem0 selfhost health
```

检查：

- endpoint reachable
- auth valid
- add/search round trip
- metadata filtering works
- provider mode
- API version

输出示例：

```json
{
  "provider": "selfhost",
  "transport": "http",
  "api_url": "https://mem0.example.com",
  "auth": "ok",
  "add": "ok",
  "search": "ok",
  "metadata_filter": "client-side",
  "warnings": []
}
```

## 15. Smoke Test

### 15.1 API Test

```bash
curl "$MEM0_SELFHOST_API_URL/configure" \
  -H "X-API-Key: $(cat $MEM0_SELFHOST_API_KEY_FILE)"
```

### 15.2 Add Test

```bash
curl -X POST "$MEM0_SELFHOST_API_URL/memories" \
  -H "X-API-Key: $(cat $MEM0_SELFHOST_API_KEY_FILE)" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role":"user","content":"self-host smoke test"}],
    "user_id": "smoke-test",
    "metadata": {
      "app_id": "smoke",
      "type": "verification"
    },
    "infer": false
  }'
```

### 15.3 Search Test

```bash
curl -X POST "$MEM0_SELFHOST_API_URL/search" \
  -H "X-API-Key: $(cat $MEM0_SELFHOST_API_KEY_FILE)" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "self-host smoke test",
    "filters": {"user_id":"smoke-test"},
    "top_k": 5,
    "threshold": 0
  }'
```

### 15.4 Codex Tool Test

在 Codex 内：

```text
add_memory(text="codex self-host smoke test", user_id="...", app_id="...")
search_memories(query="codex self-host smoke test", user_id="...", app_id="...")
```

## 16. Compatibility Matrix

| Capability | Cloud | Self-host | Product behavior |
|---|---:|---:|---|
| add memory | full | full | full |
| search memory | full | partial filter support | full via client-side post-filter |
| get memory | full | depends on REST version | native or shim |
| update memory | full | supported if endpoint exists | native or delete+add fallback |
| delete memory | full | supported if endpoint exists | native |
| list entities | full | basic support | partial |
| list events | full | request log only | partial/shim |
| get event status | full | sync REST | immediate completed shim |
| auto-capture | full | full after adapter | full |
| auto-import | full | full after adapter | full |
| session timeline | full | partial filter support | full via post-filter |
| memory review/dreaming | cloud-dependent | unknown | future/partial |

## 17. Acceptance Criteria

### MVP

- fork 完整官方 `mem0ai/mem0` 仓库，而不是复制插件片段
- 建立 `selfhost/main` 分支，并可从官方 upstream rebase
- self-host diff 集中在 adapter、bridge、installer、compatibility tests
- 用户能配置 self-host endpoint 和 API key
- Codex 能通过插件 add/search self-host memories
- lifecycle hooks 写入 self-host
- session start 能从 self-host 召回上下文
- 不需要修改 `~/.codex/plugins/cache`
- 提供安装脚本和 smoke test
- 明确文档说明 HTTP/HTTPS/SSH 三种模式

### Beta

- 支持多电脑安装
- 支持 provider `cloud` 与 `selfhost` 切换
- 支持 self-host public HTTP/HTTPS
- 支持 SSH tunnel/private endpoint
- 提供 compatibility matrix
- 至少完成一次 upstream rebase 验证
- rebase 后官方 skills/hooks 的新增能力能被继承
- fork diff 没有扩散到大量官方业务脚本

### Stable

- 发布 versioned tag
- 有基础单测覆盖 filter translation、metadata post-filter、memory_type handling
- 提供升级文档
- 连续跟随至少两个官方插件版本升级
- 每次官方升级都能用 checklist 和 smoke test 证明兼容
- 常规升级冲突可以限制在 adapter/bridge 层
- 可向官方 upstream 提通用 endpoint 配置 PR

## 18. Open Questions

- 产品是否独立命名为 `mem0-selfhost-codex`？
- 是否保持官方 plugin id `mem0`，还是使用新 id 避免与官方插件冲突？
- self-host bridge 用 Node.js 还是 Python？
- 是否默认启用 Cloud fallback？
- 是否支持多个 Mem0 endpoint profile？
- 是否要内置 memory migration tool？

## 19. Recommended Roadmap

### Phase 1: Productize Current Working Prototype

- fork 官方 `mem0ai/mem0`
- 建立 `upstream/main`、`selfhost/main`、`selfhost/release` 分支策略
- 把当前 bridge 收进 fork repo
- 抽象 `_mem0_client.py`
- 收敛 self-host 兼容逻辑
- 改 hooks 走统一 client
- 写安装脚本和 smoke test

### Phase 2: Multi-User Distribution

- 支持一键安装
- 支持多 endpoint profile
- 支持 HTTP/HTTPS/SSH transport
- 写完整 README
- 发布第一个 selfhost tag

### Phase 3: Upstream Alignment

- 跟进官方新版插件
- 降低 fork diff
- 把 self-host 差异继续向 adapter/bridge 收敛
- 删除已被官方实现覆盖的 fork 代码
- 向官方提交 configurable endpoint PR
- 如果官方接受，减少 fork 维护面

### Phase 4: Public Product Hardening

- 提供 migration/import/export 工具
- 提供 GitHub Actions 自动跑 fork diff 检查
- 提供 release note 模板
- 支持多个 self-host profile
- 提供更完整的安全部署文档

## 20. Current Demo Reference

当前 demo 服务器仅作为产品验证环境，不应写死到插件代码：

```text
MEM0_SELFHOST_API_URL=http://106.54.23.243:8888
MEM0_SELFHOST_API_KEY_FILE=~/.mem0/selfhost-admin-api-key
```

该配置只应出现在本地 `.env`、用户文档示例或 demo profile 中。
