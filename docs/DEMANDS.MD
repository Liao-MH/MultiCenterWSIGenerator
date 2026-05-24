# DEMANDS

## v0.65.1 - 2026-05-24 P6 维护性收敛需求

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 `AC-DEV-03` / P6，降低 `src/he_wsi_generator/cli.py` 和 `src/he_wsi_generator/models/torch_training.py` 两个大文件的后续维护风险。

### 结构化需求

- 本轮只做行为保持的维护性拆分，不新增 production 模型能力，不改变 CLI 命令、参数、输出格式或默认行为。
- 使用 worker 隔离开发：
  - `p6-cli-dispatch-20260524` 负责把 `cli.py` 的命令执行分支拆出到更清晰的命令处理 helper/模块，保持 `he_wsi_generator.cli:main` 入口不变。
  - `p6-torch-training-helpers-20260524` 负责把 `torch_training.py` 中的 manifest/validation/schema 辅助逻辑拆出到模型内部 helper 模块，保持公开训练/采样函数不变。
- 每个 worker 必须先写行为保持测试或运行现有覆盖测试作为基线，改动后跑对应定向测试。
- 版本号升级到 `v0.65.1`，并同步 README、`docs/audit/`、`docs/CHANGELOG.md`、版本文件和测试断言。
- 上述版本升级已完成，当前工作区以 `v0.65.1` 作为本轮维护性收敛基线。

### 边界说明

- 本轮不实现 production latent diffusion / ControlNet / DiT。
- 本轮不实现生产级 layout/style/texture prior、生产级 WSI streaming writer 或真实 SVS 全链路复跑。
- 本轮不清理 dirty worker worktree；现有 worktree 作为审计证据保留，避免误删未提交 worker 差异。

## v0.65.0 - 2026-05-24 P2 GUI 执行、刷新与输出摘要开发需求

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P2 剩余 GUI flow，补齐 `AC-MISS-03` 和 `AC-DEV-01` 中指出的 GUI 内执行、状态刷新和输出摘要查看缺口。

### 结构化需求

- 使用 `.agent/tasks/` 创建 worker 任务文件，并尝试用 `.worktrees/` 隔离 worker 实现。
- 新增非 Qt workflow helper，使 PySide 页面可用同一份 form state：
  - 读取 `<output-root>/ui_jobs/<generated-id>/job.json` 状态；
  - 同步执行 queued local job；
  - 在 job completed 后读取 `<output-root>/metadata.json`、`<output-root>/qc.json` 和可选 `<output-root>/qc_review.json` 输出摘要。
- PySide6 单页控制台新增执行 queued job、刷新 job 状态、加载输出摘要的按钮和展示区域。
- helper 对未知 job、非 completed job、缺失 metadata/QC、非法 artifact 和 schema/ID 不一致必须显式失败，不允许静默回退。
- 版本号升级到 `v0.65.0`，并同步 README、`docs/audit/`、`docs/CHANGELOG.md`、版本文件和测试断言。

### 边界说明

- 本批次仍保持 CLI-first，不让 `run-generation` 默认弹 GUI。
- 本批次只支持同步本地 queued job 执行，不新增后台 daemon、并发队列、运行中进程终止、跨机器调度或线程化 Qt 执行。
- 本批次不实现 production latent diffusion / ControlNet / DiT，不实现生产级 WSI streaming writer，不复跑真实 SVS 全链路。

## v0.64.0 - 2026-05-24 P2 可交互 PySide6 配置页开发需求

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P2“可交互 PySide6 自定义配置页”，优先补齐 `AC-MISS-02` 与 `AC-DEV-01` 中指出的 UI 缺口。

### 结构化需求

- 将 `src/he_wsi_generator/ui/pyside_app.py` 从只读字段展示升级为真实单页配置界面。
- UI 至少支持编辑或选择：generation config 保存路径、prior manifest、checkpoint manifest、输出目录、generated id、backend、anchor preset、structure anchor、random seed、sample steps、overlap、可选 condition packet / training index，以及 QC non-copy 开关。
- UI 需要提供 6 类 label mapping 的最小可编辑面板；明显非法的 raw label 输入、重复映射或空必填运行参数必须阻塞保存/运行并显示错误。
- UI 需要能把表单保存为 generation config JSON，并能通过现有 CLI/local job runner 创建或执行 generation job，不把核心生成逻辑写入 Qt 事件处理。
- 增加非 Qt workflow helper，用于把 UI form state 转换为 generation config、`run-generation` 命令和 local job record，便于 UI 层薄封装与单元测试。
- 使用 worker 隔离开发：
  - `p2-ui-form-20260524` 负责 PySide6 表单与 GUI smoke 测试。
  - `p2-ui-job-command-20260524` 负责非 Qt workflow helper 与单元测试。

### 边界说明

- 本批次不让 `run-generation` 默认弹 GUI，继续保留 CLI 自动化入口；GUI 优先通过 `launch-ui` 使用。
- 本批次不实现 production latent diffusion / ControlNet / DiT，不实现生产级 WSI streaming writer。
- 本批次允许将项目版本升级到 `v0.64.0`，由 orchestrator 在 worker 回收后统一同步版本、README、审计清单和变更日志。

## 2026-05-24 MultiCenterWSIGenerator conda 环境与环境化验证需求

### 用户需求

- 用户要求创建独立 conda 环境 `MultiCenterWSIGenerator`，安装项目所需全部依赖，包括 PyTorch。
- 用户要求在该环境基础上继续循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`，推进 `docs/audit/` 中仍未完成的开发事项。

### 结构化需求

- 使用独立 conda 环境隔离依赖，不在主环境中安装项目依赖。
- 安装项目完整可选依赖集合：`embeddings`、`outputs`、`training`、`torch`、`ui`、`yaml`、`wsi`。
- 验证 `torch`、CUDA、`PySide6`、OpenSlide/YAML/输出相关依赖可导入。
- 在新环境中重新验证 CLI 版本、默认 generation config、PyTorch smoke 相关测试、UI 相关测试和全量单元测试。
- 把环境创建命令、依赖验证结果、测试结果同步到 `docs/audit/`、`docs/CHANGELOG.md` 和 README。

### 边界说明

- 本轮环境验证不等于完成真实可交互 PySide6 自定义配置页；该功能仍按 `docs/audit/IMPLEMENTATION_PLAN.md` 的 P2 继续开发。
- 本轮环境验证不等于完成 production latent diffusion / ControlNet / DiT 或真实 SVS 全链路复跑；相关项目仍保留在未完成/未验证清单中。
- 本轮不因单纯环境和文档收口额外升级版本号，仍归入当前 `v0.63.0` 补救基线。

## 2026-05-24 v0.63.0 复审计需求

### 用户需求

- 用户显式调用 `project-remediation-audit`，要求基于当前仓库状态进入补救审计模式。
- 本轮只做审计、证据复核和审计工件维护，不开始新的实现修复。

### 结构化需求

- 捕获当前 git 状态、分支、版本号、docs/source/tests 文件结构。
- 对照 `AGENTS.md`、`README.md`、`docs/DEMANDS.MD`、`docs/audit/`、设计文档、开发附录和当前实现，复核 `v0.63.0` P1 补救后的项目状态。
- 输出并维护 `已完成 / 缺失 / 偏离 / 未验证` 分类。
- 明确区分：
  - 当前工作区已实现并通过验证的能力；
  - 仍未实现的完整项目成果；
  - 仅作为历史证据存在的 `build/validation/` 工件；
  - 尚未提交/打 tag 的工作区状态。

### 边界说明

- 本轮不修改 `src/`、`tests/`、`configs/` 运行时代码。
- 本轮不升级版本号，继续以当前工作区 `v0.63.0` 作为复审计对象。
- 本轮不复跑真实 SVS 全链路，不安装 PyTorch 或 PySide6。

## v0.63.0 - 2026-05-24

### 用户需求

- 用户要求根据 `docs/audit/` 中的审计内容继续开发，并明确使用 `codex-worker-orchestration` 进行 worker 并行编排。
- 本轮优先推进 `docs/audit/IMPLEMENTATION_PLAN.md` 中的 P1“契约一致性与文档诚实度”批次。

### 结构化需求

- 使用 `.agent/tasks/` 创建 worker 任务文件，并用 `.worktrees/` 隔离 worker 实现。
- 并行处理两个文件范围不重叠的 P1 子任务：
  - 为 `qc_review` 增加 `he-wsi-gen validate qc-review <path>` 通用校验入口。
  - 收紧 `collect_output_summary()`：metadata 必须通过 schema 校验，metadata/QC/可选 `qc_review` 的 `generated_id` 必须一致。
- 新增仓库实体 `AGENTS.md`，让本仓库工作规则可持久追踪。
- 更新 README 的当前版本、schema kind 列表、输出摘要说明和 M5/M7 边界表述，避免把 smoke/proxy 或 UI 控制层误表述为完整 production 成果。
- 版本号升级到 `v0.63.0`，并同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 更新 `docs/audit/`、`docs/CHANGELOG.md` 和 worker 报告，保留并行开发证据链。

### 边界说明

- 本轮不实现 production latent diffusion / ControlNet / DiT，不实现生产级 WSI streaming writer，不实现真正可交互的 PySide6 配置页。
- 本轮不复跑真实 SVS 全链路；历史 `build/validation/v0.62.0-291288/` 仍只作为历史工件存在性证据。
- 共享文档与版本号由 orchestrator 统一更新，不交给 worker 并行修改。

## 2026-05-24 One-time Parallel Developer 整合 Skill 需求

### 用户需求

- 用户认为“每循环一个问题”会降低并行效率，确认循环粒度应改为“一个补救主题或优先级批次”，批次内部并行派发多个 worker。
- 用户要求将 `codex-worker-orchestration` 和 `project-remediation-audit` 整合到一个 `one-time-parallel-developer` 大 skill 中。
- 用户要求同时确保 `codex-worker-orchestration` 和 `project-remediation-audit` 仍然可以被单独调用。

### 结构化需求

- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/one-time-parallel-developer`。
- `one-time-parallel-developer` 需要定义完整闭环：`Audit -> Batch -> Task -> Worker -> Review -> Merge -> Re-audit -> Repeat/Stop`。
- `one-time-parallel-developer` 需要明确一个循环解决一个补救主题或优先级批次，而不是单个问题。
- `one-time-parallel-developer` 需要明确每批建议 2-5 个可并行 worker，并说明哪些任务适合并行、哪些必须串行。
- `one-time-parallel-developer` 需要明确停止条件，避免无约束循环。
- `project-remediation-audit` 需要保留独立审计能力，并说明它也可作为整合闭环的审计/复审计阶段使用。
- `codex-worker-orchestration` 需要保留独立 worker 编排能力，并说明它也可作为整合闭环的 worker 派发阶段使用。

### 边界说明

- 本轮只新增和更新个人 Codex skill、README、需求记录和变更日志，不修改 `src/`、`tests/`、`configs/` 运行时代码。
- 三个个人 skill 位于 `/home/muhengliao/.codex/skills/`，不纳入当前仓库版本控制。
- `one-time-parallel-developer` 是上层编排 skill，不替代两个子 skill；两个子 skill 必须仍能按各自触发条件单独使用。

## 2026-05-24 Worker 模板与 Skill 中文化需求

### 用户需求

- 用户确认 worker final report 是每个子任务一份后，要求把两个 skill、子任务模板、子任务报告模板都改为中文。

### 结构化需求

- 将仓库内 `.agent/templates/worker_task.md` 的可读文本改为中文。
- 将仓库内 `.agent/templates/worker_report.md` 的可读文本改为中文。
- 将个人 Codex skill `codex-worker-orchestration` 的 `SKILL.md` 和 `agents/openai.yaml` 改为中文。
- 将个人 Codex skill `project-remediation-audit` 的 `SKILL.md` 和 `agents/openai.yaml` 改为中文。
- 将 `codex-worker-orchestration` skill assets 中的 worker task/report 模板同步改为中文。

### 边界说明

- 保留必要的命令、路径、branch/worktree 命名和文件名，避免破坏自动化流程。
- 本轮不修改 `src/`、`tests/`、`configs/` 运行时代码。
- 个人 skill 位于 `/home/muhengliao/.codex/skills/`，不纳入当前仓库版本控制。
- 当前环境缺少 PyYAML，仍不在主环境安装依赖；skill 结构继续采用手工校验。

## 2026-05-24 Codex worker 并行开发与项目审计 Skill 固化需求

### 用户需求

- 用户要求为类 subagent 并行开发生成两个模板：
  - 子任务文件模板；
  - 子报告文件模板。
- 用户要求把“主 Codex orchestrator + 独立 Codex exec worker + 任务文件 + 结果报告 + git worktree 隔离区”的并行开发流程确定为 skill。
- 用户要求把前面已经形成的项目补救审计流程确定为 skill。

### 结构化需求

- 在当前仓库内新增 `.agent/templates/worker_task.md`，作为 worker prompt / task file 模板。
- 在当前仓库内新增 `.agent/templates/worker_report.md`，作为 worker final report 模板。
- 在个人 Codex skill 目录创建 `codex-worker-orchestration`，用于后续并行 worker 调度、worktree 隔离、任务文件和报告文件管理。
- 在个人 Codex skill 目录创建 `project-remediation-audit`，用于后续补救审计模式：先读需求/设计/README/docs/代码结构，再输出“已完成 / 缺失 / 偏离 / 未验证”和最小补救计划。
- 更新 `.gitignore`，忽略 `.worktrees/` 和 `.agent/logs/`，避免并行 worker 隔离区与日志污染 git 状态。

### 边界说明

- 本轮只新增协作模板、skill 和相关文档说明，不修改项目运行时代码。
- 个人 skill 位于 `/home/muhengliao/.codex/skills/`，不纳入当前仓库版本控制。
- 当前环境缺少 PyYAML，`skill-creator` 的 `quick_validate.py` 不能直接运行；需进行手工结构校验，或后续在隔离环境安装 PyYAML 后补跑。

## 2026-05-24 审计文件迁移与项目进度审计需求（针对 v0.62.0）

### 用户需求

- 用户要求先把审计文件移动到 `docs/audit/`：
  - `docs/audit/ACCEPTANCE_CHECKLIST.md`
  - `docs/audit/IMPLEMENTATION_PLAN.md`
  - `docs/audit/DECISIONS.md`
- 用户要求读取现有设计说明、开发指南、README、`docs/` 目录和当前代码结构，总结当前项目开发进度，并明确距离完整项目成果还有多远。
- 用户要求把本轮审计结果一并更新到 `docs/audit/` 的相关文件中。

### 结构化需求

- 审计文件只保留在 `docs/audit/`，避免继续散落在 `docs/` 根目录。
- `docs/audit/ACCEPTANCE_CHECKLIST.md` 需要以证据为基础记录“已完成 / 缺失 / 偏离 / 未验证”，并说明当前项目相对完整成果的差距。
- `docs/audit/IMPLEMENTATION_PLAN.md` 需要把补救工作拆成任务包，按优先级说明后续实现顺序。
- `docs/audit/DECISIONS.md` 需要记录当前审计基线、完整项目成果定义、关键设计决策和禁止变更项。
- README 需要提供审计文件入口，便于后续直接查看。

### 边界说明

