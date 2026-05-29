# Stage/Module 真实实现对照审计（v0.80.0 当前态）

审计日期：2026-05-28

审计范围：
- 设计文档：`docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- 开发文档：`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- 当前可见代码：`src/he_wsi_generator/`
- 当前可见测试：`tests/`
- 当前版本文件：`VERSION = v0.80.0`

本轮只做对照审计与审计文档产出，不修改业务代码。`build/validation/` 历史工件只作为已有记录背景，不作为本轮重新验证证据。

## 设计/开发文档一致性检查

未发现需要暂停并向用户确认的直接冲突：
- 两份文档对 Stage 1-7 的顺序、M01-M26 的模块名称和主体目标一致。
- 设计文档描述的是完整系统目标：学习真实 WSI 的 layout、mask、style、texture，并输出可追溯、可质控的 OME-TIFF pyramid WSI。
- 开发文档给出的是阶段最低门槛：Stage Gate 允许先完成可审计的最小真实主链，不要求在每个 Stage 内提前实现商业产品级增强。

审计口径因此采用双层判断：
- 是否满足当前 Module / Stage Gate 的最低真实主链。
- 是否已经达到设计文档中的完整 slide 级 WSI 生成目标。

## 审计口径

`真实、非 smoke、无偏离` 的判定条件：
- 能读取真实文件或真实产物契约，不只返回固定假数据。
- 不依赖 `smoke`、`fixture`、`proxy`、`placeholder` 路径作为主体完成依据。
- 产物能被下游 Module 按开发文档消费。
- metadata / manifest 如实记录 backend、production status、source、mask 和限制，不把最小链路包装成完整 production generator。
- 测试可以是 fixture 级单元测试，但对应代码路径不能是 smoke-only 业务实现。

状态分类沿用用户指定的 4 类：
- 已有可直接保留
- 已有但需要简化/收敛/修改
- 属于后置增强项，暂时冻结不继续扩展
- 缺失，需要后续新写

## M01-M26 逐项审计

