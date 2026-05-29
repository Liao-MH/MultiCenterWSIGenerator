# 2026-05-26 Module / Stage Code Audit

## 审计范围

- 仅以当前仓库中的 `src/he_wsi_generator/`、`tests/`、`README.md`、`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md` 为判定依据。
- 本文不引入新的产品设想，不把 README 里的 smoke/proxy/contract 路径自动等价为开发文档中的“主体功能已完成”。
- 本轮只做对照审计，不改源码，不重排模块，不更新设计/开发文档代码追踪块。

## 状态分类口径

- `已有可直接保留`：已有真实实现，和当前 module-stage 方案的最小目标基本一致，可作为后续主线直接保留。
- `已有但需要简化/收敛`：仓库里已有实现，但范围、抽象层次、数据契约或主线位置与当前方案不完全一致，需要收敛到更小、更明确的主路径。
- `属于后置增强项，暂时冻结不继续扩展`：仓库里已有 smoke/contract/增强性实现，但不应在当前轮次继续扩张，先冻结，等待前置 Stage 收敛后再决定是否保留。
- `缺失，需要后续新写`：只有零散 helper/字段/契约，没有形成开发文档要求的独立 Module 能力。

## 总体结论

- `Stage 1`：基本具备。M01-M02 已稳定，M03 可用但 manifest/audit 字段范围还未完全收敛到开发文档口径。
- `Stage 2`：未过 gate。M04、M06 有基础，M05 只有部分 mask loader，M07 的“统一 6 类 mask 对齐与合并”仍是实质缺口。
- `Stage 3`：基本具备 proxy/artifact 主线。M09-M11 可直接沿用；M08 只有 embedding/cache/cluster 组件，缺少连到 WSI 的 pseudo-mask 产物链路。
- `Stage 4`：是当前最大真实缺口。M12 只有训练索引和 batch contract；M13-M15 以 smoke/contract 为主，不是开发文档里的真实多倍率条件生成训练主线。
- `Stage 5`：部分具备，但需要强收敛。M17、M19 很强；M16 已有多条生成/写出路径但主线分散；M18 只有 source-condition 契约，没有真实 source-conditioned 生成实现。
- `Stage 6`：基本具备。metadata、QC、batch archive 都有真实落地。
- `Stage 7`：基本具备本地调度与展示能力，但 M26 仍是“分散 smoke 测试集合”，不是一个收束过的最小 E2E 验收入口。

## Module 审计明细

### Stage 1

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M01 Python core 与 CLI 骨架 | 有 | 代码：`src/he_wsi_generator/cli.py::build_parser`、`src/he_wsi_generator/cli_commands.py::run_command`、`src/he_wsi_generator/__main__.py`。测试：`tests/test_cli.py`、`tests/test_version.py`。 | 已有可直接保留 | core package 和 CLI 骨架已稳定；当前 CLI 命令面比 Stage 1 更大，但不需要重头改写。 |
| M02 基础 schema 与配置 | 有 | 代码：`src/he_wsi_generator/schemas.py::{validate_input_manifest, validate_label_mapping, validate_generation_config, validate_metadata, validate_qc_report}`、`src/he_wsi_generator/constants.py::DEFAULT_GENERATION_CONFIG`。测试：`tests/test_schemas.py`、`tests/test_cli.py`。 | 已有可直接保留 | 已覆盖 manifest / mapping / generation config / metadata / QC 基础契约；字段多于 Stage 1 最小要求，但不是阻断。 |
| M03 输入 manifest 与数据审计 | 有，但字段范围偏窄 | 代码：`src/he_wsi_generator/io/audit.py::{build_reader, audit_manifest}`、`src/he_wsi_generator/io/readers.py::SlideMetadata`。测试：`tests/test_wsi_io.py`、`tests/test_cli.py`。 | 已有但需要简化/收敛 | 现有 manifest/audit 能列出 WSI、MPP、split、annotation 数，但 `center`、`tissue_type` 等开发文档字段没有进入统一 audit 主线；当前更像“最小 audit”而不是开发文档里的标准输入清单。 |

