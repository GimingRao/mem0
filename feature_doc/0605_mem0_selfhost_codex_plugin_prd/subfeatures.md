# Mem0 Self-Hosted Codex Plugin 子功能拆解

## 总目标

基于官方 `mem0ai/mem0` 插件 fork，交付一个插件 ID 为 `mem0-self` 的 Mem0 Self-Hosted Codex Plugin。

该插件应尽量继承官方 Codex 插件的 skills、hooks、auto-capture、auto-import、session summary 和 MCP tool schema，只在少数 adapter、bridge、installer 和 compatibility tests 中集中实现 self-host 差异。Codex 需要能通过用户自部署的 Mem0 REST endpoint 完成 memory add/search、上下文召回、生命周期自动记忆、安装验证和后续 upstream 低成本升级。

当前技术决策：

- Codex self-host bridge/adapter 使用 Python + shell。
- 插件 ID 使用 `mem0-self`。
- Node.js/TypeScript 只作为 OpenCode 插件方向参考，不作为 Codex 主链路实现。

## 子功能包

### 1. Fork 与分支/发布基线

目标：把项目从本地 patch 插件 cache 变成可维护 fork。

范围：

- fork 完整 `mem0ai/mem0` 仓库。
- 建立 `upstream/main`、`selfhost/main`、`selfhost/release` 分支策略。
- 确认当前官方插件版本、commit 或 tag。
- 定义 self-host tag 规则，例如 `codex-mem0-0.2.9-selfhost.1`。
- 写入 upstream base 记录，例如 `UPSTREAM.md` 或 release base note。

验收：

- `selfhost/main` 能从 upstream rebase。
- 当前 self-host diff 可以被列出并解释。
- 不依赖 `~/.codex/plugins/cache/...`。

依赖：无，第一批先做。

### 2. 配置系统与 Provider 选择

目标：让插件能在 `cloud` 和 `selfhost` 间切换。

范围：

- 读取环境变量：
  - `MEM0_PROVIDER`
  - `MEM0_SELFHOST_API_URL`
  - `MEM0_SELFHOST_API_KEY_FILE`
  - `MEM0_SELFHOST_API_KEY`
  - `MEM0_USER_ID`
  - `MEM0_PROJECT_ID`
  - `MEM0_SELFHOST_TRANSPORT`
- 可选支持 `~/.mem0/settings.json`。
- 实现 secret 读取与日志脱敏。
- 实现默认 project/app scope 解析。

验收：

- 无 API key 时有明确错误。
- debug log 不打印完整 key。
- `cloud` 模式仍走官方默认行为。
- `selfhost` 模式不访问 `api.mem0.ai`。

依赖：1，可并行启动。

### 3. Self-host Mem0 Client / Adapter

目标：所有 self-host 后端差异集中在统一 client/adapter。

范围：

- 新增或改造 `mem0-plugin/scripts/_mem0_client.py`。
- 新增 `mem0-plugin/scripts/_selfhost.py`。
- 实现：
  - add
  - search
  - get
  - update
  - delete
  - get_all/list
  - event status shim
- 实现 filter translation：
  - self-host 请求至少传 `user_id`。
  - `app_id`、`project_id`、`type`、`source` 做本地后筛。
- 实现 metadata 兼容：
  - Cloud: `result.metadata.type`
  - Self-host: `result.type` 或 `result.metadata.type`
- 实现 memory type 兼容：
  - 普通类型写入 metadata。
  - 不随便传 REST `memory_type`。

验收：

- adapter 单测覆盖 filter translation、metadata post-filter、memory_type handling。
- add/search 可以对真实 self-host server 跑通。
- self-host adapter 之外没有散落 HTTP 调用。

依赖：2。

### 4. MCP Bridge / Tools 对齐

目标：Codex 里暴露和官方尽量一致的 MCP tools。

范围：

- 暴露工具：
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
- 对 self-host 缺失能力做 shim 或明确 partial。
- tool schema 尽量跟官方一致。
- bridge 只调用统一 client。

验收：

- Codex 内能 add/search self-host memory。
- unsupported capability 有清晰返回，不静默失败。
- tool schema 不要求 skills 为 self-host 单独适配。

依赖：3。

### 5. Lifecycle Hooks 接入

目标：保留官方 hook 体验，但后端调用走统一 client。

范围：

- SessionStart：召回相关 memory context。
- UserPromptSubmit：memory relevance 检查。
- PreToolUse：metadata/scope enforcement。
- PostToolUse：记录 memory tool 使用。
- Stop：session summary capture。
- PreCompact：compact summary capture。
- 禁止 hook 直接调用 cloud API。

验收：

- session start 可以从 self-host 拉上下文。
- Stop/PreCompact 能写入 self-host。
- hook 脚本改动只集中在最终 API 调用处。
- 官方抽取、summary、chunking、identity 逻辑不大改。

依赖：3，可和 4 部分并行。

### 6. Auto-capture / Auto-import / Session Timeline

目标：把官方自动记忆能力迁移到 self-host 兼容语义。

范围：

- Auto-capture：
  - 保留官方抽取策略。
  - 强制注入 `user_id`、`app_id`、`project_id`、`source`、`session_id`、`branch`、`type`。
- Auto-import：
  - 支持 `AGENTS.md`、`CLAUDE.md`、`.cursorrules`、`.windsurfrules`、`mem0.md`。
  - 保留官方 chunking。
  - 不依赖 Cloud nested metadata filter。