- 本轮只修改文档和审计材料，不修改 `src/`、`tests/`、`configs/` 实现逻辑。
- 本轮不升级版本号，仍以 `v0.62.0` 作为审计基线。
- 对 `docs/CHANGELOG.md`、`docs/DEMANDS.MD` 等超过 100KB 的文件，只读取和更新与本轮需求直接相关的顶部记录，避免无关重写。
- 历史 `build/validation/` 工件可作为存在性证据，但仍不等价于本轮重新执行真实 SVS 全链路生成。

## 2026-05-24 审计需求（针对 v0.62.0）

### 用户需求

- 用户要求进入项目补救审计模式。
- 本轮先做偏差审计，不开始修代码。

### 结构化需求

- 读取当前会话提供的 `AGENTS.md` 约束、现有设计说明、开发附录、`README.md`、`docs/` 目录和当前代码结构。
- 先输出当前项目的偏差审计，并按“已完成 / 缺失 / 偏离 / 未验证”分类。
- 生成或更新 `docs/DEMANDS.MD`、`docs/ACCEPTANCE_CHECKLIST.md`、`docs/IMPLEMENTATION_PLAN.md`、`docs/DECISIONS.md`、`docs/CHANGELOG.md`。
- `docs/ACCEPTANCE_CHECKLIST.md` 需要把每项验收条件绑定到文件、测试或命令证据。
- `docs/IMPLEMENTATION_PLAN.md` 需要拆成最小补救任务包，并按优先级排序。
- `docs/DECISIONS.md` 需要记录关键设计决策和禁止变更项。
- 在用户确认前，不开始实现层修复。

### 边界说明

- 本轮允许更新审计类文档，但不修改 `src/`、`tests/`、`configs/` 中的实现逻辑。
- 本轮不做版本号升级，基线仍为 `v0.62.0`；避免在未修复实现前制造新的版本同步面。
- 若仓库内不存在实体 `AGENTS.md` 文件，应显式记录该事实，而不是假设仓库自带该文件。
- 历史 `build/validation/` 工件可作为存在性证据，但不等价于本轮重新执行真实 SVS 全链路生成。

## v0.62.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进自动 QC 后的人工审阅工作流第一版：当生成样本出现 warning/fail 或需要用户确认时，系统需要能把 QC 结果转换为可落盘、可追踪、可更新决策的 `qc_review` artifact，便于后续 UI 与批量交付使用。

### 结构化需求

- 版本号升级为 `v0.62.0`。
- 新增 `qc_review` artifact 构建能力，输入 `metadata.json` 和 `qc.json`，输出 JSON 需记录 `schema_version`、`artifact_type=qc_review`、`generated_id`、输入文件路径与 sha256、QC overall/level 状态、需要审阅的 warning/fail metric 列表、`review_required`、`decision=pending` 和创建时间。
- `review_required` 必须在 QC overall status 为 `warning` 或 `fail` 时为 `true`，在 `pass` 时为 `false`。
- warning/fail metric 列表必须保留 metric 所在 level、metric name、status、value、reference 和 message/reason 字段（若存在），让审阅者能复查触发原因。
- 新增决策更新能力：将 `pending` 的 review artifact 更新为 `accepted`、`rejected` 或 `needs_rerun`，并记录 reviewer、note、reviewed_at；非法决策、空 reviewer、非 pending artifact 必须显式报错。
- CLI 新增 `create-qc-review --metadata ... --qc ... --output ...` 和 `apply-qc-review-decision --review ... --decision ... --reviewer ... [--note ...]`。
- `inspect-output-summary` 支持可选 `--qc-review`，输出 review 的 `review_required`、`decision`、`reviewer` 和 `review_item_count`，供后续 UI 控制层展示。
- 新增/更新测试覆盖：review artifact 从 warning/fail QC 提取待审阅条目、pass QC 不要求审阅、非法决策显式失败、CLI 可生成和更新 review、output summary 可合并 review 状态。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。
- 若代码开发完成，必须继续使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 做真实 SVS 验证，并确保生成输出、QC review artifact 和输出摘要都能正常交付。

### 边界说明

- 本次版本只实现本地 JSON 文件级人工审阅工作流，不实现 PySide6 图形审阅界面、不实现权限/签名系统、不实现数据库或远端协作审阅。
- 本次版本不改变自动 QC 的 pass/warning/fail 判定，也不让人工审阅结果反向修改原始 `qc.json`；审阅决策以独立 `qc_review.json` artifact 记录。

## v0.61.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本在 v0.60.0 的分层 `qc_reference_distribution` artifact 基础上，推进运行时消费能力：生成/QC 链路需要能根据当前样本的可追踪上下文选择匹配 stratum 阈值，而不是永远只使用全局 `metrics`。

### 结构化需求

- 版本号升级为 `v0.61.0`。
- `build_qc_report()` 新增可选 `qc_reference_context` 参数，用于提供运行时分层字段值，例如 `metadata.cancer_type`、`metadata.tissue_type` 或 `metadata.center_id`。
- 当 `qc_reference_distribution.stratification.enabled=true` 且 context 完整匹配某个 stratum 时，QC engine 必须使用该 stratum 的 `metrics` 判定阈值。
- 被分层阈值判定的 metric 必须在 `reference` 字段记录：`source=qc_reference_distribution`、`selection=stratified`、`stratum_key`、`stratification_fields` 和 `group_values`。
- 当分层 reference 启用但 context 缺失、不完整或找不到匹配 stratum 时，QC engine 必须显式回退到全局 `metrics`，并在 metric reference 中记录 `selection=global_fallback` 与 fallback reason，避免静默误判。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 必须从 condition packet summary 中提取可追踪 QC context 并传入 QC engine。
- Condition packet summary 必须从 `wsi_tissue_overview.records[0].manifest` 保留 `cancer_type`、`tissue_type` 等输入 manifest 元数据，用于运行时 stratum 选择。
- `build-wsi-tissue-overview` 产物需保留输入 manifest 中的 `center_id`（若存在），并在 condition packet 中只透传 `cancer_type`、`tissue_type`、`center_id`、`split` 这些稳定字符串字段，缺失字段后续应触发带原因的 global fallback 审计。
- 新增/更新测试覆盖：QC engine 命中分层 stratum、context 缺失时显式 global fallback、smoke generation 使用 condition packet 中的 cancer type 选择分层阈值。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现 QC reference 的运行时 stratum 选择和全局 fallback 审计，不实现按 mask class 内部像素级阈值、不实现人工复核工作流，也不改变 reference builder 的分层估计逻辑。
- 当前 context 主要来自 condition packet 中的 `wsi_tissue_overview` manifest 摘要；若没有 condition packet 或没有匹配字段，系统会使用带审计字段的全局 fallback，而不是终止生成。

## v0.60.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“按组织区域、疾病类型或中心分层统计/QC”的工程落地：`qc_reference_distribution` 需要支持显式分层阈值估计，在保留全局阈值兼容性的同时，为癌种、中心、组织类型等元数据分组写出独立 warning/fail 区间和审计记录。

### 结构化需求

- 版本号升级为 `v0.60.0`。
- `build_qc_reference_distribution()` 新增可选 `stratify_by` 参数，接受一个或多个 dot-path 字段，例如 `metadata.cancer_type`、`metadata.center_id` 或 `metadata.tissue_type`。
- 未传 `stratify_by` 时，必须保持既有全局 `metrics`、`outlier_policy` 和 `outlier_audit` 行为兼容。
- 传入 `stratify_by` 时，输出 JSON 必须新增 `stratification` 和 `strata` 字段：记录启用状态、分层字段、分层数量、每个 stratum 的字段值、样本数、metric 阈值和分层 outlier audit。
- 每个 stratum 必须使用与全局一致的 estimator、outlier policy 和 `min_samples` 规则独立估计阈值；某个 stratum 的某个 metric 样本数不足时必须显式报错，不得回退到全局阈值。
- 分层字段缺失、为 `null`、为空字符串或值类型不适合做分组时，必须显式报错，避免静默把样本归入未知组。
- CLI `build-qc-reference` 新增可重复参数 `--stratify-by <dot.path>`。
- Prior manifest 的 `qc_reference_distribution` artifact metadata 应记录分层字段和分层数量，便于后续审计。
- 新增/更新测试覆盖：函数级分层阈值输出、缺失分层字段显式失败、CLI 可写出分层 reference、prior artifact metadata 记录 stratum 信息。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现 reference distribution artifact 的显式分层阈值估计和审计，不改变现有 QC engine 的默认消费逻辑；生成/QC 仍默认消费全局 `metrics`。
- 本次版本不实现自动选择最匹配 stratum 的运行时 QC policy、不实现人工复核工作流，也不实现 mask class 内部像素级分层阈值。

## v0.59.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持 robust z-score 风格的全局阈值估计，让颜色、清晰度、组织比例等数值 metric 能用 median/MAD 生成抗离群的 warning/fail 区间。

### 结构化需求

- 版本号升级为 `v0.59.0`。
- `build_qc_reference_distribution()` 的 `estimator` 新增 `robust_mad_z_score`。
- `robust_mad_z_score` 必须基于排序后的数值计算 median、MAD、scaled MAD，并输出 `median`、`mad`、`scaled_mad`、`warning_z_score`、`fail_z_score` 和 `estimator=robust_mad_z_score`。
- `robust_mad_z_score` 的 warning 区间使用 `median ± 3.0 * scaled_mad`，fail 区间使用 `median ± 6.0 * scaled_mad`。
- MAD 为 0 时必须使用有限非零 margin 生成阈值，避免阈值坍缩到单点。
- `robust_mad_z_score` 必须兼容既有 `outlier_policy`；若用户显式启用 `robust_iqr_filter`，应先过滤参考样本，再用保留样本计算 MAD/z-score 阈值。
- CLI `build-qc-reference --estimator` 新增 `robust_mad_z_score` 可选值。
- 新增/更新测试覆盖：MAD/z-score estimator 不被单个离群值拉宽到 observed max、输出 MAD/z-score 字段、零 MAD 可生成非坍缩区间、CLI 可选择 MAD estimator。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现全局 metric 的 MAD-based robust z-score 阈值估计，不实现按组织、癌种、中心或 mask 类别分层 z-score。
- 本次版本不改变 QC engine 对 reference distribution 的消费逻辑；它仍只消费最终写入的 warning/fail 区间。
- 本次版本不实现人工复核工作流，也不改变原始 QC 文件。

## v0.58.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持显式的参考 QC 异常值过滤策略，在生成阈值前排除少量明显离群参考样本，同时保留完整审计记录，避免静默丢弃数据。

### 结构化需求

- 版本号升级为 `v0.58.0`。
- `build_qc_reference_distribution()` 新增 `outlier_policy` 参数，默认 `none`，保持既有行为兼容。
- 新增 `robust_iqr_filter` policy：对每个 metric 的参考值计算 Q1、Q3 和 IQR，并使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 作为保留区间；区间外样本在该 metric 的阈值估计中排除。
- `robust_iqr_filter` 必须仅在用户显式选择时生效，不得作为默认静默回退。
- 输出 JSON 必须记录 `outlier_policy` 和 `outlier_audit`，审计内容至少包含：policy、每个 metric 的原始样本数、保留样本数、排除样本数、filter fence、以及被排除样本的 `generated_id`、metric name 和数值。
- 若过滤后某个 metric 的样本数低于 `min_samples`，必须显式报错，不能回退到未过滤样本。
- 非法 `outlier_policy` 必须显式报错。
- CLI `build-qc-reference` 新增 `--outlier-policy` 参数，支持 `none` 与 `robust_iqr_filter`。
- 新增/更新测试覆盖：异常样本被排除并写入 audit、过滤后样本不足时报错、非法 policy 报错、CLI 可选择 outlier policy。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现全局 metric 的 IQR-based reference QC 异常值过滤，不实现按组织、癌种、中心或 mask 类别分层异常处理。
- 本次版本不实现稳健 z-score、不实现人工复核工作流、不从磁盘删除或修改原始 QC 文件。
- 本次版本不改变 QC engine 对 reference distribution 的消费逻辑；它仍只消费最终写入的阈值区间。

## v0.57.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“训练分布自适应阈值”的稳健估计能力：`qc_reference_distribution` 需要支持 IQR-based robust threshold estimator，避免少量离群参考 QC 把 warning/fail 区间过度拉宽。

### 结构化需求

