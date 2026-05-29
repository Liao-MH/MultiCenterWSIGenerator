# H&E WSI 数据生成器：模块化分阶段开发文档

日期：2026-05-26
版本：v0.5.1-stage-module
状态：主体功能优先的分阶段开发计划
来源范围：
- [2026-05-18-he-wsi-generator-study-design.md](../plans/2026-05-18-he-wsi-generator-study-design.md)
- [2026-05-23-he-wsi-generator-development-appendix.md](./2026-05-23-he-wsi-generator-development-appendix.md)

---

## 1. 文档目的

针对于完成一个科研级别工具而非商业产品的开发。本文档把现有研究设计重组为“Module + Stage”的开发版本。它不重新定义系统目标，也不引入源文档之外的新功能，只把已有设计整理成更便于实施的开发顺序。

本版采用“主体功能优先”的开发取向：先打通 H&E WSI 数据生成器的核心链路，再补充更细的错误兜底、复杂 QC、非复制分析和诊断报告。换句话说，第一轮开发应优先回答“系统能否从输入 WSI 走到生成 OME-TIFF WSI、mask、metadata 和基础 QC”，而不是把大量精力提前放在所有边界失败情况上。

本文档中的 `Module` 是开发过程中的最小实现单位。一个 Module 对应一项可交付工程能力，不细分到单个 helper 或内部函数。本文档中的 `Stage` 是进度管理单位，带有严格时间顺序：完成 Stage 1 后才能进入 Stage 2，依次推进。

## 2. 开发取向

| 原则 | 本版处理方式 |
|---|---|
| 主体链路优先 | 优先实现数据导入、mask、prior、训练、生成、OME-TIFF、metadata、基础 QC 和 UI 调度 |
| 补充功能后置 | 非复制报告、细粒度诊断、高级失败归因、复杂阈值策略不作为早期独立开发主线 |
| 失败处理保留最低限度 | 只对会阻断主体链路的输入缺失、坐标不明、checkpoint/prior 缺失、写出失败做明确阻断 |
| Module 不过细 | 每个 Module 是一个可验收能力，不拆成零散函数级任务 |
| Stage 数量受控 | 全项目共 7 个 Stage，不超过 10 个 |
| Stage 内 Module 数量受控 | 每个 Stage 最多 4 个 Module，不超过 20 个 |
| Core first | 先实现 Python core 和 CLI，再接入 PySide6 桌面控制台 |

## 3. Stage 总览

| Stage | 名称 | 主体目标 | 包含 Module | 进入下一阶段的最低门槛 |
|---|---|---|---|---|
| Stage 1 | 工程骨架与基础契约 | 建立 core package、CLI、最小 schema 和输入 manifest | M01-M03 | 能读取/校验项目配置和输入 manifest |
| Stage 2 | WSI 与 6 类 mask | 读取 WSI、annotation，并形成统一 6 类 mask | M04-M07 | 每张可用 WSI 有 thumbnail、pyramid metadata 和对齐 mask |
| Stage 3 | 语义与风格 priors | 形成 layout/mask、style、texture 等生成条件 | M08-M11 | 生成模型可加载 prior artifact 和 prior manifest |
| Stage 4 | 训练数据与生成模型 | 构造训练样本并训练结构锚定多倍率生成模型 | M12-M15 | 可产出 checkpoint、训练配置和 anchor 条件记录 |
| Stage 5 | 级联生成与 OME-TIFF 输出 | 执行 1/32 -> 1/16 -> 1/4 -> 1/1 生成并写出 WSI | M16-M19 | 生成 OME-TIFF pyramid、mask 和基本运行记录 |
| Stage 6 | Metadata 与基础 QC | 写出可追溯 metadata、batch index 和基础 QC | M20-M22 | 每个样本有 metadata.json、qc.json、batch.jsonl 记录 |
| Stage 7 | 本地控制台与端到端验收 | 用 PySide6 调度 core/CLI 并完成一次完整生成流程 | M23-M26 | 用户可通过 UI 或 CLI 完成一次可复现生成任务 |

## 4. Module 全局清单

| Module | 所属 Stage | 名称 | 主体实现内容 | 最小产物 |
|---|---|---|---|---|
| M01 | Stage 1 | Python core 与 CLI 骨架 | 建立 `he_wsi_generator` 包、核心目录和 `he-wsi-gen` CLI 入口 | 可运行的空骨架命令 |
| M02 | Stage 1 | 基础 schema 与配置 | 定义 input manifest、label mapping、generation config、metadata、QC 的最小字段 | schema 文件和示例配置 |
| M03 | Stage 1 | 输入 manifest 与数据审计 | 汇总 WSI 路径、center、cancer_type、tissue_type、MPP、split | input manifest 与 audit summary |
| M04 | Stage 2 | WSI reader | 读取 WSI pyramid、thumbnail、level metadata 和 MPP | WSI metadata 与 thumbnail |
| M05 | Stage 2 | Annotation loader | 读取 PNG/numpy/ROI annotation 并保留坐标层级 | raw mask 或 ROI object |
| M06 | Stage 2 | Label mapping | 将 annotation 编号映射到 6 类 mask | label mapping JSON |
| M07 | Stage 2 | Mask alignment 与合并 | 对齐 WSI/mask 坐标，合并人工 mask、ROI 和伪 mask 候选 | 对齐后的 6 类 mask |
| M08 | Stage 3 | Patch embedding 与伪 mask | 抽取 tissue patch、运行 PatchEmbedder、聚类形成伪 mask 候选 | embedding cache、pseudo mask、cluster report |
| M09 | Stage 3 | Layout/mask prior | 学习组织轮廓、区域比例、邻接关系和低倍 mask 分布 | layout_mask_prior |
| M10 | Stage 3 | Style 与 texture prior | 学习 slide-level style seed、颜色/清晰度分布和局部 texture codebook | style_prior、texture_prior |
| M11 | Stage 3 | Prior manifest | 将 prior artifact、训练数据、seed、版本和路径统一登记 | prior_manifest |
| M12 | Stage 4 | 多倍率训练样本 | 构造 1/32、1/16、1/4、1/1 图像或 latent、mask、coord、style、source、anchor | training index |
| M13 | Stage 4 | 条件生成模型骨架 | 实现 latent diffusion U-Net 主干及 mask、上一尺度、style、coord、source、anchor 条件接口 | model module |
| M14 | Stage 4 | 三阶段训练流程 | 执行 prior 条件准备、mask-conditioned 多倍率训练、WSI 一致性微调 | checkpoint、training log |
| M15 | Stage 4 | Anchor 训练与 checkpoint 记录 | 训练模型响应高、中、低 `structure_anchor`，登记 checkpoint 信息 | checkpoint manifest |
| M16 | Stage 5 | Cascade generation | 按 1/32 -> 1/16 -> 1/4 -> 1/1 顺序生成各层中间结果 | cascade outputs |
| M17 | Stage 5 | Tile traversal 与 blending | 按 tile grid 生成 40x tile，并用 overlap 做基础融合 | generated tiles |
| M18 | Stage 5 | Source-conditioned generation | 支持高 anchor 和中 anchor 时使用 source WSI 条件 | source-aware generated outputs |
| M19 | Stage 5 | OME-TIFF writer | 将 generated tiles 和 mask 写出为 OME-TIFF pyramid 与对齐 mask | `generated.ome.tiff`、`generated_mask/` |
| M20 | Stage 6 | Per-WSI metadata | 记录 source、seed、model、prior、mask mapping、输出路径 | `metadata.json` |
| M21 | Stage 6 | 基础 QC | 检查文件完整性、pyramid 层级、mask 对齐和基础图像质量 | `qc.json` |
| M22 | Stage 6 | Batch index 与最小归档 | 汇总一批生成样本的 metadata、QC 和输出路径 | `batch.jsonl`、run summary |
| M23 | Stage 7 | PySide6 单页控制台 | 提供数据输入、mapping、prior/model、生成参数、任务状态和输出查看区域 | 本地 UI |
| M24 | Stage 7 | UI 配置持久化 | 将用户设置保存为 JSON/YAML，并交给 core/CLI 执行 | job config |
| M25 | Stage 7 | Job runner 与状态展示 | 调度 core/CLI 任务，展示 queued/running/completed/failed 状态 | job status |
| M26 | Stage 7 | 端到端 E2E 验收 | 用非 smoke backend 跑通输入、生成、输出、metadata、QC、UI config | E2E result |