### Stage 2

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M04 WSI reader | 有 | 代码：`src/he_wsi_generator/io/readers.py::{OpenSlideReader, FixtureImageSlideReader}`。测试：`tests/test_wsi_io.py`、`tests/test_wsi_tissue_overview.py`。 | 已有可直接保留 | pyramid metadata、MPP、thumbnail 读取能力都在；当前可直接作为 Stage 2 reader 主线保留。 |
| M05 Annotation loader | 有，但只覆盖 raster mask 主线 | 代码：`src/he_wsi_generator/annotations/masks.py::{read_mask_array, read_mask_labels}`、`src/he_wsi_generator/schemas.py::_validate_annotation_record`。测试：`tests/test_annotations.py`。 | 已有但需要简化/收敛 | 当前真实 loader 只覆盖 PNG/TIFF/NPY/NPZ 整型 mask；`roi_json` 只在 schema 层被接受，没有真正的 ROI object loader，也没有统一 annotation loader 入口。 |
| M06 Label mapping | 有 | 代码：`src/he_wsi_generator/annotations/masks.py::apply_label_mapping`、`src/he_wsi_generator/schemas.py::validate_label_mapping`。测试：`tests/test_annotations.py`、`tests/test_training_index.py`。 | 已有可直接保留 | 6 类标签映射契约已经明确，未映射编号会显式报错，符合当前“主体功能优先”的处理边界。 |
| M07 Mask alignment 与合并 | 只有局部 helper，没有完整 module | 代码：`src/he_wsi_generator/annotations/alignment.py::validate_mask_alignment`、`src/he_wsi_generator/models/training_batch.py::_mask_tile_bounds`。测试：`tests/test_annotations.py`、`tests/test_training_batch.py`。 | 缺失，需要后续新写 | 现有代码只有 transform 校验和 tile 坐标反推，没有“对齐后的统一 6 类 mask artifact”，也没有“人工 mask + ROI + pseudo mask 候选”的合并主线，因此 Stage 2 gate 还没成立。 |

### Stage 3

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M08 Patch embedding 与伪 mask | 有 embedding 组件，但没有完整 pseudo-mask pipeline | 代码：`src/he_wsi_generator/embeddings/embedder.py::{CheckpointPatchEmbedder, FixturePatchEmbedder}`、`src/he_wsi_generator/embeddings/cache.py::{save_embedding_cache, load_embedding_cache}`、`src/he_wsi_generator/embeddings/cluster.py::cluster_embeddings`。测试：`tests/test_embeddings.py`。 | 已有但需要简化/收敛 | 已有 embedding/cache/cluster，但没有从 WSI 抽 patch、回写坐标、形成 `pseudo mask` 候选 artifact 的闭环；当前更像组件库，不是完整 M08。 |
| M09 Layout/mask prior | 有 | 代码：`src/he_wsi_generator/priors/layout.py::build_layout_mask_prior_from_training_index`、`src/he_wsi_generator/priors/sampler.py::sample_layout_mask_from_prior`。测试：`tests/test_layout_mask_prior.py`、`tests/test_layout_mask_sampler.py`。 | 已有可直接保留 | 虽然是统计型 prior，不是 trainable mask generator，但开发文档 Stage 3 明确允许“先保留最小 artifact”，因此当前实现可直接保留。 |
| M10 Style 与 texture prior | 有 | 代码：`src/he_wsi_generator/priors/style.py::{build_style_prior_from_training_index, sample_style_policy_from_prior}`、`src/he_wsi_generator/priors/texture.py::{build_texture_prior_from_embedding_cache, sample_texture_policy_from_prior}`。测试：`tests/test_style_prior.py`、`tests/test_texture_prior.py`。 | 已有可直接保留 | 当前是 fitted/statistical prior，不是深度 style/texture encoder，但已满足“可保存/加载 artifact，并能进入 condition packet”的最小目标。 |
| M11 Prior manifest | 有 | 代码：`src/he_wsi_generator/priors/artifacts.py::{build_prior_manifest_from_artifacts, save_prior_manifest, load_prior_manifest, validate_prior_manifest}`。测试：`tests/test_priors.py`、`tests/test_generation_conditioning.py`。 | 已有可直接保留 | prior artifact、路径、hash、版本、seed、production readiness contract 都已统一登记，已满足当前 Stage 3 gate。 |

