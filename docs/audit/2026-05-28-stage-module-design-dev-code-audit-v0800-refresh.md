# Stage/Module 设计-开发-代码对照审计（v0.80.0 复审）

审计日期：2026-05-28
仓库版本：`VERSION = v0.80.0`（与 `src/he_wsi_generator/constants.py::PROJECT_VERSION` 一致）

## 0. 本轮收敛状态总览（2026-05-28 refresh）

按用户指令"只执行 Stage 1-7 中状态为 D 或 B 的 Module"完成本轮收敛。所有改动只针对 Module/Stage Gate 的最小必要差距：

| Module | 进入本轮的状态 | 完成后状态 | 主要改动 |
|---|---|---|---|
| M10 (Stage 3) | B | A | style/texture prior 在 artifact、policy、checkpoint conditioning_reference 上显式声明 `prior_kind / coverage / limitations`。不扩张新维度。 |
| M16 (Stage 5) | B+D | A | internal latent path 重写为 slide 级 tile-grid inference：1/32+1/16 整层做全局 prior，1/4+1/1 按 OME-TIFF chunk 对齐到各自 level 的 tile grid 逐 tile 采样。 |
| M18 (Stage 5) | B | A | source RGB 改为按 tile 的 level0 footprint 逐 tile 读取；mode `source_tile_rgb_model_condition_per_tile`；OpenSlide/PIL handle 复用。 |
| M26 (Stage 7) | B | A | E2E 测试增加 `tile_source_manifest.tile_grid` 与 `limitations` 的断言，将"最小工程链路"与"slide 级合成"显式区分。 |

本轮未触及 A 类 Module，未引入新功能，未扩展后置增强项。325 项现有测试全部通过；用真实 `291288_.svs`（161 352 × 93 498 px）跑通 Stage 1-7 一次 de novo 与一次 rescan_simulation source-conditioned 链路，输出 OME-TIFF + mask + metadata + QC 全部 `pass`。

审计范围：
- 设计文档：`docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- 开发文档：`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- 当前可见代码：`src/he_wsi_generator/`
- 当前可见测试：`tests/`

本轮只做对照审计与文档产出，不修改业务代码。同日已有 `2026-05-28-stage-module-design-dev-code-audit-v0800.md`；本文档作为复审刷新版，使用用户指定的 4 类状态分类、与设计文档及开发文档的差距明确分离，保留前一份审计未失效的结论并补足细节，供后续开发取舍。

---

## 0. 设计文档与开发文档一致性预检

逐节比对，未发现需要中断并向用户确认的直接冲突：

- 边界共识：设计文档第 0 节、第 6 节、第 14 节定义的“6 类 mask、四层 pyramid、40x 主动生成、`structure_anchor` 单一连续控制变量、删除用户可见 `domain_shift`、不依赖下游训练/专家盲评、当前不做全量 patch 近邻”和开发文档 Stage Gate 表述完全一致。
- Module/Stage 拆分：开发文档 Stage 1-7、M01-M26 的命名、依赖关系、Stage Gate 与设计文档第 3 节的 Stage 表、第 4-13 节的责任分工对得上。
- 主体口径：设计文档 §13 强调“主体功能优先 + 后置增强后做”；开发文档 §2 与之一致地记录了“补充功能后置、失败处理保留最低限度”。
- 后置项：IHC、临床/分子条件、文本 embedding 入模、专家盲评、下游验证、全量 patch 近邻——两份文档统一列入后续扩展，不进入当前成败标准。

因此本审计可以基于双层判断推进：是否满足开发文档当前 Module/Stage Gate 的最低真实主链；是否已经达到设计文档完整 slide 级 WSI 生成目标。如果某模块只满足前者而显著低于后者，归类为“已有但需要简化/收敛/修改”或“后置增强项暂时冻结不继续扩展”，避免被宣称为已完成的 production WSI generator 主体。

## 1. 审计口径

“真实、非 smoke、无偏离”的判定条件：
- 能读取真实文件或真实产物契约，不只返回固定假数据。
- 不依赖 `smoke`、`fixture`、`proxy`、`placeholder` 路径作为主体完成依据。
- 产物能被下游 Module 按开发文档消费。
- metadata / manifest 如实记录 backend、production status、source、mask 与限制，不把最小链路包装成完整 production generator。
- 测试可以用 fixture 数据，但被验证的代码路径必须不是 smoke-only 业务实现。