| Module | 当前是否已有真实的、非 smoke 级、无偏离实现 | 真实代码路径 / 核心函数或类 | 现有测试路径 | 状态分类 | 与当前 module-stage 开发方案的差距 |
|---|---|---|---|---|---|
| M01 Python core 与 CLI 骨架 | 有。CLI 与 package 入口是真实工程入口，不是 smoke 替代。 | `src/he_wsi_generator/cli.py::build_parser`；`src/he_wsi_generator/cli_commands.py::run_command`；`src/he_wsi_generator/__main__.py`；`src/he_wsi_generator/constants.py::PROJECT_VERSION` | `tests/test_cli.py`；`tests/test_version.py` | 已有可直接保留 | 当前命令面已经覆盖后续 Stage，范围大于 Stage 1 最小骨架，但没有偏离主体方案。后续只需随真实模块做最小参数维护。 |
| M02 基础 schema 与配置 | 有。manifest、label mapping、generation config、metadata、QC 具备真实校验。 | `src/he_wsi_generator/schemas.py::{validate_input_manifest,validate_label_mapping,validate_generation_config,validate_metadata,validate_qc_report,validate_generation_output_diagnostics}`；`src/he_wsi_generator/constants.py::DEFAULT_GENERATION_CONFIG`；`configs/generation.default.json` | `tests/test_schemas.py`；`tests/test_cli.py`；`tests/test_version.py` | 已有可直接保留 | 字段多于 Stage 1 最小需求，但主要服务后续 Stage 契约。需要继续避免 schema 字段暗示上游能力已经完整 production-ready。 |
| M03 输入 manifest 与数据审计 | 有。可读取 manifest 并用 reader 生成 audit summary，包含 WSI、MPP、split、center、tissue、annotation 摘要。 | `src/he_wsi_generator/io/audit.py::{build_reader,audit_manifest}`；`src/he_wsi_generator/io/readers.py::SlideMetadata` | `tests/test_wsi_io.py`；`tests/test_cli.py` | 已有可直接保留 | 满足 Stage 1 gate。当前不负责复杂数据治理、批量缺陷修复或多中心统计报告，这些不应提前并入 M03。 |
| M04 WSI reader | 有。OpenSlide 路径是真实 WSI reader；fixture reader 明确只用于测试和 smoke。 | `src/he_wsi_generator/io/readers.py::OpenSlideReader`；`src/he_wsi_generator/io/readers.py::FixtureImageSlideReader` | `tests/test_wsi_io.py`；`tests/test_wsi_tissue_overview.py` | 已有可直接保留 | 真实 pyramid metadata、MPP、thumbnail 读取已具备。差距不在 reader，而在后续生成是否真正消费 slide 级尺度。 |
| M05 Annotation loader | 有。支持 PNG/TIFF/numpy/ROI JSON/cluster pseudo mask 的统一读取入口。 | `src/he_wsi_generator/annotations/masks.py::{read_mask_array,read_mask_labels,load_annotation_source,_load_roi_json}` | `tests/test_annotations.py` | 已有可直接保留 | 满足 Stage 2 最小 annotation loader。复杂厂商专有 annotation 格式不属于当前 Stage Gate。 |
| M06 Label mapping | 有。能把输入编号映射到 6 类项目 mask，未映射 label 显式失败。 | `src/he_wsi_generator/annotations/masks.py::apply_label_mapping`；`src/he_wsi_generator/schemas.py::validate_label_mapping` | `tests/test_annotations.py`；`tests/test_schemas.py`；`tests/test_training_index.py` | 已有可直接保留 | 当前 6 类映射契约与开发文档一致。无需扩展成更复杂 ontology。 |
| M07 Mask alignment 与合并 | 有。已有 block streaming 6 类 mask 合并、priority、冲突检测、compact provenance 和临时 artifact 编排。 | `src/he_wsi_generator/annotations/masks.py::build_six_class_mask`；`src/he_wsi_generator/annotations/pipeline.py::{build_six_class_mask_artifact,cleanup_temporary_six_class_masks}`；`src/he_wsi_generator/annotations/alignment.py::validate_mask_alignment` | `tests/test_annotations.py`；`tests/test_cli.py`；`tests/test_training_batch.py` | 已有可直接保留 | 满足 Stage 2 gate。当前不应恢复 per-pixel `source_trace` 或为低概率格式扩展复杂合并系统。 |
| M08 Patch embedding 与伪 mask | 有，但不是 pathology foundation model。真实 WSI patch 读取、batch streaming embedding、聚类、pseudo mask artifact 已形成闭环。 | `src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest`；`src/he_wsi_generator/embeddings/embedder.py::{CheckpointPatchEmbedder,FixturePatchEmbedder}`；`src/he_wsi_generator/embeddings/cache.py::{save_embedding_cache,load_embedding_cache}`；`src/he_wsi_generator/embeddings/cluster.py::cluster_embeddings` | `tests/test_pseudo_mask_pipeline.py`；`tests/test_embeddings.py`；`tests/test_cli.py` | 已有可直接保留 | 当前可保留的真实边界是“统计型 patch moment embedding + clustering pseudo-mask”。不得把它表述为真实病理基础模型、语义 segmentation 模型或专家级伪标注。 |
| M09 Layout/mask prior | 有。可从真实 training-index mask tile 学习统计型 layout/mask prior，并可采样 layout mask。 | `src/he_wsi_generator/priors/layout.py::build_layout_mask_prior_from_training_index`；`src/he_wsi_generator/priors/sampler.py::sample_layout_mask_from_prior` | `tests/test_layout_mask_prior.py`；`tests/test_layout_mask_sampler.py` | 已有可直接保留 | 符合 Stage 3 最小 artifact 目标。它不是 trainable mask diffusion / full slide layout generator，设计目标中的更强布局生成能力尚未达到。 |
| M10 Style 与 texture prior | 部分有。style prior 覆盖 RGB 统计和拟合 style latent；texture prior 覆盖 embedding cluster/codebook。 | `src/he_wsi_generator/priors/style.py::{build_style_prior_from_training_index,sample_style_policy_from_prior}`；`src/he_wsi_generator/priors/texture.py::{build_texture_prior_from_embedding_cache,sample_texture_policy_from_prior}` | `tests/test_style_prior.py`；`tests/test_texture_prior.py` | 已有但需要简化/收敛/修改 | Stage 3 gate 的可保存/加载 artifact 已成立；但设计文档中的清晰度、焦平面、污渍、压缩、扫描噪声等 global style prior 维度尚未进入 M10 主 artifact。当前应明确为统计型 RGB/style 与 embedding texture prior。 |
| M11 Prior manifest | 有。统一登记 prior artifact、hash、版本、seed、路径和 production readiness contract。 | `src/he_wsi_generator/priors/artifacts.py::{build_prior_manifest_from_artifacts,save_prior_manifest,load_prior_manifest,validate_prior_manifest}`；`src/he_wsi_generator/generation/conditioning.py::build_generation_condition_packet` | `tests/test_priors.py`；`tests/test_generation_conditioning.py` | 已有可直接保留 | 满足 Stage 3 gate。后续差距来自 prior 内容强度，不是 manifest 汇总能力。 |
| M12 多倍率训练样本 | 有。training index 与 batch loader 已覆盖 1/32、1/16、1/4、1/1 的 image/mask/coord/source/anchor 条件字段和读取。 | `src/he_wsi_generator/models/training_index.py::build_training_index`；`src/he_wsi_generator/models/training_batch.py::{load_training_batch,training_batch_summary,write_training_batch_summary}` | `tests/test_training_index.py`；`tests/test_training_batch.py` | 已有可直接保留 | 满足 Stage 4 最小训练样本门槛。它不是 materialized latent dataset，也不做全量分布采样优化；当前不应继续膨胀 M12。 |
| M13 条件生成模型骨架 | 有。新增最小真实 `latent_diffusion_unet` 后端，包含 tile VAE、conditioned latent U-Net、mask head，并接收 mask、previous scale、style/texture、coord、source、anchor 条件。 | `src/he_wsi_generator/models/latent_diffusion_training.py::{train_latent_diffusion_unet,_build_tile_vae,_build_latent_denoiser,_build_mask_head,condition_feature_schema,cross_scale_condition_schema,source_condition_schema}` | `tests/test_latent_diffusion_training.py`；`tests/test_models_generation.py`；`tests/test_torch_training.py` | 已有可直接保留 | 满足 Stage 4 gate 的“真实训练链路和条件链路成立”。但 checkpoint manifest 诚实标记 `production_ready=false`，不能把该最小模型宣称为已验证的病理真实感生产模型。 |
| M14 三阶段训练流程 | 有。真实执行 `prior_ready -> image_generator -> wsi_consistency`，写出 `model.pt`、training log、training plan、run 和 checkpoint manifest。 | `src/he_wsi_generator/models/latent_diffusion_training.py::{train_latent_diffusion_unet,_run_vae_stage,_run_diffusion_stage,_trained_checkpoint_manifest}`；`src/he_wsi_generator/models/training.py::create_training_run` | `tests/test_latent_diffusion_training.py` | 已有可直接保留 | 满足 Stage 4 最小训练流程。当前训练是小型 PyTorch 最小链路，不证明视觉质量、泛化能力或完整 slide 级一致性。 |
| M15 Anchor 训练与 checkpoint 记录 | 有。训练循环覆盖低/中/高 anchor preset，checkpoint 记录 anchor strategy、sample counts、condition schema。 | `src/he_wsi_generator/models/latent_diffusion_training.py::{ANCHOR_TRAINING_PRESETS,_anchor_training_summary,_source_condition_channels,_trained_checkpoint_manifest}`；`src/he_wsi_generator/models/training.py::validate_checkpoint_manifest` | `tests/test_latent_diffusion_training.py`；`tests/test_models_generation.py` | 已有可直接保留 | 满足 Stage 4 gate。差距是当前 source condition 训练用 observed RGB 近似，不等价于已验证的真实中/高 anchor slide 级结构迁移能力。 |
| M16 Cascade generation | 有，但需要收敛。external production tile-stream 合同真实；internal latent path 能按 1/32 -> 1/16 -> 1/4 -> 1/1 生成四层 tile source。 | `src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`；`src/he_wsi_generator/generation/latent_diffusion_internal.py::{materialize_internal_latent_diffusion_tile_sources,_sample_internal_cascade,_write_internal_tile_source_manifest}`；`src/he_wsi_generator/generation/planner.py::create_generation_plan` | `tests/test_production_latent_generation.py`；`tests/test_generation_runner.py`；`tests/test_stage1_7_real_backend_e2e.py` | 已有但需要简化/收敛/修改 | 当前 internal path 是按 `canvas_size_40x` 生成整层小画布数组后切 tile source，不是 slide/GB 级 tile-grid latent inference。满足当前最小输出链路，但不能宣称完整 WSI 级生成模型已实现。 |
| M17 Tile traversal 与 blending | 有。tile traversal、overlap blending、resumable manifest 和完成性校验是可复用基础设施。 | `src/he_wsi_generator/generation/tiling.py::{create_tile_traversal_plan,blend_rgb_tiles,build_resumable_tile_manifest,update_resumable_tile_manifest,require_complete_tile_manifest}` | `tests/test_generation_tiling.py` | 已有可直接保留 | M17 基础设施真实存在。差距是 internal latent generation 当前没有逐 tile 调用模型并在 overlap 区域做模型级 blending；该差距属于 M16/M18 主体生成路径。 |
| M18 Source-conditioned generation | 有，但需要收敛。高 anchor 时 Stage5 可解析 source WSI 并读取 source RGB 作为模型条件，metadata 记录 source provenance。 | `src/he_wsi_generator/generation/latent_diffusion_internal.py::{_source_condition_summary,_load_source_level0_rgb,_source_condition_channels}`；`src/he_wsi_generator/generation/executor.py::{_resolve_source_wsi_path_from_prior,_metadata_source_payload,run_production_tile_stream_generation}`；`src/he_wsi_generator/models/latent_diffusion_training.py::_source_condition_channels` | `tests/test_production_latent_generation.py::ProductionLatentGenerationTests::test_internal_latent_generation_records_real_source_conditioning`；`tests/test_generation_runner.py` | 已有但需要简化/收敛/修改 | 当前已不是纯 contract 或 RGB mix smoke；但 source 条件只覆盖当前 `canvas_size_40x` 区域，尚未实现 slide 级按 tile 坐标读取 source、与 layout prior 连续混合并验证中 anchor 结构迁移的完整路径。 |
| M19 OME-TIFF writer | 有。支持 array writer、disk tile assembly 和 tiled iterator streaming writer，并写出 mask。 | `src/he_wsi_generator/outputs/ome_tiff.py::{write_pyramid_ome_tiff,write_pyramid_ome_tiff_from_tile_sources,write_pyramid_ome_tiff_streaming_from_tile_sources}`；`src/he_wsi_generator/generation/production_streaming.py::write_streaming_mask_from_tile_sources`；`src/he_wsi_generator/outputs/masks.py::write_mask_array` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py`；`tests/test_production_latent_generation.py` | 已有可直接保留 | Writer 主体真实且强于 Stage 5 最小要求。上游图像是否为 GB/slide 级真实合成，不应归因给 M19。 |
| M20 Per-WSI metadata | 有。metadata 写出 source、seed、model、prior、mask mapping、输出路径、checkpoint inference contract、production tile backend。 | `src/he_wsi_generator/generation/executor.py::{_metadata_payload,_metadata_source_payload,_metadata_mask_schema}`；`src/he_wsi_generator/metadata/archive.py::{write_metadata,archive_sample}` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py`；`tests/test_production_latent_generation.py`；`tests/test_ui.py` | 已有可直接保留 | 当前 metadata 已能诚实记录 `production_ready=false`、backend 和 source provenance。后续重点是继续防止将小画布 internal path 包装成 GB 级 production generator。 |
| M21 基础 QC | 有。文件、pyramid、mask 对齐、基础图像质量 proxy、streaming tile source QC、reference distribution 和 review artifact 均可用。 | `src/he_wsi_generator/qc/engine.py::{build_qc_report,write_qc_report}`；`src/he_wsi_generator/generation/production_streaming.py::build_streaming_tile_source_qc_report`；`src/he_wsi_generator/qc/reference.py::build_qc_reference_distribution`；`src/he_wsi_generator/qc/review.py` | `tests/test_outputs_qc_archive.py`；`tests/test_qc_reference.py`；`tests/test_qc_review.py` | 已有可直接保留 | 满足 Stage 6 基础 QC。高级专家级病理真实性评价、复杂 seam/style 定位和商业级诊断仍属于后置增强，暂时冻结不扩展。 |
| M22 Batch index 与最小归档 | 有。能写 `metadata.json`、`qc.json`、`batch.jsonl`，并返回 archive 路径。 | `src/he_wsi_generator/metadata/archive.py::{append_batch_index,archive_sample,write_metadata}` | `tests/test_outputs_qc_archive.py`；`tests/test_generation_runner.py` | 已有可直接保留 | 满足 Stage 6 gate。无需扩展复杂数据湖或批处理管理。 |
| M23 PySide6 单页控制台 | 有。单页 UI 暴露输入、mapping、prior/model、generation 参数、backend、状态与输出摘要，并支持 `production-tile-stream`。 | `src/he_wsi_generator/ui/pyside_app.py::{create_main_window,launch_ui}`；`src/he_wsi_generator/ui/workflow.py::{build_generation_config_from_form,build_run_generation_command}` | `tests/test_ui.py`；`tests/test_ui_workflow.py` | 已有可直接保留 | 满足 Stage 7 最小 UI。当前 UI 调度真实 backend，但不负责证明生成模型达到 slide/GB 级。 |
| M24 UI 配置持久化 | 有。JSON/YAML config roundtrip 和 form-state 到 generation config 的转换存在。 | `src/he_wsi_generator/ui/config.py::{create_default_ui_config,save_ui_config,load_ui_config}`；`src/he_wsi_generator/ui/workflow.py::build_generation_config_from_form` | `tests/test_ui.py`；`tests/test_ui_workflow.py` | 已有可直接保留 | 满足 Stage 7 gate。后续只需随真实字段做最小维护。 |
| M25 Job runner 与状态展示 | 有。本地 job runner、queued/running/completed/failed/cancelled 状态和 output summary 已成链。 | `src/he_wsi_generator/ui/jobs.py::JobRunner`；`src/he_wsi_generator/ui/controller.py::{JobStateStore,collect_output_summary}`；`src/he_wsi_generator/ui/workflow.py::{create_run_generation_job,run_queued_generation_job,load_generation_job_status,collect_generation_job_output_summary}` | `tests/test_job_runner.py`；`tests/test_ui.py`；`tests/test_ui_workflow.py` | 已有可直接保留 | 满足 Stage 7 gate。真实程度取决于被调度 backend，不由 job runner 自身保证。 |
| M26 端到端 E2E 验收 | 有，但需要收敛。已有 non-smoke internal latent backend E2E 测试和历史真实 SVS 验证记录；当前可见自动测试仍主要用 fixture slide。 | `tests/test_stage1_7_real_backend_e2e.py::Stage1To7RealBackendE2ETests::test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary`；`tests/test_production_latent_generation.py`；`src/he_wsi_generator/ui/workflow.py`；`src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation` | `tests/test_stage1_7_real_backend_e2e.py`；`tests/test_production_latent_generation.py`；`tests/test_ui_workflow.py` | 已有但需要简化/收敛/修改 | 当前 M26 能证明非 smoke 工程闭环，但不能证明 GB 级 slide 合成。自动 E2E 的 fixture slide 和当前 `canvas_size_40x=512` 仍应明确标为最小链路验证，而不是完整 H&E WSI 质量验收。 |

