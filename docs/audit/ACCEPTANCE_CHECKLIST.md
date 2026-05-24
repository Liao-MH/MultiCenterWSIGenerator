# 审计验收清单（v0.63.0 复审计，原始 v0.62.0 基线）

## 进度结论

- 当前项目处于“可测试 core/CLI 骨架 + smoke/proxy 生成验证链 + P1 契约闭环 + 独立 conda 环境验证”阶段。
- 相比研究设计中的完整项目成果，已完成数据契约、基础 I/O、统计 prior、condition packet、smoke 级生成、基础 OME-TIFF/QC/归档、UI 控制层和当前机器的 PyTorch/PySide6 依赖验证；尚未完成 production 级 latent diffusion/ControlNet 训练与推理、真正可交互的 PySide6 配置页、生产级 WSI 流式写出/恢复和真实 SVS 全链路复跑。
- 按设计目标拆解，M1 基本完成；M2-M4/M6 为基础能力完成但仍偏 smoke/proxy；M5 和 M7 只完成骨架或控制层，离完整项目成果仍有主要工程缺口。
- 复审计基线已收口为 `main` 分支上的 v0.63.0 提交；尚未打 tag 或形成发布包。

## 已完成

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-DOC-01 | 审计文件已迁移到 `docs/audit/` | `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md` | 已完成 | 原 `docs/` 根目录审计文件已移动 |
| AC-DOC-02 | 研究设计、开发附录、需求和变更日志存在 | `docs/plans/2026-05-18-he-wsi-generator-study-design.md`、`docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`、`docs/DEMANDS.MD`、`docs/CHANGELOG.md` | 已完成 | 设计文档明确完整成果边界 |
| AC-CORE-01 | 版本号同步为 `v0.63.0` | `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json`、`tests/test_version.py` | 已完成 | `PYTHONPATH=src python -m he_wsi_generator.cli --version` 返回 `v0.63.0` |
| AC-CORE-02 | 包结构覆盖开发附录建议的核心模块 | `src/he_wsi_generator/{io,annotations,embeddings,priors,models,generation,qc,metadata,outputs,ui}` | 已完成 | core/CLI/UI 控制层边界已建立 |
| AC-CORE-03 | 基础 schema、manifest、label mapping、generation config、metadata、QC 校验可用 | `src/he_wsi_generator/schemas.py`、`tests/test_schemas.py`、`tests/test_cli.py` | 已完成 | 默认 generation config 本轮验证通过 |
| AC-CORE-04 | 统计 prior、condition packet、sampled layout mask 和 smoke generation 链路存在 | `src/he_wsi_generator/priors/`、`src/he_wsi_generator/generation/`、`tests/test_priors.py`、`tests/test_generation_conditioning.py`、`tests/test_generation_runner.py` | 已完成 | 当前为统计/smoke/proxy 能力，不是最终生成模型 |
| AC-CORE-05 | OME-TIFF 小型写出、mask 输出、QC、batch index、`qc_review` 文件级审阅工作流存在 | `src/he_wsi_generator/outputs/`、`src/he_wsi_generator/qc/`、`src/he_wsi_generator/metadata/archive.py`、`tests/test_outputs_qc_archive.py`、`tests/test_qc_review.py` | 已完成 | `qc_review` 已有独立构建和决策更新命令 |
| AC-CORE-06 | 历史真实 SVS 验证工件存在 | `build/validation/v0.62.0-291288/...` | 已完成 | 只能证明历史工件存在；不等于本轮重新跑完整链路 |
| AC-TEST-01 | 常规单元测试覆盖面较广 | `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v` | 已完成 | 独立 conda 环境中通过 `191` 个测试，未再因缺少 PyTorch 跳过 torch smoke 测试 |
| AC-ENV-01 | 独立 conda 环境已创建并安装完整可选依赖 | `mamba create -y -n MultiCenterWSIGenerator -c conda-forge python=3.11 pip openslide`、`mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'` | 已完成 | Python `3.11.15`；依赖包含 torch、PySide6、OpenSlide、YAML、tifffile、Pillow、numpy |
| AC-ENV-02 | 当前环境可运行 PyTorch smoke 训练/采样/生成测试 | `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`、`mamba run -n MultiCenterWSIGenerator python -c 'import torch'` | 已完成 | PyTorch `2.12.0+cu130`，CUDA 可用，GPU 为 `NVIDIA GeForce RTX 5060 Ti` |
| AC-ENV-03 | 当前环境可导入 PySide6 并创建现有 UI 窗口 | `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python - <<'PY' ... create_main_window() ... PY` | 已完成 | offscreen smoke 返回窗口标题 `MultiCenterWSIGenerator`、central widget 存在、widget count `88`；不等于 AC-MISS-02 的真实交互式配置页 |
| AC-P1-01 | 仓库内实体 `AGENTS.md` 已持久化 | `AGENTS.md` | 已完成 | 记录本仓库通用、代码、文档、版本和 worker 编排规则 |
| AC-P1-02 | `qc_review` 接入通用 `validate` CLI/schema kind | `src/he_wsi_generator/schemas.py`、`src/he_wsi_generator/cli.py`、`tests/test_qc_review.py` | 已完成 | `he-wsi-gen validate qc-review <path>` 可校验有效 artifact，非法 `artifact_type` 显式失败 |
| AC-P1-03 | 输出摘要严格遵循 metadata 契约 | `src/he_wsi_generator/ui/controller.py`、`tests/test_ui.py` | 已完成 | `collect_output_summary()` 校验 metadata schema，并校验 metadata/QC/review `generated_id` 一致性 |
| AC-P1-04 | README 里程碑状态区分骨架/控制层与完整成果 | `README.md` | 已完成 | M5/M7 和当前边界已明确 production 模型与真实 PySide6 配置页未完成 |
| AC-AUDIT-01 | 本轮复审计已捕获当前工作区状态 | `git status --short`、`git log -1 --oneline`、`docs/CHANGELOG.md` Audit Snapshot | 已完成 | v0.63.0 已提交为主分支基线；尚未 tag 或打包发布 |