## 5. Stage 详细开发顺序

### Stage 1：工程骨架与基础契约

Stage 1 只做主体链路的地基，不展开复杂错误系统。目标是让后续所有模块有共同入口、共同配置和共同数据记录格式。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M01 | 建立 Python package、core 目录和 CLI 命令入口 | CLI 能显示主要命令组 |
| M02 | 建立最小 schema 和示例配置 | manifest、mapping、generation config 能校验 |
| M03 | 读取输入 manifest 并生成基础 audit summary | 可列出 WSI、MPP、split、annotation 路径 |

Stage Gate：
- 能从配置文件读取一次项目输入。
- 能把输入 WSI 记录整理为 manifest。
- 对完全缺失路径、缺少核心字段这类阻断问题做直接报错即可。

### Stage 2：WSI 与 6 类 mask

Stage 2 是第一个真正的数据功能阶段。它的目标不是处理所有 annotation 边界情况，而是先形成可供 prior 和模型训练使用的统一 6 类 mask。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M04 | 读取 WSI pyramid、thumbnail、MPP 和 level metadata | 能读取样本 WSI 并输出 metadata |
| M05 | 读取 PNG/numpy/ROI annotation | 能得到 raw mask 或 ROI object |
| M06 | 将输入编号映射到 6 类 mask | 输出 label mapping JSON |
| M07 | 对齐 WSI/mask 坐标并合并 mask 来源 | 输出对齐的 6 类 mask |

Stage Gate：
- 每张进入训练链路的 WSI 有 thumbnail、pyramid metadata 和 6 类 mask。
- 若没有人工 annotation，允许标记为待 Stage 3 伪 mask 补全。
- 只处理明显阻断问题，例如 mask 尺寸完全无法对齐或编号未映射。

### Stage 3：语义与风格 priors

Stage 3 把 WSI 数据转为生成模型可使用的条件对象。此阶段保留 patch embedding 和聚类伪 mask，因为它们直接服务于主体生成能力；复杂置信度解释和精细失败归因后置。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M08 | 抽取 patch、生成 embedding、聚类 pseudo mask | 生成 embedding cache、pseudo mask、cluster report |
| M09 | 学习 layout/mask prior | 能保存并加载 layout_mask_prior |
| M10 | 学习 style 和 texture prior | 能保存并加载 style_prior、texture_prior |
| M11 | 统一保存 prior manifest | generation/training config 可引用 prior_manifest |

Stage Gate：
- 训练流程可以加载 layout、mask、style、texture 条件。
- prior artifact 有 manifest 记录路径、seed 和输入数据版本。
- 若某个高级 prior 暂不成熟，可以先保留接口和最小 artifact，不阻断主体训练。

Implementation Trace:
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/io/audit.py::audit_manifest，落实 M03，输出包含 `center_id`、`tissue_type` 和 annotation 摘要的 manifest audit。
  - src/he_wsi_generator/annotations/masks.py::{load_annotation_source, build_six_class_mask}，落实 M05/M07，统一读取 annotation，并按 block streaming 合并为 6 类 level0 mask。
  - src/he_wsi_generator/annotations/pipeline.py::{build_six_class_mask_artifact,cleanup_temporary_six_class_masks}，落实 M07 的 artifact 编排、临时 full mask 标记和成功后 cleanup。
  - src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest，落实 M08 的 batch streaming patch embedding / clustering / pseudo-mask 闭环。