## 后置增强项冻结清单

这些能力在仓库中存在，但不应被本轮或当前 Stage Gate 当作主体完成依据，也不应在前置缺口未收敛前继续扩展：
- `train-torch-smoke`、`train-torch-vae-smoke`、`train-torch-diffusion-smoke`、`sample-torch-diffusion-smoke`：保留为 smoke / proxy 验证路径，不能替代 M13-M18 主体实现。
- external `production-tile-stream` 的 retry、resume、progress、disk preflight、temporary publish recovery：是生产执行合同和可靠性增强，不等于仓库内置 latent diffusion / pathology generator。
- QC review、stratified QC reference、复杂 non-copy proxy：可保留，但 Stage 6 当前只要求基础 QC；不要把这些扩展成当前主体阻塞项。
- PySide6 UI 的展示增强：可保留，但 UI 不承担像素真实性证明。

## Stage 级结论

### 已基本具备

| Stage | 结论 |
|---|---|
| Stage 1 工程骨架与基础契约 | M01-M03 已有真实实现，可直接保留。 |
| Stage 2 WSI 与 6 类 mask | M04-M07 已有真实实现，可直接保留。 |
| Stage 3 语义与风格 priors | M08/M09/M11 可直接保留；M10 已具备最小 artifact，但需要收敛其设计表述和缺失维度。 |
| Stage 4 训练数据与生成模型 | M12-M15 已具备最小真实训练主链，可直接保留；边界是 `production_ready=false`，不能宣称模型质量已完成生产验证。 |
| Stage 6 Metadata 与基础 QC | M20-M22 已具备，可直接保留。 |
| Stage 7 本地控制台与调度 | M23-M25 已具备；M26 有非 smoke 工程闭环，但需要收敛验收表述。 |

