# v0.65.0 审计补救实施计划

## 当前定位

当前仓库不是完整 production H&E WSI 生成器，而是一个可测试、可追踪的 core/CLI 工程骨架，并具备 smoke/proxy 级生成、QC、归档链路、可交互 PySide6 配置页和 GUI 内同步 queued job 执行/状态刷新/输出摘要查看。后续补救顺序应进入 production 模型、生产级 prior/WSI 输出能力，或先做维护性收敛降低大文件风险。

## P0. 审计材料归位与证据闭环

- 目标：把审计材料集中到 `docs/audit/`，并让 README、需求记录和变更日志能指向新位置。
- 当前状态：本轮已执行迁移，后续只维护 `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md`。
- 完成标准：`docs/` 根目录不再保留上述三个审计文件；`README.md` 能直接找到审计入口。

## P0.5. v0.63.0 交付收口

- 目标：把当前已验证的 v0.63.0 工作区状态收敛为可追踪的提交/发布基线。
- 当前状态：v0.63.0 已提交到 `main` 作为后续 worker 基线；两个历史 worker worktree 仍存在，尚未打 tag 或形成发布包。
- 建议任务包：
  - 已完成：审查 `git diff --stat` 和 `git status --short`，确认所有 v0.63.0 改动都属于本轮范围。
  - 已完成：`.agent/logs/` 原始 JSONL 日志继续被忽略，任务和报告文件保留在 `.agent/tasks/`、`.agent/reports/`。
  - 删除或保留 `.worktrees/p1-qc-review-validate`、`.worktrees/p1-output-summary-contract` 前先确认不再需要继续审查。
  - 待完成：如需正式发布，补 tag 和发布包流程。
- 完成标准：`git status --short` 只剩预期未跟踪/忽略项或完全干净；v0.63.0 有明确 commit，tag/发布包状态被清楚记录。

## P1. 契约一致性与文档诚实度

- 目标：避免把 smoke/proxy 能力或 UI 骨架描述成完整项目成果。
- 当前状态：v0.63.0 已完成第一轮补救。
- 已完成：
  - README 的 M5/M7 和当前边界已明确标注 smoke/proxy、控制层与 production 完整成果的差异。
  - 新增仓库实体 `AGENTS.md`，让会话规则可持久追踪。
  - `he-wsi-gen validate qc-review <path>` 已接入现有 `validate_qc_review()`。
  - `collect_output_summary()` 已对 metadata 执行 schema 校验，并校验 metadata/QC/review 的 generated id 一致性。
- 影响范围：`README.md`、`AGENTS.md`、`src/he_wsi_generator/schemas.py`、`src/he_wsi_generator/cli.py`、`src/he_wsi_generator/ui/controller.py`、`tests/test_ui.py`、`tests/test_qc_review.py`。
- 完成标准：相关测试已覆盖坏 metadata、坏 qc_review、id 不一致和 validate CLI 路径。

## P2. 可交互 PySide6 自定义配置页与本地 GUI flow

- 目标：实现设计文档要求的本地单页控制台，让用户不手工编辑中间 JSON 也能完成配置。
- 当前状态：v0.65.0 已完成可交互配置页、非 Qt UI workflow helper、generation config 保存、queued local job record 创建、GUI 内同步执行 queued job、刷新 job 状态和 metadata/QC/可选 qc_review 输出摘要查看。
- 建议任务包：
  - 已完成：建立独立 conda UI 环境并验证 PySide6 offscreen。
  - 已完成：把 `pyside_app.py` 从只读字段展示升级为真实表单：路径选择、anchor preset、seed、sample steps、prior/checkpoint、输出目录、QC 设置。
  - 已完成：实现最小 label mapping 面板，非法 raw label、重复编号和空映射会阻塞。
  - 已完成：将 UI 表单保存为 JSON generation config，并通过 `JobRunner` 创建 queued local job record。
  - 已完成：给 PySide6 交互层补最小 GUI 单元/集成测试；无 GUI 环境下保留明确 skip。
  - 已完成：GUI 内执行 queued job、刷新 job 状态、展示 metadata/QC/qc_review 输出摘要。
- 决策点：是否让 `run-generation` 默认先弹配置页需要用户确认；默认建议保留 CLI 自动化，把 GUI 放在 `launch-ui`。
- 完成标准：安装 PySide6 后，用户能通过 UI 配置、保存 generation config、创建 smoke generation queued job、同步执行 queued job、刷新状态并查看输出摘要；后台 daemon、并发队列、运行中进程终止和线程化 Qt 执行不属于本阶段。

## P3. Production 级生成模型补齐

- 目标：从 smoke/proxy 生成升级到设计目标中的结构锚定多分辨率生成模型。
- 建议任务包：
  - 定义 production training dataset contract 和真实训练运行配置。
  - 实现或接入 production latent diffusion / ControlNet / DiT 之一，保留 `structure_anchor`、mask、style、texture 和 source condition。
  - 实现真实 multi-scale cascade sampler，不再只输出 preview/proxy。
  - 建立 checkpoint manifest 的真实 inference 可用性判定。
  - 增加小规模可重复训练 fixture，避免每次验证都依赖大型真实数据。
- 完成标准：模型 checkpoint 可被标记为 `usable_for_inference=true`，并能用真实推理 backend 生成完整交付物。

## P4. 生产级 WSI 输出、恢复和 QC 验证

- 目标：补齐 gigapixel 级交付可靠性。
- 建议任务包：
  - 实现磁盘级 tile streaming 和可恢复 OME-TIFF 写入。
  - 将 run manifest 的 completed/pending tile 信息接入恢复执行。
  - 扩展 QC 到更真实的 stain、focus、seam、mask-image consistency 和 non-copy 审计。
  - 保留当前自动 QC 的 pass/warning/fail 和 reference distribution 审计链。
- 完成标准：中断后可恢复生成；不完整输出不能被标为 pass。

## P5. 环境化复跑验证

- 目标：区分“历史上有工件”和“当前环境可复现”。
- 当前状态：已创建 conda 环境 `MultiCenterWSIGenerator`，安装完整可选依赖并通过 PyTorch/UI 定向测试、PySide6 offscreen 表单 smoke 和 `213` 个全量单元测试；真实 SVS 全链路仍未在本轮复跑。
- 建议任务包：
  - 已完成：准备独立 conda/pip 环境说明，覆盖 `torch`、`ui`、`wsi`、`outputs`、`yaml`。
  - 已完成：复跑完整单元测试、PyTorch smoke 路径和 PySide6 当前窗口创建 smoke。
  - 待完成：复跑真实 SVS 链路，并记录输入数据、输出目录、metadata/QC/batch index 证据。
  - 把每条命令和输出摘要记录到 `docs/audit/ACCEPTANCE_CHECKLIST.md` 与 `docs/CHANGELOG.md`。
- 完成标准：当前机器可从干净环境复现主要验证结果。

## P6. 维护性收敛

- 目标：降低后续补救风险，不做风格化大重构。
- 建议任务包：
  - 优先拆分 `src/he_wsi_generator/cli.py` 的命令注册和命令执行分支。
  - 再拆分 `src/he_wsi_generator/models/torch_training.py` 中训练、采样、manifest/schema 辅助逻辑。
  - 每次拆分都保持行为不变，并先跑相关测试。
- 完成标准：测试不减少，功能边界更清楚，后续 production 模型和 UI 迭代不再堆入单个大文件。