- 版本号升级为 `v0.57.0`。
- `build_qc_reference_distribution()` 新增 `estimator` 参数，支持既有 `observed_min_max_with_range_margin` 和新增 `robust_iqr`。
- `robust_iqr` 必须基于排序后的数值计算 Q1、median、Q3 和 IQR。
- `robust_iqr` 输出每个 metric 的 `warning_min`、`warning_max`、`fail_min`、`fail_max`、`sample_count`、`observed_min`、`observed_max`、`q1`、`median`、`q3`、`iqr` 和 `estimator=robust_iqr`。
- `robust_iqr` 的 warning 区间使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`，fail 区间使用 `[Q1 - 3.0*IQR, Q3 + 3.0*IQR]`，并在零 IQR 时使用有限非零 margin，避免所有阈值坍缩到单点。
- 非法 estimator 必须显式报错，不得静默回退。
- CLI `build-qc-reference` 新增 `--estimator` 参数，默认保持既有 `observed_min_max_with_range_margin`，以保持兼容。
- 新增/更新测试覆盖：robust IQR 估计器不会被单个离群值拉宽到 observed max、输出 quartile/IQR 字段、非法 estimator 报错、CLI 可选择 robust estimator。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现全局 metric 的 robust IQR 阈值估计，不实现按组织、癌种、中心或 mask 类别分层阈值。
- 本次版本不自动剔除异常参考样本，也不改变 QC engine 对已有 reference distribution 的消费逻辑。

## v0.56.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 和 README 中 `chunked_pyramid_write` 的输出侧前置能力：OME-TIFF writer 需要输出可审计的 chunked write plan / BigTIFF 决策记录，减少 generation plan 与实际 writer 报告之间的语义落差。

### 结构化需求

- 版本号升级为 `v0.56.0`。
- `write_pyramid_ome_tiff()` 新增 chunked write audit report：记录 writer backend、实际 `write_mode`、是否 production streaming、BigTIFF 决策、估算字节数和每层 chunk plan。
- Chunk plan 至少记录每层 level index、shape、dtype、chunk shape、chunk grid、chunk count 和边缘 chunk 尺寸。
- Chunk shape 必须是两个正整数；非法 chunk shape 必须显式报错。
- BigTIFF 决策必须基于估算 pyramid 字节数与阈值，不允许静默固定为 false。
- 当前版本仍可使用内存数组一次性写入小型 OME-TIFF；必须在报告中明确 `production_streaming=false` 与 `streaming_limitations`，不得伪装为 production gigapixel streaming writer。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 写出的 `generation_run.json.pyramid_report` 必须包含同一 chunked write audit 字段，便于从最终交付物追踪写出计划。
- 新增/更新测试覆盖：writer 报告 chunked write plan、非法 chunk shape 报错、smoke generation run summary 中保留 writer audit。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只补齐 OME-TIFF 写出计划与审计契约，不实现磁盘级 tile streaming、不实现真正 gigapixel 级增量写入、不实现中断后继续写入 OME-TIFF。
- BigTIFF 决策在本版本用于 writer 配置和审计记录；是否能承载生产级超大 WSI 仍受当前内存数组 writer 限制。

## v0.55.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本为 v0.54.0 的 sampled layout mask 条件输出补齐 QC 审计，确认最终 generated mask 是否忠实保留 sampled mask 条件。

### 结构化需求

- 版本号升级为 `v0.55.0`。
- `build_qc_report()` 新增可选 `sampled_layout_mask_summary` 参数。
- QC 的 `non_copy_report.metrics` 新增 `sampled_layout_mask_match_proxy`，读取 sampled layout `.npy` 与最终 generated mask 逐像素比较，记录 matched pixel fraction。
- sampled mask 与 generated mask 尺寸不一致但都是二维时，可用 nearest resize 对齐后计算匹配率；非二维、缺文件或不可读必须显式报错。
- `sampled_layout_mask_match_proxy.reference` 必须记录 sampled artifact path、mask path、sample id、mask shape、class counts/fractions。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition summary 包含 `sampled_layout_mask` 时，必须把该摘要传给 QC builder。
- 本次版本不把 sampled mask 匹配失败作为硬错误之外的新终止条件，仍只作为 QC metric 暴露。
- 新增/更新测试覆盖：QC builder 记录 sampled mask match proxy、缺失 sampled mask 文件显式失败、smoke generation QC 中包含该 proxy。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 该 QC 指标只审计工程链路是否保留 sampled mask 条件，不判断 sampled mask 本身是否病理合理。
- 本次版本不实现 mask diffusion、语义一致性模型或 production ControlNet 条件校验。

## v0.54.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 v0.53.0 的 `sampled_layout_mask` 从独立 artifact 接入 generation condition packet 和 smoke generation 输出，使统计型 sampled layout mask 能作为实际 mask 条件交付。

### 结构化需求

- 版本号升级为 `v0.54.0`。
- `build_generation_condition_packet()` 新增可选 `sampled_layout_mask_path` 参数，传入时必须读取并校验 `sampled_layout_mask.json`。
- CLI `build-condition-packet` 新增 `--sampled-layout-mask <sampled_layout_mask.json>`。
- Condition packet 的 `artifact_inputs.sampled_layout_mask` 必须记录 artifact path、kind 和 sample/mask metadata。
- Condition packet 的 `conditions.mask` 在传入 sampled layout mask 时必须切换为 `source=sampled_layout_mask`，记录 `mask_path`、sample id、mask shape、class counts/fractions 和 limitations。
- `run_smoke_generation()` 在 condition packet 的 mask 条件来自 sampled layout mask 时，必须读取该 `.npy` mask，校验二维和 0-5 类 id，必要时 nearest resize 到输出 canvas，并写为最终 `generated_mask/mask.npy`。
- `metadata.json` 与 `generation_run.json` 的 condition summary 必须记录 sampled layout mask 摘要，便于追溯输出 mask 来源。
- 对缺失 sampled mask 文件、非二维 mask、非法 class id 或坏 sampled layout manifest 必须显式报错。
- 本次版本不改变 smoke RGB 生成算法，不实现 production mask diffusion、真实 segmentation 或 ControlNet 条件注入。
- 新增/更新测试覆盖：condition packet 记录 sampled layout mask、smoke generation 使用 sampled layout mask 输出最终 mask。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只把 sampled layout mask 作为工程链路中的 mask 条件接入输出归档。
- 该能力用于验证结构条件可追踪和可交付，不代表 production de novo layout / mask diffusion 已实现。

## v0.53.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 Phase 1 layout/mask prior 的可执行能力：把统计型 `layout_mask_prior` 转成可复现的 sampled layout mask artifact，使低 anchor / fully de novo 路径有可交付的结构条件输入。

### 结构化需求

- 版本号升级为 `v0.53.0`。
- 新增 `sample_layout_mask_from_prior()`，从 `layout_mask_prior.json` 读取 6 类比例和 tile layout records，输出 `.npy` sampled layout mask 与 `sampled_layout_mask.json` manifest。
- CLI 新增 `sample-layout-mask <layout_mask_prior.json> --output-dir <dir> --sample-id <id> --height <n> --width <n> --random-seed <seed>`。
- 可选 `--wsi-tissue-overview <path>`：传入时读取第一条真实 thumbnail tissue proxy 的 tissue fraction、bounding box 和 connected component count，并用 bounding box 约束 sampled mask 的非背景 footprint。
- 输出 manifest 必须记录 schema version、artifact type、sample id、random seed、mask path/shape、source prior path、可选 tissue overview path、class counts/fractions、tissue overview reference 和 limitations。
- 对非法 mask shape、空 sample id、非整数 random seed、坏 prior JSON、prior_type 不匹配、class_fractions 非 6 类或 tissue overview 字段缺失必须显式报错。
- 本次版本不实现 mask diffusion、语义分割模型、source-anchor layout mixing 或 production layout generator。
- 新增/更新测试覆盖：函数输出 mask/manifest、seed 确定性、非法 shape 失败和 CLI 成功路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次 sampled layout mask 是统计型结构条件 artifact，用于连接 prior 与后续 generation conditioning。
- 它只提供可审计、可复现的低倍结构条件，不代表病理语义分割质量或 production 级 de novo layout sampler。

## v0.52.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把已进入 generation condition summary 的 `wsi_tissue_overview` 接入 QC 报告，形成生成 mask 组织比例与真实 WSI thumbnail tissue fraction 的轻量一致性审计。

### 结构化需求

- 版本号升级为 `v0.52.0`。
- `build_qc_report()` 新增可选 `wsi_tissue_overview_summary` 参数；传入时必须校验该摘要的基础结构。
- QC 的 `non_copy_report.metrics` 必须新增 `wsi_tissue_fraction_reference_proxy`，记录生成 mask tissue fraction 与真实 WSI tissue overview tissue fraction 的接近程度。
- `wsi_tissue_fraction_reference_proxy.reference.tissue_fraction` 必须保留 `wsi_tissue_overview` 源 artifact 中的原始数值精度，避免真实 SVS 验证时把 `0.156499895` 这类值舍入为 `0.1565`。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition packet summary 包含 `wsi_tissue_overview` 时，必须把该摘要传给 QC builder。
- 缺失 `wsi_tissue_overview` 时，既有 QC 路径保持兼容。
- 输入的 tissue overview summary 缺少 records、record 缺少 tissue_fraction 或 tissue_fraction 非数值时必须显式报错。
- 本次版本不把 tissue fraction reference proxy 作为硬 fail 条件，不改变 smoke/PyTorch smoke 生成算法，也不实现 production layout sampler 或 mask diffusion。
- 新增/更新测试覆盖：QC builder 记录 tissue fraction reference proxy、坏 tissue overview summary 显式失败、生成输出 QC 中包含该 proxy。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只补齐真实 WSI 低倍组织轮廓 proxy 与 QC 报告之间的审计连接。
- 该 proxy 是轻量一致性指标，不代表语义分割质量或病理真实性判定。

## v0.51.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 condition packet 中已经记录的可选 `wsi_tissue_overview` 摘要继续写入 generation 交付物，使真实 WSI 低倍组织轮廓 proxy 能从 prior artifact 追踪到 `metadata.json` 和 `generation_run.json`。

### 结构化需求

- 版本号升级为 `v0.51.0`。
- `run_smoke_generation()` 传入 condition packet 且其 `conditions.layout.wsi_tissue_overview` 存在时，必须把该摘要写入 `metadata["generation"]["condition_summary"]["wsi_tissue_overview"]`。
- `generation_run.json` 的 `condition_packet.summary` 必须记录同一份 `wsi_tissue_overview` 摘要，便于批量审计。
- 摘要至少包含 source、artifact path、record count、source backend、thumbnail max size，以及每张 WSI 的 tissue fraction、bounding box 和 connected component count。
- condition packet 不包含 `wsi_tissue_overview` 时，既有 smoke generation 路径保持兼容。
- 本次版本不改变 smoke backend 的图像采样算法，不实现 production layout sampler、mask diffusion 或真实 tissue contour 条件注入。
- 新增/更新测试覆盖：带 tissue overview 的 condition packet 进入 smoke generation metadata/run summary，以及缺失 tissue overview 的旧路径兼容。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只增强生成交付物审计链路，使低倍组织轮廓 proxy 可追溯到最终输出 JSON。
- `wsi_tissue_overview` 在本版本仍不作为 smoke backend 的像素采样控制输入。

## v0.50.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 prior manifest 中可选的 `wsi_tissue_overview` 继续接入 generation condition packet，使真实 WSI 低倍组织轮廓 proxy 能进入生成条件审计链路。

### 结构化需求

- 版本号升级为 `v0.50.0`。
- `build_generation_condition_packet()` 在 prior manifest 包含 `wsi_tissue_overview` 时，必须读取并校验该 artifact。
- `conditions.layout` 必须记录 `wsi_tissue_overview` 摘要，至少包含 artifact path、record count、source backend、thumbnail max size、每张 WSI 的 tissue fraction、bounding box 和 connected component count。
- `artifact_inputs` 必须继续包含可选 `wsi_tissue_overview` 的 path/hash/size，便于复现。
- `wsi_tissue_overview` 缺失时，condition packet 仍保持兼容，不要求该 artifact。
- `wsi_tissue_overview` artifact 非 JSON、`artifact_type` 不匹配、records 非列表或 tissue proxy 字段缺失时必须显式报错。
- 新增/更新测试覆盖：带 tissue overview 的 condition packet、缺失 tissue overview 的兼容路径和坏 artifact 失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只把真实 WSI 组织轮廓 proxy 写入条件包，不改变 smoke/torch generation backend 的采样算法。
- 本次版本不实现可采样 layout generator、mask diffusion、source-anchor layout mixing 或 production diffusion 条件注入。

## v0.49.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 `v0.48.0` 新增的 `wsi_tissue_overview` 接入 prior manifest，使真实 WSI 低倍组织轮廓 artifact 能被统一 manifest 追踪、校验和复现。

### 结构化需求

- 版本号升级为 `v0.49.0`。
- `build_prior_manifest_from_artifacts()` 新增可选 `wsi_tissue_overview_path` 参数；传入时必须校验该 artifact 并写入 `artifacts.wsi_tissue_overview`。
- `build-prior-manifest` CLI 新增可选 `--wsi-tissue-overview <path>`。
- `validate_prior_manifest()` 必须继续要求四类核心 artifact：`layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`；同时允许可选 `wsi_tissue_overview`，并继续拒绝其它未知 artifact type。
- `wsi_tissue_overview` artifact 必须校验 `artifact_type == "wsi_tissue_overview"`，并在 manifest metadata 中记录 artifact schema version、record count、source backend 和 thumbnail max size。
- 不传 `wsi_tissue_overview` 时，既有 prior manifest 构建、保存、加载和 CLI 行为必须保持兼容。
- 新增/更新测试覆盖：可选 tissue overview 被写入 manifest、CLI 可传入该 artifact、未知 artifact 仍被拒绝、未传 tissue overview 的旧路径仍通过。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只把 tissue overview 纳入 prior manifest 追踪，不改变四类核心 prior artifact 的必需性。
- 本次版本不让 generation condition packet 或 generation backend 直接消费 tissue overview；后续再把它接入 layout prior / QC / de novo layout sampling。

## v0.48.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐真实 WSI 低倍组织概览 artifact：从输入 manifest 读取真实 WSI thumbnail，输出可审计的 tissue contour proxy，为 layout/mask prior、QC 和后续 de novo layout 采样建立 WSI-level 组织轮廓基础。

### 结构化需求

- 版本号升级为 `v0.48.0`。
- 新增 `build_wsi_tissue_overview_from_manifest()`，必须读取 manifest、通过指定 reader 读取 WSI metadata 和 thumbnail，并写出 `wsi_tissue_overview` JSON。
- CLI 新增 `build-wsi-tissue-overview <manifest> --backend <openslide|fixture-image> --thumbnail-max-size <n> --output <path>`。
- 输出 artifact 必须记录 schema version、artifact type、manifest path、dataset id、reader backend、thumbnail max size、record count、每张 WSI 的 slide metadata、manifest 摘要、thumbnail RGB 统计和 tissue mask proxy 指标。
- Tissue mask proxy 至少包含检测方法、阈值、thumbnail size、tissue/background pixel count、tissue fraction、bounding box 和 connected component count。
- 对 manifest schema 错误、非法 thumbnail size、reader 失败、空 thumbnail 或未检测到 tissue pixel 必须显式报错，不得静默写出空 artifact。
- 新增测试覆盖函数成功路径、空白 thumbnail 失败路径和 CLI 成功路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只实现基于低倍 thumbnail 的轻量 tissue contour proxy，不实现语义分割、tumor/stroma 分类、6 类 mask 推断或可采样 layout generator。
- `wsi_tissue_overview` 作为独立 artifact 供后续 prior manifest / layout prior 消费，本次不改变既有 `layout_mask_prior` 的输入契约。

## v0.47.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐 UI 配置的 YAML 支持：`write-ui-config` 和 `launch-ui` 相关配置应能按路径后缀读写 JSON/YAML，并在缺少 PyYAML 时显式报错。

### 结构化需求

- 版本号升级为 `v0.47.0`。
- `save_ui_config()` 必须根据目标路径后缀写出 JSON 或 YAML；`.yaml` / `.yml` 路径需要使用 PyYAML，缺失依赖时必须显式报错。
- `load_ui_config()` 必须根据输入路径后缀读取 JSON 或 YAML；`.yaml` / `.yml` 路径需要使用 PyYAML，缺失依赖时必须显式报错，不得静默把 YAML 当作 JSON。
- 新增/更新测试覆盖 JSON roundtrip、YAML roundtrip 和 YAML 缺依赖错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只扩展 UI 配置文件格式支持，不实现通用 YAML 配置树、复杂标签或多文档 YAML。
- YAML 仍是可选依赖能力；未安装 PyYAML 时，涉及 YAML 的读写必须明确失败，而不是隐式降级为 JSON。

## v0.46.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐输出摘要的 CLI 入口：UI controller 已有 `collect_output_summary()`，但命令行还没有一个可复现方式把 metadata + QC 汇总成稳定 JSON。

### 结构化需求

- 版本号升级为 `v0.46.0`。
- CLI 新增 `inspect-output-summary --metadata <metadata.json> --qc <qc.json>`。
- `inspect-output-summary` 必须复用 `collect_output_summary()`，把 metadata + QC 汇总成 JSON 输出到 stdout。
- 读取失败、QC schema 错误或缺失输入必须显式报错并返回非零退出码。
- 新增/更新测试覆盖 success 路径和 invalid QC 失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露输出摘要查看入口，不实现 HTML 报告、可视化渲染、上传或远程聚合。
- `inspect-output-summary` 只读输入文件，不会修改 metadata 或 QC。

## v0.45.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 执行命令的工作目录透传：`JobRunner.create_job()` 已支持 `cwd`，但 `run-local-job` 还没有暴露这个能力。

### 结构化需求

- 版本号升级为 `v0.45.0`。
- `run-local-job` CLI 新增可选 `--cwd <path>`，并将其透传给 `JobRunner.create_job()`。
- 使用 `--cwd` 时，后续命令必须在指定工作目录执行，并把该 cwd 持久化到 job record。
- 新增/更新测试覆盖 `--cwd` 成功路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露工作目录透传，不实现路径预检查、目录创建或跨机器调度。
- `--cwd` 只影响 job 命令的执行目录，不改变 job_root 的持久化位置。

## v0.44.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的批量查看入口：在 `run-local-job`、`cancel-local-job` 和 `inspect-local-job` 之外，再提供一个可复现的 list 命令，直接列出 job_root 下的持久化 job 状态。

### 结构化需求

- 版本号升级为 `v0.44.0`。
- CLI 新增 `list-local-jobs <job_root>`。
- `list-local-jobs` 必须读取 job_root 下的持久化 job 记录，并以 JSON 数组输出，便于脚本和人工查看任务状态。
- `list-local-jobs` 对未知 job、非法 job id 或损坏记录必须显式报错并返回非零退出码，不得静默跳过坏记录。
- 新增/更新测试覆盖 list 成功路径和损坏记录失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 job 记录批量查看入口，不实现分页、过滤、后台 daemon、并发调度或状态订阅。
- `list-local-jobs` 只读 job_root 中的持久化记录，不会修改 job 状态。

## v0.43.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的查看入口：既然 `run-local-job` 和 `cancel-local-job` 已经可用，`he-wsi-gen` 也应提供可复现的 inspect 命令，把持久化 job 记录导出为 JSON 供排障和状态查看。

### 结构化需求

- 版本号升级为 `v0.43.0`。
- CLI 新增 `inspect-local-job <job_root> --job-id <id>`。
- `inspect-local-job` 必须复用 `JobRunner.load_job()` 读取已持久化记录；未知 job id、非法 job id 或损坏 JSON 必须显式报错并返回非零退出码。
- 成功时必须把完整 job record 以 JSON 形式写到 stdout，便于脚本和人工查看。
- 新增/更新测试覆盖 inspect 成功路径、未知 job 失败路径和损坏记录失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 job 记录查看入口，不实现 job 编辑、重放、批量列表、后台 daemon 或并发调度。
- `inspect-local-job` 只负责读取已存在的持久化记录，不会自动执行或修改 job 状态。

## v0.42.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地任务取消的 CLI 入口：既然 UI job runner 已支持 queued job 取消，`he-wsi-gen` 也应提供可复现命令来把已排队任务显式标记为 `cancelled`。

### 结构化需求

- 版本号升级为 `v0.42.0`。
- CLI 新增 `cancel-local-job <job_root> --job-id <id> [--message <message>]`。
- `cancel-local-job` 必须复用 `JobRunner.cancel_job()`，只允许取消 `queued` job；未知 job、非法 job id 或非 queued 状态必须显式报错并返回非零退出码。
- 取消成功时必须持久化 `job.json`、写空 `stdout.txt` / `stderr.txt`，并在 stdout 输出包含 `local job cancelled` 和记录路径的信息。
- 新增/更新测试覆盖 CLI 取消成功路径和非 queued job 的失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 queued job 的显式取消入口，不实现运行中进程终止、后台 daemon、并发队列或跨机器调度。
- `run-local-job` 仍是同步执行命令；取消命令用于已经持久化但尚未运行的 queued job。

## v0.41.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐生成完成态审计：成功输出的 smoke generation 结果必须把 `tile_traversal_plan` 物化成完成态，而不是把已完成样本保留为 pending 计划。

### 结构化需求

- 版本号升级为 `v0.41.0`。
- 新增或更新 tile traversal completion helper，使 tile traversal plan 可转换为完成态，并能显式记录部分完成时的 `completed_tile_count`、`pending_tile_count`、`resume_index` 和 `next_tile_index`。
- `run_smoke_generation` 写出的 `metadata["generation"]["tile_traversal_plan"]` 和 `generation_run.json` 中的 plan 必须在成功输出时记录完成态，至少包含 `completed_tile_count = tile_count`、`pending_tile_count = 0`、`next_tile_index = null`、所有 `tiles.status = completed`。
- 同一份成功运行记录里的 `plan.stages` 也必须切换为 completed，避免生成运行摘要看起来仍停留在 planned 状态。
- QC 的 non-copy report 必须输出轻量 similarity proxy metrics，至少覆盖 thumbnail、tissue contour、mask layout 和 global embedding 四类指标；这些指标可以保持为 proxy，不要求做全量 patch nearest-neighbor 搜索。
- QC 还要给出 tile 级 seam score proxy 和 WSI 级 style consistency proxy，作为默认自动质控的一部分。
- smoke generation 必须真正按 `canvas_size_40x` 拼接 1/1 canvas，而不是只输出固定 512 方块。
- UI job runner 需要支持把 queued job 显式取消为 `cancelled`，并持久化终态记录。
- helper 必须支持部分完成状态，用于未来的中断/恢复审计；非法 completed count 或损坏的 traversal plan 必须显式报错。
- 新增/更新测试覆盖完成态 tile traversal plan、部分完成 helper，以及成功生成输出中的 completion state。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本断言和相关测试。

### 边界说明

- 本次版本只完善生成完成态与中断态的审计表达，不改变图像合成算法、QC 规则或采样逻辑。
- 本次版本不实现真正的磁盘级断点续写、partial write recovery 或额外的任务调度机制。

## v0.40.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进生成输出的可审计性：把 `tile_traversal_plan` 写入 smoke generation metadata，便于从单个产物直接追溯 traversal / resume / write-region 信息。

### 结构化需求

- 版本号升级为 `v0.40.0`。
- `run_smoke_generation` 产生的 metadata 必须在 `generation` 字段里记录 `tile_traversal_plan`，与 run summary 中已有的物化 plan 保持一致。
- `tile_traversal_plan` 的记录必须来自 `create_generation_plan` 的输出，不得静默重建或伪造。
- 新增/更新测试覆盖 `metadata["generation"]["tile_traversal_plan"]` 的存在、tile count 和 tile origin。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本断言和相关测试 fixture。

### 边界说明

- 本次版本只提升 smoke 输出的审计完整度，不改变现有 smoke backend 的图像合成逻辑。
- 本次版本不引入新的生成模型、不改变 sampling 顺序，也不实现 production cascade sampler。

## v0.39.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 中 production cascade sampler 的前置执行能力：把 `tile traversal`、`resume index` 和 `overlap weighted blending` 从 generation plan 的字符串说明推进为可测试、可审计的基础设施。

### 结构化需求

- 版本号升级为 `v0.39.0`。
- 新增 generation tiling 基础模块，能够根据 40x canvas、512x512 tile 和 overlap 生成 row-major tile traversal plan。
- Tile traversal plan 必须记录 `resume_index`、tile 总数、已完成/待处理 tile 数、每个 tile 的 40x origin、模型 tile size、实际写入区域、stride、状态和 edge crop 策略。
- Traversal 需要显式校验 canvas、tile size、overlap 和 resume index；非法输入必须报错，不得静默回退。
- 新增 overlap weighted RGB tile blending helper，支持按 tile origin 把多个 RGB tile 写入 canvas，并对 overlap 区域执行权重平均。
- Blending 必须显式拒绝非 uint8 RGB tile、无效 tile origin、空 tile 输入和未覆盖完整 canvas 的输入。
- `create_generation_plan` 必须写入物化后的 `tile_traversal_plan`，同时保留既有 `tile_traversal`、`blending` 和 `write_mode` 字段，便于旧记录可读。
- 新增/更新测试覆盖 row-major traversal、resume 状态、edge crop write region、overlap weighted blending、未覆盖 canvas 错误，以及 generation plan 中的 traversal plan。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 sampler/reconstructor 需要的 tile traversal 与 blending 基础设施，并把 generation plan 从字符串记录推进为可审计对象。
- 本次版本不实现 production latent diffusion checkpoint、不实现真实 full-WSI tile batch inference、不实现异步 resume 执行、不实现磁盘级 chunk streaming。
- 默认 generation config 仍使用 512x512 smoke canvas；更大 canvas 的 traversal/blending 已可测试，但完整 production backend 后续继续接入。

## v0.38.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 的推理顺序要求：`torch-diffusion-smoke` generation backend 必须按 `1/32 -> 1/16 -> 1/4 -> 1/1` 执行级联采样，并保存每层中间状态。

### 结构化需求

- 版本号升级为 `v0.38.0`。
- `run_torch_diffusion_smoke_generation` 必须依次执行四个 cascade levels，而不是只采样 `1/1`。
- 每层采样必须写入独立目录和 `sample_manifest.json`，generation run summary 必须记录 `cascade_sample_manifests`。
- `1/32` 层必须使用默认 zero previous-scale condition；`1/16`、`1/4`、`1/1` 必须把上一层 `sample_preview.npy` 作为 `previous_scale_condition_path` 传入 sampler。
- Metadata 的 generation 字段必须记录 `cascade_sample_manifests`，便于追踪每个级联层级的采样输入输出。
- OME-TIFF pyramid 必须由四个 cascade sample preview 组装，而不是只从最终 preview resize 出所有层。
- Generation plan stage 必须记录每个层级已完成，以及 condition inputs 包含 previous-scale RGB proxy、mask、timestep、condition features 和 checkpoint。
- 新增/更新测试覆盖 generation run summary、metadata、四层 sample manifest 路径、previous-scale condition source/path 传递和 OME-TIFF 层级输出。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级四层级联采样链路，用于把文档要求的推理顺序和中间状态保存落到可审计文件。
- 本次版本不实现 production cascade sampler、不实现 tile traversal over full WSI、不实现 overlap weighted blending、不实现真实跨倍率 latent encoder 或 WSI consistency fine-tuning。
- 级联输出仍是 64x64 preview 级 smoke sample 后 resize 组装小型 pyramid，不得标记为 production inference。

## v0.37.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1 的“上一尺度图像 / latent”条件输入要求：让 PyTorch diffusion smoke denoiser 不再只依赖当前 latent、mask、timestep 和条件特征，而是接收可审计的上一尺度 RGB proxy 条件通道。

### 结构化需求

- 版本号升级为 `v0.37.0`。
- Diffusion checkpoint payload、checkpoint manifest 和 sampler manifest 必须记录 `cross_scale_condition_schema`。
- `cross_scale_condition_schema` 必须说明条件名称、通道数、注入方式、训练来源、采样来源、根层级行为和 smoke-only production 状态。
- `train_torch_diffusion_smoke_model` 必须为 denoiser 输入拼接上一尺度 RGB proxy 条件通道；对 `1/16`、`1/4`、`1/1` 从真实 RGB tile 构建 coarse-to-target proxy，对 `1/32` 使用显式 zero root condition。
- Cross-scale 条件通道必须参与 input channel 计算，并同步写入 `denoiser_architecture.input_channels`。
- `sample_torch_diffusion_smoke_model` 必须支持可选 `previous_scale_condition_path`，可从 `.npy` RGB preview 读取上一尺度条件；未提供时必须显式记录 zero/default source，不得静默假装已有上一尺度生成结果。
- CLI `sample-torch-diffusion-smoke` 必须新增 `--previous-scale-condition` 参数并传给 sampler。
- Sampling 必须校验 checkpoint manifest/payload 中的 `cross_scale_condition_schema`；缺失或不匹配时显式报错。
- 新增/更新测试覆盖训练 manifest/payload schema、input channel 增量、sampler manifest 默认 zero source、显式 previous-scale condition source、CLI 参数和缺失 schema 的错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级上一尺度 RGB proxy 条件通道，用于把 cross-scale condition 推进到真实张量输入与 checkpoint 契约。
- 本次版本不实现 production cascade sampler、不实现跨倍率 latent encoder、不实现 ControlNet、不实现 attention/cross-attention 或 WSI consistency fine-tuning。
- 未提供 previous-scale condition 时，sampler 必须记录 zero/default source，避免把单层 smoke sampling 伪装成真实多倍率级联推理。

## v0.36.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1 的 `latent_diffusion_unet` 主干要求：把 PyTorch diffusion smoke denoiser 从简单卷积堆栈升级为带 downsample、bottleneck、upsample 和 skip connection 的 smoke U-Net。

### 结构化需求

- 版本号升级为 `v0.36.0`。
- `_MaskConditionedLatentDenoiser` 必须实现 smoke U-Net 结构，至少包含 encoder、downsample、bottleneck、upsample、skip connection、decoder/output blocks。
- Diffusion checkpoint payload 和 checkpoint manifest 必须记录 `denoiser_architecture`，包括 architecture 名称、base channels、bottleneck channels、downsample stages、skip connection 语义、输入来源和 production 状态。
- `sample_torch_diffusion_smoke_model` 必须校验 checkpoint manifest/payload 中的 denoiser architecture；缺失或不匹配时显式报错。
- U-Net smoke denoiser 必须同时兼容 `rgb_downsample_proxy` latent 和 `trainable_vae_smoke` latent 的不同 output channel 数。
- 新增/更新测试覆盖 payload/manifest 架构记录、state_dict 中的 U-Net block key、VAE latent 路径兼容和缺失 denoiser architecture 的错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级 U-Net denoiser，用于把模型结构从普通卷积堆栈推进到可审计 U-Net 主干。
- 本次版本不实现 production-scale U-Net/ControlNet、不实现 attention blocks、多尺度 cross-scale encoder、EMA、classifier-free guidance 或 WSI consistency fine-tuning。
- Checkpoint 仍必须标记为不可生产推理，避免把 smoke U-Net 伪装成完整 WSI latent diffusion generator。

## v0.35.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 v0.34.0 VAE smoke checkpoint 与 diffusion smoke 的连接：让 diffusion smoke trainer/sampler 可以选择使用 `trainable_vae_smoke` latent，而不是只能使用 `rgb_downsample_proxy`。

### 结构化需求

- 版本号升级为 `v0.35.0`。
- `train_torch_diffusion_smoke_model` 新增可选 `vae_checkpoint_manifest_path` 参数；提供时必须加载并校验 VAE smoke checkpoint。
- CLI `train-torch-diffusion-smoke` 新增可选 `--vae-checkpoint-manifest` 参数。
- 使用 VAE checkpoint 时，diffusion trainer 必须通过 VAE encoder 的 `mu` 构造 latent batch，记录 `latent_source=trainable_vae_smoke`。
- 使用 VAE latent 时，diffusion checkpoint payload/manifest 的 `latent_batch_shape`、`input_channels`、`output_channels` 必须反映 VAE latent channel 数。
- Diffusion checkpoint manifest 和 payload 必须记录 `vae_checkpoint_manifest_path`，便于审计 latent 来源。
- `sample_torch_diffusion_smoke_model` 遇到 `latent_source=trainable_vae_smoke` 时必须加载 VAE checkpoint，通过 VAE decoder 将 sampled latent 解码为 RGB preview，并在 `sample_manifest.json` 记录 latent sample shape。
- 旧的 `rgb_downsample_proxy` 路径必须保持可用；未提供 VAE checkpoint 时不得伪装为 VAE latent。
- 新增/更新测试覆盖 VAE latent diffusion 直接训练、采样解码、CLI 训练参数和 manifest 字段。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只把 smoke VAE encoder/decoder 接入 smoke diffusion 训练与采样路径，用于验证 VAE latent 工程闭环。
- 本次版本不实现 production VAE、不实现完整 U-Net/ControlNet、不实现 perceptual/adversarial VAE loss、不实现 VAE-diffusion 联合训练或 WSI consistency fine-tuning。
- VAE 和 diffusion checkpoint 仍必须标记为不可生产推理，不能伪装为完整 WSI latent diffusion generator。

## v0.34.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1/7.2 的 VAE latent 缺口：新增 PyTorch VAE smoke trainer，使项目不再只有 RGB downsample proxy latent，而是具备可训练、可审计的 latent autoencoder 工程入口。

### 结构化需求

- 版本号升级为 `v0.34.0`。
- 新增 `train_torch_vae_smoke_model`，输入为 training-index JSONL、输出目录、batch size、split、cascade level、epochs、learning rate、random seed、device、latent channels、latent size 和 KL loss weight。
- 新增 CLI `train-torch-vae-smoke`，用于从 training-index 执行一次可审计的 PyTorch VAE smoke training。
- Trainer 必须通过 `load_training_batch(..., include_image=True)` 读取真实 RGB image tile，不得只消费 mask 或伪造图像。
- VAE smoke trainer 必须包含 encoder、reparameterization 和 decoder，并真实执行 reconstruction loss + KL loss 的反向传播。
- `model.pt` payload 与 `checkpoint_manifest.json` 必须记录 `latent_source=trainable_vae_smoke`、`target_type=vae_rgb_reconstruction`、latent channels、latent size、latent batch shape、loss histories、KL weight、checkpoint hash 和 batch summary。
- Trainer 必须写出 `latent_preview.npy` 与 `reconstruction_preview.npy`，用于审计 latent shape 和重建输出。
- Checkpoint manifest 必须明确 `usable_for_inference=false`，说明该 VAE 是 smoke 级 latent autoencoder，不是 production VAE。
- 新增/更新测试覆盖直接函数调用、checkpoint payload、manifest 字段、preview 文件形状和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只新增 trainable VAE smoke autoencoder 入口，目的是把 latent diffusion 路线从 RGB proxy 迈向可训练 latent。
- 本次版本不把 diffusion smoke trainer 切换到 VAE latent，不实现 production VAE、perceptual loss、adversarial loss、EMA、large-scale dataset streaming 或 WSI consistency fine-tuning。
- 后续仍需把 VAE encoder/decoder 接入 diffusion trainer/sampler，并替换当前 `rgb_downsample_proxy` latent。

## v0.33.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 6.3 与 7.1 的条件注入路径：让 PyTorch diffusion smoke denoiser 不再只记录 `generation_condition_packet`，而是把条件包中的 style、texture、coordinate、source 和 structure anchor 摘要编码为空间条件通道参与训练/采样。

### 结构化需求

- 版本号升级为 `v0.33.0`。
- PyTorch diffusion smoke checkpoint 必须记录 condition feature schema，包含 feature 名称、数量、来源和训练期默认策略。
- `train_torch_diffusion_smoke_model` 必须在 denoiser 输入中加入条件特征通道；训练期可从 training-index/tile 元数据构建确定性默认条件，不得伪造 production prior。
- `sample_torch_diffusion_smoke_model` 在提供 condition packet 时必须把同一份条件摘要编码为 feature vector，并作为 spatial condition channels 拼接到 denoiser 输入。
- `sample_manifest.json` 必须记录 `condition_feature_schema` 和 `condition_feature_vector`；没有 condition packet 时必须记录明确的 zero/default condition feature vector，而不是静默缺省。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 必须通过 sampler 使用相同的 condition feature vector，并让 sampler manifest、metadata、generation run summary 保持可审计一致。
- Checkpoint payload 与 checkpoint manifest 的 `input_channels` 必须包含 RGB latent、6 类 mask、timestep 和 condition feature channels。
- Sampling 必须校验 checkpoint 的 condition feature schema；缺失或不匹配时显式报错，避免用旧结构 checkpoint 静默采样。
- 新增/更新测试覆盖训练 manifest、checkpoint payload、sampler manifest、直接 generation 和 CLI generation 中的 condition feature schema/vector。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本是 smoke 级条件通道注入，用于把条件包推进到模型输入张量路径。
- 本次版本不实现 production VAE latent、不实现完整 U-Net/ControlNet、多尺度 source encoder、trainable style encoder、texture codebook 或 WSI consistency fine-tuning。
- Checkpoint 仍必须标记为 `usable_for_inference=false` / `usable_for_production=false`，不得把 smoke 条件注入伪装成生产级 WSI diffusion generator。

## v0.32.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 condition packet 从 smoke-cascade 记录链路扩展到 PyTorch diffusion smoke sampling/generation：让 `sample-torch-diffusion-smoke` 和 `run-generation --backend torch-diffusion-smoke` 可以显式消费并记录同一个 `generation_condition_packet`。

### 结构化需求

- 版本号升级为 `v0.32.0`。
- `sample_torch_diffusion_smoke_model` 新增可选 `condition_packet_path` 参数，并在 `sample_manifest.json` 中记录 `condition_packet_path` 与 `condition_summary`。
- `run_torch_diffusion_smoke_generation` 新增可选 `condition_packet_path` 参数，并将该参数传给 PyTorch smoke sampler。
- CLI `sample-torch-diffusion-smoke` 新增可选 `--condition-packet` 参数。
- CLI `run-generation --backend torch-diffusion-smoke` 必须复用已有 `--condition-packet` 参数，并传给 PyTorch diffusion smoke generation。
- PyTorch diffusion smoke sampling/generation 必须读取并校验 condition packet JSON：schema version、condition packet type、必要条件对象必须存在。
- 在 generation backend 中，condition packet 的 `prior_id` 必须与当前 prior manifest 的 `prior_id` 一致；不一致时显式报错。
- Metadata 的 `generation` 字段、`generation_run.json` 和 sampler 的 `sample_manifest.json` 必须记录 condition packet 路径与同一份条件摘要。
- 当未提供 condition packet 时，保持现有 PyTorch diffusion smoke 行为，不静默伪造条件包。
- 新增/更新测试覆盖 sampler 直接调用、generation 直接调用、CLI 行为、metadata/run summary/sample manifest 记录和 prior id mismatch 错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只让 PyTorch diffusion smoke 链路消费并记录 condition packet，用于把条件包推进到更接近真实采样的工程路径。
- 本次版本不改变 diffusion smoke 模型结构，不实现生产级 layout/style/texture 条件注入，也不把 smoke checkpoint 标记为 production inference 权重。
- 后续仍需实现真正消费 layout/style/texture/source 条件的 latent diffusion U-Net、VAE latent、采样器和多倍率一致性训练。

## v0.31.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 v0.30.0 条件包与生成执行链路的连接：让 `run-generation --backend smoke-cascade` 可以显式消费 `generation_condition_packet`，并把条件包路径与关键条件摘要写入 metadata 和 generation run summary。

### 结构化需求

- 版本号升级为 `v0.31.0`。
- `run_smoke_generation` 新增可选 `condition_packet_path` 参数。
- CLI `run-generation` 新增可选 `--condition-packet` 参数，传给 smoke backend。
- Smoke generation 必须读取并校验 condition packet JSON：schema version、condition packet type、prior id、必要条件对象和 prior manifest 关系必须一致。
- 条件包 prior id 与当前 prior manifest 的 `prior_id` 不一致时必须显式报错。
- Metadata 的 `generation` 字段必须记录 `condition_packet_path` 和 `condition_summary`，摘要至少包含 cascade level、tile origin、style seed value/source、texture cluster id、source condition enabled 和 structure anchor。
- `generation_run.json` 必须记录同样的 condition packet 路径和摘要，便于批量任务审计。
- 当未提供 condition packet 时，保持现有 smoke backend 行为，不静默伪造条件包。
- 新增/更新测试覆盖直接函数调用消费 condition packet、CLI `--condition-packet` 行为、metadata/run summary 记录和 prior id mismatch 错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只让 smoke generation 执行链路消费并记录已存在的 condition packet，用于打通条件包到生成记录的审计链路。
- 本次版本不实现 production latent diffusion 条件注入，不让 PyTorch diffusion smoke sampler 真实使用 layout/style/texture 条件，也不改变 smoke backend 的非生产性质。
- 后续仍需让 PyTorch/production backend 基于条件包执行真实条件采样，并逐步实现 VAE latent、U-Net sampler、多倍率一致性和 WSI consistency fine-tuning。

## v0.30.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 6.3 的 prior 与生成模型连接：把 `prior_manifest.json` 和 generation config 解析为可审计的 generation condition packet，使 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 不再只停留在 generation plan 的字符串列表中。

### 结构化需求

- 版本号升级为 `v0.30.0`。
- 新增 `build_generation_condition_packet`，输入为 generation config、prior manifest、输出路径、cascade level 和 40x tile 坐标。
- Builder 必须复用 `validate_generation_config` 和 `load_prior_manifest`，不得绕过既有 schema、artifact hash 和文件存在校验。
- Builder 必须读取四类 artifact JSON，并校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type` 和 `qc_reference_distribution` 的 `source`。
- 输出 JSON 必须包含 schema version、condition packet type、created time、prior id、prior manifest path、generation config summary 和完整条件对象。
- 条件对象必须显式包含 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor`。
- `style_seed=auto` 时必须采用可复现的 deterministic 解析规则并记录来源；整数 style seed 必须原样记录。
- `texture_token` 必须从 `texture_prior.texture_prototypes` 中按 random seed 做确定性选择，记录 cluster id、selection policy 和 representative embedding index。
- `coord` 必须记录 cascade level、40x tile origin、tile size 和 max magnification，并拒绝非法 cascade level 或负坐标。
- `source_condition` 必须明确记录是否启用；source-anchored generation 继续依赖 generation config 校验要求 `source_wsi_id`。
- CLI 新增 `build-condition-packet`，支持 generation config、`--prior-manifest`、`--output`、`--cascade-level`、`--tile-origin-x` 和 `--tile-origin-y`。
- 缺失 artifact、artifact 非 JSON、artifact 类型不匹配、缺失 texture prototypes、非法坐标、source-anchored 缺 source 等错误必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、condition packet 字段、auto style seed 解析、texture token 选择和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现可审计的条件包 JSON，用于把 prior artifact 与后续训练/生成接口连接起来。
- 本次版本不实现 production latent diffusion 条件注入、可采样 layout generator、style latent encoder、真实 texture sampler、source image encoder 或 WSI consistency fine-tuning。
- 后续仍需让 PyTorch/production 生成 backend 消费该条件包，并逐步替换当前 smoke/proxy 生成链路。

## v0.29.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 prior artifact 汇总能力：把已经可独立生成的 `layout_mask_prior`、`style_prior`、`texture_prior` 和 `qc_reference_distribution` JSON 组装为统一、可校验、可复现的 `prior_manifest.json`，减少后续 generation/training 入口对手工 manifest 编写的依赖。

### 结构化需求

- 版本号升级为 `v0.29.0`。
- 新增 `build_prior_manifest_from_artifacts`，输入为输出目录、prior id、dataset id、输入 manifest 路径、训练数据版本、WSI id 列表、随机种子和四类 prior artifact 路径。
- Builder 必须复用既有 `create_prior_artifact_entry`、`save_prior_manifest` 和 `load_prior_manifest`/校验契约，写出 `prior_manifest.json`。
- Builder 必须读取 artifact JSON，校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type` 与 artifact 类型一致，并校验 `qc_reference_distribution` 来源为 QC reference distribution。
- 输出 manifest 必须记录 schema version、prior id、created_at、random seed、input data、WSI ids、四类 artifact 的 path/kind/sha256/size_bytes/metadata。
- Artifact metadata 必须记录 artifact type、artifact schema version，以及能从源 JSON 中直接审计的关键摘要字段。
- CLI 新增 `build-prior-manifest`，支持 `--output-dir`、`--prior-id`、`--dataset-id`、`--input-manifest`、`--training-data-version`、可重复 `--wsi-id`、`--random-seed` 和四类 artifact 路径参数。
- 缺失 artifact、artifact 非 JSON、artifact 类型不匹配、缺失 WSI id、非法 random seed、重复 artifact 路径或 hash/size 不一致必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、manifest roundtrip 校验、artifact metadata 摘要和 artifact 类型不匹配错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 prior artifact manifest 汇总与校验，不实现 layout/style/texture 的采样策略。
- 本次版本不把统计 prior 接入 production latent diffusion 条件注入，也不实现 trainable prior model、source-anchor layout mixing 或 tile-level texture sampler。
- 后续仍需把 `prior_manifest.json` 接入更完整的训练/生成工作流，并逐步实现可采样 layout、style seed sampler、texture condition selector 和 production inference backend。