- 完整依赖：
  - 入口与编排：
    - src/he_wsi_generator/cli.py::build_parser，新增 `build-six-class-mask` 和带 `--batch-size` 的 `build-pseudo-mask` 命令。
    - src/he_wsi_generator/cli_commands.py::run_command，连接 Stage 1-3 新命令到 core。
  - 输入契约：
    - src/he_wsi_generator/schemas.py::validate_input_manifest，校验 manifest 和 annotation record。
    - src/he_wsi_generator/schemas.py::validate_label_mapping，校验 6 类 label mapping。
  - 输出契约：
    - src/he_wsi_generator/outputs/masks.py::{write_mask_array,write_mask_metadata}，写出普通 mask array 或 streaming memmap mask 的 metadata。
    - src/he_wsi_generator/annotations/pipeline.py::build_six_class_mask_artifact，写出 compact provenance summary、临时 mask 标记和 cleanup policy。
    - src/he_wsi_generator/priors/pseudo_mask.py::{build_pseudo_mask_from_manifest,_build_embedding_summary}，写出 `cluster_report.json`、`pseudo_mask.npy`、`cluster_pseudo_mask.json`、batch streaming 元数据和顶层 `embedding_summary`。
  - 核心逻辑：
    - src/he_wsi_generator/io/readers.py::{OpenSlideReader, FixtureImageSlideReader}，读取 metadata、thumbnail 和 level0 patch。
    - src/he_wsi_generator/annotations/alignment.py::validate_mask_alignment，校验 raster mask 的 transform。
    - src/he_wsi_generator/annotations/masks.py::_merge_source_into_block，统一处理 ROI/mask source 的 block-local 合并、优先级覆盖和同优先级冲突。
    - src/he_wsi_generator/embeddings/embedder.py::{CheckpointPatchEmbedder, FixturePatchEmbedder}，生成统计型 patch embedding，并显式暴露 `embedder_kind / embedding_backend / limitations`。
    - src/he_wsi_generator/embeddings/cache.py::{save_embedding_cache, load_embedding_cache}，保存/读取 embedding cache。
    - src/he_wsi_generator/embeddings/cluster.py::cluster_embeddings，生成 cluster labels / counts / inertia，并修正重复前导样本初始化退化。
  - 配置与默认值：
    - src/he_wsi_generator/constants.py::{PROJECT_VERSION, DEFAULT_GENERATION_CONFIG}，同步本轮版本与默认 schema version。
  - 错误处理：
    - src/he_wsi_generator/annotations/masks.py::MaskMappingError，负责 transform 非整数对齐、越界、未映射编号和同优先级冲突的显式失败。
    - src/he_wsi_generator/annotations/pipeline.py::AnnotationPipelineError，负责 manifest/audit/mapping 组合阶段的显式失败。
    - src/he_wsi_generator/annotations/pipeline.py::cleanup_temporary_six_class_masks，在目标输出缺失时拒绝删除临时 full mask。
    - src/he_wsi_generator/priors/pseudo_mask.py::PseudoMaskBuildError，负责 patch extraction、embedder、cluster 和输出阶段的显式失败。
  - 输出与持久化：
    - src/he_wsi_generator/io/audit.py::audit_manifest，写出 manifest audit JSON。
    - src/he_wsi_generator/annotations/pipeline.py::build_six_class_mask_artifact，写出 `six_class_mask_summary.json`、每张 WSI 的临时 mask artifact 和 compact provenance summary。
    - src/he_wsi_generator/annotations/pipeline.py::cleanup_temporary_six_class_masks，全流程目标输出存在后删除临时 full level0 six-class mask。
    - src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest，写出 pseudo-mask 相关 artifact。
  - 测试覆盖：
    - tests/test_wsi_io.py::WSIIOTests::test_audit_manifest_fills_metadata_from_reader，验证 M03 audit 收敛。
    - tests/test_annotations.py::AnnotationTests::test_load_annotation_source_reads_roi_json，验证 M05 ROI loader。
    - tests/test_annotations.py::AnnotationTests::test_build_six_class_mask_merges_manual_roi_and_pseudo_sources，验证 M07 合并优先级。
    - tests/test_annotations.py::AnnotationTests::test_build_six_class_mask_rejects_same_priority_conflict，验证 M07 冲突失败。
    - tests/test_annotations.py::AnnotationTests::test_cleanup_temporary_six_class_masks_requires_target_outputs_before_deleting，验证临时 full mask 删除保护。
    - tests/test_embeddings.py::EmbeddingTests::test_checkpoint_embedder_outputs_finite_embedding_metadata，验证 M08 统计型 checkpoint embedder metadata 和限制说明。
    - tests/test_embeddings.py::EmbeddingTests::test_fixture_embedder_marks_low_confidence，验证 fixture embedder 的 smoke-only 限制说明。
    - tests/test_embeddings.py::EmbeddingTests::test_cluster_embeddings_handles_duplicate_leading_rows，验证 M08 cluster 初始化修正。
    - tests/test_pseudo_mask_pipeline.py::PseudoMaskPipelineTests::test_build_pseudo_mask_from_manifest_writes_embedding_cache_and_cluster_mask，验证 M08 闭环产物和 `cluster_pseudo_mask.json.embedding_summary`。
    - tests/test_pseudo_mask_pipeline.py::PseudoMaskPipelineTests::test_build_pseudo_mask_from_manifest_streams_patch_embedding_batches，验证 M08 batch streaming。
    - tests/test_training_batch.py::TrainingBatchTests::test_load_training_batch_reads_npy_mask_with_mmap_mode，验证 downstream mask tile 读取使用 mmap。
    - tests/test_cli.py::CliValidationTests::{test_cli_builds_six_class_mask_summary,test_cli_builds_pseudo_mask}，验证 CLI 入口和 pseudo-mask 产物摘要。
  - 脚本与命令：
    - 无新增 shell 脚本；统一通过 `he-wsi-gen` CLI 命令执行。
- 调用链 / 实现流程：
  manifest -> audit_manifest -> load_annotation_source -> build_six_class_mask(block streaming) -> write_mask_metadata -> cleanup_temporary_six_class_masks
  manifest -> patch batch iterator -> statistical PatchEmbedder(batch) -> save_embedding_cache -> cluster_embeddings(all embeddings) -> build_embedding_summary -> pseudo_mask.npy(open_memmap)
- 外部关键依赖：
  - Pillow，用于 fixture-image/ROI 相关读取。
  - openslide-python，用于真实 WSI metadata/thumbnail/patch 读取。
  - numpy，用于 mask、embedding 和 pseudo-mask 数组处理。
- 参考行号：
  - src/he_wsi_generator/io/audit.py 16-54，manifest audit 收敛。
  - src/he_wsi_generator/annotations/masks.py 87-189，block streaming six-class merge 入口与 compact provenance 汇总。
  - src/he_wsi_generator/annotations/masks.py 272-592，block-local mask/ROI 合并、冲突记录和 provenance counts。
  - src/he_wsi_generator/annotations/pipeline.py 14-130，six-class mask artifact 编排与临时 mask cleanup helper。
  - src/he_wsi_generator/embeddings/embedder.py 24-109，统计型 checkpoint/fixture embedder metadata 与限制声明。
  - src/he_wsi_generator/priors/pseudo_mask.py 17-129，pseudo-mask 主入口、`embedding_summary` 写出和 memmap artifact 编排。
  - src/he_wsi_generator/priors/pseudo_mask.py 157-347，patch batch extraction、embedding streaming 和 pseudo-mask 写盘。
  - src/he_wsi_generator/priors/pseudo_mask.py 350-367，artifact 顶层 `embedding_summary` 构建。
  - src/he_wsi_generator/embeddings/cluster.py 1-65，cluster 初始化修正。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_wsi_io tests.test_annotations tests.test_embeddings tests.test_pseudo_mask_pipeline tests.test_cli tests.test_schemas tests.test_version -v
  - conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/embeddings/embedder.py src/he_wsi_generator/priors/pseudo_mask.py src/he_wsi_generator/cli.py
  - conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
  - git diff --check
- 更新时间：2026-05-27