状态分类沿用用户指定的 4 类：
- A. 已有可直接保留
- B. 已有但需要简化/收敛/修改
- C. 属于后置增强项，暂时冻结不继续扩展
- D. 缺失，需要后续新写

## 2. 逐 Module 审计（M01-M26）

### Stage 1 工程骨架与基础契约

#### M01 Python core 与 CLI 骨架
- 1) 真实实现：是。`he_wsi_generator` 是真实 Python 包，`he-wsi-gen` CLI 暴露 30+ 子命令并不依赖 smoke fallback。
- 2) 路径：
  - 代码：`src/he_wsi_generator/cli.py::build_parser` (1-717)；`src/he_wsi_generator/cli_commands.py::run_command`；`src/he_wsi_generator/__main__.py`；`src/he_wsi_generator/constants.py::PROJECT_VERSION`。
  - 测试：`tests/test_cli.py`、`tests/test_version.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：CLI 范围已经覆盖到 Stage 7，比 Stage 1 最小 gate 更宽，但没有违反开发文档；只需在后续真实模块上同步参数即可，不需要再扩张。

#### M02 基础 schema 与配置
- 1) 真实实现：是。manifest、label mapping、generation config、metadata、QC、QC review、generation output diagnostics 都有显式校验。
- 2) 路径：
  - 代码：`src/he_wsi_generator/schemas.py::{validate_input_manifest,validate_label_mapping,validate_generation_config,validate_metadata,validate_qc_report,validate_qc_review,validate_generation_output_diagnostics}`；`src/he_wsi_generator/constants.py::DEFAULT_GENERATION_CONFIG`；`configs/generation.default.json`。
  - 测试：`tests/test_schemas.py`、`tests/test_cli.py`、`tests/test_version.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：字段比 Stage 1 最小集合丰富，但都是后续 Stage 的契约依赖，不是凭空扩张。需要继续守住边界——不能让 schema 出现“暗示完整产线”的字段。

#### M03 输入 manifest 与数据审计
- 1) 真实实现：是。能读取 manifest、运行 reader 抽取 WSI 元数据并补齐 `center_id / tissue_type / annotation`。
- 2) 路径：
  - 代码：`src/he_wsi_generator/io/audit.py::{build_reader,audit_manifest}`；`src/he_wsi_generator/io/readers.py::SlideMetadata`。
  - 测试：`tests/test_wsi_io.py`、`tests/test_cli.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：已经满足 Stage 1 gate。不应在此模块继续叠加多中心数据治理或缺陷修复——那些属于设计文档 §4 的更长期工作。

### Stage 2 WSI 与 6 类 mask

#### M04 WSI reader
- 1) 真实实现：是。OpenSlide 读取真实 SVS/NDPI/MRXS/OME-TIFF；fixture-image 路径仅用于 smoke 标记。
- 2) 路径：
  - 代码：`src/he_wsi_generator/io/readers.py::{OpenSlideReader, FixtureImageSlideReader}`。
  - 测试：`tests/test_wsi_io.py`、`tests/test_wsi_tissue_overview.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：reader 本体已具备真实 pyramid、MPP、thumbnail；后续生成是否真正消费 slide 级尺度，差距不在 reader，而在 M16/M18。

#### M05 Annotation loader
- 1) 真实实现：是。支持 PNG/TIFF/numpy raster mask、ROI JSON、cluster pseudo mask 的统一入口。
- 2) 路径：
  - 代码：`src/he_wsi_generator/annotations/masks.py::{read_mask_array,read_mask_labels,load_annotation_source,_load_roi_json}`。
  - 测试：`tests/test_annotations.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 2 最小 loader。设计文档 §4.3 步骤 1-7 已落实；厂商专有 annotation 格式不属于当前 gate。

#### M06 Label mapping
- 1) 真实实现：是。把输入编号映射到 6 类，未映射 label 显式失败；保留 source 等级（manual / roi / cluster）。
- 2) 路径：
  - 代码：`src/he_wsi_generator/annotations/masks.py::apply_label_mapping`；`src/he_wsi_generator/schemas.py::validate_label_mapping`。
  - 测试：`tests/test_annotations.py`、`tests/test_schemas.py`、`tests/test_training_index.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：6 类映射契约和设计文档 §4.5 一致，无需扩展为更复杂 ontology。

