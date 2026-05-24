# 审计验收清单（v0.66.0 复审计，原始 v0.62.0 基线）

## 进度结论

- 当前项目处于“可测试 core/CLI 骨架 + smoke/proxy 生成验证链 + P1 契约闭环 + 独立 conda 环境验证 + P2 可交互 PySide6 配置页 + GUI 内同步执行/刷新/输出摘要查看 + P6 维护性收敛 + P4 可恢复 tile 状态与磁盘 tile source contract”阶段。
- 相比研究设计中的完整项目成果，已完成数据契约、基础 I/O、统计 prior、condition packet、smoke 级生成、基础 OME-TIFF/QC/归档、UI 控制层、可交互 PySide6 配置页、GUI 内同步执行 queued job/刷新状态/查看输出摘要、CLI 命令分发拆分、PyTorch smoke training 纯 helper 拆分、可恢复 tile manifest contract、磁盘 `.npy` tile source contract 校验和当前机器的 PyTorch/PySide6 依赖验证；尚未完成 production 级 latent diffusion/ControlNet 训练与推理、生产级 layout/style/texture prior、真正逐 tile OME-TIFF streaming writer 和真实 SVS 全链路复跑。
- 按设计目标拆解，M1 基本完成；M2-M4/M6 为基础能力完成但仍偏 smoke/proxy，其中 M6 新增可恢复 tile 状态和磁盘 tile source 发布前校验但仍不是 production streaming；M5 仍为 smoke/proxy；M7 的本地同步 GUI flow 已补齐，后台 daemon、并发队列和运行中进程终止仍不属于当前实现；P6 的首轮行为保持维护性收敛已完成。
- 当前 v0.66.0 作为本轮补救基线提交，尚未打 tag 或形成发布包。