## 缺失

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-MISS-02 | 真正可交互的 PySide6 自定义配置页 | `src/he_wsi_generator/ui/pyside_app.py` | 缺失 | 当前窗口只显示字段文本，运行按钮 disabled |
| AC-MISS-03 | 生成器使用前自动或显式进入完整图形配置流程 | `src/he_wsi_generator/cli.py`、`src/he_wsi_generator/ui/pyside_app.py` | 缺失 | 当前 `run-generation` 是 CLI-first；只有独立 `launch-ui` |
| AC-MISS-04 | Production 级结构锚定多分辨率 latent diffusion / ControlNet / DiT 训练和推理 | `src/he_wsi_generator/models/torch_training.py`、`README.md` 当前边界说明 | 缺失 | 当前仅 smoke/VAE/proxy latent 路线 |
| AC-MISS-05 | 生产级 layout/style/texture prior 和 style sampling policy | `src/he_wsi_generator/priors/` | 缺失 | 当前主要是统计 prior 与可审计 artifact |
| AC-MISS-06 | 生产级 gigapixel OME-TIFF 流式写出、恢复和磁盘级 tile streaming | `src/he_wsi_generator/outputs/ome_tiff.py`、`README.md` 当前边界说明 | 缺失 | 现有 writer 记录 chunk plan audit，但仍非生产流式实现 |

## 偏离

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-DEV-01 | M7 “PySide6 控制台”表述与实现一致 | `README.md` M7 行、`docs/dev/...`、`src/he_wsi_generator/ui/pyside_app.py` | 偏离 | 文档目标是单页任务配置/状态/输出查看；实现只有只读骨架窗口 |
| AC-DEV-03 | CLI 与 torch smoke 训练代码保持低维护风险 | `src/he_wsi_generator/cli.py` 1156 行、`src/he_wsi_generator/models/torch_training.py` 1912 行 | 偏离 | 功能集中在大文件中，后续补救风险偏高 |

## 未验证

| ID | 验收项 | 文件或测试证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-VER-03 | 本轮重新执行真实 SVS v0.62.0 全链路生成 | `build/validation/v0.62.0-291288/...` | 未验证 | 只看到了历史工件，未在本轮重新生成 |
| AC-VER-04 | 完整 production 项目成果可验收 | 研究设计 Phase 4/5/6、README 当前边界 | 未验证 | 关键 production 模型和完整 GUI 尚不存在，不能验收 |
| AC-VER-05 | v0.63.0 tag/发布包状态 | `git tag --list` 未在本轮执行发布流程 | 未验证 | v0.63.0 已提交到 `main`，但尚未 tag 或打包发布 |
| AC-VER-06 | worker 隔离区清理状态 | `git worktree list --porcelain` | 未验证 | `.worktrees/p1-qc-review-validate` 与 `.worktrees/p1-output-summary-contract` 仍存在；若不再需要，后续应清理 |