M10 边界收敛（v0.80.0 refresh，2026-05-28）：
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/priors/style.py::{STYLE_COVERAGE_DIMENSIONS,STYLE_PRIOR_KIND,build_style_prior_from_training_index,sample_style_policy_from_prior,_coverage_reference}，把 `prior_kind`、`coverage`（covered/uncovered/details）和扩展的 `limitations` 写入 style_prior 与 sampled_style_policy。
  - src/he_wsi_generator/priors/texture.py::{TEXTURE_COVERAGE_DIMENSIONS,TEXTURE_PRIOR_KIND,build_texture_prior_from_embedding_cache,sample_texture_policy_from_prior,_texture_coverage_reference}，把 `prior_kind`、`coverage` 与 morphology / region / trainable codebook 的未覆盖项写入 texture_prior 与 sampled_texture_policy。
  - src/he_wsi_generator/models/latent_diffusion_training.py::{_load_conditioning_reference,_coverage_summary,_string_list}，让 Stage 4 trained checkpoint 的 `conditioning_reference.style_target / texture_target` 透传 `prior_kind / coverage / limitations`，把上游 prior 的边界一直带到 Stage 5。
- 完整依赖：保留原 Stage 3 编排链路与 Stage 4 训练编排。本轮新增字段是只读元数据，不改变 prior 内容、不引入新维度计算。
- 测试覆盖：
  - tests/test_style_prior.py::StylePriorTests::{test_build_style_prior_from_training_index_writes_rgb_statistics,test_sample_style_policy_from_prior_writes_selected_style_artifact}
  - tests/test_texture_prior.py::TexturePriorTests::{test_build_texture_prior_from_embedding_cache_writes_cluster_prototypes,test_sample_texture_policy_from_prior_writes_selected_texture_artifact}
  - tests/test_latent_diffusion_training.py::LatentDiffusionTrainingTests::test_train_latent_diffusion_unet_writes_trained_checkpoint_and_stage_execution
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior tests.test_texture_prior tests.test_latent_diffusion_training tests.test_priors -v
  - 真实 `291288_.svs` Stage 1-7 链路：`build/validation/real-291288-stage1-7-v0800-refresh.<ts>/` 下依次执行 `audit-manifest`、`build-pseudo-mask --batch-size 256 --n-clusters 4`、`build-six-class-mask`、`build-training-index`、`build-layout-mask-prior`、`build-style-prior`、`build-texture-prior`、`build-wsi-tissue-overview`、`build-prior-manifest`、`validate-prior-manifest`、`init-training-run`、`train-latent-diffusion-unet`，验证 `training-run/checkpoint_manifest.json` 的 trained checkpoint 上 `conditioning_reference.style_target.coverage.uncovered_dimensions` 包含 `slide_level_style_seed_with_local_perturbation / sharpness_focus_plane / smudges_dust_artifacts / compression_noise / scanner_noise`，`texture_target.coverage.uncovered_dimensions` 包含 `trainable_codebook / vq_vae_token_sampler / morphology_semantic_class / region_specific_token_distribution`。
- 更新时间：2026-05-28

### Stage 4：训练数据与生成模型

Stage 4 是模型主体阶段。它应优先跑通 latent diffusion U-Net 的条件训练链路，而不是提前比较多种 backbone 或扩展复杂调参系统。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M12 | 构造多倍率训练样本 | training index 包含层级、mask、coord、style、source、anchor |
| M13 | 实现条件 LDM U-Net | 模型能接收 mask、上一尺度、style、coord、source、anchor |
| M14 | 实现三阶段训练流程 | 训练命令能写出 checkpoint 和 training log |
| M15 | 记录 anchor 训练与 checkpoint | checkpoint manifest 包含模型版本、seed、训练数据和 anchor 策略 |

Stage Gate：
- 能训练或微调得到可被推理加载的 checkpoint。
- `structure_anchor` 作为模型条件进入训练，而不是只在推理阶段临时调权。
- 不在此阶段追求最终视觉质量，只要求训练链路和条件链路成立。

Implementation Trace:
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/models/training_index.py::build_training_index，落实 M12，保留现有四层 cascade training-index 主线。
  - src/he_wsi_generator/models/training_batch.py::load_training_batch，落实 M12，提供多倍率 image/mask batch 读取。
  - src/he_wsi_generator/models/latent_diffusion_training.py::train_latent_diffusion_unet，落实 M13-M15，执行真实 `prior_ready -> image_generator -> wsi_consistency` 三阶段训练并写出 trained checkpoint。
- 完整依赖：
  - 入口与编排：
    - src/he_wsi_generator/cli.py::build_parser，暴露 `build-training-index`、`inspect-training-batch` 和 `train-latent-diffusion-unet`。
    - src/he_wsi_generator/cli_commands.py::run_command，连接 Stage4 contract gate、真实训练 backend 和 CLI 输出。
    - src/he_wsi_generator/models/training.py::create_training_run，继续承担 config / dataset / objective / prior contract gate，不改变 `init-training-run` 语义。
  - 输入契约：
    - src/he_wsi_generator/schemas.py::{validate_input_manifest, validate_label_mapping}，校验 manifest 与 label mapping。
    - src/he_wsi_generator/io/audit.py::audit_manifest，提供 WSI metadata 与 annotation 摘要。
    - src/he_wsi_generator/priors/artifacts.py::load_prior_manifest，校验 Stage3 prior manifest 文件完整性。
  - 输出契约：
    - src/he_wsi_generator/models/training_index.py::build_training_index，输出四层 training-index JSONL。
    - src/he_wsi_generator/models/training_batch.py::write_training_batch_summary，输出 auditable batch summary JSON。
    - src/he_wsi_generator/models/latent_diffusion_training.py::_trained_checkpoint_manifest，写出真实 `checkpoint_manifest.json`，记录 `stage_execution`、`anchor_training`、`dataset_sampling` 和 inference/load contract。
  - 核心逻辑：
    - src/he_wsi_generator/models/training_index.py::{_records_for_slide,_coord_condition}，保留 M12 多倍率记录和目标尺寸契约。
    - src/he_wsi_generator/models/training_batch.py::{_load_project_mask_tile,_load_fixture_image_tile,_load_openslide_image_tile,_resize_nearest_mask,_resize_rgb_tile}，按层级读取真实训练样本。
    - src/he_wsi_generator/models/latent_diffusion_training.py::{_load_conditioning_reference,_load_level_batches}，从 prior manifest 读取 style/texture 摘要，并按 `runtime.batch_size` 对每层训练记录做子采样。
    - src/he_wsi_generator/models/latent_diffusion_training.py::{_run_vae_stage,_run_diffusion_stage}，执行 tile VAE 预热、conditioned latent diffusion 训练和 WSI consistency fine-tune。
    - src/he_wsi_generator/models/latent_diffusion_training.py::{_previous_scale_condition,_source_condition_channels,_condition_feature_channels}，把 `previous_scale`、`source_condition`、`coord`、`style`、`texture` 和 `structure_anchor` 接成真实模型输入。
    - src/he_wsi_generator/models/latent_diffusion_training.py::{_tile_seam_loss,_style_consistency_loss}，提供最小 `tile_seam_consistency` / `slide_style_consistency` 训练目标。
  - 配置与默认值：
    - src/he_wsi_generator/constants.py::{CASCADE_LEVELS,TILE_SIZE_40X,ANCHOR_PRESETS,PROJECT_VERSION}，固定四层 pyramid、40x tile 与 anchor preset。
    - src/he_wsi_generator/models/latent_diffusion_training.py::DEFAULT_RUNTIME，定义 Stage4 真实训练 backend 的默认 batch / epoch / latent / diffusion 参数。
  - 错误处理：
    - src/he_wsi_generator/models/training_index.py::TrainingIndexError，负责缺 annotation/mapping/有效 tile 的阻断失败。
    - src/he_wsi_generator/models/training_batch.py::TrainingBatchError，负责缺 `conditioning.coord`、tile 越界、mask transform 非整数对齐和目标 shape 非法。
    - src/he_wsi_generator/models/latent_diffusion_training.py::LatentDiffusionTrainingError，负责 prior artifact 非法、runtime 配置非法、设备不可用、non-finite loss 和条件契约不完整等阻断失败。
  - 输出与持久化：
    - src/he_wsi_generator/models/latent_diffusion_training.py::train_latent_diffusion_unet，写出真实 `model.pt`、`training_log.jsonl`、更新后的 `training_plan.json`、`training_run.json` 和 `checkpoint_manifest.json`。
  - 测试覆盖：
    - tests/test_training_index.py::TrainingIndexTests::test_build_training_index_writes_four_level_tile_records，验证 M12 记录字段与多倍率目标尺寸。
    - tests/test_training_batch.py::TrainingBatchTests::{test_load_training_batch_downsamples_mask_for_lower_cascade_level,test_load_training_batch_reads_fixture_image_tiles_for_lower_cascade_level}，验证 lower cascade batch 读取。
    - tests/test_models_generation.py::ModelGenerationSkeletonTests::*，验证 `init-training-run` contract gate 仍保持 plan-only 语义。
    - tests/test_latent_diffusion_training.py::LatentDiffusionTrainingTests::{test_train_latent_diffusion_unet_writes_trained_checkpoint_and_stage_execution,test_cli_trains_latent_diffusion_unet,test_train_latent_diffusion_unet_respects_runtime_batch_size_per_level}，验证 M13-M15 真实 backend、CLI 和大图子采样。
    - tests/test_torch_training.py::TorchSmokeTrainingTests::*，验证旧 smoke backend 兼容性未回归。
  - 脚本与命令：
    - 无新增 shell 脚本；统一通过 `he-wsi-gen build-training-index`、`he-wsi-gen inspect-training-batch`、`he-wsi-gen init-training-run` 和 `he-wsi-gen train-latent-diffusion-unet`。