## v0.28.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 `texture_prior` 落地：从 embedding cache 和 cluster report 中读取真实 patch embedding 与聚类标签，估计可追溯的 cluster-level texture prototype 统计，输出可作为 prior manifest `texture_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.28.0`。
- 新增 `build_texture_prior_from_embedding_cache`，输入为 embedding cache 目录、cache key、cluster report JSON、输出路径。
- Texture prior builder 必须通过 `load_embedding_cache` 读取真实 embedding array 和 metadata，不得静默构造假 embedding。
- Builder 必须校验 cluster report 的 `labels` 数量与 embedding row count 一致，`embedding_dim` 与 embedding metadata/array 一致，cluster count 与 labels 一致。
- 输出 JSON 必须包含 schema version、prior type、created time、source cache dir/cache key、embedding metadata、cluster report summary、embedding count、embedding dim、cluster count 和 texture prototype records。
- 每个 texture prototype record 必须记录 cluster id、sample count、fraction、mean embedding、embedding std 和 representative embedding index。
- 输出 JSON 必须记录 global embedding mean/std，用于后续 texture/morphology prior 条件和 non-copy/global similarity 报告复用。
- CLI 新增 `build-texture-prior`，支持 `--cache-dir`、`--cache-key`、`--cluster-report` 和 `--output`。
- 缺失 cache、cluster report 非 JSON、labels 数量不匹配、embedding dim 不匹配、非法 cluster count、非有限 embedding 等错误必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、prototype 统计、global embedding 统计、metadata 记录和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于 embedding/cluster 的统计型 `texture_prior` JSON，作为 texture/morphology prior 的可审计工程基础。
- 本次版本不实现 trainable texture codebook、VQ-VAE、morphology token sampler、区域特异纹理生成器或 production diffusion 条件注入。
- 后续仍需把该 texture prior 接入真实图像生成训练、mask 区域条件、tile-level texture conditioning 和 non-copy/global similarity QC。