## 已完成

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-DOC-01 | 审计文件已迁移到 `docs/audit/` | `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md` | 已完成 | 原 `docs/` 根目录审计文件已移动 |
| AC-DOC-02 | 研究设计、开发附录、需求和变更日志存在 | `docs/plans/2026-05-18-he-wsi-generator-study-design.md`、`docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`、`docs/DEMANDS.MD`、`docs/CHANGELOG.md` | 已完成 | 设计文档明确完整成果边界 |
| AC-CORE-01 | 版本号同步为 `v0.66.0` | `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json`、`tests/test_version.py` | 已完成 | `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version` 返回 `v0.66.0` |
| AC-CORE-02 | 包结构覆盖开发附录建议的核心模块 | `src/he_wsi_generator/{io,annotations,embeddings,priors,models,generation,qc,metadata,outputs,ui}` | 已完成 | core/CLI/UI 控制层边界已建立 |
| AC-CORE-03 | 基础 schema、manifest、label mapping、generation config、metadata、QC 校验可用 | `src/he_wsi_generator/schemas.py`、`tests/test_schemas.py`、`tests/test_cli.py` | 已完成 | 默认 generation config 本轮验证通过 |
| AC-CORE-04 | 统计 prior、condition packet、sampled layout mask 和 smoke generation 链路存在 | `src/he_wsi_generator/priors/`、`src/he_wsi_generator/generation/`、`tests/test_priors.py`、`tests/test_generation_conditioning.py`、`tests/test_generation_runner.py` | 已完成 | 当前为统计/smoke/proxy 能力，不是最终生成模型 |
| AC-CORE-05 | OME-TIFF 小型写出、mask 输出、QC、batch index、`qc_review` 文件级审阅工作流存在 | `src/he_wsi_generator/outputs/`、`src/he_wsi_generator/qc/`、`src/he_wsi_generator/metadata/archive.py`、`tests/test_outputs_qc_archive.py`、`tests/test_qc_review.py` | 已完成 | `qc_review` 已有独立构建和决策更新命令 |
| AC-CORE-06 | 历史真实 SVS 验证工件存在 | `build/validation/v0.62.0-291288/...` | 已完成 | 只能证明历史工件存在；不等于本轮重新跑完整链路 |
| AC-TEST-01 | 常规单元测试覆盖面较广 | `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v` | 已完成 | 独立 conda 环境中通过 `223` 个测试，未再因缺少 PyTorch 或 PySide6 跳过 P2/P4 路径 |
| AC-ENV-01 | 独立 conda 环境已创建并安装完整可选依赖 | `mamba create -y -n MultiCenterWSIGenerator -c conda-forge python=3.11 pip openslide`、`mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'` | 已完成 | Python `3.11.15`；依赖包含 torch、PySide6、OpenSlide、YAML、tifffile、Pillow、numpy |
| AC-ENV-02 | 当前环境可运行 PyTorch smoke 训练/采样/生成测试 | `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`、`mamba run -n MultiCenterWSIGenerator python -c 'import torch'` | 已完成 | PyTorch `2.12.0+cu130`，CUDA 可用，GPU 为 `NVIDIA GeForce RTX 5060 Ti` |
| AC-ENV-03 | 当前环境可导入 PySide6 并创建现有 UI 窗口 | `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python - <<'PY' ... create_main_window() ... PY` | 已完成 | offscreen smoke 返回窗口标题 `MultiCenterWSIGenerator`、widget count `86`、button count `5`，并确认执行/刷新/摘要按钮存在 |
| AC-P1-01 | 仓库内实体 `AGENTS.md` 已持久化 | `AGENTS.md` | 已完成 | 记录本仓库通用、代码、文档、版本和 worker 编排规则 |
| AC-P1-02 | `qc_review` 接入通用 `validate` CLI/schema kind | `src/he_wsi_generator/schemas.py`、`src/he_wsi_generator/cli.py`、`tests/test_qc_review.py` | 已完成 | `he-wsi-gen validate qc-review <path>` 可校验有效 artifact，非法 `artifact_type` 显式失败 |
| AC-P1-03 | 输出摘要严格遵循 metadata 契约 | `src/he_wsi_generator/ui/controller.py`、`tests/test_ui.py` | 已完成 | `collect_output_summary()` 校验 metadata schema，并校验 metadata/QC/review `generated_id` 一致性 |
| AC-P1-04 | README 里程碑状态区分骨架/控制层与完整成果 | `README.md` | 已完成 | M5/M7 和当前边界已明确 production 模型与真实 PySide6 配置页未完成 |
| AC-P2-01 | 真正可交互的 PySide6 自定义配置页 | `src/he_wsi_generator/ui/pyside_app.py`、`tests/test_ui.py` | 已完成 | UI 表单支持配置保存路径、prior/checkpoint/output/generated id、backend、anchor preset、structure anchor、seed、sample steps、overlap、condition packet、training index、QC non-copy 和 6 类 label mapping |
| AC-P2-02 | UI 表单保存 generation config 前执行显式校验 | `src/he_wsi_generator/ui/workflow.py`、`tests/test_ui_workflow.py`、`tests/test_ui.py` | 已完成 | 非法 label mapping、缺必填字段、source-anchored 缺 source WSI、torch backend 缺 training index 均显式失败 |
| AC-P2-03 | UI 可创建 queued local generation job | `src/he_wsi_generator/ui/pyside_app.py`、`src/he_wsi_generator/ui/workflow.py`、`tests/test_ui.py`、`tests/test_ui_workflow.py` | 已完成 | 创建 `<output-root>/ui_jobs/<generated-id>/job.json`，不自动执行生成 |
| AC-P2-04 | GUI 内同步执行、刷新 job 状态和查看输出摘要 | `src/he_wsi_generator/ui/pyside_app.py`、`src/he_wsi_generator/ui/workflow.py`、`tests/test_ui.py`、`tests/test_ui_workflow.py` | 已完成 | UI 调用 workflow helper 执行 queued job、刷新 job record，并在 completed 后读取 metadata/QC/可选 qc_review 摘要；不包含后台 daemon 或运行中取消 |
| AC-P4-01 | 可恢复 tile manifest contract | `src/he_wsi_generator/generation/tiling.py`、`tests/test_generation_tiling.py`、`.agent/reports/p4-resumable-tile-manifest-20260524.md` | 已完成 | 支持从 traversal plan 构建状态 manifest、标记 completed/failed、计算 resume/next tile，pending/failed/非 row-major 完成或计数不一致显式失败 |
| AC-P4-02 | 磁盘 `.npy` tile source contract 校验 | `src/he_wsi_generator/outputs/ome_tiff.py`、`tests/test_outputs_qc_archive.py`、`.agent/reports/p4-ome-tiff-streaming-contract-20260524.md` | 已完成 | 写出前校验 expected count、level/tile index、路径存在、shape、dtype 和 completed 状态；pending/failed/missing/duplicate 等显式失败；返回 `partial_contract_only` |
| AC-AUDIT-01 | 本轮复审计已捕获当前工作区状态 | `git status --short`、`git log -1 --oneline`、`docs/CHANGELOG.md` | 已完成 | v0.66.0 作为本轮主分支基线提交；尚未 tag 或打包发布 |