- 调用链 / 实现流程：
  manifest + audit + label_mapping -> build_training_index -> training-index JSONL -> create_training_run(contract gate) -> train_latent_diffusion_unet(prior_ready -> image_generator -> wsi_consistency) -> model.pt/checkpoint_manifest.json
- 外部关键依赖：
  - numpy，用于 mask/image batch 处理与 nearest resize。
  - Pillow、openslide-python，用于真实图像 tile 读取。
  - torch，用于真实 Stage4 训练 backend。
- 参考行号：
  - src/he_wsi_generator/models/training_index.py 12-153，多倍率训练记录与条件对象。
  - src/he_wsi_generator/models/training_batch.py 12-287，多倍率 batch 读取与缩放。
  - src/he_wsi_generator/models/latent_diffusion_training.py 114-357，Stage4 真实训练主入口、checkpoint/training plan 回写。
  - src/he_wsi_generator/models/latent_diffusion_training.py 484-510，每层 batch 子采样加载。
  - src/he_wsi_generator/models/latent_diffusion_training.py 557-694，真实 diffusion / consistency 训练循环。
  - src/he_wsi_generator/models/latent_diffusion_training.py 869-977，trained checkpoint manifest 与 inference contract。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index tests.test_training_batch tests.test_models_generation tests.test_latent_diffusion_training tests.test_torch_training tests.test_version -v
  - conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/models/latent_diffusion_training.py src/he_wsi_generator/models/__init__.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py src/he_wsi_generator/constants.py
  - conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
  - 真实 `291288_.svs` 链路：`build/validation/real-291288-stage1-4-v0790.ITFzbb/` 下依次执行 `audit-manifest`、`build-training-index`、`build-layout-mask-prior`、`build-style-prior`、`build-texture-prior`、`build-wsi-tissue-overview`、`build-prior-manifest`、`validate-prior-manifest`、`init-training-run`、`train-latent-diffusion-unet`
- 更新时间：2026-05-27

### Stage 5：级联生成与 OME-TIFF 输出

Stage 5 是生成器主体功能闭环。目标是从 checkpoint 和 priors 生成多倍率 WSI，并写出工具可读的 OME-TIFF pyramid。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M16 | 执行 1/32 -> 1/16 -> 1/4 -> 1/1 cascade | 每层有中间输出 |
| M17 | 生成 tile 并做基础 overlap blending | 40x tile 能拼入输出网格 |
| M18 | 接入 source-conditioned generation | 高 anchor 生成能使用 source WSI 条件 |
| M19 | 写出 OME-TIFF pyramid 和 mask | 文件可读，层级完整，mask 对齐 |

Stage Gate：
- 输出至少包含 `generated.ome.tiff` 和 `generated_mask/`。
- cascade 顺序固定为 `1/32 -> 1/16 -> 1/4 -> 1/1`。
- 此阶段只要求基础可读和结构完整，复杂恢复、复杂诊断和全量异常处理后置。

Implementation Trace:
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation，落实 M16 / M18，统一处理 external tile backend 和 internal `latent_diffusion_unet_checkpoint` 两类 Stage5 入口。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py::materialize_internal_latent_diffusion_tile_sources，把 Stage4 checkpoint 接成真实四层 cascade tile source，并输出 level0 mask tile。
  - src/he_wsi_generator/generation/executor.py::{_resolve_source_wsi_path_from_prior,_metadata_source_payload}，在高 anchor 时回填并透传真实 source WSI provenance。