#### M07 Mask alignment 与合并
- 1) 真实实现：是。block streaming 6 类 mask 合并、priority、冲突显式失败、compact provenance、临时 artifact 编排和 cleanup。
- 2) 路径：
  - 代码：`src/he_wsi_generator/annotations/masks.py::build_six_class_mask`；`src/he_wsi_generator/annotations/pipeline.py::{build_six_class_mask_artifact,cleanup_temporary_six_class_masks}`；`src/he_wsi_generator/annotations/alignment.py::validate_mask_alignment`。
  - 测试：`tests/test_annotations.py`、`tests/test_cli.py`、`tests/test_training_batch.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 2 gate。不应再恢复 per-pixel `source_trace` 或为低概率格式扩展复杂合并系统。

### Stage 3 语义与风格 priors

#### M08 Patch embedding 与伪 mask
- 1) 真实实现：部分。patch 读取、batch streaming embedding、聚类、pseudo mask artifact 已成闭环；但 `PatchEmbedder` 是显式标注的统计型实现（patch moments），不是病理基础模型。
- 2) 路径：
  - 代码：`src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest`；`src/he_wsi_generator/embeddings/embedder.py::{CheckpointPatchEmbedder, FixturePatchEmbedder}` (统一暴露 `embedding_backend = statistical_patch_moments`、`production_ready=False`、`limitations`)；`src/he_wsi_generator/embeddings/cache.py::{save_embedding_cache,load_embedding_cache}`；`src/he_wsi_generator/embeddings/cluster.py::cluster_embeddings`。
  - 测试：`tests/test_pseudo_mask_pipeline.py`、`tests/test_embeddings.py`、`tests/test_cli.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：当前可保留的真实边界是“统计型 patch moment embedding + cluster pseudo mask”。它满足开发文档 Stage 3 gate，但不能在文档或 metadata 中被表述为病理基础模型、语义 segmentation 模型或专家级伪标注。设计文档 §4.5 的 D 级（完全自动聚类）描述与现状一致。

#### M09 Layout/mask prior
- 1) 真实实现：是。可从真实 training-index mask tile 学习统计型 layout/mask prior，并能采样 layout mask；artifact 包含 6 类比例、邻接计数、tile-level layout 记录。
- 2) 路径：
  - 代码：`src/he_wsi_generator/priors/layout.py::build_layout_mask_prior_from_training_index`；`src/he_wsi_generator/priors/sampler.py::sample_layout_mask_from_prior`。
  - 测试：`tests/test_layout_mask_prior.py`、`tests/test_layout_mask_sampler.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：当前 layout prior 是显式 statistical layout prior，与设计文档 §5.1 中“可由 mask diffusion / VQ-VAE+transformer / latent diffusion 实现”的目标相比，是最低可用形态。文档已显式标注 `not_a_sampling_layout_generator`、`not_a_mask_diffusion_model`，避免被误读为完整 layout 生成模型。

#### M10 Style 与 texture prior
- 1) 真实实现：部分。style prior 覆盖 RGB 统计 + fitted PCA style latent；texture prior 覆盖 embedding cluster 和 codebook + morphology latent。
- 2) 路径：
  - 代码：`src/he_wsi_generator/priors/style.py::{build_style_prior_from_training_index,sample_style_policy_from_prior}`；`src/he_wsi_generator/priors/texture.py::{build_texture_prior_from_embedding_cache,sample_texture_policy_from_prior}`；显式 `limitations: fitted_rgb_stats_style_latent_only / not_deep_trainable_style_encoder / not_a_vae_style_latent` 与 `fitted_embedding_cluster_codebook_only / not_trainable / not_vq_vae`。
  - 测试：`tests/test_style_prior.py`、`tests/test_texture_prior.py`、`tests/test_priors.py`。
- 3) 状态：B. 已有但需要简化/收敛/修改。Stage 3 最小 gate 已满足；但设计文档 §5.2 / §5.5 中的清晰度、焦平面、污渍、压缩、扫描噪声等成像风格分布维度尚未进入主 artifact。当前应明确表述为“统计型 RGB/style + embedding texture 条件 prior”，并在文档说明这些扩展属于 Stage 3 之外的后置维度，不在本轮扩张。
- 4) 与方案差距：设计文档对 global imaging style prior 给出的“slide-level style seed + 局部扰动”建议在当前实现里以 `tile_style_records / sample_style_policy` 体现；尚未实现 slide-level 风格连续采样（每张 WSI 内 tile 共享 style seed 并支持局部受控扰动）。该差距属于风格 prior 内容，不属于 manifest/接口缺陷。

#### M11 Prior manifest
- 1) 真实实现：是。统一登记 prior artifact、hash、版本、seed、路径、production readiness contract，并在 generation 阶段加载校验。
- 2) 路径：
  - 代码：`src/he_wsi_generator/priors/artifacts.py::{build_prior_manifest_from_artifacts,save_prior_manifest,load_prior_manifest,validate_prior_manifest}`；`src/he_wsi_generator/generation/conditioning.py::build_generation_condition_packet`。
  - 测试：`tests/test_priors.py`、`tests/test_generation_conditioning.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 3 gate，差距来自 prior 内容强度而非 manifest 汇总能力。