- Session timeline：
  - 远端按 `user_id` 粗筛。
  - 本地按 `app_id`、`project_id`、`type`、`source` 后筛。

验收：

- 项目文件可导入并避免重复导入。
- 自动捕获的 memory 可按 project/type 查回。
- timeline 在 self-host filter 弱的情况下仍正确。

依赖：3、5。

### 7. Transport Modes 与安全模式

目标：支持 Direct HTTP、Direct HTTPS、SSH tunnel 三种连接方式。

范围：

- `http` transport：HTTP/HTTPS REST。
- `ssh` transport：本地 bridge 通过 ssh/curl 访问远端 localhost。
- 安全提示：
  - HTTP 只适合 demo/可信网络。
  - HTTPS 为推荐生产模式。
  - SSH tunnel 为私有模式。
- 统一 timeout 和 error handling。

验收：

- HTTP demo 可跑通。
- HTTPS 配置路径清晰。
- SSH 模式至少完成 add/search smoke test。
- 文档明确 X-API-Key 明文传输风险。

依赖：2、3。可在 MVP 后半段做。

### 8. Installer / Health / Smoke Test

目标：让其他用户能安装、验证、排障。

范围：

- 提供 `scripts/install.sh`。
- 检查 Codex、Node/Python、依赖。
- 写配置，不写明文 key 到 repo。
- 检测重复 MCP registration。
- 提供 `mem0 selfhost health` 或等价 health command。
- smoke test 覆盖：
  - configure
  - add
  - search
  - Codex tool add/search

验收：

- 新机器按文档能完成安装。
- health 输出 provider、transport、api_url、auth、add、search、metadata_filter、warnings。
- smoke test 失败时能定位是 endpoint、auth、schema 还是 filter 问题。

依赖：3、4。可以和 5/6 并行。

### 9. 文档、兼容矩阵与升级维护

目标：把产品变成可持续维护的 self-host distribution。

范围：

- README。
- install guide。
- config guide。
- security mode guide。
- compatibility matrix。
- upgrade guide。
- release note 模板。
- upstream merge checklist。
- fork diff 检查脚本，可选 GitHub Actions。
- 未来 upstream PR 拆分：
  - configurable base URL
  - self-host docs
  - compatibility tests

验收：

- 每个 release 有：
  - official base commit/tag
  - self-host release tag
  - smoke test 输出
  - compatibility matrix
  - known differences
- 至少完成一次 upstream rebase 验证。
- diff 没扩散到大量官方 skills/hooks 业务脚本。

依赖：1、3、4、5、8。

## 推荐分批实现顺序

### 第一批：MVP 核心链路

包含：

- 1. Fork 与分支/发布基线
- 2. 配置系统与 Provider 选择
- 3. Self-host Mem0 Client / Adapter
- 4. MCP Bridge / Tools 对齐

目标：先让 `mem0-self` 作为独立 Codex 插件连上 self-host Mem0，并完成 add/search 基本闭环。

### 第二批：官方体验恢复

包含：

- 5. Lifecycle Hooks 接入
- 6. Auto-capture / Auto-import / Session Timeline

目标：恢复官方插件的自动记忆、上下文召回、session summary 和项目文件导入体验。

### 第三批：可安装可验证

包含：

- 7. Transport Modes 与安全模式
- 8. Installer / Health / Smoke Test

目标：让非开发者也能安装、配置、验证和排障，并支持 HTTP、HTTPS、SSH tunnel 三种部署方式。

### 第四批：产品化维护

包含：

- 9. 文档、兼容矩阵与升级维护

目标：把 self-host fork 做成长期可维护、可发布、可跟随 upstream 的 distribution。

## 分组建议

### A 线：Fork / Release / Upgrade 维护线

负责：

- 1. Fork 与分支/发布基线
- 9. 文档、兼容矩阵与升级维护

职责重点：

- 控制长期 fork diff。
- 建立 upstream rebase 和 release 规则。
- 维护 compatibility matrix、release note 和 upgrade checklist。

### B 线：Adapter / Client 核心线

负责：

- 2. 配置系统与 Provider 选择
- 3. Self-host Mem0 Client / Adapter

职责重点：

- 统一 cloud/selfhost provider 入口。
- 集中处理 filter translation、metadata post-filter、memory_type handling。
- 确保 self-host 差异不扩散到 hooks 和 skills。

### C 线：Codex 集成线

负责：

- 4. MCP Bridge / Tools 对齐
- 5. Lifecycle Hooks 接入
- 6. Auto-capture / Auto-import / Session Timeline

职责重点：

- 让 Codex 使用体验尽量保持官方插件一致。
- 保证 skills、hooks、MCP tool schema 不为 self-host 大幅分叉。
- 打通 session start、stop、precompact 等生命周期写入和召回。

### D 线：安装 / 运维 / 安全线

负责：

- 7. Transport Modes 与安全模式
- 8. Installer / Health / Smoke Test

职责重点：

- 支持 HTTP、HTTPS、SSH tunnel 三种部署模式。
- 提供安装脚本、health command 和 smoke test。
- 确保 secret 不进仓库，日志不泄露完整 key。

## 关键前置决策

已确定：

- Codex bridge/adapter 使用 Python + shell。
- 插件 ID 使用 `mem0-self`。

仍待确认：

- 是否默认保留 Cloud fallback。
- 是否支持多个 Mem0 endpoint profile。
- 是否内置 memory migration tool。