- 完整依赖：
  - 入口与编排：
    - src/he_wsi_generator/generation/planner.py::create_generation_plan，提供四层 stage 顺序和 generation backend compatibility gate。
    - src/he_wsi_generator/cli.py::build_parser 与 src/he_wsi_generator/cli_commands.py::run_command，暴露 `run-generation --backend production-tile-stream`。
  - 输入契约：
    - src/he_wsi_generator/schemas.py::validate_generation_config，校验 Stage 5 输入配置。
    - src/he_wsi_generator/models/training.py::load_checkpoint_manifest，校验 checkpoint inference contract。
    - src/he_wsi_generator/priors/artifacts.py::load_prior_manifest，校验 prior artifact 路径与输入 manifest 路径。
    - src/he_wsi_generator/generation/executor.py::_load_generation_condition_packet，校验 sampled layout / style / texture / source / anchor 条件摘要。
  - 核心逻辑：
    - src/he_wsi_generator/generation/latent_diffusion_internal.py::{_sample_internal_cascade,_write_internal_tile_source_manifest}，落实 M16，把 Stage4 checkpoint 转成 `1/32 -> 1/16 -> 1/4 -> 1/1` cascade tile source manifest。
    - src/he_wsi_generator/generation/latent_diffusion_internal.py::{_load_source_level0_rgb,_source_condition_summary}，落实 M18，真实读取 source WSI RGB 并记录 `source_region`。
    - src/he_wsi_generator/generation/executor.py::_run_stage5_shared_cascade_core，继续保留 smoke 兼容入口，但不再承载本轮新增真实行为。
    - src/he_wsi_generator/generation/tiling.py::{create_tile_traversal_plan, build_resumable_tile_manifest, update_resumable_tile_manifest, require_complete_tile_manifest}，继续复用 M17 traversal/resume 基础设施。
  - 配置与默认值：
    - src/he_wsi_generator/constants.py::{CASCADE_LEVELS,TILE_SIZE_40X,PROJECT_VERSION}，固定四层和默认 tile 尺寸。
    - src/he_wsi_generator/generation/latent_diffusion_internal.py::{INTERNAL_LATENT_DIFFUSION_BACKEND_NAME,INTERNAL_LATENT_DIFFUSION_TILE_SOURCE}，定义 internal backend 与 manifest source。
  - 错误处理：
    - src/he_wsi_generator/generation/executor.py::GenerationExecutionError，负责 source WSI 解析失败、checkpoint/backend 不兼容、writer handoff 失败。
    - src/he_wsi_generator/generation/latent_diffusion_internal.py::InternalLatentDiffusionError，负责 sampled layout 缺失、checkpoint 不兼容、source RGB 读取失败和内部 sampling 失败。
  - 输出与持久化：
    - src/he_wsi_generator/outputs/ome_tiff.py::write_pyramid_ome_tiff_streaming_from_tile_sources，负责 OME-TIFF 输出。
    - src/he_wsi_generator/generation/production_streaming.py::write_streaming_mask_from_tile_sources，负责 level0 mask tile -> final mask。
  - 测试覆盖：
    - tests/test_production_latent_generation.py::ProductionLatentGenerationTests::test_run_production_tile_stream_generation_with_internal_latent_checkpoint，验证 internal latent checkpoint 的 Stage5 主路径。
    - tests/test_production_latent_generation.py::ProductionLatentGenerationTests::test_internal_latent_generation_records_real_source_conditioning，验证 M18 source-conditioned 图像差异与 provenance。
    - tests/test_generation_runner.py::GenerationRunnerTests::*，验证既有 smoke/external production path 不回归。
  - 脚本与命令：
    - 无新增 shell 脚本；统一通过 `he-wsi-gen run-generation`。
- 调用链 / 实现流程：
  generation_config + prior_manifest + latent_diffusion_unet_checkpoint + condition_packet -> create_generation_plan -> materialize_internal_latent_diffusion_tile_sources -> write_pyramid_ome_tiff_streaming_from_tile_sources + write_streaming_mask_from_tile_sources -> metadata/qc/archive
- 外部关键依赖：
  - numpy，用于 sampled layout mask / RGB tile / tile source materialization。
  - torch，用于 internal latent diffusion checkpoint sampling。
  - Pillow、openslide-python，用于真实 source WSI RGB 读取。
- 参考行号：
  - src/he_wsi_generator/generation/executor.py 432-620，Stage5 production entry、internal/external backend 分流、writer/QC/archive 串联。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py 27-110，internal latent tile source 主入口与 summary。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py 113-230，四层 cascade sampling。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py 430-489，tile source manifest 写出。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_production_latent_generation -v
  - 真实 `291288_.svs` Stage1-7 链路：`build/validation/real-291288-stage1-7-v0800.GEITCR/` 下执行 `run-generation --backend production-tile-stream --wsi-writer tile-streaming` 的 UI/workflow job。
- 更新时间：2026-05-28

M16/M18 slide-grid inference 收敛（v0.80.0 refresh，2026-05-28）：
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/generation/latent_diffusion_internal.py::{materialize_internal_latent_diffusion_tile_sources,_sample_full_canvas_levels,_sample_and_write_level,_split_full_level_to_tiles,_level_tile_grid,_levels_summary,_write_internal_tile_source_manifest}，把 internal latent path 重写为 slide 级 tile-grid inference：1/32 与 1/16 在内存里一次采样作为全局结构 prior，1/4 与 1/1 按 OME-TIFF chunk 对齐到各自 level 的 tile grid 逐 tile 采样。每层 `tile_grid` 在 manifest 与 plan 摘要中都被显式记录。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py::{_previous_scale_for_tile,_crop_full_level_to_target,_crop_mask_region_at_level}，按 level frame 计算 previous-scale crop、mask crop，1/1 tile 从 1/4 tile 中取对应 sub-region 作为 cross-scale 条件。
  - src/he_wsi_generator/generation/latent_diffusion_internal.py::{_SourceSlideHandle,_open_source_slide,_read_source_tile_region,_source_condition_summary}，把 source RGB 改为按 tile 的 level0 footprint 逐 tile 读取（OpenSlide 或 PIL handle 复用），mode 显式标记为 `source_tile_rgb_model_condition_per_tile`，仅在 `structure_anchor>0.3` 与 `source_wsi_id` 同时存在时启用。
  - src/he_wsi_generator/generation/executor.py::_metadata_source_payload，将新 mode `source_tile_rgb_model_condition_per_tile` 接入 metadata source provenance 白名单，使 metadata.json 的 `source.source_wsi_path / source.source_region` 被诚实回填。
- 完整依赖：
  - 入口与编排保持原有 Stage 5 production tile stream executor 不变；M17 的 traversal/blending 基础设施被复用。
  - 真实 source slide 读取依赖 `openslide-python`（SVS）或 `Pillow`（PNG/TIFF/JPG）。
- 测试覆盖：
  - tests/test_production_latent_generation.py::ProductionLatentGenerationTests::{test_run_production_tile_stream_generation_with_internal_latent_checkpoint,test_internal_latent_generation_records_real_source_conditioning}，验证 de novo 与 source-conditioned 两条 internal latent path 上 manifest / metadata / OME-TIFF 输出诚实记录 slide-grid inference。
  - tests/test_stage1_7_real_backend_e2e.py::Stage1To7RealBackendE2ETests::test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary，断言 `tile_source_manifest.streaming.json` 含 `tile_grid` 和 internal latent backend 的 `limitations` 列表。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_production_latent_generation tests.test_generation_runner tests.test_stage1_7_real_backend_e2e -v
  - 真实 `291288_.svs` Stage 5/6 链路（4096×4096 slide-grid canvas）：`build/validation/real-291288-stage1-7-v0800-refresh.<ts>/` 下执行 `sample-layout-mask`、`build-condition-packet`、`run-generation --backend production-tile-stream --wsi-writer tile-streaming`，并验证 `tile_source_manifest.streaming.json` 的 `tile_grid` 在 1/1 / 1/4 / 1/16 / 1/32 上分别为 [8,8] / [2,2] / [1,1] / [1,1]，以及 source-conditioned 模式 metadata.json 上 `source.source_wsi_path` 与 `plan.cascade_generation.source_condition.mode == source_tile_rgb_model_condition_per_tile`。