## v0.27.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 `layout_mask_prior` 落地：从 training-index 中真实读取 6 类 mask tile，估计可追溯的全局类别比例、tile 级 layout 分布和相邻类别计数，输出可作为 prior manifest `layout_mask_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.27.0`。
- 新增 `build_layout_mask_prior_from_training_index`，输入为 training-index JSONL、输出路径、batch size、split 和 cascade level。
- Layout/mask prior builder 必须通过 `load_training_batch(..., include_image=False)` 读取真实 mask tile，不得依赖图像 tile 或构造假 mask。
- 输出 JSON 必须包含 schema version、prior type、created time、source training-index、batch size、split、cascade level、sample ids、WSI ids、tile records、mask batch shape 和 mask class ids。
- 输出 JSON 必须记录项目 6 类名称、每类 pixel count、fraction、present flag、non-background tissue fraction 和 tile-level dominant class。
- 输出 JSON 必须记录 tile-level class fractions 和 source WSI id，用于审计 layout/mask prior 是否来自真实训练 mask tile。
- 输出 JSON 必须记录横向/纵向相邻类别 pair counts，作为后续 layout/mask prior 学习邻接关系的统计基础。
- CLI 新增 `build-layout-mask-prior`，支持 `--batch-size`、`--split`、`--cascade-level` 和 `--output`。
- 缺失 mask、非法 batch size、空匹配样本、未知 split/level、mask 维度非法或 label mapping 不完整等错误必须沿用 training batch loader 的显式错误路径，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、统计字段、tile-level layout records、adjacency counts、summary 不写入完整 mask batch，以及错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于真实 mask tile 的统计型 `layout_mask_prior` JSON，作为 de novo layout/mask prior 的可审计工程基础。
- 本次版本不实现可采样 layout generator、mask diffusion、VQ-VAE、空间生成模型、跨 WSI 结构扰动或 source-anchor layout mixing。
- 后续仍需把该 layout/mask prior 接入真实 layout 采样、生成条件构造和 production inference backend。

