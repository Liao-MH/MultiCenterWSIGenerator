# Stage/Module 真实实现对照审计（v0.78.0）

审计日期：2026-05-27

审计范围：
- 开发方案：`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- 当前仓库代码：`src/he_wsi_generator/`
- 当前测试：`tests/`
- 用户文档：`README.md`
- 当前版本：`VERSION = v0.78.0`

本轮只做 Stage/Module 对照审计，不修改业务代码。`build/validation/` 历史工件不作为本轮重新验证证据，仅作为 README/开发文档中的历史记录背景。

## 审计口径

`真实代码实现` 的判定口径：
- 数据读取、mask、prior、metadata、QC、writer、job runner 等模块：能处理真实输入文件或真实产物契约，并且不是只返回固定假数据。
- 模型训练与生成模块：`smoke`、`fixture`、`proxy`、`contract_only`、`plan_only_no_production_training_loop`、`production_ready=false` 不计为真实 pathology generation/model 实现。
- `production-tile-stream` 计为真实外部 production tile backend 执行合同和 WSI 写出编排，但不计为仓库内置 latent diffusion / ControlNet / DiT / pathology-realistic generator 本体。

状态分类沿用用户指定的 4 类：
- 已有可直接保留
- 已有但需要简化/收敛
- 属于后置增强项，暂时冻结不继续扩展
- 缺失，需要后续新写

## M01-M26 逐项审计

| Module | 当前是否有非 smoke 真实实现 | 真实代码路径 / 核心函数或类 | 现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|---|
| M01 Python core 与 CLI 骨架 | 有 | `src/he_wsi_generator/cli.py::build_parser`；`src/he_wsi_generator/cli_commands.py::run_command`；`src/he_wsi_generator/__main__.py` | `tests/test_cli.py`；`tests/test_version.py` | 已有可直接保留 | CLI 入口和命令分发已覆盖主体模块。后续只需随真实模块新增命令参数，不应再扩展 smoke-only 入口。 |
| M02 基础 schema 与配置 | 有 | `src/he_wsi_generator/schemas.py`；`src/he_wsi_generator/constants.py::DEFAULT_GENERATION_CONFIG`；`configs/generation.default.json` | `tests/test_schemas.py`；`tests/test_cli.py`；`tests/test_version.py` | 已有可直接保留 | manifest、label mapping、generation config、metadata、QC 等最小契约已具备。差距主要来自后续真实模型字段尚无生产训练实现支撑。 |
| M03 输入 manifest 与数据审计 | 有 | `src/he_wsi_generator/io/audit.py::audit_manifest`；`src/he_wsi_generator/io/audit.py::build_reader` | `tests/test_wsi_io.py`；`tests/test_cli.py` | 已有可直接保留 | 已记录 WSI 路径、尺寸、MPP、backend、`center_id`、`tissue_type` 和 annotation 摘要。当前差距不是 M03，而是后续模块是否消费这些字段。 |
| M04 WSI reader | 有 | `src/he_wsi_generator/io/readers.py::OpenSlideReader`；`FixtureImageSlideReader` 仅为 fixture/smoke 辅助 | `tests/test_wsi_io.py`；`tests/test_wsi_tissue_overview.py` | 已有可直接保留 | OpenSlide 真实读取入口存在。fixture reader 应继续限定在测试/小图路径，不应被描述为真实 WSI 能力。 |
| M05 Annotation loader | 有 | `src/he_wsi_generator/annotations/masks.py::load_annotation_source`；`read_mask_array`；`_load_roi_json` | `tests/test_annotations.py` | 已有可直接保留 | PNG/TIFF/numpy/ROI JSON/cluster pseudo mask loader 已覆盖 Stage 2 最小需求。复杂 annotation 格式不在当前开发方案主体范围内。 |
| M06 Label mapping | 有 | `src/he_wsi_generator/annotations/masks.py::apply_label_mapping`；`src/he_wsi_generator/schemas.py::validate_label_mapping` | `tests/test_annotations.py`；`tests/test_schemas.py` | 已有可直接保留 | 6 类映射和未映射 label 显式失败已具备。无需扩展到更复杂标签体系。 |
| M07 Mask alignment 与合并 | 有 | `src/he_wsi_generator/annotations/masks.py::build_six_class_mask`；`src/he_wsi_generator/annotations/pipeline.py::build_six_class_mask_artifact`；`cleanup_temporary_six_class_masks` | `tests/test_annotations.py`；`tests/test_cli.py` | 已有可直接保留 | block streaming merge、`.npy` memmap、compact provenance summary、临时 full mask cleanup 已覆盖当前内存收敛要求。下游应避免重新引入 per-pixel source_trace。 |
| M08 Patch embedding 与伪 mask | 有，但 embedder 真实性有限 | `src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest`；`src/he_wsi_generator/embeddings/embedder.py::CheckpointPatchEmbedder`；`FixturePatchEmbedder` 仅 smoke | `tests/test_pseudo_mask_pipeline.py`；`tests/test_embeddings.py`；`tests/test_cli.py` | 已有但需要简化/收敛 | 真实 WSI patch 读取、batch streaming embedding、全量 embedding 聚类、pseudo mask 写出已具备；但 `CheckpointPatchEmbedder` 当前是 JSON checkpoint + 统计 embedding，不是 pathology foundation model。应在文档和命名上收敛，避免把统计 embedder 误称为真实深度特征模型。 |
| M09 Layout/mask prior | 有 | `src/he_wsi_generator/priors/layout.py::build_layout_mask_prior_from_training_index`；`src/he_wsi_generator/priors/sampler.py::sample_layout_mask_from_prior` | `tests/test_layout_mask_prior.py`；`tests/test_layout_mask_sampler.py` | 已有可直接保留 | 当前是统计型 layout/mask prior，能从真实 mask tile 学习比例、记录和邻接统计，符合 Stage 3 最小 artifact 目标。无需提前扩展成复杂生成模型。 |
| M10 Style 与 texture prior | 有 | `src/he_wsi_generator/priors/style.py::build_style_prior_from_training_index`；`src/he_wsi_generator/priors/texture.py::build_texture_prior_from_embedding_cache` | `tests/test_style_prior.py`；`tests/test_texture_prior.py` | 已有可直接保留 | 当前是 RGB 统计与 embedding cluster/codebook prior，符合 Stage 3 最小条件 artifact。它不是深度 style/texture generator，但当前方案不要求在 M10 内实现该能力。 |
| M11 Prior manifest | 有 | `src/he_wsi_generator/priors/artifacts.py::build_prior_manifest_from_artifacts`；prior manifest 校验逻辑 | `tests/test_priors.py` | 已有可直接保留 | prior artifact、hash、版本、路径和 production component contract 校验已具备。后续缺口在真实模型是否能消费这些 priors。 |
| M12 多倍率训练样本 | 有，但仍偏 contract/index 层 | `src/he_wsi_generator/models/training_index.py::build_training_index`；`src/he_wsi_generator/models/training_batch.py::load_training_batch` | `tests/test_training_index.py`；`tests/test_training_batch.py` | 已有但需要简化/收敛 | 四层 cascade 记录、mask/image tile 读取、conditioning 字段已具备；但仍是 JSONL training index + batch loader，不是完整 materialized latent dataset。当前应保留，不要在 M13-M15 缺失前继续膨胀 M12。 |
| M13 条件生成模型骨架 | 无非 smoke 真实模型 | `src/he_wsi_generator/models/torch_training.py` 为 PyTorch smoke loop；`src/he_wsi_generator/models/training.py::create_training_run` 为 plan/contract manifest；`src/he_wsi_generator/models/torch_training_contracts.py` 明确 smoke/production_ready=false | `tests/test_torch_training.py` | 缺失，需要后续新写 | 现有 PyTorch RGB/VAE/DDPM-style 路径真实执行训练 loop，但 README 和 manifest 明确标记为 smoke/proxy，不是 latent diffusion U-Net 生产模型。M13 的真实条件模型本体缺失。 |
| M14 三阶段训练流程 | 无非 smoke 真实训练流程 | `src/he_wsi_generator/models/training.py::create_training_run` 仅写 training plan 和 checkpoint manifest；`torch_training.py` 仅 smoke training | `tests/test_torch_training.py`；training contract 相关测试 | 缺失，需要后续新写 | `prior_ready -> image_generator -> wsi_consistency` 三阶段生产训练没有真实训练 loop、优化过程、checkpoint 产物。当前 smoke training 应冻结为验证路径，不能替代 M14。 |
| M15 Anchor 训练与 checkpoint 记录 | 无非 smoke 真实 anchor training | `src/he_wsi_generator/models/training.py` 有 anchor/source 条件 contract；`src/he_wsi_generator/models/torch_training_contracts.py` 有 smoke condition schema | `tests/test_torch_training.py`；`tests/test_models_generation.py` | 缺失，需要后续新写 | checkpoint manifest 和 condition schema 有记录能力，但没有训练模型响应高/中/低 `structure_anchor` 的真实实现。 |
| M16 Cascade generation | 有真实编排与外部 production 合同，但内置生成仍依赖 smoke/proxy | `src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`；`run_smoke_generation` 和 `run_torch_diffusion_smoke_generation` 为 smoke/proxy；`src/he_wsi_generator/generation/planner.py::create_generation_plan` | `tests/test_generation_runner.py`；`tests/test_torch_training.py` | 已有但需要简化/收敛 | 四层 cascade plan、production tile-stream 外部 backend 合同和 writer handoff 已具备；但仓库内置生成路径仍是 smoke/proxy。需要在文档和入口上明确 production path 与 smoke path 边界。 |
| M17 Tile traversal 与 blending | 有 | `src/he_wsi_generator/generation/tiling.py::create_tile_traversal_plan`；`blend_rgb_tiles`；`build_resumable_tile_manifest`；`update_resumable_tile_manifest`；`require_complete_tile_manifest` | `tests/test_generation_tiling.py` | 已有可直接保留 | tile grid、overlap blending、resume manifest、失败 tile 状态均已具备。该模块是可复用基础设施，不依赖 smoke 模型本体。 |
| M18 Source-conditioned generation | 无非 smoke 真实生成模型 | `src/he_wsi_generator/generation/executor.py::_stage5_source_condition_summary`；`_mix_source_conditioned_tile`；`_resolve_source_wsi_path_from_prior` 为 RGB mix/source 条件摘要；production tile-stream 可把 condition packet 交给外部 backend | `tests/test_generation_runner.py` | 缺失，需要后续新写 | 现有 source-conditioned 行为是最小 RGB 混合或外部 backend request contract，不是高/中 anchor 下的真实 source-conditioned generative model。 |
| M19 OME-TIFF writer | 有 | `src/he_wsi_generator/outputs/ome_tiff.py::write_pyramid_ome_tiff`；`write_pyramid_ome_tiff_from_tile_sources`；`write_pyramid_ome_tiff_streaming_from_tile_sources`；`src/he_wsi_generator/outputs/masks.py` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py` | 已有可直接保留 | array writer、disk tile source assembly、tiled iterator streaming writer、mask writer 和 transaction/report 均已具备。真实图像内容质量取决于上游 M13-M18，不是 writer 缺口。 |
| M20 Per-WSI metadata | 有，但部分字段来源仍会暴露 smoke/proxy | `src/he_wsi_generator/generation/executor.py::_metadata_payload`；`_metadata_source_payload`；`_metadata_mask_schema`；`src/he_wsi_generator/metadata/archive.py::write_metadata` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py`；`tests/test_ui.py` | 已有但需要简化/收敛 | metadata 写出、source、mask mapping、输出路径、diagnostics 引用已具备。需要继续保持 backend/provenance 诚实记录，避免 smoke/proxy 输出被 metadata 包装成 production。 |
| M21 基础 QC | 有 | `src/he_wsi_generator/qc/engine.py::build_qc_report`；`src/he_wsi_generator/qc/reference.py`；`src/he_wsi_generator/qc/review.py`；`src/he_wsi_generator/generation/production_streaming.py::build_streaming_tile_source_qc_report` | `tests/test_outputs_qc_archive.py`；`tests/test_qc_reference.py`；`tests/test_qc_review.py` | 已有可直接保留 | 文件完整性、pyramid、mask 对齐、基础图像质量 proxy、reference distribution、QC review 均已具备。注意这些是基础 QC/proxy，不是专家级病理质量模型。 |
| M22 Batch index 与最小归档 | 有 | `src/he_wsi_generator/metadata/archive.py::archive_sample`；`append_batch_index`；`write_metadata` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py` | 已有可直接保留 | metadata/QC/batch JSONL 归档链路已具备。后续只需消费真实生成输出，不需要扩展归档系统。 |
| M23 PySide6 单页控制台 | 有 UI 骨架，但 production backend 未接入 UI | `src/he_wsi_generator/ui/pyside_app.py::create_main_window`；`src/he_wsi_generator/ui/workflow.py::build_run_generation_command` | `tests/test_ui.py`；`tests/test_ui_workflow.py` | 已有但需要简化/收敛 | 单页 UI、输入项、配置保存、job 操作、输出摘要已具备；但 `_BACKENDS` 和 UI 下拉目前只有 `smoke-cascade`、`torch-diffusion-smoke`，没有 `production-tile-stream`，因此不能作为真实生产链路 UI 验收。 |
| M24 UI 配置持久化 | 有 | `src/he_wsi_generator/ui/config.py`；`src/he_wsi_generator/ui/workflow.py::build_generation_config_from_form` | `tests/test_ui.py`；`tests/test_ui_workflow.py` | 已有可直接保留 | JSON/YAML 配置持久化和 form 到 generation config 的校验已具备。后续若新增真实 backend 字段，应做最小增量更新。 |
| M25 Job runner 与状态展示 | 有 | `src/he_wsi_generator/ui/jobs.py::JobRunner`；`src/he_wsi_generator/ui/workflow.py::create_run_generation_job`；`run_queued_generation_job`；`load_generation_job_status`；`src/he_wsi_generator/ui/controller.py` | `tests/test_job_runner.py`；`tests/test_ui_workflow.py`；`tests/test_ui.py` | 已有可直接保留 | queued/running/completed/failed/cancelled、本地命令执行、状态持久化和 output summary 已具备。真实程度取决于被调度的 backend。 |
| M26 端到端 smoke test | 有 smoke E2E；无 no-smoke 真实 SVS E2E 测试 | `tests/test_stage1_7_e2e.py::Stage1To7E2ETests::test_stage1_to_7_fixed_e2e_entry_runs_generation_job_and_collects_summary`；使用 fixture slide 和 smoke checkpoint/backend | `tests/test_stage1_7_e2e.py` | 已有但需要简化/收敛 | M26 按开发方案是 smoke E2E，当前实现成立；但它不能证明真实 `.svs`、非 smoke 模型、pathology-realistic GB 级 WSI 的 Stage1-7 链路成立。需要把 M26 的验收表述限制为工程闭环 smoke。 |