- 更新时间：2026-05-28

### Stage 6：Metadata 与基础 QC

Stage 6 不再拆成大量补充模块，只保留生成样本成为可追踪数据对象所需的最低功能。QC 以基础自动检查为主，不提前追求完整质量评估系统。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M20 | 写出 per-WSI metadata | 记录 source、seed、model、prior、mask mapping、输出路径 |
| M21 | 执行基础 QC | 检查文件可读、pyramid 层级、mask 对齐和基础图像质量 |
| M22 | 写出 batch index 和 run summary | batch JSONL 能定位 metadata、QC 和 OME-TIFF |

Stage Gate：
- 每个 generated sample 有 `metadata.json`、`qc.json` 和 `batch.jsonl` 记录。
- QC 至少能区分 `pass`、`warning`、`fail`。
- 轻量 non-copy report、细粒度 seam/style 定位、复杂阈值策略列为后续增强，不作为主体功能阶段的独立阻塞项。

Implementation Trace:
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/generation/executor.py::_metadata_payload，统一生成 per-WSI metadata 主体结构。
  - src/he_wsi_generator/generation/executor.py::{_metadata_source_payload,_metadata_mask_schema}，落实 M20，对 internal latent backend 继续诚实回填 source/path/mask provenance。
- 完整依赖：
  - 入口与编排：
    - src/he_wsi_generator/generation/executor::{run_smoke_generation,run_torch_diffusion_smoke_generation,run_production_tile_stream_generation}，统一在生成出口构造 metadata。
  - 输入契约：
    - src/he_wsi_generator/schemas.py::validate_metadata，约束 metadata schema 与允许字段。
  - 输出契约：
    - src/he_wsi_generator/metadata/archive.py::{write_metadata,archive_sample}，写出 `metadata.json` 并与 `qc.json / batch.jsonl` 绑定。
  - 核心逻辑：
    - src/he_wsi_generator/generation/executor.py::_metadata_source_payload，在 internal source-conditioned 路径下回填真实 `source_wsi_path / source_region / source_scale`。
    - src/he_wsi_generator/generation/executor.py::_metadata_payload，为 `production-tile-stream` internal backend 新增 `checkpoint_inference_contract` 与 `production_tile_backend` 摘要。
    - src/he_wsi_generator/generation/executor.py::_metadata_mask_schema，在 sampled layout mask 条件下回填 artifact provenance。
  - 错误处理：
    - src/he_wsi_generator/metadata/archive.py::write_metadata，经 `validate_metadata()` 失败时显式阻断。
  - 输出与持久化：
    - src/he_wsi_generator/metadata/archive.py::{write_metadata,append_batch_index,archive_sample}，保持 M22 现有落盘链路不变。
  - 测试覆盖：
    - tests/test_production_latent_generation.py::ProductionLatentGenerationTests::{test_run_production_tile_stream_generation_with_internal_latent_checkpoint,test_internal_latent_generation_records_real_source_conditioning}，验证 source provenance 与 backend 诚实记录。
    - tests/test_outputs_qc_archive.py::OutputQCArchiveTests::*，验证 metadata/QC/archive 无回归。
    - tests/test_ui.py 与 tests/test_ui_workflow.py 相关 output summary 用例，验证 Stage 7 消费 metadata 无回归。
  - 脚本与命令：
    - 无新增 shell 脚本；统一复用生成命令与 archive 主线。
- 调用链 / 实现流程：
  generation executor -> _metadata_payload -> archive_sample -> write_metadata + write_qc_report + append_batch_index
- 外部关键依赖：
  - 无新增外部关键依赖。
- 参考行号：
  - src/he_wsi_generator/generation/executor.py 642-758，metadata payload 组装与回填。
  - src/he_wsi_generator/metadata/archive.py 1-68，metadata/QC/batch index 落盘。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_production_latent_generation tests.test_outputs_qc_archive tests.test_ui tests.test_ui_workflow -v
  - 真实 `291288_.svs` Stage1-7 链路：`validate metadata`、`validate qc`、`inspect-output-summary`
- 更新时间：2026-05-28

### Stage 7：本地控制台与端到端验收

Stage 7 将 core/CLI 能力接入 PySide6 本地单页控制台。UI 的目标是调度主体流程和展示核心输出，不在第一轮承担复杂解释系统。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M23 | 实现 PySide6 单页控制台 | 页面包含数据输入、mapping、model/prior、生成参数、状态和输出区域 |
| M24 | 保存 UI job config | UI 配置可被 CLI/core 复现 |
| M25 | 实现 job runner 和状态展示 | 能显示 queued/running/completed/failed |
| M26 | 跑通端到端 E2E 验收 | 从 manifest 到 OME-TIFF、metadata、QC、UI config 的闭环成立 |

Stage Gate：
- 用户可以通过 UI 或 CLI 完成一次完整生成任务。
- UI 不直接实现 core 数据处理逻辑，只负责配置、调度和展示。
- 失败说明只需可操作，例如缺路径、缺 checkpoint、输出不可写；复杂解释后续再补。

Implementation Trace:
- 状态：已实现
- 主实现：
  - src/he_wsi_generator/ui/workflow.py::{build_run_generation_command,create_run_generation_job,run_queued_generation_job,load_generation_job_status,collect_generation_job_output_summary}，落实 M23，支持 `production-tile-stream` 和显式 `job_root`。
  - src/he_wsi_generator/ui/pyside_app.py::create_main_window，落实 M23，把 `production-tile-stream` 暴露到单页 UI backend 下拉。
  - tests/test_stage1_7_real_backend_e2e.py::Stage1To7RealBackendE2ETests::test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary，落实 M26，新增 non-smoke Stage1-7 入口。