### Stage 4

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M12 多倍率训练样本 | 有，但更像 training-index contract | 代码：`src/he_wsi_generator/models/training_index.py::build_training_index`、`src/he_wsi_generator/models/training_batch.py::{load_training_batch, write_training_batch_summary}`。测试：`tests/test_training_index.py`、`tests/test_training_batch.py`。 | 已有但需要简化/收敛 | 当前 index 会为四个 cascade level 重复生成 tile record，并按需读取 mask/image；但没有真实的多倍率图像/latent/style/source/anchor 样本物化，也没有“每层独立训练输入”收敛主线。 |
| M13 条件生成模型骨架 | 有，但主体是 smoke/contract skeleton | 代码：`src/he_wsi_generator/models/training.py::{create_training_run, validate_checkpoint_manifest}`、`src/he_wsi_generator/models/torch_training.py::train_torch_diffusion_smoke_model`、`src/he_wsi_generator/models/torch_training_contracts.py`。测试：`tests/test_models_generation.py`、`tests/test_torch_training.py`。 | 属于后置增强项，暂时冻结不继续扩展 | 当前是 smoke latent denoiser / inference contract 骨架，不是开发文档中的真实 latent diffusion U-Net 主干；在 Stage 2/3/M12 还未收敛前，不建议继续堆更多模型变体。 |
| M14 三阶段训练流程 | 有，但主体是 smoke training path | 代码：`src/he_wsi_generator/models/torch_training.py::{train_torch_smoke_model, train_torch_vae_smoke_model, train_torch_diffusion_smoke_model}`、`src/he_wsi_generator/models/training.py::create_training_run`。测试：`tests/test_torch_training.py`。 | 属于后置增强项，暂时冻结不继续扩展 | 当前训练流程验证的是 smoke RGB reconstruct / smoke VAE / smoke diffusion mechanics，不是 prior-ready -> image_generator -> wsi_consistency 的真实三阶段训练主线。 |
| M15 Anchor 训练与 checkpoint 记录 | 只有字段/契约，没有真实 anchor 训练闭环 | 代码：`src/he_wsi_generator/models/training.py` 的 dataset/objective/checkpoint contract、`src/he_wsi_generator/models/torch_training_contracts.py` 的 condition feature schema。测试：`tests/test_models_generation.py`、`tests/test_torch_training.py`。 | 属于后置增强项，暂时冻结不继续扩展 | 仓库里有 `structure_anchor` 字段、condition feature 和 checkpoint contract，但没有“训练模型响应高/中/低 anchor”的真实训练与验证链路。 |