## v0.26.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4/M5 之间的 `global_imaging_style_prior` 落地：从 training-index 中真实读取 RGB tile，估计可追溯的 slide/tile 级成像风格统计，并输出可作为 prior manifest `style_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.26.0`。
- 新增 `build_style_prior_from_training_index`，输入为 training-index JSONL、输出路径、batch size、split 和 cascade level。
- Style prior builder 必须通过 `load_training_batch(..., include_image=True)` 读取真实 RGB image tile，不得只依赖 mask 或静默构造假图像。
- 输出 JSON 必须包含 schema version、prior type、created time、source training-index、batch size、split、cascade level、wsi ids、sample ids、tile records、image batch shape/dtype 和 RGB 统计。
- RGB 统计至少包含 per-channel mean、standard deviation、min、max，以及归一化到 `[0, 1]` 的 mean/std，供后续 generation style seed 与 QC 阈值复用。
- 输出 JSON 必须包含每个样本的 tile-level mean RGB 和 source WSI id，用于审计 global style prior 是否来自真实训练 tile。
- CLI 新增 `build-style-prior`，支持 `--batch-size`、`--split`、`--cascade-level` 和 `--output`。
- 缺失 WSI、无法读取 RGB tile、非法 batch size、空匹配样本、未知 split/level 等错误必须沿用 training batch loader 的显式错误路径，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、统计字段、tile-level style records、summary 不写入完整 image batch，以及错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于真实 RGB tile 的统计型 `style_prior` JSON，作为 `global_imaging_style_prior` 的可审计工程基础。
- 本次版本不实现 trainable style encoder、VAE style latent、stain normalization、style sampling policy、风格迁移模型或 production diffusion 条件注入。
- 后续仍需把该 style prior 接入真实 generation backend 的 style conditioning、同 WSI 风格一致性训练和更完整 QC reference 统计。

## v0.25.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进完整生成输出链路：在已有 PyTorch diffusion smoke sampler 基础上，新增 `torch-diffusion-smoke` generation backend，使 PyTorch sampler 输出能够进入 OME-TIFF、mask、metadata、QC 和 batch index 归档链路。

### 结构化需求

- 版本号升级为 `v0.25.0`。
- 新增 `run_torch_diffusion_smoke_generation`，输入为 generation config、prior manifest、diffusion smoke checkpoint manifest、training-index、输出目录、generated id 和 batch size。
- CLI `run-generation` 新增 backend 选择 `torch-diffusion-smoke`。
- `torch-diffusion-smoke` backend 必须要求 `--training-index`，用于提供 mask 条件；缺失时必须显式报错。
- Backend 必须调用 `sample_torch_diffusion_smoke_model`，复用 diffusion smoke checkpoint 和 generation config 中的 `sample_steps` / `random_seed`。
- Backend 必须从 sampler 输出的 `sample_preview.npy` 构造四层小型 pyramid：`1/1`、`1/4`、`1/16`、`1/32`。
- Backend 必须从 training-index batch 读取 mask，并写出与 `1/1` 输出尺寸一致的 `.npy` mask。
- Backend 必须复用现有 `write_pyramid_ome_tiff`、`write_mask_array`、`build_qc_report` 和 `archive_sample`，写出 OME-TIFF、mask、metadata、QC、batch index 和 generation run summary。
- Metadata 必须记录 `generation_backend=torch-diffusion-smoke`、checkpoint、prior、cascade、sample steps 和输出路径。
- QC non-copy report 必须记录该 backend 是 PyTorch diffusion smoke backend，不是 production WSI diffusion generator。
- Backend 不得把 diffusion smoke checkpoint 改成 `usable_for_inference=true`，不得伪装为 production inference。
- 新增/更新测试覆盖直接函数调用和 CLI 行为，验证 metadata、QC、batch index、sample manifest、OME-TIFF pyramid shape 和 backend 标记。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只把 PyTorch diffusion smoke sampler 接入完整输出归档链路，输出仍来自下采样 RGB proxy preview resize。
- 本次版本不实现真实 VAE decode、production sampler、multi-resolution cascade diffusion inference、tile stitching、gigapixel chunked OME-TIFF 或 WSI consistency fine-tuning。
- 后续仍需把真实模型主干、VAE latent、采样器和跨倍率条件接入 `run-generation` 的 production backend。

## v0.24.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进推理/采样链路：在已有 DDPM-style diffusion smoke trainer 基础上，新增一个可审计的 PyTorch diffusion smoke sampler，用于验证 checkpoint 加载、mask 条件输入、反向 DDPM-style 采样和 preview 输出链路。

### 结构化需求

- 版本号升级为 `v0.24.0`。
- 新增 `sample_torch_diffusion_smoke_model`，输入为 diffusion smoke checkpoint manifest、training-index JSONL、输出目录、batch size、split、cascade level、sample steps、random seed 和 device。
- 新增 CLI `sample-torch-diffusion-smoke`，用于从 diffusion smoke checkpoint 和 training-index mask 条件执行一次可审计 proxy latent sampling。
- Sampler 必须只接受 `training_backend=torch-smoke-mask-conditioned-latent-diffusion` 且 `target_type=diffusion_noise` 的 diffusion smoke checkpoint；其它 checkpoint 必须显式报错。
- Sampler 必须读取 checkpoint payload、恢复 denoiser `state_dict`、复用 manifest/payload 中的 `linear_ddpm` schedule 与 `rgb_downsample_proxy` latent shape。
- Sampler 必须通过 `load_training_batch(..., include_image=False)` 读取 mask 条件，不得要求 RGB target，也不得静默忽略 mask。
- 采样输入必须包含当前 latent、下采样 6 类 mask 条件和 timestep channel；采样过程必须执行反向 DDPM-style 更新。
- 输出必须包含 `sample_preview.npy` 和 `sample_manifest.json`。
- `sample_manifest.json` 必须记录 sampling backend、checkpoint manifest/path、checkpoint training backend、training-index、sample path、sample shape、dtype、sample steps、random seed、diffusion schedule、batch summary，并明确 `usable_for_production=false`。
- Sample manifest 的 batch summary 不得写入完整 `mask_batch` 数组。
- 非法 sample steps、sample steps 超过 diffusion timesteps、checkpoint 缺失/不匹配、state_dict 缺失、diffusion schedule 非法、缺失 mask 或 PyTorch/numpy 缺失时必须显式报错。
- 新增/更新测试覆盖直接函数调用、CLI 行为、preview `.npy` shape/dtype、sample manifest 字段、checkpoint backend 校验和 non-production 标记。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证 reverse DDPM-style mechanics 和 mask-conditioned sampling 工程链路，输出是下采样 RGB proxy latent preview。
- 本次版本不把 diffusion smoke checkpoint 改为 `usable_for_inference=true`，不接入 `run-generation`，不输出 OME-TIFF，不实现 production latent diffusion sampler 或 VAE decoder。
- 后续仍需实现可生产的模型主干、VAE latent、真实 sampler、multi-resolution cascade inference、tile stitching、OME-TIFF 写出和 QC/metadata 归档。

## v0.23.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M5 中的 latent diffusion 训练目标：在已有 RGB training batch 与 PyTorch smoke training 基础上，新增一个真实执行 DDPM-style 加噪和噪声预测 loss 的 mask-conditioned latent diffusion smoke trainer。

### 结构化需求

- 版本号升级为 `v0.23.0`。
- 新增 `train_torch_diffusion_smoke_model`，输入为 training-index JSONL、输出目录、batch size、split、cascade level、epochs、learning rate、random seed、device、diffusion timesteps、beta schedule 和 latent size。
- 新增 CLI `train-torch-diffusion-smoke`，用于从 training-index 执行一次可审计的 PyTorch diffusion smoke training。
- Trainer 必须通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch，不得回退到只读 mask。
- 训练必须构造下采样 RGB proxy latent，记录 `latent_source=rgb_downsample_proxy`，避免伪装成 VAE latent。
- 训练必须实现线性 DDPM smoke schedule，记录 `scheduler=linear_ddpm`、`timesteps`、`beta_start`、`beta_end` 和 `latent_batch_shape`。
- 训练输入必须包含 noisy RGB proxy latent、下采样 6 类 mask 条件和 timestep channel；训练目标必须为加入的噪声，loss 名称为 `mse_noise_prediction`。
- Trainer 必须继续真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 checkpoint 写出。
- `model.pt` payload 必须记录 `target_type=diffusion_noise`、`input_channels=10`、`output_channels=3`、diffusion schedule、mask classes、cascade level、random seed 和 loss history。
- `checkpoint_manifest.json` 必须记录 target type、输入/输出通道、diffusion schedule、training parameters、image batch summary、loss summary、torch version、checkpoint hash，并保持 `usable_for_inference=false`。
- Manifest 的 batch summary 必须包含 `image_batch_shape` 和 `image_dtype`，不得写入完整 `image_batch` 或 `mask_batch` 数组。
- 非法 diffusion timesteps、latent size、beta schedule、缺失 WSI、图像不可读、tile 越界或 PyTorch 缺失时必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、backend 名称、diffusion target、scheduler、latent shape、checkpoint payload、image batch summary 和 finite loss。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证真实 DDPM-style noise prediction 训练机制进入工程链路；latent 是下采样 RGB proxy，不是训练好的 VAE latent。
- 本次版本不实现完整 latent diffusion U-Net、VAE encoder/decoder、生产级噪声调度和采样器、多倍率 cross-scale condition、style latent、source anchor 条件、WSI 一致性微调或真实 inference backend。
- 本次 diffusion smoke checkpoint 仍不可用于 `run-generation` 的真实 diffusion inference；后续仍需实现 production dataset、模型主干、采样器、VAE latent 与生成执行 backend。

## v0.22.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 PyTorch 训练链路：把 `train-torch-smoke` 从只训练 mask autoencoder，升级为消费 RGB image tile 的 mask-conditioned RGB reconstruction smoke backend，使训练 loop 开始学习 mask 条件到 H&E 图像像素的映射。

### 结构化需求

- 版本号升级为 `v0.22.0`。
- `train_torch_smoke_model` 必须通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch。
- 训练输入必须为 6 类 mask one-hot tensor，训练目标必须为归一化到 `[0, 1]` 的 RGB image tile tensor。
- Smoke backend 名称升级为 `torch-smoke-mask-conditioned-rgb-reconstructor`，避免继续把产物描述为 mask autoencoder。
- Trainer 必须继续真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 checkpoint 写出；loss 使用明确的 RGB reconstruction MSE。
- `model.pt` payload 必须记录 `target_type=rgb_image`、`input_channels=6`、`output_channels=3`、`image_dtype`、mask classes、cascade level、random seed 和 loss history。
- `checkpoint_manifest.json` 必须记录 target type、输入/输出通道、loss 名称、image batch summary、torch version、training parameters、loss summary、checkpoint hash，并保持 `usable_for_inference=false`。
- Manifest 的 batch summary 必须包含 `image_batch_shape` 和 `image_dtype`，不得写入完整 `image_batch` 或 `mask_batch` 数组。
- CLI `train-torch-smoke` 继续使用原命令入口，但输出 manifest/backend 语义必须反映 RGB reconstruction smoke training。
- 缺失 WSI、图像不可读、tile 越界等 image batch 读取失败必须通过既有显式错误路径暴露，不得静默回退到只训练 mask。
- 新增/更新测试覆盖真实 fixture RGB slide 参与训练、backend 名称、target type、输入/输出通道、image batch summary、checkpoint payload 和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现最小可审计的 RGB reconstruction smoke training，用于验证图像目标进入 PyTorch 训练链路。
- 本次版本不实现完整 latent diffusion U-Net、VAE latent 编码、噪声调度、扩散去噪目标、多倍率条件注入、style latent、source anchor 训练、WSI 一致性微调或真实可推理生成权重。
- 本次 smoke checkpoint 仍不可用于 `run-generation` 的真实 diffusion inference；后续仍需实现 production dataset、latent diffusion loss、sampler 和推理 backend。

## v0.21.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实图像训练输入能力：在 training batch loader 中新增可选 RGB image tile 读取，使后续 PyTorch 图像生成训练不再只有 mask 条件输入。

### 结构化需求

- 版本号升级为 `v0.21.0`。
- `load_training_batch` 新增 `include_image` 参数；默认保持只读 mask，显式启用时读取 WSI/fixture 图像 tile。
- 图像 tile 读取必须使用 training-index 中的 `wsi_path`、tile 坐标和 source backend。
- 对 `fixture-image` backend，读取 PNG/TIFF 等小图并裁剪 RGB tile；对 `openslide` backend，使用 OpenSlide `read_region` 读取 level0 tile 并转为 RGB。
- Loader 输出新增 `image_batch`、`image_batch_shape` 和 `image_dtype`；summary 必须排除完整 `image_batch` 数组，只保留形状和 dtype。
- 缺失 WSI 文件、图像不可读、tile 超出图像范围、未知 backend 或 OpenSlide 缺依赖时必须显式报错。
- CLI `inspect-training-batch` 新增 `--include-image` 参数，用于训练前同时审计 mask 和 RGB tile 输入。
- 新增测试覆盖 fixture image tile 读取、summary 不写完整 image batch、缺失 WSI 报错和 CLI `--include-image` 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只读取训练输入 RGB tile，不实现真实 VAE latent 编码、归一化策略搜索、颜色增强、stain normalization 或 OpenSlide 多层降采样采样策略。
- 后续 PyTorch trainer 仍需把 image batch 接入真实图像重建/扩散损失；本次只让输入数据链路具备图像 tile。

## v0.20.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实 PyTorch 训练 backend：在既有 training-index batch loader 基础上，新增一个真实调用 PyTorch 的 smoke training backend，用于验证训练 loop、loss、optimizer、checkpoint 写出和 manifest 记录链路。

### 结构化需求

- 版本号升级为 `v0.20.0`。
- 新增 PyTorch smoke trainer，输入为 training-index JSONL、输出目录、batch size、epochs、learning rate、split 和 cascade level。
- Trainer 必须显式要求 PyTorch；未安装 torch 时必须清晰报错，不得静默回退到 numpy。
- Trainer 必须复用 `load_training_batch` 读取 batch，将 mask batch 转为 torch tensor，并执行真实 `torch.nn.Module`、loss、optimizer 和反向传播。
- Trainer 必须写出 `model.pt`、`training_log.jsonl` 和 `checkpoint_manifest.json`。
- Checkpoint manifest 必须包含 schema version、model family、status、usable_for_inference、model version、training backend、torch version、训练参数、loss summary、checkpoint path/hash 和明确边界说明。
- Smoke trainer 产物不得伪装成真实 latent diffusion 推理权重；`usable_for_inference` 必须为 `false`。
- 新增 CLI `train-torch-smoke`，用于从 training-index 执行一次可审计 PyTorch smoke training。
- 新增测试覆盖 PyTorch smoke trainer 产物、manifest 可校验、CLI 行为；在无 torch 环境中测试应跳过真实 torch 用例。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证真实 PyTorch 训练 loop、loss、optimizer 和 checkpoint 写出，不实现完整 latent diffusion U-Net、噪声调度、VAE latent、图像重建、WSI 一致性训练或真实可推理生成权重。
- 本次 smoke checkpoint 不可用于 `run-generation` 的真实推理；后续仍需实现 production PyTorch dataset、真实图像/latent 输入、扩散损失、采样器和 inference backend。