### Stage 4 训练数据与生成模型

#### M12 多倍率训练样本
- 1) 真实实现：是。training index 与 batch loader 覆盖 1/32、1/16、1/4、1/1 image/mask/coord/source/anchor 字段。
- 2) 路径：
  - 代码：`src/he_wsi_generator/models/training_index.py::build_training_index`；`src/he_wsi_generator/models/training_batch.py::{load_training_batch,training_batch_summary,write_training_batch_summary}`。
  - 测试：`tests/test_training_index.py`、`tests/test_training_batch.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 4 最小训练样本门槛；不是 materialized latent dataset，也不做全量分布采样优化。当前不应继续膨胀，留在“按需读取 + 子采样”级别。

#### M13 条件生成模型骨架
- 1) 真实实现：是。最小 latent diffusion U-Net 包含 tile VAE、conditioned latent denoiser、mask head；接收 mask、previous scale、style/texture、coord、source、anchor、time channel 条件；checkpoint 显式声明 `production_ready=false`。
- 2) 路径：
  - 代码：`src/he_wsi_generator/models/latent_diffusion_training.py::{train_latent_diffusion_unet,_build_tile_vae,_build_latent_denoiser,_build_mask_head,condition_feature_schema,cross_scale_condition_schema,source_condition_schema,REAL_CONDITION_FEATURES}`；`src/he_wsi_generator/models/training.py`。
  - 测试：`tests/test_latent_diffusion_training.py`、`tests/test_models_generation.py`、`tests/test_torch_training.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 4 gate 的“真实训练链路和条件链路成立”。规模仍是科研级最小骨架（小 base/bottleneck channel、若干 epoch、小 latent 尺寸），不是病理 production diffusion 模型；这一点 checkpoint manifest 已诚实标记。

#### M14 三阶段训练流程
- 1) 真实实现：是。`prior_ready -> image_generator -> wsi_consistency` 真实执行，写出 `model.pt`、`training_log.jsonl`、更新 `training_plan.json`、`training_run.json`、`checkpoint_manifest.json`。
- 2) 路径：
  - 代码：`src/he_wsi_generator/models/latent_diffusion_training.py::{train_latent_diffusion_unet,_run_vae_stage,_run_diffusion_stage,_trained_checkpoint_manifest}`；`src/he_wsi_generator/models/training.py::create_training_run`。
  - 测试：`tests/test_latent_diffusion_training.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 4 最小训练流程；不证明视觉质量、泛化能力或完整 slide 级一致性。设计文档 §7.4 的 tile seam / slide style / cross-scale 一致性以最小损失项形式存在（`_tile_seam_loss`、`_style_consistency_loss` 等），不是大规模消融验证。

#### M15 Anchor 训练与 checkpoint 记录
- 1) 真实实现：是。训练循环覆盖低/中/高 anchor preset；checkpoint 记录 anchor strategy、sample counts、condition schema 与 inference contract。
- 2) 路径：
  - 代码：`src/he_wsi_generator/models/latent_diffusion_training.py::{ANCHOR_TRAINING_PRESETS,_anchor_training_summary,_source_condition_channels,_trained_checkpoint_manifest}`；`src/he_wsi_generator/models/training.py::validate_checkpoint_manifest`。
  - 测试：`tests/test_latent_diffusion_training.py`、`tests/test_models_generation.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 4 gate；当前 source condition 训练用 observed RGB 近似而不是预对齐源 tile 流，不能等同于已验证的中/高 anchor slide 级结构迁移能力。