- 完整依赖：
  - 入口与编排：
    - src/he_wsi_generator/ui/workflow::{create_run_generation_job,run_queued_generation_job,load_generation_job_status,collect_generation_job_output_summary}，负责 workflow 主链。
    - src/he_wsi_generator/ui/jobs::JobRunner，负责本地 job 生命周期。
    - src/he_wsi_generator/cli_commands.py::run_command，负责真实 SVS CLI 验证链路的各阶段命令分发。
  - 输入契约：
    - src/he_wsi_generator/ui/workflow::{build_generation_config_from_form,build_run_generation_command}，负责 form -> CLI contract，并为 `production-tile-stream` 注入 `--wsi-writer tile-streaming`。
  - 输出契约：
    - src/he_wsi_generator/ui/controller::collect_output_summary，负责 metadata/QC/review 输出摘要。
  - 核心逻辑：
    - src/he_wsi_generator/ui/workflow.py::_BACKENDS，把 `production-tile-stream` 纳入 Stage7 可调度 backend。
    - tests/test_stage1_7_real_backend_e2e.py 复用 Stage1-4 主链工件、真实 latent checkpoint 和 production backend 串到 Stage7。
    - build/validation/real-291288-stage1-7-v0800.GEITCR/，保存本轮真实 `.svs` Stage1-7 复跑工件；最终输出位于 `generated/gen-real-291288-stage1-7-v0800/`。
  - 错误处理：
    - src/he_wsi_generator/ui/workflow.py::UIWorkflowError，负责 job 缺失、输出缺失、未完成 job 和非法 backend 选择等阻断失败。
  - 输出与持久化：
    - src/he_wsi_generator/ui/jobs.py::JobRunner，写出 job record/stdout/stderr。
    - src/he_wsi_generator/metadata/archive.py::{write_metadata,append_batch_index}，写出最终 metadata/batch index。
  - 测试覆盖：
    - tests/test_ui_workflow.py::UIWorkflowTests::test_build_run_generation_command_accepts_production_tile_stream_backend
    - tests/test_ui.py::PySideFormTests::test_main_window_exposes_enabled_form_controls
    - tests/test_stage1_7_real_backend_e2e.py::Stage1To7RealBackendE2ETests::test_stage1_to_7_real_backend_entry_runs_generation_job_and_collects_summary
    - tests/test_ui.py::UITests::*，验证 output summary / UI config / CLI UI 辅助路径无回归。
  - 脚本与命令：
    - 无新增 shell 脚本；固定入口以 Python unittest 和 UI workflow helper 落地。
- 调用链 / 实现流程：
  form_state -> build_generation_config_from_form -> build_run_generation_command(production-tile-stream) -> create_run_generation_job -> run_queued_generation_job -> load_generation_job_status -> collect_generation_job_output_summary
- 外部关键依赖：
  - PySide6，可选；用于 Stage 7 GUI 层。
- 参考行号：
  - src/he_wsi_generator/ui/workflow.py 17-110，workflow 主链、backend 列表和 production command builder。
  - src/he_wsi_generator/ui/jobs.py 1-89，本地 job 持久化与执行。
  - src/he_wsi_generator/ui/pyside_app.py 59-90，backend 下拉与 Stage7 UI 输入区。
  - tests/test_stage1_7_real_backend_e2e.py 41-459，non-smoke Stage1-7 E2E 入口。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_ui tests.test_ui_workflow tests.test_stage1_7_real_backend_e2e tests.test_version -v
  - 真实 `.svs` Stage1-7 复跑：`build/validation/real-291288-stage1-7-v0800.GEITCR/` 下执行 sampled layout、condition packet、UI workflow job、`validate metadata`、`validate qc` 和 `inspect-output-summary`
- 更新时间：2026-05-28

M26 验收边界收敛（v0.80.0 refresh，2026-05-28）：
- 状态：已实现
- 主实现：
  - tests/test_stage1_7_real_backend_e2e.py 在 non-smoke E2E 上新增对 `tile_source_manifest.streaming.json.tile_grid`、`source` 和 `limitations` 的断言，把"最小工程链路"与"slide 级合成"区分开。
  - tests/test_production_latent_generation.py 已在 `test_internal_latent_generation_records_real_source_conditioning` 上断言 internal latent 的 `source_condition.mode == source_tile_rgb_model_condition_per_tile`，证明 source 条件覆盖 per-tile 路径。
- 验证命令：
  - conda run -n MultiCenterWSIGenerator python -m unittest tests.test_stage1_7_real_backend_e2e tests.test_production_latent_generation tests.test_ui tests.test_ui_workflow -v
  - 真实 `291288_.svs` Stage 1-7 链路：`build/validation/real-291288-stage1-7-v0800-refresh.<ts>/` 下执行 de novo 与 source-conditioned 两组 `run-generation --backend production-tile-stream --wsi-writer tile-streaming`，分别检查 `metadata.json.source.source_wsi_path` 是否与 `structure_anchor` 语义一致（fully_de_novo -> null；rescan_simulation -> 真实 SVS 路径），并通过 `inspect-output-summary` 收束 metadata/QC 摘要。
- 更新时间：2026-05-28

## 6. Stage 间依赖关系

| 前置 Stage | 后续依赖 | 不能跳过的原因 |
|---|---|---|
| Stage 1 | Stage 2-7 | 没有 package、CLI 和配置契约，后续功能难以串联 |
| Stage 2 | Stage 3-6 | 没有 WSI metadata 和 6 类 mask，prior、训练和 QC 缺少主体条件 |
| Stage 3 | Stage 4-5 | 没有 priors，模型缺少 layout/style/texture 条件 |
| Stage 4 | Stage 5 | 没有 checkpoint，级联生成无法执行 |
| Stage 5 | Stage 6-7 | 没有 OME-TIFF 和 mask 输出，metadata、QC、UI 都没有真实对象可引用 |
| Stage 6 | Stage 7 | 没有 metadata 和 QC，UI 无法展示可信生成结果 |

## 7. 推荐验证节奏

验证也按主体功能推进。每个 Stage 完成后集中验证，不在每个内部函数后设计过多细碎测试。

| Stage | 推荐验证 |
|---|---|
| Stage 1 | schema validation、manifest load test、CLI smoke test |
| Stage 2 | WSI read smoke test、annotation load test、mask alignment test |
| Stage 3 | PatchEmbedder interface test、prior artifact load/save test |
| Stage 4 | training sample contract test、checkpoint save/load test |
| Stage 5 | cascade generation smoke test、OME-TIFF write/read test |
| Stage 6 | metadata JSON test、QC JSON test、batch JSONL test |
| Stage 7 | UI config test、job runner test、end-to-end E2E test |


## 9. 完成标准

模块化分阶段开发可视为完成，当且仅当：

1. Stage 1 到 Stage 7 按顺序完成。
2. 输入 WSI 能进入 manifest，并产生 thumbnail、pyramid metadata 和 6 类 mask。
3. 系统能学习或加载 layout/mask、style、texture priors。
4. 系统能训练或加载结构锚定的多倍率 latent diffusion U-Net checkpoint。
5. 系统能按 `1/32 -> 1/16 -> 1/4 -> 1/1` 级联生成 WSI。
6. 系统能写出 `generated.ome.tiff`、`generated_mask/`、`metadata.json`、`qc.json` 和 `batch.jsonl`。
7. PySide6 控制台能调度一次生成任务，并显示任务状态和输出路径。