## v0.19.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实 PyTorch 训练 backend 的前置输入能力：新增 training-index batch loader，使后续训练 loop 可以从 JSONL 样本索引读取、校验、抽样并形成可审计 batch，而不是只停留在索引文件。

### 结构化需求

- 版本号升级为 `v0.19.0`。
- 新增 training batch loader，输入为 training-index JSONL 路径、batch size 和可选 split/cascade level。
- Loader 必须逐行解析 JSONL，显式拒绝空文件、非法 JSON、缺失字段、非法 batch size、未知 split、未知 cascade level、mask 文件缺失、mask 维度非法和 tile 超出 mask 范围。
- Loader 必须读取 `.npy` mask，按 training-index 中的 tile 坐标裁剪 batch mask，并将原始 mask 编号按 label mapping 转为项目 6 类 id。
- Loader 输出必须包含 schema version、batch size、sample ids、cascade levels、WSI ids、tile records、mask batch shape、mask class ids、conditioning 摘要和 source records。
- 新增 CLI `inspect-training-batch`，用于从 training-index 读取一个 batch 并输出 batch summary JSON，供训练前审计和后续 UI 调用。
- 新增测试覆盖 batch summary 写出、split/level 过滤、缺失 mask 报错和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现训练输入 batch loader 和审计 summary，不实现 PyTorch Dataset/DataLoader、GPU tensor 转换、latent diffusion 训练 loop、loss 计算或 checkpoint 权重更新。
- 由于当前环境未安装 PyTorch，本轮不得伪装真实 PyTorch backend 已完成；后续需在隔离环境中安装并验证 torch 后继续实现真实模型训练。

## v0.18.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 PySide6 本地控制台所需的长任务调度基础：新增可持久化本地 job runner，使 CLI/core 工作流能被排队、同步执行、记录 stdout/stderr、保存状态和结果，供 UI 后续调用。

### 结构化需求

- 版本号升级为 `v0.18.0`。
- 新增本地 job runner，支持创建 job、状态持久化、执行命令、记录 stdout/stderr、保存 return code 和时间戳。
- Job 状态必须使用既有 UI 状态集合：`queued`、`running`、`completed`、`failed`、`cancelled`。
- 空 job id、空命令、重复 job id、未知 job id 和非法状态必须显式报错。
- 执行成功时状态为 `completed`，命令返回非零或启动失败时状态为 `failed`，不得静默吞掉失败或留下 stale `running` 状态。
- 新增 CLI `run-local-job`，用于创建并同步执行一个本地命令 job，输出 job record 路径和最终状态。
- 新增测试覆盖成功 job、非零退出 job、命令启动失败、重复 job 拒绝和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现同步本地 job runner，不实现后台 daemon、进程取消、并发队列、跨机器调度或 PySide6 事件循环集成。
- 后续 UI 可通过该 job runner 触发已有 CLI/core 命令，但本次不实现完整图形界面按钮绑定。

## v0.17.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 `qc_reference_distribution` 的自动生成能力：从一组训练/参考 QC JSON 抽取数值 metrics，估计区间阈值并输出可作为 prior artifact 使用的 reference distribution JSON。

### 结构化需求

- 版本号升级为 `v0.17.0`。
- 新增 QC reference builder，输入为多个 QC report、metric 名称列表、输出 JSON 路径和最小样本数。
- Builder 必须复用现有 QC schema 校验，显式拒绝空输入、空 metric 列表、非法 min samples、缺失 metric 和样本数不足。
- 输出 JSON 必须包含 schema version、创建时间、来源、总样本数和 `metrics` 对象。
- 每个 metric 必须记录 `warning_min`、`warning_max`、`fail_min`、`fail_max`、`sample_count`、observed min/max 和 estimator 名称。
- 新增 CLI `build-qc-reference`，支持多个 QC JSON 输入、可重复 `--metric`、`--min-samples` 和 `--output`。
- 新增测试覆盖 reference distribution 写出、缺失 metric 报错和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本使用 observed min/max 与 range margin 的确定性估计器，不实现 IQR、稳健 z-score、分层组织/疾病阈值或自动异常样本剔除。
- 输入 QC report 的可信度仍由用户或训练数据准备流程保证；builder 不判断 QC report 是否来自真实训练集。
- 后续仍需把该 builder 接入完整 prior learning workflow，并从真实 WSI 训练集批量生成 QC metrics。

## v0.16.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进自动 QC 的训练分布自适应阈值能力：让 QC engine 使用 prior artifact 中的 `qc_reference_distribution` 对已计算指标进行 warning/fail 判定，而不是只使用固定规则。

### 结构化需求

- 版本号升级为 `v0.16.0`。
- QC engine 新增可选 `qc_reference_distribution` 输入，格式为 `{"metrics": {"metric_name": {"warning_min": number, "warning_max": number, "fail_min": number, "fail_max": number}}}`。
- 对支持的数值指标，QC 应优先使用 reference distribution 阈值：低于 `fail_min` 或高于 `fail_max` 为 `fail`，低于 `warning_min` 或高于 `warning_max` 为 `warning`，否则为 `pass`。
- 被 reference distribution 判定的 metric 必须记录 reference threshold 信息，便于用户解释 warning/fail 来源。
- reference distribution 格式非法、阈值非数值或边界顺序不合法时必须显式报错。
- `run-generation` 应从 prior manifest 的 `qc_reference_distribution` artifact 自动加载 JSON 并传入 QC engine。
- 新增测试覆盖 reference 阈值 warning/fail、非法阈值报错、端到端生成使用 prior reference。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只支持 JSON reference distribution 和简单区间阈值，不实现 IQR、稳健 z-score 或分层组织/疾病阈值。
- 本次版本不做训练分布估计，只消费已经存在的 `qc_reference_distribution` artifact。
- 后续仍需实现从真实训练集统计生成 reference distribution 的 prior learner。

## v0.15.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进自动 QC 的真实指标能力：从只检查文件存在，扩展为读取生成 OME-TIFF 和 mask，输出 WSI/tile/mask-region 三级可解释指标，为后续真实生成样本筛选建立基础。

### 结构化需求

- 版本号升级为 `v0.15.0`。
- QC engine 必须读取 OME-TIFF pyramid 首层，记录可读性、实际 level count、RGB 均值和动态范围。
- QC engine 必须计算轻量 tile 质量指标，至少包含清晰度 proxy 和 tile proxy 样本数。
- QC engine 必须读取 `.npy` mask，记录 mask 可读性、出现类别数量、类别 id 列表、组织占比和 mask 与 WSI 首层尺寸是否一致。
- OME-TIFF 不可读、mask 不可读、mask 维度非法或 mask 与 WSI 尺寸不一致时，QC 必须显式 fail。
- 对低动态范围、空组织比例等非硬错误场景可给 warning，不静默通过。
- 新增测试覆盖真实 OME-TIFF/mask 指标写入和 mask-WSI 尺寸错位 fail。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本仍不实现训练分布自适应阈值，只提供确定性 smoke/规则指标。
- 本次版本不做真实病理质量判定，不替代专家评价或下游验证。
- 后续仍需接入 prior 中的 `qc_reference_distribution`，并补充颜色离群、seam、style consistency、mask 区域比例等训练分布阈值。

## v0.14.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实训练 backend 的前置能力：把输入 manifest、manifest audit 和 label mapping 转成四层 cascade training-index JSONL，使后续 PyTorch latent diffusion 训练 loop 有可审计的训练样本输入，而不是只引用一个未定义路径。

### 结构化需求

- 版本号升级为 `v0.14.0`。
- 新增 training index builder，输入为 input manifest、manifest audit、一个或多个 label mapping、输出 JSONL 路径。
- Training index builder 必须复用现有 schema 校验，拒绝非法 manifest、非法 label mapping、缺失 audit record、audit status 非 `ok`、缺失可训练 mask annotation、缺失匹配 label mapping、mask 文件不存在和无法切出完整 40x tile 的输入。
- 每条 JSONL 记录必须包含 dataset、WSI、split、cancer type、cascade level、40x tile 坐标、source metadata、mask annotation、6 类 label mapping 和 conditioning 约定。
- 对每个可训练 40x tile 写出 `1/32`、`1/16`、`1/4`、`1/1` 四层记录，保持与生成模型级联训练顺序一致。
- 新增 CLI `build-training-index`，支持 `--audit`、可重复 `--label-mapping` 和 `--output`。
- 新增测试覆盖 training index 写出、缺失 label mapping 拒绝和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本不执行真实 PyTorch 训练，也不产生可推理模型权重。
- Training index 仅建立可审计训练样本输入；后续仍需实现真实 dataset loader、latent diffusion U-Net、训练 loop、checkpoint 权重保存和真实推理 backend。
- 当前 tile 采样采用非重叠完整 512x512 40x tile；不处理 partial tile、组织区域过滤、hard negative 采样或 class-balanced sampler，以避免在无真实训练数据时过度设计。

## v0.13.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进完整核心系统中的“可运行生成任务”缺口：在现有 M1-M7 契约、prior、checkpoint、OME-TIFF、mask、metadata、QC 和 batch index 基础上，新增一个明确标记的端到端 smoke generation backend，用于验证生成任务可以产出完整 WSI 数据对象。

### 结构化需求

- 版本号升级为 `v0.13.0`。
- 新增 generation executor，接收 generation config、prior manifest、trained checkpoint manifest、output root 和 generated id。
- Executor 必须复用现有 generation plan 校验，拒绝未训练 checkpoint、缺失 prior artifact 或非法 generation config。
- 新增 `smoke-cascade` backend，按 `1/32 -> 1/16 -> 1/4 -> 1/1` 生成可审计的四层小型 cascade 输出，并写出 OME-TIFF pyramid。
- 生成输出必须包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`batch.jsonl` 和 generation run summary。
- Metadata 必须记录 backend 为 `smoke-cascade`，避免把 smoke backend 伪装为真实 PyTorch diffusion 生成。
- 新增 CLI `run-generation`，要求显式选择 `--backend smoke-cascade`，并写出完整生成样本目录。
- 新增测试覆盖端到端生成输出、未训练 checkpoint 拒绝和 CLI 生成行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本不实现真实 PyTorch latent diffusion 训练或推理；`smoke-cascade` 只用于端到端工程链路验证。
- 本次版本不声称生成图像具有病理真实性，不替代真实模型 checkpoint。
- 后续仍需实现真实训练 backend、真实推理 backend、训练分布自适应 QC 指标和生产级 gigapixel 写出，才能满足完整 H&E WSI 生成器完成标准。

## v0.12.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M7：PySide6 本地单页控制台，为数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出查看建立 UI 配置与控制层。

### 结构化需求

- 版本号升级为 `v0.12.0`。
- 新增 UI 配置对象，覆盖数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出区域。
- 新增 UI job config 保存/读取能力，确保 UI 产生的配置可被 CLI/core 复现。
- 新增任务状态管理，支持 `queued`、`running`、`completed`、`failed`、`cancelled`，非法状态需显式报错。
- 新增输出摘要读取能力，从 metadata/QC JSON 中提取 generated id、QC 状态和核心输出路径。
- 新增 PySide6 单页控制台模块；若 PySide6 未安装，启动 UI 时必须明确报错。
- 新增 CLI `write-ui-config` 和 `launch-ui`。
- 新增测试覆盖 UI config roundtrip、任务状态转换、输出摘要、CLI config 写出和 PySide6 缺依赖错误。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不执行真实长任务调度、不在 UI 内训练模型或生成图像；UI 只负责配置、状态和输出查看控制层。
- Core 逻辑仍保留在 `he_wsi_generator` 包内，UI 不应绕过 CLI/core 直接实现业务处理。
- 当前环境未安装 PySide6 时，`launch-ui` 应失败并给出可操作错误，而不是静默跳过。

## v0.11.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M6：OME-TIFF 与 QC，建立小尺寸 pyramid 写出、QC JSON 和 batch JSONL 归档基础。

### 结构化需求

- 版本号升级为 `v0.11.0`。
- 新增 pyramid OME-TIFF smoke writer，使用 `tifffile` 写出多层 pyramid TIFF，并验证层级尺寸。
- 新增 mask 输出基础能力，支持写出 6 类 mask `.npy` 文件与 metadata。
- 新增 QC report builder，输出 WSI/tile/mask-region 三级状态、metrics 和轻量 non-copy report。
- 新增 per-WSI metadata writer，metadata 必须能通过既有 schema 校验。
- 新增 batch JSONL index writer，每行记录 generated sample 的 metadata、QC、WSI、mask 路径和状态。
- 新增 CLI `archive-sample`，用于把已有 WSI/mask/QC/metadata 归档到 batch JSONL。
- 新增测试覆盖 pyramid OME-TIFF smoke 写出与读取、QC JSON 校验、metadata 写出、batch JSONL 追加和 CLI 归档行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本只实现小尺寸 pyramid OME-TIFF smoke writer，不声称支持生产级 gigapixel chunked OME-TIFF。
- 本次版本不执行真实自动图像质量评估，只建立 QC JSON 结构、硬错误检查和可扩展 metrics 契约。
- 本次版本不实现 PySide6 UI，也不生成真实 diffusion tile。

## v0.10.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M5：训练与生成骨架，为后续真实 latent diffusion 训练和级联生成提供可审计入口。

### 结构化需求

- 版本号升级为 `v0.10.0`。
- 新增训练配置与训练 run manifest，记录 model family、prior manifest、training index、random seed、cascade levels、tile size、训练阶段和输出路径。
- 训练骨架必须要求 `latent_diffusion_unet`、四层 cascade、40x、512x512 tile，并校验 prior manifest 文件存在且有效。
- 新增 checkpoint manifest placeholder，明确状态为 `not_trained`，不得伪装成真实可用模型权重。
- 新增 cascade generation plan，基于 generation config、prior manifest 和 checkpoint manifest 输出四层生成顺序、tile traversal、resume index、overlap 和 write mode。
- generation plan 必须拒绝未训练 checkpoint、缺失 prior manifest、非法 cascade 或 source-anchored 配置缺 source。
- 新增 CLI `init-training-run` 和 `plan-generation`，分别生成训练 run manifest 和 generation plan JSON。
- 新增测试覆盖 training manifest、未训练 checkpoint、generation plan、非法 checkpoint 和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、默认配置和版本断言。

### 边界说明

- 本次版本不执行真实 PyTorch 训练，不产生真实模型权重，不生成像素 tile。
- 本次 checkpoint manifest 只用于声明训练入口和状态，不得被视为可用于真实推理。
- 本次版本不实现 OME-TIFF 写出、自动 QC 执行、batch JSONL 归档或 PySide6 UI。