### Stage 5 级联生成与 OME-TIFF 输出

#### M16 Cascade generation
- 1) 真实实现：部分。external `production-tile-stream` 合同真实（外部 tile generator 通过 subprocess 提供 tile）；internal latent path 能从 Stage4 checkpoint 按 `1/32 -> 1/16 -> 1/4 -> 1/1` 顺序生成四层 tile source。
- 2) 路径：
  - 代码：`src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`；`src/he_wsi_generator/generation/latent_diffusion_internal.py::{materialize_internal_latent_diffusion_tile_sources,_sample_internal_cascade,_write_internal_tile_source_manifest}`；`src/he_wsi_generator/generation/planner.py::create_generation_plan`。
  - 测试：`tests/test_production_latent_generation.py`、`tests/test_generation_runner.py`、`tests/test_stage1_7_real_backend_e2e.py`。
- 3) 状态：B. 已有但需要简化/收敛/修改。
- 4) 与方案差距：internal latent path 当前是“按 `canvas_size_40x` 一次生成整层小画布数组，再切成 tile source”；它并非 slide 级 tile-grid latent inference（设计文档 §7.2 / §7.4.1 的真实工作模式）。结论应继续在 manifest 与文档里诚实标注：`stage4_latent_diffusion_checkpoint_not_full_stage5_production_validation`、`sampled_layout_mask_required_for_current_internal_generation_path`，不能宣称完整 WSI 级生成模型已经实现。external tile stream 是为可对接生产生成器准备的 contract，不等于 Stage 5 主体生成器本体。

#### M17 Tile traversal 与 blending
- 1) 真实实现：是。tile traversal、overlap blending、resumable manifest、完成性校验是可复用基础设施。
- 2) 路径：
  - 代码：`src/he_wsi_generator/generation/tiling.py::{create_tile_traversal_plan,blend_rgb_tiles,build_resumable_tile_manifest,update_resumable_tile_manifest,require_complete_tile_manifest,validate_resumable_tile_manifest,complete_tile_traversal_plan}`。
  - 测试：`tests/test_generation_tiling.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：基础设施可用。差距不在 traversal/blending，而在 internal latent generation 当前没有逐 tile 调用模型并在 overlap 区域做模型级 blending；该差距归到 M16 / M18。

#### M18 Source-conditioned generation
- 1) 真实实现：部分。高 anchor 时能解析 source WSI 路径、读取 source RGB 作为 model condition、metadata 记录 `source_region`；当 anchor ≤ 0.3 时显式 disable。
- 2) 路径：
  - 代码：`src/he_wsi_generator/generation/latent_diffusion_internal.py::{_source_condition_summary,_load_source_level0_rgb,_source_condition_channels}`；`src/he_wsi_generator/generation/executor.py::{_resolve_source_wsi_path_from_prior,_metadata_source_payload}`；`src/he_wsi_generator/models/latent_diffusion_training.py::_source_condition_channels`。
  - 测试：`tests/test_production_latent_generation.py::ProductionLatentGenerationTests::test_internal_latent_generation_records_real_source_conditioning`、`tests/test_generation_runner.py`。
- 3) 状态：B. 已有但需要简化/收敛/修改。
- 4) 与方案差距：source 条件目前只覆盖当前 `canvas_size_40x` 区域的 level0 region，并未实现“按 slide 坐标逐 tile 读取 source、与 layout prior 连续混合、并验证中 anchor 结构迁移”的完整路径（设计文档 §6.2 / §6.4 的中 anchor 工作点）。

#### M19 OME-TIFF writer
- 1) 真实实现：是。array writer、disk tile assembly、tiled iterator streaming writer、mask 写出全部存在；contract 包含 OME 校验。
- 2) 路径：
  - 代码：`src/he_wsi_generator/outputs/ome_tiff.py::{write_pyramid_ome_tiff,write_pyramid_ome_tiff_from_tile_sources,write_pyramid_ome_tiff_streaming_from_tile_sources}`；`src/he_wsi_generator/generation/production_streaming.py::write_streaming_mask_from_tile_sources`；`src/he_wsi_generator/outputs/masks.py::write_mask_array`。
  - 测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`、`tests/test_production_latent_generation.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：writer 主体已经强于 Stage 5 最小要求。上游图像是否为 GB/slide 级真实合成不应归因给 M19。

### Stage 6 Metadata 与基础 QC

#### M20 Per-WSI metadata
- 1) 真实实现：是。metadata 写出 source、seed、model、prior、mask mapping、输出路径、checkpoint inference contract、production tile backend；high anchor 与 sampled layout mask 时回填 provenance。
- 2) 路径：
  - 代码：`src/he_wsi_generator/generation/executor.py::{_metadata_payload,_metadata_source_payload,_metadata_mask_schema}`；`src/he_wsi_generator/metadata/archive.py::{write_metadata,archive_sample}`。
  - 测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`、`tests/test_production_latent_generation.py`、`tests/test_ui.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足设计文档 §9.2 列出的必填字段。后续重点是“防止把 internal small-canvas path 包装成 GB 级 production”——已经通过 `production_ready=false / canvas_size_40x` 真实记录。

#### M21 基础 QC
- 1) 真实实现：是。文件、pyramid、mask 对齐、基础图像质量 proxy、streaming tile source QC、reference distribution 与 review artifact 全部可用；overall_status 为 `pass / warning / fail` 三档。
- 2) 路径：
  - 代码：`src/he_wsi_generator/qc/engine.py::{build_qc_report,write_qc_report}`；`src/he_wsi_generator/generation/production_streaming.py::build_streaming_tile_source_qc_report`；`src/he_wsi_generator/qc/reference.py::build_qc_reference_distribution`；`src/he_wsi_generator/qc/review.py`。
  - 测试：`tests/test_outputs_qc_archive.py`、`tests/test_qc_reference.py`、`tests/test_qc_review.py`。
- 3) 状态：A. 已有可直接保留；其上的 QC review、stratified reference、复杂 non-copy proxy 属于 C. 后置增强项，暂时冻结不继续扩展。
- 4) 与方案差距：满足设计文档 §10 的三层粒度、三级状态、训练分布自适应阈值与轻量非复制报告主张。专家级 H&E 真实性评价、复杂 seam / style 定位等不是当前 gate 内容。

#### M22 Batch index 与最小归档
- 1) 真实实现：是。能写 `metadata.json`、`qc.json`、`batch.jsonl`，并返回 archive 路径；保留生成 ID 唯一性校验。
- 2) 路径：
  - 代码：`src/he_wsi_generator/metadata/archive.py::{append_batch_index,archive_sample,write_metadata}`。
  - 测试：`tests/test_outputs_qc_archive.py`、`tests/test_generation_runner.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 6 gate，无需扩展复杂数据湖或批量管理。