### 需要收敛

| Stage | 需要收敛的点 |
|---|---|
| Stage 3 | M10 当前更像 RGB/statistical style prior + embedding texture codebook，缺少设计文档中的清晰度、焦平面、污渍、压缩、扫描噪声等 style 分布维度。 |
| Stage 5 | M16 internal latent path 是小画布整层采样后切 tile source，不是 slide/GB 级 tile-grid inference；M18 source conditioning 已接入真实 source RGB，但只覆盖当前 canvas 区域，不是完整 slide 坐标 source-conditioned generation。 |
| Stage 7 | M26 当前证明非 smoke 工程闭环，不证明 GB 级 H&E WSI 合成质量；自动测试仍应明确 fixture / small-canvas 边界。 |

### 真正缺口

| Stage | 缺口 |
|---|---|
| Stage 5 | 缺少 slide 级、tile-grid、memory-safe 的 internal latent diffusion inference：按 WSI 坐标逐 tile 采样、逐 tile source condition、跨 tile overlap / seam 处理、跨倍率一致性、直接输出 GB 级 tile source，而不是先生成单个小画布 array。 |
| Stage 5 / Stage 7 验收边界 | 缺少把“当前最小真实链路”与“GB 级 slide 合成 H&E WSI”严格分开的自动验收标签或集成测试层级。当前已有 `production-tile-stream` OME 输出流程验证，但不能视为完整 slide 级合成模型验证。 |