## Stage 级结论

### 已基本具备

| Stage | 结论 |
|---|---|
| Stage 1 工程骨架与基础契约 | M01-M03 已有真实实现，可直接保留。 |
| Stage 2 WSI 与 6 类 mask | M04-M07 已有真实实现，尤其 v0.78.0 后 M07 的 block streaming 和 compact provenance summary 已解决真实 SVS 内存风险中的关键部分。 |
| Stage 3 语义与风格 priors | M09-M11 已基本具备；M08 的真实 WSI patch/pseudo-mask 流程已具备，但 embedder 真实性需要收敛表述。 |
| Stage 6 Metadata 与基础 QC | M20-M22 基本具备；M20 需要继续保持 provenance 诚实记录，但不是主体缺口。 |

### 需要收敛

| Stage | 需要收敛的点 |
|---|---|
| Stage 3 | M08 不应把统计型 `CheckpointPatchEmbedder` 表述成 pathology foundation model；应只称为当前可审计统计 embedding / clustering pseudo-mask 路径。 |
| Stage 4 | M12 已有 training index/batch loader，但不应继续膨胀为复杂 dataset 系统；真正缺口在 M13-M15。 |
| Stage 5 | M16 有 production tile-stream 外部 backend 编排，但 smoke/proxy 与 production 合同混在同一阶段叙述中，容易误判为内置真实生成模型已完成。 |
| Stage 6 | M20 metadata 已具备，但必须继续显式记录 backend、production status、source/mask provenance，避免掩盖上游 smoke/proxy。 |
| Stage 7 | M23/M26 已能验证 UI/job/smoke E2E 工程闭环，但不应作为真实 `.svs` no-smoke 全链路验收证据。 |

### 存在真实代码缺口

| Stage | 缺口 |
|---|---|
| Stage 4 | M13 条件生成模型骨架、M14 三阶段生产训练流程、M15 anchor 训练与 checkpoint 记录均缺少非 smoke 真实实现。当前 PyTorch 路径明确是 smoke/proxy。 |
| Stage 5 | M18 source-conditioned generation 缺少非 smoke 真实生成模型。M16 的内置生成仍依赖 smoke/proxy；`production-tile-stream` 是外部 backend 合同，不是仓库内置 pathology generator。 |
| Stage 7 | M23 未接入 `production-tile-stream` UI 选择；M26 没有 no-smoke 真实 `.svs` Stage1-7 E2E 测试。现有 M26 仅证明 smoke 工程闭环。 |


## 本轮未做事项

- 未修改业务代码。
- 未更新 `docs/DEMANDS.MD`、`docs/CHANGELOG.md` 或 README，因为本轮用户要求只新增开发审计文档。
- 未运行全量测试；本轮审计只做代码/文档静态对照和非侵入式文件检查。