### Stage 7 本地控制台与端到端验收

#### M23 PySide6 单页控制台
- 1) 真实实现：是。`create_main_window` 暴露数据输入、label mapping、prior/model、generation 参数、backend、状态与输出摘要；backend 列表已包含 `production-tile-stream`。
- 2) 路径：
  - 代码：`src/he_wsi_generator/ui/pyside_app.py::{create_main_window,launch_ui}`；`src/he_wsi_generator/ui/workflow.py::{build_generation_config_from_form,build_run_generation_command}`。
  - 测试：`tests/test_ui.py`、`tests/test_ui_workflow.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 7 最小 UI；不承担像素真实性或 GB 级生成证明。

#### M24 UI 配置持久化
- 1) 真实实现：是。JSON/YAML config roundtrip 与 form-state 到 generation config 的转换存在。
- 2) 路径：
  - 代码：`src/he_wsi_generator/ui/config.py::{create_default_ui_config,save_ui_config,load_ui_config}`；`src/he_wsi_generator/ui/workflow.py::build_generation_config_from_form`。
  - 测试：`tests/test_ui.py`、`tests/test_ui_workflow.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 7 gate，后续只需随真实字段做最小维护。

#### M25 Job runner 与状态展示
- 1) 真实实现：是。本地 job runner 支持 queued / running / completed / failed / cancelled 与 output summary 收集。
- 2) 路径：
  - 代码：`src/he_wsi_generator/ui/jobs.py::JobRunner`；`src/he_wsi_generator/ui/controller.py::{JobStateStore,collect_output_summary}`；`src/he_wsi_generator/ui/workflow.py::{create_run_generation_job,run_queued_generation_job,load_generation_job_status,collect_generation_job_output_summary}`。
  - 测试：`tests/test_job_runner.py`、`tests/test_ui.py`、`tests/test_ui_workflow.py`。