## 总体判断

当前仓库已经不是早期纯 smoke 骨架：Stage 1-4 的数据、prior、训练链路和 Stage 5-7 的 OME 输出、metadata、QC、UI 调度都有真实代码路径。

但当前最容易被误判的点是 Stage 5：`production-tile-stream` 和 OME writer 能验证 slide-level 输出流程，internal latent path 能验证非 smoke checkpoint 到 OME 的最小链路；它仍没有实现设计文档意义上的 GB 级、slide 级、tile-grid H&E WSI 合成生成器本体。因此，后续开发如果要回应“为什么不是 GB 级合成 H&E WSI”，真正缺口应聚焦 M16/M18 的 slide 级 internal generation，而不是继续扩展 writer、QC、UI 或 smoke backend。

## 本轮验证记录

本轮审计前执行过的非侵入式检查：
- `git status --short`
- `git branch --show-current`
- `wc -c docs/plans/2026-05-18-he-wsi-generator-study-design.md docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md docs/DEMANDS.MD docs/CHANGELOG.md README.md VERSION pyproject.toml`
- `rg --files docs src tests | sort`
- `rg -n "M0[1-9]|M1[0-9]|M2[0-6]|Stage|阶段|Implementation Trace|真实|smoke|Module" docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `rg -n "M0[1-9]|M1[0-9]|M2[0-6]|Stage|阶段|Implementation Trace|真实|smoke|Module" docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `rg -n "class .*Tests|def test_" tests/...`

本轮尚未执行全量测试。原因：用户请求是静态对照审计与文档产出，不是代码实现或回归修复；历史测试结果不在本审计中伪装为本轮重新验证。