### Stage 5

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M16 Cascade generation | 有，但主线分散在多套 backend | 代码：`src/he_wsi_generator/generation/planner.py::create_generation_plan`、`src/he_wsi_generator/generation/executor::{run_smoke_generation, run_torch_diffusion_smoke_generation, run_production_tile_stream_generation}`。测试：`tests/test_generation_runner.py`、`tests/test_generation_conditioning.py`。 | 已有但需要简化/收敛 | 仓库已支持 smoke、torch-diffusion-smoke、external production tile backend 三条路径；但当前 module-stage 方案需要一条明确、可收敛的主体 cascade 主线，而不是继续并行扩张 backend。 |
| M17 Tile traversal 与 blending | 有 | 代码：`src/he_wsi_generator/generation/tiling.py::{create_tile_traversal_plan, blend_rgb_tiles, build_resumable_tile_manifest, require_complete_tile_manifest}`。测试：`tests/test_generation_tiling.py`。 | 已有可直接保留 | row-major traversal、overlap blending、resumable manifest 已成型，和 Stage 5 的最小目标一致。 |
| M18 Source-conditioned generation | 只有 condition contract，没有真实生成实现 | 代码：`src/he_wsi_generator/generation/conditioning::{_source_condition, _structure_anchor_condition}`、`src/he_wsi_generator/generation/executor` 中 condition summary/metadata/request 透传。测试：`tests/test_generation_conditioning.py`。 | 缺失，需要后续新写 | 当前只把 source-condition 写进 condition packet、metadata 和 external request contract，没有真正把 source WSI tile/feature 注入生成主干，也没有“高 anchor/中 anchor 真实使用 source 条件”的生成逻辑。 |
| M19 OME-TIFF writer | 有 | 代码：`src/he_wsi_generator/outputs/ome_tiff.py::{write_pyramid_ome_tiff, write_pyramid_ome_tiff_from_tile_sources, write_pyramid_ome_tiff_streaming_from_tile_sources}`、`src/he_wsi_generator/outputs/masks.py::write_mask_array`。测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`。 | 已有可直接保留 | OME-TIFF pyramid、mask、disk tile source、streaming publish 都已有真实实现，远超过 Stage 5 最小 writer 目标。 |

### Stage 6

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M20 Per-WSI metadata | 有，但部分字段仍偏 placeholder | 代码：`src/he_wsi_generator/metadata/archive.py::{write_metadata, archive_sample}`、`src/he_wsi_generator/generation/executor::_metadata_payload`。测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`。 | 已有但需要简化/收敛 | `metadata.json` 已真实写出，但 source/path/mask mapping 等字段在 smoke/production path 下仍有统一占位写法，尚未完全回填到“真实上游输入来源”。 |
| M21 基础 QC | 有 | 代码：`src/he_wsi_generator/qc/engine::build_qc_report`、`src/he_wsi_generator/generation/production_streaming.py::build_streaming_tile_source_qc_report`、`src/he_wsi_generator/qc/reference.py::build_qc_reference_distribution`。测试：`tests/test_outputs_qc_archive.py`、`tests/test_qc_reference.py`、`tests/test_qc_review.py`。 | 已有可直接保留 | 基础完整性、pyramid、mask 对齐、颜色/清晰度/缝合 proxy 都已落地；虽然后续还有很多增强契约，但基本 QC 主线已具备。 |
| M22 Batch index 与最小归档 | 有 | 代码：`src/he_wsi_generator/metadata/archive.py::{append_batch_index, archive_sample}`。测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`。 | 已有可直接保留 | `metadata.json`、`qc.json`、`batch.jsonl` 的最小归档链路已成立，可直接沿用。 |

### Stage 7

| Module | 当前仓库中是否已有对应实现 | 真实代码路径、核心函数/类、现有测试路径 | 状态分类 | 与当前 module-stage 方案的差距 |
|---|---|---|---|---|
| M23 PySide6 单页控制台 | 有 | 代码：`src/he_wsi_generator/ui/pyside_app.py::{create_main_window, launch_ui}`。测试：`tests/test_ui.py`。 | 已有可直接保留 | 单页 UI 已覆盖数据输入、mapping、prior/model、生成参数、状态、输出摘要，符合 Stage 7 最小界面要求。 |
| M24 UI 配置持久化 | 有 | 代码：`src/he_wsi_generator/ui/config::{create_default_ui_config, save_ui_config, load_ui_config}`、`src/he_wsi_generator/ui/workflow::build_generation_config_from_form`。测试：`tests/test_ui.py`、`tests/test_ui_workflow.py`。 | 已有可直接保留 | JSON/YAML 配置持久化和从表单回写 generation config 的路径已经存在。 |
| M25 Job runner 与状态展示 | 有 | 代码：`src/he_wsi_generator/ui/jobs::JobRunner`、`src/he_wsi_generator/ui/controller::{JobStateStore, collect_output_summary}`、`src/he_wsi_generator/ui/workflow::{create_run_generation_job, run_queued_generation_job, load_generation_job_status}`。测试：`tests/test_job_runner.py`、`tests/test_ui_workflow.py`、`tests/test_ui.py`。 | 已有可直接保留 | 本地 job 调度、状态持久化和输出摘要展示都已形成真实链路。 |
| M26 端到端 smoke test | 有，但分散在多套 smoke 测试中 | 代码/入口：`src/he_wsi_generator/generation/executor.py`、`src/he_wsi_generator/ui/workflow.py`、CLI `run-generation` / UI job 路径。测试：`tests/test_generation_runner.py`、`tests/test_ui_workflow.py`、`tests/test_outputs_qc_archive.py`。 | 已有但需要简化/收敛 | 当前有多条分散 smoke 路径，但还不是一个“最小、固定、可重复”的 Stage 7 E2E 验收入口；后续应收束成一条标准 fixture 流程。 |

## Stage 级汇总

### 已基本具备的 Stage

- `Stage 1`
  - M01、M02 已稳定，M03 也已可用，足以支撑后续模块继续在现有骨架上收敛。
- `Stage 3`
  - M09-M11 已形成可保存、可加载、可进入 condition packet 的 prior artifact 主线。
- `Stage 6`
  - metadata、QC、batch archive 都有真实写出路径。
- `Stage 7`
  - 本地 UI、job runner、配置持久化和输出摘要都已形成真实可跑链路。

### 需要收敛的 Stage

- `Stage 2`
  - 需要把“mask 读取 -> label mapping -> 坐标对齐 -> 统一 6 类 mask artifact”收束成一条主线，而不是停留在分散 helper。
- `Stage 5`
  - 需要从多 backend 并行状态收敛出一条明确的核心生成主线；当前写出能力很强，但生成主线本身分散。
- `Stage 7 / M26`
  - 需要把现有分散 smoke 测试收束成一个固定的最小 E2E fixture。
- `Stage 1 / M03`、`Stage 6 / M20`
  - 输入 manifest/audit 字段、metadata 字段都需要向当前开发文档口径靠拢，减少 placeholder 和历史兼容噪声。

### 真正缺口

- `Stage 2 / M07`
  - 统一 6 类 mask 的对齐与合并主线尚未建立。
- `Stage 5 / M18`
  - 只有 source-conditioned 契约，没有真实 source-conditioned generation。
- `Stage 4`
  - 当前是全仓库最大的真实缺口。
  - M12 还是 training-index / batch contract 级实现。
  - M13-M15 以 smoke/contract 为主，不是开发文档定义的真实多倍率条件生成训练链路。


## 本轮审计结论摘要

- 可以直接沿用的底座主要在 `Stage 1`、`Stage 3`、`Stage 6`、`Stage 7`。
- 需要马上收敛的不是 writer、QC 或 UI，而是更前面的 `Stage 2 mask 主线` 和 `Stage 3 的 M08 连接层`。
- 当前真正不应继续“在现有 smoke/contract 上横向加料”的区域，是 `Stage 4` 的模型/训练层。
- 如果遵循“现有代码收敛式重构”，下一轮最合理的切入点不是再加新 backend，而是补齐 `M05 + M07`，随后再接 `M08` 和 `M12`。