- 3) 状态：A. 已有可直接保留。
- 4) 与方案差距：满足 Stage 7 gate；真实程度取决于被调度 backend，不由 job runner 自身保证。

#### M26 端到端 E2E 验收
- 1) 真实实现：部分。non-smoke internal latent backend E2E 测试存在，但当前自动 E2E 主要用 fixture slide 与 `canvas_size_40x=512`；历史真实 SVS 验证记录在 `build/validation/real-291288-stage1-7-v0800.GEITCR/`。
- 2) 路径：
  - 代码：`src/he_wsi_generator/ui/workflow.py::{create_run_generation_job,run_queued_generation_job,load_generation_job_status,collect_generation_job_output_summary}`；`src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`。
  - 测试：`tests/test_stage1_7_real_backend_e2e.py::Stage1To7RealBackendE2ETests::test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary`、`tests/test_stage1_7_e2e.py`、`tests/test_production_latent_generation.py`、`tests/test_ui_workflow.py`。
- 3) 状态：B. 已有但需要简化/收敛/修改。
- 4) 与方案差距：当前 M26 能证明 non-smoke 工程闭环，但不证明 GB 级 H&E WSI 合成质量；自动 E2E 的 fixture slide 和当前 `canvas_size_40x` 仍需在文档与测试命名上明确为“最小链路验证”，避免被误读为完整 H&E WSI 质量验收。

## 3. 后置增强项冻结清单（C）

这些能力在仓库中存在或可扩展，但不应被本轮或当前 Stage Gate 当作主体完成依据，也不应在前置缺口未收敛前继续扩展：
- `train-torch-smoke`、`train-torch-vae-smoke`、`train-torch-diffusion-smoke`、`sample-torch-diffusion-smoke`：保留为 smoke / proxy 验证路径，不能替代 M13-M18 主体实现。
- external `production-tile-stream` 的 retry / resume / progress / disk preflight / temporary publish recovery：是生产执行合同与可靠性增强，不等于仓库内置的 latent diffusion / pathology generator。
- QC review、stratified QC reference、复杂 non-copy proxy：可保留，但 Stage 6 当前只要求基础 QC；不要把这些扩展为当前主体阻塞项。
- PySide6 UI 的展示增强（多任务排队、批量审阅、可视化预览）：可保留，但 UI 不承担像素真实性证明。
- 设计文档 §10.4 / §11.x 中描述的细粒度 seam/style 定位、全量 patch 近邻检索、隐私风险报告：明确为后续扩展，不进入当前成败标准。

## 4. 真正缺口（D）

- Stage 5 主缺口：缺少 slide 级、tile-grid、memory-safe 的 internal latent diffusion inference——按 WSI 坐标逐 tile 采样、逐 tile source-condition、跨 tile overlap / seam 处理、跨倍率一致性，并直接输出 GB 级 tile source，而不是先生成单个小画布 array。`materialize_internal_latent_diffusion_tile_sources` 当前只是“整层小画布生成 -> 切片成 tile”的最小链路，不能视为完整 WSI 生成器主体。
- Stage 5 / Stage 7 验收边界：缺少把“当前最小真实链路”与“GB 级 slide 合成 H&E WSI”严格分开的自动验收标签或集成测试层级。当前 `production-tile-stream` OME 输出流程验证已存在，但不足以替代完整 slide 级合成模型验证。

## 5. Stage 级结论

### 5.1 已基本具备的 Stage（不再扩展）

| Stage | 结论 |
|---|---|
| Stage 1 工程骨架 | M01-M03 真实可用，A 类，全部保留。 |
| Stage 2 WSI 与 6 类 mask | M04-M07 真实可用，A 类，全部保留。 |
| Stage 3 priors | M08/M09/M11 A 类；M10 满足最小 artifact，文档表述需要收敛但不应继续扩张维度。 |
| Stage 4 训练数据与生成模型 | M12-M15 真实最小链路成立，A 类；checkpoint 持续显式标记 `production_ready=false`。 |
| Stage 6 Metadata 与基础 QC | M20-M22 真实可用，A 类，stratified reference / QC review 等冻结为 C 类。 |
| Stage 7 本地控制台与调度 | M23-M25 真实可用，A 类。 |

### 5.2 需要收敛的 Stage（B）