## 缺失

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-MISS-04 | Production 级结构锚定多分辨率 latent diffusion / ControlNet / DiT 训练和推理 | `src/he_wsi_generator/models/torch_training.py`、`README.md` 当前边界说明 | 缺失 | 当前仅 smoke/VAE/proxy latent 路线 |
| AC-MISS-05 | 生产级 layout/style/texture prior 和 style sampling policy | `src/he_wsi_generator/priors/` | 缺失 | 当前主要是统计 prior 与可审计 artifact |
| AC-MISS-06 | 生产级 gigapixel OME-TIFF 流式写出、恢复和磁盘级 tile streaming | `src/he_wsi_generator/outputs/ome_tiff.py`、`src/he_wsi_generator/generation/tiling.py`、`README.md` 当前边界说明 | 部分完成 / 仍缺失 production writer | v0.66.0 已有可恢复 tile manifest contract 与磁盘 `.npy` tile source contract gate；仍没有真正逐 tile OME-TIFF streaming writer、写入中断恢复执行或 gigapixel 级磁盘 streaming |

## 偏离

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-DEV-03 | CLI 与 torch smoke 训练代码保持低维护风险 | `src/he_wsi_generator/cli.py` 662 行、`src/he_wsi_generator/cli_commands.py` 505 行、`src/he_wsi_generator/models/torch_training.py` 1445 行、`src/he_wsi_generator/models/torch_training_contracts.py` 495 行 | 已完成 | 行为保持拆分完成，CLI 命令分发与纯 helper 已从主大文件中迁出，后续维护风险已明显下降 |
| AC-DEV-04 | P4 输出可靠性仍弱于完整设计 | `src/he_wsi_generator/outputs/ome_tiff.py`、`README.md` 当前边界说明 | 偏离 | 当前只完成可恢复状态与发布前 contract gate，writer 本体仍是 in-memory tifffile pyramid writer |

## 未验证

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-VER-03 | 本轮重新执行真实 SVS v0.62.0 全链路生成 | `build/validation/v0.62.0-291288/...` | 未验证 | 只看到了历史工件，未在本轮重新生成 |
| AC-VER-04 | 完整 production 项目成果可验收 | 研究设计 Phase 4/5/6、README 当前边界 | 未验证 | 关键 production 模型和完整 GUI 尚不存在，不能验收 |
| AC-VER-05 | v0.66.0 tag/发布包状态 | `git tag --list` 未在本轮执行发布流程 | 未验证 | v0.66.0 已提交，尚未 tag 或打包发布 |
| AC-VER-06 | worker 隔离区清理状态 | `git worktree list --porcelain` | 未验证 | 历史 worker worktree 与本轮 worker worktree 仍存在；当前作为审计证据保留，未清理 |