## v0.9.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M4：prior artifact，为 layout/style/texture/QC priors 建立统一 manifest、文件校验和可追溯基础。

### 结构化需求

- 版本号升级为 `v0.9.0`。
- 新增 `priors` 模块，支持 prior artifact manifest 的创建、保存、读取与校验。
- Prior manifest 必须记录 `prior_id`、版本、创建时间、训练输入、随机种子和 artifact 清单。
- Artifact 清单必须覆盖 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`，每项记录路径、kind、sha256、size_bytes 和 metadata。
- 校验 manifest 时必须显式拒绝缺失 artifact、缺失文件、hash 不匹配、非法 seed、非法 artifact type 和重复路径。
- 新增 CLI `validate-prior-manifest`，用于校验 prior manifest 与 artifact 文件完整性。
- 新增测试覆盖 prior manifest roundtrip、缺失必需 artifact、hash mismatch、重复路径和 CLI 校验。
- 同步更新 README、CHANGELOG、VERSION、默认配置和版本断言。

### 边界说明

- 本次版本不实现真实 layout/style/texture/QC prior 学习算法，只建立 artifact 契约和审计校验。
- 本次版本不实现 latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。
- Prior manifest 的文件完整性校验不得静默跳过；如 artifact 文件缺失或 checksum 不一致，必须报错。

## v0.8.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M3：patch embedding 与伪 mask 基础能力，为后续 prior artifact 和聚类伪 mask 工作流提供接口与缓存。

### 结构化需求

- 版本号升级为 `v0.8.0`。
- 新增 `PatchEmbedder` 接口和 embedding result 数据结构。
- 新增 checkpoint-backed embedder：缺少 checkpoint、checkpoint JSON 损坏、embedding 维度非法或输出非有限值时必须显式报错。
- 新增 fixture/smoke embedder，用于小型测试数据，不得伪装成正式 pathology foundation model。
- 新增 embedding cache，支持保存和读取 embedding array 与 metadata，metadata 至少记录 model_id、checkpoint_hash、embedding_dim 和 patch_count。
- 新增轻量 clustering report，支持对 embedding array 生成 cluster labels、cluster counts 和 inertia；空 embedding 或非法 cluster 数需显式报错。
- 新增测试覆盖缺 checkpoint、合法 checkpoint embedding metadata、cache roundtrip、cluster report 和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不绑定任何第三方 pathology foundation model，不下载模型权重，不实现真实伪 mask UI。
- fixture/smoke embedder 只用于开发测试；正式 prior 学习仍需要用户提供 checkpoint。
- 本次版本不实现 prior artifact、latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。

## v0.7.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M2：WSI 与 mask I/O，为后续 patch embedding、prior 学习、训练生成和 QC 建立真实输入基础。

### 结构化需求

- 版本号升级为 `v0.7.0`。
- 新增 WSI metadata 读取抽象，生产路径使用 OpenSlide；缺少文件、OpenSlide 不可读取、MPP 缺失等情况必须显式报错。
- 新增 fixture image reader，用于小型 PNG/TIFF smoke test，不得伪装成生产 WSI 后端。
- 新增 manifest audit 能力：校验 manifest 后逐条读取 WSI 元数据，输出可审计记录，包括路径、尺寸、level、MPP、倍率和 backend。
- 新增 thumbnail 读取/生成基础能力，至少支持在 fixture reader 中输出指定尺寸 thumbnail，用于后续 UI 与 QC。
- 新增 mask label 读取与 label mapping 应用能力，支持 PNG/numpy 小型 mask，并拒绝未映射编号。
- 新增 mask 坐标对齐校验，基于 `transform_to_level0` 的 scale/offset 判断 mask 是否落在 WSI level0 范围内。
- 新增 CLI `audit-manifest`，用于根据 manifest 生成数据审计 JSON。
- 新增单元测试覆盖 WSI metadata、thumbnail、manifest audit、mask 编号读取、mapping 应用和坐标对齐错误。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不实现 patch embedding、聚类伪 mask、prior artifact、latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。
- fixture image reader 只服务于 smoke test 和小型开发样例；真实 WSI 仍应走 OpenSlide 后端。
- 若 PNG/numpy mask 需要可选依赖而环境缺失，必须显式报错，不做静默替代。

## v0.6.0 - 2026-05-23

### 用户需求

- 用户要求根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 当前开发应从 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md` 的里程碑顺序推进，保持完整 H&E WSI 生成器作为最终目标。
- 本次版本先落地 M1：数据契约与 schema 校验，为后续 WSI I/O、mask 映射、prior、训练生成、QC 和 PySide6 UI 提供可测试基础。

### 结构化需求

- 版本号升级为 `v0.6.0`。
- 创建 Python core package，包名采用开发附录建议的 `he_wsi_generator`。
- 创建 CLI 入口 `he-wsi-gen`，至少支持对 manifest、label mapping、generation config、metadata 和 QC JSON 进行校验。
- 建立项目配置文件，支持本地以源码路径运行测试，不在主环境中安装额外运行依赖。
- 实现严格 schema 校验：缺少必填字段、非法 mask 类别、非法 `structure_anchor`、非法 cascade/tile/magnification、缺失 source 追踪和不完整 QC 输出都需要显式报错。
- 提供默认 generation config 示例，默认值需与开发附录一致：`latent_diffusion_unet`、`40x`、`512 x 512`、`["1/32", "1/16", "1/4", "1/1"]`、`sample_steps=50`、`overlap_px_40x=64`、`non_copy_patch_nearest_neighbor_search=false`。
- 添加单元测试覆盖 schema validator 和 CLI 校验行为。
- 同步更新 README、CHANGELOG、VERSION 和测试中的版本断言。

### 边界说明

- 本次版本不实现真实 WSI 读取、OME-TIFF 写出、patch embedding、prior 学习、latent diffusion 训练、级联生成或 PySide6 桌面 UI。
- 对 YAML 配置的支持若缺少解析依赖，必须显式报错，不允许把 YAML 静默当作 JSON 或忽略。
- 当前 M1 产物应作为后续 M2-M7 的基础，不应宣称完整 H&E WSI 生成器已经完成。

## v0.5.1 - 2026-05-23

### 用户需求

- 用户要求将本地仓库文件夹重命名为 `MultiCenterWSIGenerator`。
- 用户要求将当前文件夹内容同步到 GitHub 仓库 `Liao-MH/MultiCenterWSIGenerator`。
- 用户要求同步本地项目展示名称与远端仓库名称。

### 结构化需求

- README 项目标题更新为 `MultiCenterWSIGenerator`。
- README 增加 GitHub 仓库链接。
- 版本号升级为 `v0.5.1`。
- 新增 `.gitignore`，避免 `.DS_Store` 和 Python 缓存进入远端仓库。
- 初始化本地 git 仓库，将当前内容提交并推送到 `https://github.com/Liao-MH/MultiCenterWSIGenerator.git`。

### 边界说明

- 当前远端仓库经 `git ls-remote` 检查未返回 refs，按空仓库处理。
- 当前 `gh` 未登录，SSH 公钥不可用；若 HTTPS push 被拒绝，需要用户完成 GitHub 鉴权后再重试推送。
- 不使用强推，不覆盖远端已有历史。

## v0.5.0 - 2026-05-23

### 用户需求

- 用户要求保存第一版开发指南，将现有 proposal 转换为可开发规格。
- 用户已确认开发附录采用单文件形态，细节深度达到“可开发规格”，首版重点为全链路骨架。
- 用户已确认工程默认：Python core/CLI + PySide6 桌面控制台，OpenSlide+tifffile WSI I/O，v1 使用 latent diffusion U-Net，可插拔 PatchEmbedder，严格字段契约，训练/生成配置采用默认值加可覆盖项。

### 结构化需求

- 新建 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`。
- 开发附录需覆盖数据契约、工程结构、模块契约、conditional priors 工程落地、模型训练、推理重建、QC、UI、测试验收和 v1 边界。
- 开发附录需明确不实现代码，只保存开发规格。
- README 需要新增开发附录入口，并把项目状态更新为研究设计 + 开发规格阶段。
- 版本号升级到 `v0.5.0`，并同步更新需求记录和开发日志。

### 边界说明

- 当前版本仍不实现训练代码、推理代码或图形界面。
- 当前版本不新增 IHC、免疫荧光、临床/分子标签、下游训练验证、专家盲评、DiT 主干或文本 embedding 入模。
- 当前目录不是 git 仓库，因此不执行 git commit。

## v0.4.0 - 2026-05-21

### 用户需求

- 用户希望把 conditional priors learning 的数理逻辑写进 proposal，明确它实际会学到什么结果，以及这些结果如何在模型中形成约束。
- 用户希望把 prior 的输出类型、条件注入方式、训练目标、`structure_anchor` 权重语义和 QC 作用一起写清楚，避免停留在概念层。
- 用户要求继续在同一 proposal 路径上增补内容，不改变当前课题方向。

### 结构化需求

- 在研究设计文档中新增 conditional priors 的联合分布定义，明确 `layout`、`mask`、`style`、`texture`、`artifact`、`source-anchor` 和 `QC reference` 的关系。
- 补充 prior 产物类型的清单，说明哪些输出是分布参数、哪些输出是 sampleable condition、哪些输出只用于 QC。
- 补充 prior 如何进入生成模型的实际机制，包括条件输入、采样边界、训练损失、推理 guidance 和自动 QC。
- 明确 `structure_anchor` 在数学上对应条件强度与 loss 权重的连续控制，而不是像素插值。
- 在三阶段训练协议中注明 conditional priors 的实例化条件，避免把 priors 误写成临时拼接特征。
- 同步更新版本号、README、CHANGELOG 和 proposal 主文档中的版本字段。

### 边界说明

- 当前版本仍只更新文档，不实现训练代码、推理代码或图形界面。
- 当前版本不新增下游训练验证、真人专家盲评、IHC、免疫荧光或临床/分子标签条件。
- 当前版本保持同一文档路径 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，通过版本号表达内容增强。

## v0.3.0 - 2026-05-18

### 用户需求

- 用户希望 proposal 文档覆盖前期讨论达成的所有细节共识。
- 用户希望研究设计文档比 v0.2.0 更详细，尤其是因果分析、设计取舍、训练协议、QC 逻辑、metadata 和 LLM 边界。
- 用户要求在现有 proposal 基础上增强内容，而不是改变课题方向。

### 结构化需求

- 在研究设计文档中补充共识总表，集中记录系统目标、模型路线、生成路径、`structure_anchor`、`global_imaging_style_prior`、mask、LLM、UI、QC、非复制检测和后续扩展边界。
- 补充“因果假设与反事实边界”，解释为什么 WSI 生成器不能只做 patch 或颜色增强。
- 补充“设计选择与被放弃路线”，说明为什么 GAN、CycleGAN、纯随机生成、先高倍后拼接和文本 prompt 入模不作为当前主线。
- 补充数据流与因果依赖，明确 thumbnail、6 类 mask、patch embedding、style statistics、source relation 和 QC reference distribution 的作用。
- 细化 mask 生成与映射流程，记录人工标注、ROI、聚类伪标签和用户确认的可信度层级。
- 细化 `structure_anchor` 的训练与推理语义，明确 anchor=1 是重扫描模拟，anchor=0 是 fully de novo。
- 细化多分辨率级联生成模型，补充 backbone 选择原则、四层责任分工、训练样本构造、训练约束与 QC 映射。
- 细化本地桌面单页控制台和高级参数暴露范围。
- 细化 LLM 角色，限定为知识约束与交互编排，不承担像素真实性和专家判断。
- 细化 metadata，增加 run-level manifest 与 per-WSI metadata 的分工。
- 细化自动 QC 的 warning/fail 逻辑、训练分布自适应阈值、轻量非复制报告解释规则和核心系统完成标准。

### 边界说明

- 当前版本仍只更新文档，不实现训练代码、推理代码或图形界面。
- 当前版本不新增下游训练验证、真人专家盲评、IHC、免疫荧光或临床/分子标签条件。
- 当前版本保持同一文档路径 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，通过版本号表达内容增强。

## v0.2.0 - 2026-05-18

### 用户需求

- 用户要求根据 `research-design-ladder` 技能，将前期多轮讨论形成的 H&E WSI 数据生成器课题方案写入正式研究设计文档。
- 用户要求新建 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，保留旧草案，不覆盖历史版本。
- 用户要求同步更新版本号、README、需求记录和开发日志。

### 结构化需求

- 研究对象：H&E 染色 Whole Slide Image（WSI）的本地化数据生成器。
- 核心目标：设计一个可训练、可配置、可追溯、可自动质控的 WSI 生成系统。
- 主模型路线：结构锚定的多分辨率 mask-conditioned latent diffusion / diffusion transformer。
- 生成路径：从低倍到高倍级联生成，层级为 `1/32 -> 1/16 -> 1/4 -> 1/1`，最高主动生成层为 40x。
- Tile 规格：40x 主动生成 tile 为 `512 x 512`。
- 控制变量：保留 `structure_anchor`，删除用户可见 `domain_shift`，内部使用 `global_imaging_style_prior`。
- 输出内容：OME-TIFF pyramid WSI、疾病无关 6 类 mask、per-WSI metadata JSON、QC JSON、batch JSONL index。
- Mask 类别：`background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact`。
- 标注策略：支持 PNG/numpy mask 和 ROI；无标注时使用 patch embedding 聚类生成伪 mask，并由用户映射到 6 类。
- 软件形态：本地桌面工具，单页控制台，暴露完整高级参数。
- 自动 QC：覆盖 WSI 级、tile 级和 mask 区域级，输出 `pass`、`warning`、`fail`；阈值采用训练分布自适应。
- 非复制检测：作为强制 QC 报告内容，但第一版不做全量 patch 近邻检索，也不自动触发 fail。

### 边界说明

- 当前版本只完成研究设计，不实现训练代码、推理代码或图形界面。
- 当前系统边界只覆盖 H&E WSI 生成器本身，不把下游训练/测试作为当前成败标准。
- IHC、免疫荧光、临床/分子标签、真人专家盲评和下游训练验证均作为后续可选扩展。
- LLM 仅作为知识约束与交互编排模块，不作为像素级病理真实性依据，也不做文本 embedding 入模。

## v0.1.0 - 2026-05-16

### 用户需求

- 用户希望基于多中心病理数据收集困难这一现实限制，设计一个面向 H&E 染色 WSI 数据的多中心数据生成器。
- 用户显式要求使用 `research-design-ladder` 技能，将初始想法整理成完整的研究设计文档。

### 结构化需求

- 研究对象：H&E 染色 Whole Slide Image（WSI）。
- 核心问题：如何在真实多中心数据难以收集的情况下，生成可控、可信、可验证的多中心样式数据。
- 主要目标：构建一个生成器设计方案，使其能够模拟不同中心之间的染色、扫描和图像处理差异，同时尽量保持诊断相关形态与标签不变。
- 证据重点：形态保真、中心域覆盖、下游跨中心泛化提升、隐私与泄漏控制、病理专家可接受性。
- 输出形式：完整 Markdown 研究设计文档，并同步生成项目 README、需求记录和变更日志。

### 边界说明

- 当前版本只完成研究设计，不实现训练代码、推理代码或图形界面。
- 当前版本不承诺合成数据可替代真实多中心临床验证。
- 当前版本不扩展到 IHC、特殊染色或非病理影像，除非后续用户提出新的迭代需求。