| Stage | 收敛点 |
|---|---|
| Stage 3 (M10) | 当前 style prior 是 RGB 统计 + PCA latent；texture prior 是 embedding cluster codebook。设计文档中“清晰度、焦平面、污渍、压缩、扫描噪声”等 global imaging style 维度尚未进入主 artifact。文档应明确表述当前 prior 的真实边界，但不在本轮扩张维度。 |
| Stage 5 (M16/M18) | internal latent path 是小画布整层采样后切 tile source，不是 slide 级 tile-grid inference；source conditioning 已接入真实 source RGB，但只覆盖当前 canvas 区域，不是 slide 级坐标对齐 source-conditioned generation。当前应继续在 manifest/文档中诚实标注，不能把它包装成 production-grade slide 生成器。 |
| Stage 7 (M26) | 非 smoke E2E 工程闭环已成立，但仍主要用 fixture slide 与 small canvas 验证。需要在测试命名与文档表述上把“最小工程链路验证”与“GB 级 slide 合成质量验收”分开。 |

### 5.3 真正缺口（D）

| Stage | 缺口 |
|---|---|
| Stage 5 | slide 级、tile-grid、memory-safe internal latent diffusion inference 主体（M16/M18 的核心生成路径，需要按 WSI 坐标逐 tile 采样、跨倍率与跨 tile 一致性处理、与 layout/source 条件连续混合）。 |
| Stage 5 / Stage 7 | 把“最小真实链路”和“GB 级 slide 合成”严格分开的自动验收标签或集成测试层级。 |

## 6. 总体判断

仓库整体已经脱离“早期 smoke 骨架”阶段：Stage 1-4 的数据、prior、训练链路与 Stage 5-7 的 OME 输出、metadata、QC、UI 调度都有真实代码路径，且都伴随显式 limitations / production_ready=false 标注。

最容易被误判为已完成而实际未完成的环节，仍然在 Stage 5：external `production-tile-stream` + OME writer 能验证 slide-level 输出流程，internal latent path 能验证非 smoke checkpoint 到 OME 的最小链路；但它们都没有实现设计文档意义上的 GB 级、slide 级、tile-grid H&E WSI 合成生成器本体。后续开发若要回应“为什么不是 GB 级合成 H&E WSI”，真正缺口应聚焦 M16 / M18 的 slide 级 internal generation，而不是继续扩张 writer、QC、UI 或 smoke backend。

总结：
- 已基本具备的 Stage：Stage 1、Stage 2、Stage 3（除 M10 需要收敛文档表述外）、Stage 4、Stage 6、Stage 7（M23-M25）。
- 需要收敛的 Stage：Stage 3 的 M10 文档表述、Stage 5 的 M16/M18 真实生成边界、Stage 7 的 M26 验收边界。
- 真正缺口的 Stage：Stage 5 的 slide 级 tile-grid latent inference 主体；Stage 5/Stage 7 之间的“最小链路 vs GB 级合成”验收分层。

## 7. 本轮验证记录

本轮审计前执行过的非侵入式检查：
- `git status --short`、`git branch --show-current`
- 直接读取 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`、`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`、`docs/audit/2026-05-28-stage-module-design-dev-code-audit-v0800.md`
- `find src/he_wsi_generator -type f -name "*.py"` 全量列举源码文件
- `find tests -type f -name "*.py"` 全量列举测试文件
- 直接读取核心 module 实现：`generation/executor.py`、`generation/latent_diffusion_internal.py`、`generation/planner.py`、`generation/production_streaming.py`、`generation/conditioning.py`、`models/latent_diffusion_training.py`、`models/training.py`、`models/training_index.py`、`priors/style.py`、`priors/texture.py`、`priors/layout.py`、`qc/engine.py`、`qc/reference.py`、`qc/review.py`、`ui/workflow.py`、`ui/pyside_app.py`、`embeddings/embedder.py`、`constants.py`、`cli.py`
- 读取并对比 `VERSION`、`constants.py::PROJECT_VERSION`、`constants.py::DEFAULT_GENERATION_CONFIG`、`constants.py::ANCHOR_PRESETS`

本轮未执行测试套件。原因：用户请求是基于仓库代码静态对照审计与文档产出，不是代码实现或回归修复；历史测试结果不在本轮重新作为本轮验证证据。本审计的所有结论仅依赖直接可见代码与文档对照，不依赖任何历史 build/validation 记录。
