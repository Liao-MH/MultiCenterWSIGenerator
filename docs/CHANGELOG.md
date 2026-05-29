# CHANGELOG

## v0.80.0 - 2026-05-28 审计补充

### 用户需求

- 用户要求再次审计整个仓库，严格基于设计文档、开发文档和当前可见代码做 `M01-M26` Stage / Module 对照审计。
- 用户要求识别真实、非 smoke、无偏离实现，标注真实代码路径、核心函数/类、测试路径、状态分类和与 module-stage 方案的差距。
- 用户要求如设计文档与开发文档冲突需先征求确认，不得脱离文档引入新功能设想。

### 已做改动

- 新增 `docs/audit/2026-05-28-stage-module-design-dev-code-audit-v0800.md`，记录当前 `v0.80.0` 可见仓库状态下的 `M01-M26` 逐项审计。
- 审计结论明确区分：
  - Stage Gate 最小真实链路；
  - 设计文档中的完整 slide 级 / GB 级 H&E WSI 合成目标；
  - smoke/proxy/fixture 路径和后置增强项。
- 更新 `docs/DEMANDS.MD`，置顶记录本轮审计需求。
- 本轮未修改业务代码，未升级版本号。

### 影响文件

- `docs/audit/2026-05-28-stage-module-design-dev-code-audit-v0800.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- 静态审计命令：
  - `git status --short`
  - `git branch --show-current`
  - `wc -c docs/plans/2026-05-18-he-wsi-generator-study-design.md docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md docs/DEMANDS.MD docs/CHANGELOG.md README.md VERSION pyproject.toml`
  - `rg --files docs src tests | sort`
  - `rg -n "M0[1-9]|M1[0-9]|M2[0-6]|Stage|阶段|Implementation Trace|真实|smoke|Module" docs/plans/2026-05-18-he-wsi-generator-study-design.md`
  - `rg -n "M0[1-9]|M1[0-9]|M2[0-6]|Stage|阶段|Implementation Trace|真实|smoke|Module" docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
  - `rg -n "class .*Tests|def test_" tests/...`
- 文档格式检查：
  - `git diff --check`
- 未运行全量测试。原因：本轮为静态审计与文档产出，不修改业务代码；不把历史验证工件或历史测试结果声明为本轮重新验证。

## v0.80.0 - 2026-05-27

### 用户需求

- 用户要求根据 `docs/audit/2026-05-27-stage-module-real-implementation-audit-v0780.md` 的结论，只执行 `Stage 5-7` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 5-7`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现非 smoke 级的真实主体功能，处理会阻断主体链路的失败情况。
- 用户要求保留当前可复用代码，不重头开发，不删除已有后置增强能力，但本轮不围绕它继续扩展。
- 用户要求使用当前仓库规定的验证方式和真实 SVS `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 运行 `Stage 1-7` 链路测试，且不得使用 smoke 级代码。
- 用户要求完成后更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.80.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 新增 `src/he_wsi_generator/generation/latent_diffusion_internal.py`，提供 internal latent diffusion generation path：
  - 直接加载 `latent_diffusion_unet` checkpoint；
  - 要求 sampled layout mask condition packet；
  - 生成四层 `1/32 -> 1/16 -> 1/4 -> 1/1` cascade RGB arrays；
  - 在高 anchor 时从 source WSI 读取真实 RGB 作为 source condition；
  - 输出完整 `disk_npy_tile_source_manifest` 和 level0 mask tile。
- `src/he_wsi_generator/generation/executor.py` 的 `run_production_tile_stream_generation()` 现在支持两类 backend：
  - 既有 external tile backend artifact；
  - 新的 internal `latent_diffusion_unet_checkpoint`。
- `production-tile-stream` 路径新增 `plan.cascade_generation`、`production_tile_backend=internal_latent_diffusion_unet`、以及 metadata 中的 `checkpoint_inference_contract` / `production_tile_backend` 摘要。
- `src/he_wsi_generator/ui/workflow.py` 与 `src/he_wsi_generator/ui/pyside_app.py` 将 `production-tile-stream` 纳入 Stage7 UI/workflow backend 列表；workflow 自动为该 backend 注入 `--wsi-writer tile-streaming`。
- 新增 `tests/test_production_latent_generation.py` 与 `tests/test_stage1_7_real_backend_e2e.py`，分别覆盖：
  - Stage5/M20 internal latent generation 和 source-conditioned metadata；
  - Stage7/M26 non-smoke UI/workflow E2E。
- README、需求文档、CHANGELOG、设计文档与开发文档同步更新为当前真实边界与验证结果。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/latent_diffusion_internal.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_production_latent_generation.py`
- `tests/test_stage1_7_real_backend_e2e.py`
- `tests/test_ui_workflow.py`
- `tests/test_ui.py`
- `tests/*.py` 中引用当前 schema version 的 fixture
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- 单元/回归测试：
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index tests.test_training_batch tests.test_models_generation tests.test_latent_diffusion_training tests.test_torch_training tests.test_generation_runner tests.test_production_latent_generation tests.test_ui_workflow tests.test_ui tests.test_stage1_7_real_backend_e2e tests.test_version -v`
  - 结果：通过，`Ran 152 tests ... OK`。
- 语法与配置：
  - `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/models/latent_diffusion_training.py src/he_wsi_generator/generation/latent_diffusion_internal.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/ui/workflow.py src/he_wsi_generator/ui/pyside_app.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py src/he_wsi_generator/constants.py`
  - `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：均通过。
- 真实 `291288_.svs` Stage1-7 链路：
  - 验证目录：`build/validation/real-291288-stage1-7-v0800.GEITCR/`
  - 已执行命令：
    - `audit-manifest manifest.raw.json --backend openslide --output audit.raw.json`
    - `build-pseudo-mask manifest.raw.json --backend openslide --output-dir pseudo-mask --embedder-checkpoint embedder.json --patch-width 1024 --patch-height 1024 --batch-size 512 --n-clusters 6`
    - `audit-manifest manifest.json --backend openslide --output audit.json`
    - `build-six-class-mask manifest.json --audit audit.json --label-mapping label-mapping.json --output-dir mask-artifacts`
    - `build-training-index manifest.json --audit audit.json --label-mapping label-mapping.json --output training-index.jsonl`
    - `build-layout-mask-prior training-index.jsonl --batch-size 8 --split train --cascade-level 1/1 --output layout_mask_prior.json`
    - `build-style-prior training-index.jsonl --batch-size 8 --split train --cascade-level 1/1 --output style_prior.json`
    - `build-texture-prior --cache-dir pseudo-mask/embedding_cache --cache-key 291288-pseudo-mask --cluster-report pseudo-mask/cluster_report.json --output texture_prior.json`
    - `build-wsi-tissue-overview manifest.json --backend openslide --thumbnail-max-size 512 --output wsi_tissue_overview.json`
    - `build-prior-manifest ... --qc-reference-distribution qc_reference_distribution.json --wsi-tissue-overview wsi_tissue_overview.json`
    - `validate-prior-manifest prior/prior_manifest.json`
    - `init-training-run training-config.json`
    - `train-latent-diffusion-unet training-config.json`
    - `sample-layout-mask layout_mask_prior.json --output-dir sampled-layout --sample-id 291288-v0800-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview wsi_tissue_overview.json`
    - `build-condition-packet generation.production.json --prior-manifest prior/prior_manifest.json --output condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask sampled-layout/sampled_layout_mask.json`
    - UI/workflow Python helper：`create_run_generation_job -> run_queued_generation_job -> load_generation_job_status -> collect_generation_job_output_summary`
    - `validate metadata generated/.../metadata.json`
    - `validate qc generated/.../qc.json`
    - `inspect-output-summary --metadata generated/.../metadata.json --qc generated/.../qc.json`
  - 结果摘要：
    - `training-index.jsonl` 写出 `229320` 条记录；`layout_mask_prior.json` / `style_prior.json` 各使用当前版本前 `8` 条 level1 记录；`texture_prior.json` 使用当前版本 pseudo-mask embedding cache。
    - 真实训练完成，生成 `training-run/model.pt`、`checkpoint_manifest.json`、`training_plan.json`、`training_run.json` 和 `training_log.jsonl`。
    - 非 smoke Stage1-7 生成完成，输出目录 `generated/gen-real-291288-stage1-7-v0800/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json`、`generation_output_diagnostics.json`、`batch.jsonl` 和 `output_summary.json`。
    - `metadata.json` 记录 `source_wsi_id=291288`、真实 `source_wsi_path`、`source_region=[0,0,512,512]`、`source_scale=1/1`、`generation_backend=production-tile-stream`、`wsi_writer=tile-streaming` 和 `checkpoint_inference_contract.backend_type=latent_diffusion_unet_checkpoint`。
    - `inspect-output-summary` 结果为 `qc_status=pass`，三级 QC 状态均为 `pass`。

## v0.79.0 - 2026-05-27

### 用户需求

- 用户要求根据 `docs/audit/2026-05-27-stage-module-real-implementation-audit-v0780.md` 的结论，只执行 `Stage 4` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 4`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现非 smoke 级的真实主体功能，处理会阻断主体链路的失败情况。
- 用户要求保留当前可复用代码，不重头开发，不删除已有后置增强能力，但本轮不围绕它继续扩展。
- 用户要求使用当前仓库规定的验证方式和真实 SVS `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 运行 `Stage 1-4` 链路测试，且不得使用 smoke 级代码。
- 用户要求完成后更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.79.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 新增 `src/he_wsi_generator/models/latent_diffusion_training.py`，实现最小真实 Stage4 backend：
  - 复用 `create_training_run()` 做 contract gate；
  - 执行 `prior_ready -> image_generator -> wsi_consistency` 三阶段训练；
  - 训练 tile VAE、conditioned latent U-Net 和 semantic mask head；
  - 使用真实 `mask + previous_scale + source_condition + coord + style/texture summary + structure_anchor` 条件；
  - 记录 `stage_execution`、`anchor_training`、`dataset_sampling`、`condition_feature_schema`、`cross_scale_condition_schema` 和 `source_condition_schema`。
- `src/he_wsi_generator/cli.py` / `src/he_wsi_generator/cli_commands.py` 新增 CLI `train-latent-diffusion-unet <training-config>`，保持 `init-training-run` 仍只负责初始化 plan/contract manifest。
- 保留现有 `M12` training index / batch loader 主线，不新增新的 dataset 系统；仅让真实 backend 支持用 `runtime.batch_size` 对每层记录做子采样，避免大图 `training-index` 全量进内存。
- `src/he_wsi_generator/models/__init__.py` 导出新的真实 backend。
- 新增 `tests/test_latent_diffusion_training.py`，覆盖真实 backend 的 checkpoint 产物、三阶段执行、anchor 记录、CLI 入口和 `runtime.batch_size` 子采样行为。
- 开发文档和设计文档的 Stage4 追踪块更新为真实 backend 路径、测试和验证命令；README 补充新命令与当前边界说明。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/latent_diffusion_training.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_latent_diffusion_training.py`
- `tests/*.py` 中引用当前 schema version 的 fixture
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- 单元/回归测试：
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index tests.test_training_batch tests.test_models_generation tests.test_latent_diffusion_training tests.test_torch_training tests.test_version -v`
  - 结果：通过，`Ran 77 tests ... OK`。
- 语法与配置：
  - `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/models/latent_diffusion_training.py src/he_wsi_generator/models/__init__.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py src/he_wsi_generator/constants.py`
  - `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：均通过。
- 真实 `291288_.svs` Stage1-4 链路：
  - 验证目录：`build/validation/real-291288-stage1-4-v0790.ITFzbb/`
  - 已执行命令：
    - `audit-manifest manifest.json --backend openslide --output audit.json`
    - `build-training-index manifest.json --audit audit.json --label-mapping label-mapping.json --output training-index.jsonl`
    - `build-layout-mask-prior training-index.jsonl --batch-size 8 --split train --cascade-level 1/1 --output layout_mask_prior.json`
    - `build-style-prior training-index.jsonl --batch-size 8 --split train --cascade-level 1/1 --output style_prior.json`
    - `build-texture-prior --cache-dir build/validation/real-291288-stage1-7-v0770.YXQuif/pseudo-mask/embedding_cache --cache-key 291288-pseudo-mask --cluster-report build/validation/real-291288-stage1-7-v0770.YXQuif/pseudo-mask/cluster_report.json --output texture_prior.json`
    - `build-wsi-tissue-overview manifest.json --backend openslide --thumbnail-max-size 512 --output wsi_tissue_overview.json`
    - `build-prior-manifest ... --qc-reference-distribution qc_reference_distribution.json --wsi-tissue-overview wsi_tissue_overview.json`
    - `validate-prior-manifest prior/prior_manifest.json`
    - `init-training-run training-config.json`
    - `train-latent-diffusion-unet training-config.json`
  - 结果摘要：
    - `training-index.jsonl` 写出 `229320` 条记录，`records_by_level` 为 `57330 x 4`。
    - 真实 prior manifest 构建通过，包含 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution` 和 `wsi_tissue_overview` 五类 artifact。
    - 真实训练完成，输出 `training-run/model.pt`、`checkpoint_manifest.json`、`training_plan.json`、`training_run.json` 和 `training_log.jsonl`。
    - `checkpoint_manifest.json` 记录 `usable_for_inference=true`、`training_backend=latent_diffusion_unet`、`input_channels=26`、`output_channels=4`、`latent_size=32`、三阶段 `completed`、`anchor_training.low/medium/high = 64/64/64`、`dataset_sampling.batch_size_by_level = 8 x 4`。

## v0.78.1 - 2026-05-27

### 用户需求

- 用户要求阅读 `docs/` 后，根据 `docs/audit/2026-05-27-stage-module-real-implementation-audit-v0780.md` 的结论，只执行 `Stage 1-3` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 1-3`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现非 smoke 级的真实主体功能，处理会阻断主体链路的失败情况。
- 用户要求保留当前可复用代码，不重头开发，不删除已有后置增强能力，但本轮不围绕它继续扩展。
- 用户要求只做满足 Stage Gate 的最小必要改动，并使用当前仓库规定的验证方式运行测试。
- 用户要求完成后更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.78.1`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 仅对 `Stage 1-3 / M08` 做收敛，不改 pseudo-mask 主流程、batch streaming、聚类或 Stage 4+ 功能。
- `src/he_wsi_generator/embeddings/embedder.py` 将 `CheckpointPatchEmbedder` 明确为 checkpoint-backed statistical patch embedder：checkpoint 错误文案改为 JSON config object，metadata 新增 `embedding_backend`、`embedder_kind`、`checkpoint_format`、`production_ready=false` 和 `limitations`。
- `FixturePatchEmbedder` metadata 同步显式声明 `statistical_patch_moments_only`、`not_a_pathology_foundation_model` 和 `fixture_smoke_only`。
- `src/he_wsi_generator/priors/pseudo_mask.py` 为 `cluster_pseudo_mask.json` 顶层新增 `embedding_summary`，让 pseudo-mask artifact 可以直接审计当前统计型 embedding / clustering 契约，无需再下钻 embedding cache metadata。
- `src/he_wsi_generator/cli.py` 将 `build-pseudo-mask` 和 `--embedder-checkpoint` 的帮助文案改为统计型 patch embedding 表述，避免暗示真实 pathology foundation model。
- `README.md`、`docs/DEMANDS.MD`、`docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md` 和 `docs/plans/2026-05-18-he-wsi-generator-study-design.md` 同步更新为 `M08` 的真实边界表述，并补齐代码追踪中的函数、测试和验证命令。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/embeddings/embedder.py`
- `src/he_wsi_generator/priors/pseudo_mask.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_embeddings.py`
- `tests/test_pseudo_mask_pipeline.py`
- `tests/test_cli.py`
- `tests/*.py` 中引用当前 schema version 的 fixture
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_wsi_io tests.test_annotations tests.test_embeddings tests.test_pseudo_mask_pipeline tests.test_cli tests.test_schemas tests.test_version -v`
  - 结果：通过，`Ran 45 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/embeddings/embedder.py src/he_wsi_generator/priors/pseudo_mask.py src/he_wsi_generator/cli.py`
  - 结果：通过。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过。

## v0.78.0 - 2026-05-27

### 用户需求

- 用户要求真实 `.svs` Stage 1-7 全链路按已确认方案做内存收敛，避免 pseudo-mask 构建一次性持有全部 patch，以及 six-class mask merge 构造 full-image per-pixel `source_trace`。
- 用户确认不解耦 `read_window_size / embed_size / stride`，只把 patch 读取和 embedding 改为 chunk/batch streaming。
- 用户确认 `batch_size` 固定默认使用 `512`。
- 用户确认取消 per-pixel `source_trace`，改为 compact provenance summary。
- 用户确认 full level0 six-class `.npy` mask 可作为临时中间文件写盘，但只在全流程目标输出成功后删除，最终 `generated_mask/mask.npy` 不删除。
- 用户要求所有图统一走同一套 streaming/block 流程，不保留小图/大图 AB 路径。

### 已做改动

- 版本号升级到 `v0.78.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `build_pseudo_mask_from_manifest()` 新增 `batch_size=512` 默认参数，按 batch 读取 patch 并调用 embedder，保留“所有 patch embedding 一起聚类”的行为。
- `pseudo_mask.npy` 改为 `numpy.lib.format.open_memmap()` 写出，`cluster_pseudo_mask.json` 记录 `batch_size`、`embedding_batch_count`、`streaming_patch_embedding` 和 `mask_write_mode`。
- `build_six_class_mask()` 改为统一 block streaming merge，可写入 `.npy` memmap；移除 full-image per-pixel `source_trace`，新增 `compact_provenance_summary`。
- compact provenance summary 记录全局 class counts、annotation class counts、block class counts、priority order、same-priority conflict count 和最多 5 个冲突样例。
- `build_six_class_mask_artifact()` 直接写出临时 full level0 mask memmap 和 metadata，artifact/summary 标记 `temporary_intermediate=true` 与 cleanup policy。
- 新增 `cleanup_temporary_six_class_masks()`，要求所有目标输出路径存在后才删除临时 six-class mask。
- `_load_project_mask_tile()` 对 `.npy` mask 使用 `numpy.load(..., mmap_mode="r")`。
- CLI `build-pseudo-mask` 新增 `--batch-size` 参数，默认 `512`。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/pseudo_mask.py`
- `src/he_wsi_generator/annotations/masks.py`
- `src/he_wsi_generator/annotations/pipeline.py`
- `src/he_wsi_generator/annotations/__init__.py`
- `src/he_wsi_generator/outputs/masks.py`
- `src/he_wsi_generator/models/training_batch.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_pseudo_mask_pipeline.py`
- `tests/test_annotations.py`
- `tests/test_training_batch.py`
- `tests/test_cli.py`
- `tests/test_version.py`
- 版本 fixture 更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_pseudo_mask_pipeline tests.test_annotations tests.test_training_batch tests.test_cli tests.test_version -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 batch streaming 参数、compact provenance、cleanup helper、mmap 读取和 CLI 参数；实现后通过，`Ran 29 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/priors/pseudo_mask.py src/he_wsi_generator/annotations/masks.py src/he_wsi_generator/annotations/pipeline.py src/he_wsi_generator/outputs/masks.py src/he_wsi_generator/models/training_batch.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py`
  - 结果：通过。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_stage1_7_e2e -v`
  - 结果：通过，`Ran 1 test ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过。
- 真实 `.svs` Stage 1-7 全链路复跑：
  - 结果：完成于 `build/validation/real-291288-stage1-7-v0770.YXQuif/`。
  - pseudo-mask：`patch_size=[1024,1024]`、`batch_size=512`、`patch_count=14536`、`embedding_batch_count=29`，写出 `pseudo-mask/pseudo_mask.npy`，shape `[93498,161352]`。
  - six-class mask：block streaming 写出 `mask-artifacts/six_class_mask_summary.json`，compact provenance `block_summaries=920`、`same_priority_conflict_count=0`。
  - 生成输出：`generated/gen-real-291288-stage1-7-v0780/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`qc_review.json`、`generation_run.json`、`batch.jsonl`、`output_summary.json`；最终 mask shape `[512,512]`，类别覆盖 `[0,1,2,3,4,5]`。
  - QC 状态为 `fail`，原因是 smoke backend/proxy reference limitation；`qc_review.json` 已记录 `decision=accepted`。
  - 临时 full level0 six-class mask `mask-artifacts/291288/mask.npy` 已在目标输出存在后删除；最终 `generated_mask/mask.npy` 保留。

## v0.77.0 - 2026-05-26

### 用户需求

- 用户要求根据 `docs/audit/2026-05-26-module-stage-code-audit.md` 的结论，只执行 `Stage 7` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 7`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现主体功能闭环，只处理会阻断主体链路的失败情况。
- 用户要求完成后复核 `Stage 1-7` 的链路是否通畅，确认无误后更新相关开发文档。

### 已做改动

- 版本号升级到 `v0.77.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 本轮只推进 `Stage 7 / M26`，不扩展 `M23-M25` 的功能面。
- 新增 [test_stage1_7_e2e.py](/home/muhengliao/LMH2025/Project/MultiCenterWSIGenerator/tests/test_stage1_7_e2e.py)，把分散的 smoke/E2E 检查收束成固定、最小、可重复的 `Stage 1-7` 端到端验收入口。
- `src/he_wsi_generator/ui/workflow.py` 新增可选 `job_root` 解析，允许 UI workflow helper 在不改变默认行为的前提下，把 job 状态目录与最终生成输出目录解耦。
- 完成 `Stage 1-7` 主链复核，确认当前版本下 job 创建、执行、状态读取、run-generation 输出、metadata/qc/batch index 和 output summary 可串通。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/workflow.py`
- `tests/test_stage1_7_e2e.py`
- `tests/test_ui_workflow.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_stage1_7_e2e -v`
  - 结果：开发过程中多轮 RED 失败符合预期，先后暴露了固定 E2E 入口中 generation config 未提前落盘、output_root 非空导致 run-generation 阻断，以及 workflow helper 默认把 job root 固定到 `output_root/ui_jobs` 的路径耦合问题。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow.UIWorkflowTests.test_run_generation_job_helpers_honor_explicit_job_root -v`
  - 结果：通过，`Ran 1 test ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow tests.test_ui tests.test_stage1_7_e2e tests.test_version -v`
  - 结果：通过，`Ran 43 tests ... OK`。
- `Stage 1-7` 主链复核：
  - 结果：通过，验证目录 `build/validation/stage1-7-chain-v0760.mdbi3uex/`；job 状态 `queued -> completed -> completed`，output summary 能定位 `generated.ome.tiff`、`mask.npy`、`qc.json`、`metadata.json`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/ui/workflow.py`
  - 结果：待本轮最后统一执行。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：待本轮最后统一执行。
- `git diff --check`
  - 结果：待本轮最后统一执行。

## v0.76.0 - 2026-05-26

### 用户需求

- 用户要求根据 `docs/audit/2026-05-26-module-stage-code-audit.md` 的结论，只执行 `Stage 6` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 6`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现主体功能闭环，只处理会阻断主体链路的失败情况。
- 用户要求完成后复核 `Stage 1-6` 的链路是否通畅，确认无误后更新相关开发文档。

### 已做改动

- 版本号升级到 `v0.76.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 本轮只推进 `Stage 6 / M20`，不扩展 `M21/M22`。
- `src/he_wsi_generator/generation/executor.py::_metadata_payload` 收敛 metadata 主线：
  - 新增 `_metadata_source_payload()`，在 source-conditioned 路径下回填真实 `source_wsi_id / source_wsi_path / source_region / source_scale`。
  - 新增 `_metadata_mask_schema()`，在 sampled layout mask 条件下按 schema 允许范围回填真实 artifact provenance，不再只保留空 mapping。
- 完成 `Stage 1-6` CLI 主链复核，确认当前版本生成的 `metadata.json / qc.json / batch.jsonl` 均能落盘，且 source-conditioned 生成样本的 metadata 已真实记录 source WSI 关系。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_uses_source_conditioned_mix_for_high_anchor tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_uses_sampled_layout_mask_condition -v`
  - 结果：开发过程中 RED 失败符合预期，旧 metadata 仍是 source 占位值，sampled layout mask 仍只写 placeholder `mask_schema`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_qc_review tests.test_ui tests.test_ui_workflow -v`
  - 结果：通过，`Ran 116 tests ... OK`。
- `Stage 1-6` CLI 主链复核：
  - 结果：通过，验证目录 `build/validation/stage1-6-chain-v0750.38NufZ/`；`training_run.status=initialized_not_trained`，生成样本 `metadata.source` 已记录真实 source WSI 路径与 region，`qc.json` 和 `batch.jsonl` 正常落盘。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/executor.py`
  - 结果：待本轮最后统一执行。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：待本轮最后统一执行。
- `git diff --check`
  - 结果：待本轮最后统一执行。

## v0.75.0 - 2026-05-26

### 用户需求

- 用户要求根据 `docs/audit/2026-05-26-module-stage-code-audit.md` 的结论，只执行 `Stage 5` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 5`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现主体功能闭环，只处理会阻断主体链路的失败情况。
- 用户明确要求不要开发任何 smoke 级新代码；若必须复用此前完成的 smoke 代码，需要将其迁移到主代码路径。
- 用户要求完成后复核 `Stage 1-5` 链路是否通畅，确认无误后再更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.75.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 本轮只推进 `Stage 5 / M16 / M18`，不扩展 Stage 6+。
- `src/he_wsi_generator/generation/executor.py` 收敛 `M16`：
  - 把现有 `run_smoke_generation()` 中可复用的 cascade 编排逻辑迁入共享 `Stage 5` 主路径 `_run_stage5_shared_cascade_core()`。
  - `generation_run.json` / plan 现在显式记录 `cascade_generation.pipeline_role=shared_stage5_cascade_core`、四层顺序和 tile traversal/blending 摘要。
- `src/he_wsi_generator/generation/executor.py` 补齐 `M18`：
  - 新增最小真实 `source_tile_rgb_mix` 行为，不再把新增功能挂在 smoke-only 分支。
  - 当 `structure_anchor > 0.3` 且存在 `source_wsi_id` 时，主路径会读取 source WSI 对应 tile，并按 anchor 强度与生成 tile 混合。
  - 若 CLI/调用方未显式传 `source_wsi_path`，主路径会从 prior manifest 的 `input_data.manifest_path` 中解析 `source_wsi_id -> wsi_path`。
- 完成 `Stage 1-5` CLI 主链复核，确认在当前代码边界下链路通畅。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_shared_stage5_cascade_core tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_uses_source_conditioned_mix_for_high_anchor -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 `plan.cascade_generation`，且 `run_smoke_generation()` 不接受 `source_wsi_path`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_resolves_source_wsi_from_prior_input_manifest -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现会回落到 `de_novo_generation`，不会从 prior manifest 解析 source WSI。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v`
  - 结果：通过，`Ran 43 tests ... OK`。
- `Stage 1-5` CLI 主链复核：
  - 结果：通过，验证目录 `build/validation/stage1-5-chain-v0740.vrjIfE/`；`training_run.status=initialized_not_trained`，`generation_run.plan.cascade_generation.source_condition.mode=source_tile_rgb_mix`，四层 OME-TIFF shape 为 `[512,512,3] -> [128,128,3] -> [32,32,3] -> [16,16,3]`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/executor.py`
  - 结果：待本轮最后统一执行。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：待本轮最后统一执行。
- `git diff --check`
  - 结果：待本轮最后统一执行。

## v0.74.0 - 2026-05-26

### 用户需求

- 用户要求根据 `docs/audit/2026-05-26-module-stage-code-audit.md` 的结论，只执行 `Stage 4` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 4`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现主体功能闭环，只处理会阻断主体链路的失败情况。
- 用户要求保留当前可复用代码，不重头开发，不删除已有后置增强能力，但本轮不围绕它继续扩展。
- 用户要求只做满足 `Stage 4 Gate` 的最小必要改动，并使用当前仓库规定的验证方式运行测试。
- 用户要求完成后更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.74.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 本轮只推进 `Stage 4 / M12`，不扩展 `M13-M15`。
- `src/he_wsi_generator/models/training_index.py::build_training_index` 由纯 contract 级记录收敛为最小多倍率训练样本主线：
  - 在既有四层记录结构上新增显式 `conditioning.style`、`conditioning.texture`、`conditioning.coord`、`conditioning.source`、`conditioning.structure_anchor`。
  - `conditioning.coord` 现在记录每个 `cascade_level` 对应的 `target_image_shape` 与 `target_mask_shape`。
- `src/he_wsi_generator/models/training_batch.py::load_training_batch` 现在会按目标 `cascade_level` 返回对应分辨率的 image/mask batch，不再把 `1/32 / 1/16 / 1/4` 都固定为 `512x512`。
- `load_training_batch()` 对 mask/image tile 的缩放采用最小必要的 nearest 策略，只为满足 Stage 4 样本主线，不提前引入 Stage 5/生成阶段逻辑。
- README、需求记录和 Stage 4 相关设计/开发文档代码追踪块同步到本轮边界。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training_index.py`
- `src/he_wsi_generator/models/training_batch.py`
- `tests/test_training_index.py`
- `tests/test_training_batch.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index tests.test_training_batch -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 `conditioning.style/coord/source/structure_anchor`，且 lower cascade level 仍固定输出 `512x512`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index tests.test_training_batch -v`
  - 结果：通过，`Ran 10 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_torch_training -v`
  - 结果：通过，`Ran 61 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/models/training_index.py src/he_wsi_generator/models/training_batch.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：待本轮最后统一执行。
- `git diff --check`
  - 结果：待本轮最后统一执行。
- 本轮暂未执行 Stage 5+ 生成、writer、QC 或 UI 相关测试；原因是本轮按用户要求只收敛 Stage 4 的 `M12`。

## v0.73.0 - 2026-05-26

### 用户需求

- 用户要求根据 `docs/audit/2026-05-26-module-stage-code-audit.md` 的结论，只执行 `Stage 1-3` 中状态为“缺失，需要后续新写”或“已有但需要简化/收敛”的 Module。
- 用户要求本轮只完成 `Stage 1-3`，不要提前开发后续 Stage，不要扩展后置增强项，优先实现主体功能闭环，只处理会阻断主体链路的失败情况。
- 用户要求保留当前可复用代码，不重头开发，不删除已有后置增强能力，但本轮不围绕它继续扩展。
- 用户要求只做满足 Stage Gate 的最小必要改动，补充或调整必要测试，并使用当前仓库规定的验证方式运行测试。
- 用户要求完成后更新相关开发文档，记录真实代码路径、函数/类、测试和验证命令。

### 已做改动

- 版本号升级到 `v0.73.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/io/audit.py::audit_manifest` 收敛 Stage 1 `M03`，在既有 WSI metadata audit 上补充 `center_id`、`tissue_type` 和 `annotation_summary`。
- `src/he_wsi_generator/annotations/masks.py` 收敛/补齐 Stage 2 `M05/M07`：
  - 新增 `load_annotation_source()`，统一读取 `png_mask`、`numpy_mask`、`roi_json` 和 `cluster_pseudo_mask`。
  - 新增 `build_six_class_mask()`，把人工 mask、ROI 和聚类伪 mask 候选按 `manual_mask > roi_json > cluster_pseudo_mask` 合并为统一 6 类 level0 mask。
  - 对 transform 非整数对齐、越界、未映射编号和同优先级冲突显式报错，不做 silent fallback。
- 新增 `src/he_wsi_generator/annotations/pipeline.py::build_six_class_mask_artifact` 与 CLI `build-six-class-mask`，把 manifest、audit 和 label mapping 收束为 `six_class_mask_summary.json` 及每张 WSI 的 mask artifact。
- 新增 `src/he_wsi_generator/priors/pseudo_mask.py::build_pseudo_mask_from_manifest` 与 CLI `build-pseudo-mask`，补齐 Stage 3 `M08` 的最小闭环：单张 WSI patch extraction、PatchEmbedder、embedding cache、cluster report 和 `cluster_pseudo_mask` 候选 artifact。
- `src/he_wsi_generator/embeddings/cluster.py` 修正 cluster center 初始化策略，避免前导重复 embedding 行导致空簇退化，保证 pseudo-mask pipeline 在当前 fixture 场景下能形成有效 cluster。
- README、需求记录和新的 Stage/Module 审计文档同步到本轮收敛边界；本轮没有扩展 Stage 4-7 主体实现。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/io/audit.py`
- `src/he_wsi_generator/annotations/masks.py`
- `src/he_wsi_generator/annotations/pipeline.py`
- `src/he_wsi_generator/annotations/__init__.py`
- `src/he_wsi_generator/priors/pseudo_mask.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/embeddings/cluster.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_wsi_io.py`
- `tests/test_annotations.py`
- `tests/test_embeddings.py`
- `tests/test_pseudo_mask_pipeline.py`
- `tests/test_cli.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/2026-05-26-module-stage-code-audit.md`
- `docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_wsi_io tests.test_annotations tests.test_pseudo_mask_pipeline -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 `center_id` 审计字段、`build_six_class_mask`、`load_annotation_source` 和 `he_wsi_generator.priors.pseudo_mask`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_embeddings tests.test_pseudo_mask_pipeline -v`
  - 结果：开发过程中 RED 失败符合预期，旧聚类初始化退化为 `{'0': 4, '1': 0}`，导致 pseudo mask 只有单一 cluster。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_embeddings tests.test_pseudo_mask_pipeline -v`
  - 结果：通过，`Ran 9 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_wsi_io tests.test_annotations tests.test_embeddings tests.test_pseudo_mask_pipeline tests.test_cli tests.test_schemas tests.test_wsi_tissue_overview tests.test_layout_mask_prior tests.test_layout_mask_sampler tests.test_style_prior tests.test_texture_prior tests.test_priors -v`
  - 结果：通过，`Ran 76 tests ... OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/io/audit.py src/he_wsi_generator/annotations/masks.py src/he_wsi_generator/annotations/pipeline.py src/he_wsi_generator/priors/pseudo_mask.py src/he_wsi_generator/embeddings/cluster.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：待本轮最后统一执行。
- 本轮暂未执行真实 SVS 全链路、Stage 4+ 训练/生成、editable install 或全量 300+ 测试；原因是本轮按用户要求只收敛 Stage 1-3 主体链路，并按开发文档建议围绕该阶段相关模块做集中验证。

## v0.72.32 - 2026-05-25

### 用户需求

- 用户要求循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 继续推进设计文档与开发附录覆盖的任务，但不要启用 multiagent；本轮由主会话直接推进 P4 writer 功能闭环。
- 用户要求继续开发前再次查看 `AGENTS.md`，并继续按里程碑集中验证节奏推进，不新增低价值 helper 级测试。
- 用户要求减少 smoke test 级代码开发，直接推进真正 gigabyte 级 WSI 输出可靠性；本轮聚焦 OME streaming writer progress evidence。
- 用户要求代码确认过关之后，再更新设计文档和开发文档代码追踪块。
- 用户要求先将当前工作区收束，整理所有未提交改动，不做后续开发；本轮收束使用两个只读 multiagent explorer 分别审查源码/测试/版本一致性和文档/审计/report 一致性。

### 已做改动

- 版本号升级到 `v0.72.32`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `write_pyramid_ome_tiff_streaming_from_tile_sources()` 在正常完整 tile iterator 写出路径新增 `<target>.progress.json` progress sidecar。
- progress sidecar 记录 planned level/tile 数、已 yield 给 `tifffile` 的 tile 数、当前 level/tile grid 位置、last tile、最后更新时间、失败原因和 `progress_semantics=tiles_yielded_to_tifffile_iterator_not_ome_internal_resume`。
- started/completed/failed transaction manifest 新增 `progress_manifest_path` 和 `progress_summary`；失败 transaction 会保留失败前 writer 进度和 failure reason。
- `generation_output_diagnostics.json` 的 `writer_summary.progress_manifest_path` / `writer_summary.progress_summary` 透传 writer 进度摘要，schema validator 对 progress summary 状态、计数字段和 `resume_capable=false` 做契约校验。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.32`；继续明确本轮不是同一 OME-TIFF 文件内部 partial tile 续写，也不是内置 production diffusion / ControlNet / DiT 模型。
- 收束阶段修正 README 中关于 `torch-diffusion-smoke --wsi-writer tile-streaming` 的过时说明，并同步补充全量单元测试与 CLI 版本验证记录。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/test_schemas.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `.agent/reports/p3-backend-compatibility-contract-20260525.md`
- `.agent/reports/p3-inference-architecture-condition-contract-20260525.md`
- `.agent/reports/p3-production-training-contract-20260525.md`
- `.agent/reports/p3-torch-diffusion-smoke-inference-planning-20260525.md`
- `.agent/reports/p3-training-objective-contract-20260525.md`
- `.agent/reports/p4-generation-output-diagnostics-contract-20260525.md`
- `.agent/reports/p4-mask-image-tissue-alignment-qc-20260525.md`
- `.agent/reports/p5-prior-production-readiness-contract-20260525.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_records_transaction_manifest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_failed_transaction_preserves_target -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现报错 `KeyError: 'progress_manifest_path'`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_records_transaction_manifest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_failed_transaction_preserves_target -v`
  - 结果：通过，`Ran 2 tests in 0.005s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 84 tests in 3.295s OK`。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 收束审计补充验证：`conda run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 300 tests in 28.868s OK`。
- 收束审计补充验证：`conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli --version`
  - 结果：输出 `v0.72.32`。
- 收束审计补充：两个只读 multiagent explorer 完成审查，结论均要求把未跟踪的 `src/he_wsi_generator/generation/production_streaming.py` 和 8 个被 changelog/audit 引用的 `.agent/reports/*.md` 纳入同一收束提交。
- 本轮暂未执行 editable install、包元数据检查或真实 SVS 全链路复跑；原因是本轮按 OME streaming writer progress evidence 代码里程碑做集中验证，未进入发布打包或真实数据全链路验收。

## v0.72.31 - 2026-05-25

### 用户需求

- 用户要求删除 mamba 环境 `MultiCenterWSIGenerator`，并在 conda 环境 `MultiCenterWSIGenerator` 中开发；本轮确认 conda/mamba 同名环境指向同一个 prefix，因此不删除共享环境目录，后续开发和验证统一使用 `conda run -n MultiCenterWSIGenerator ...`。
- 用户要求继续开发前再次查看 `AGENTS.md`，并继续按里程碑集中验证节奏推进，不新增低价值 helper 级测试。
- 用户要求减少 smoke test 级代码开发，直接推进真正 gigabyte 级 WSI 生成；本轮聚焦 `production-tile-stream` 外部 backend 执行证据合同。
- 用户要求代码确认过关之后，再更新设计文档和开发文档代码追踪块。

### 已做改动

- 版本号升级到 `v0.72.31`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `materialize_production_tile_sources()` 在每个新完成 production tile record 中写入 `request_evidence`、`backend_execution` 和 `output_evidence`。
- `request_evidence` 记录 per-tile request JSON 的相对路径、大小和 SHA-256；`backend_execution` 记录外部命令 command、cwd、return code、timeout、duration 和有限 stdout/stderr preview；`output_evidence` 记录 RGB tile 和 level0 mask tile 的相对路径、大小和 SHA-256。
- `production_tile_source_manifest.json` 顶层新增 `backend_execution_summary`，统计 completed tile 中 request / execution / output evidence 的覆盖情况。
- `generation_output_diagnostics.json` 的 `tile_source.backend_execution_summary` 透传上述覆盖统计，`validate_generation_output_diagnostics()` 接受并校验该摘要字段。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.31`；继续明确本轮不是内置 production latent diffusion / ControlNet / DiT 模型，也不是同一 OME-TIFF 文件内部 partial tile 续写。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/production_streaming.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda env list`
  - 结果：`MultiCenterWSIGenerator` 指向 `/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator`。
- `mamba env list`
  - 结果：`MultiCenterWSIGenerator` 指向 `/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator`，与 conda 同 prefix；本轮未删除共享环境目录。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_writes_external_backend_tiles -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现报错 `KeyError: 'backend_execution_summary'`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_writes_external_backend_tiles -v`
  - 结果：通过，`Ran 1 test in 0.448s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/production_streaming.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 47 tests in 3.578s OK`。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 production tile backend execution evidence 及其直接相关 generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.30 - 2026-05-25

### 用户需求

- 用户要求删除 mamba 环境 `MultiCenterWSIGenerator`，并在 conda 环境 `MultiCenterWSIGenerator` 中开发；本轮确认 conda/mamba 同名环境指向同一个 prefix，因此不删除共享环境目录，后续开发和验证统一使用 `conda run -n MultiCenterWSIGenerator ...`。
- 用户要求继续开发前再次查看 `AGENTS.md`，并继续按里程碑集中验证节奏推进，不新增低价值 helper 级测试。
- 用户要求减少 smoke test 级代码开发，直接推进真正 gigabyte 级 WSI 输出可靠性；本轮聚焦 OME streaming writer 写入前磁盘空间 preflight。
- 用户要求代码确认过关之后，再更新设计文档和开发文档代码追踪块。

### 已做改动

- 版本号升级到 `v0.72.30`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `write_pyramid_ome_tiff_streaming_from_tile_sources()` 在打开 `TiffWriter` 和读取 tile iterator 前新增 `disk_space_preflight`，用 raw pyramid byte estimate 加同等安全余量检查目标文件系统可用空间。
- 空间不足时显式抛出 `OutputWriteError`，写出 failed transaction，并避免开始 tile iterator 写入。
- completed target reuse 或 started temporary recovery 路径不重复做新写入空间 preflight；正常完整写出路径会在 transaction、streaming write report、streaming contract 和 diagnostics `writer_summary.disk_space_preflight` 中保留 preflight 摘要。
- `validate_generation_output_diagnostics()` 接受并校验 `writer_summary.disk_space_preflight`，要求 status、target directory 和非负字节字段符合契约。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.30`；继续明确本轮不是精确 TIFF 体积预测、不是同一 OME-TIFF 文件内部 partial tile 续写，也不是内置 production diffusion/ControlNet/DiT 模型。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/test_schemas.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda env list`
  - 结果：`MultiCenterWSIGenerator` 指向 `/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator`。
- `mamba env list`
  - 结果：`MultiCenterWSIGenerator` 指向 `/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator`，与 conda 同 prefix；本轮未删除共享环境目录。
- `conda run -n MultiCenterWSIGenerator python --version`
  - 结果：`Python 3.11.15`。
- `conda run -n MultiCenterWSIGenerator python -c "import sys; print(sys.executable)"`
  - 结果：`/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator/bin/python`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_rejects_insufficient_disk_space -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现报错 `AttributeError: module ... does not have the attribute '_streaming_disk_space_report'`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_rejects_insufficient_disk_space -v`
  - 结果：通过，`Ran 1 test in 0.002s OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_rejects_insufficient_disk_space tests.test_generation_runner.GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer tests.test_schemas.SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract -v`
  - 结果：通过，`Ran 3 tests in 0.211s OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 84 tests in 3.753s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4 OME streaming disk-space preflight 及其直接相关 outputs/generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.29 - 2026-05-25

### 用户需求

- 用户要求循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 继续完成设计文档与开发附录覆盖的任务，但不要启用 multiagent；本轮由主会话继续推进 P4 writer 可靠性。
- 用户要求减少 smoke test 级代码开发，直接推进真正 gigabyte 级 WSI 输出可靠性；本轮聚焦 OME streaming writer 对已发布目标文件的验证复用。
- 用户要求每完成开发节点里程碑后集中测试主功能，不增加额外 helper 级测试；代码确认过关后再更新设计文档和开发文档代码追踪块。

### 已做改动

- 版本号升级到 `v0.72.29`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `write_pyramid_ome_tiff_streaming_from_tile_sources()` 新增 completed transaction 目标复用：当既有 transaction 为 `completed`，且 target path、tile source manifest path 与当前 plan 匹配时，先验证已发布目标 OME-TIFF 可读且 pyramid shapes 一致。
- 校验通过后跳过 tile iterator 重写，复用现有目标 OME-TIFF，并在 transaction 中记录 `recovery_action=validated_existing_target_ome_tiff`。
- streaming writer report 新增 `reused_existing_target`，diagnostics `writer_summary` 同步记录 `reused_existing_target` 与 `recovered_from_temporary`，用于区分“已发布目标复用”和“started 临时文件发布恢复”。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.29`；继续明确本轮不是同一 OME-TIFF 文件内部 partial tile 续写，也不是内置 production diffusion/ControlNet/DiT 模型。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_reuses_completed_target_ome -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现触发 `AssertionError: should reuse completed target OME-TIFF`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_reuses_completed_target_ome tests.test_generation_runner.GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer -v`
  - 结果：通过，`Ran 2 tests in 0.150s OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 83 tests in 3.420s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，输出 `generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4 completed OME target validation reuse 及其直接相关 outputs/generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.28 - 2026-05-25

### 用户需求

- 用户要求继续开发前再次查看 `AGENTS.md`，并在 conda 环境 `MultiCenterWSIGenerator` 中开发；本轮确认 conda/mamba 同名环境指向同一 prefix，因此未删除共享环境目录。
- 用户要求减少 smoke test 级别代码开发，直接推进真正 gigabyte 级 WSI 生成相关能力；本轮聚焦 `production-tile-stream` 的 failed tile 显式重试恢复。
- 用户要求每完成开发节点里程碑后集中测试主功能，不增加额外 helper 级测试；代码确认过关后再更新设计文档和开发文档代码追踪块。

### 已做改动

- 版本号升级到 `v0.72.28`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `run_production_tile_stream_generation()` 与 `materialize_production_tile_sources()` 新增 `retry_failed_tiles` 显式参数；默认仍拒绝包含 failed tile 的 production tile source resume manifest。
- `_load_resumable_tile_source_manifest()` 在 `retry_failed_tiles=True` 时先校验 manifest 顶层字段和每条 tile 的不可变字段（含 `tile_request_path`），再把 failed record 重置为 pending 重新调用外部 backend。
- 重试完成后的 tile record 保留 `retry_from_failed`、`previous_status`、`previous_error_message` 和 `retry_count` 审计字段，并继续维护 attempt count、completed/pending/failed 计数和 resume index。
- CLI `run-generation` 新增 production 专用 `--retry-failed-tiles`；smoke-cascade 和 torch-diffusion-smoke 使用该参数会显式报错，避免把 production tile source retry 与 smoke resume 或 torch sampling 混淆。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.28`；继续明确本轮只覆盖 OME 发布前的 production tile source 物化恢复，不是内置 production diffusion/ControlNet/DiT 模型，也不是同一 OME-TIFF 文件内部 partial tile 续写。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/production_streaming.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_retries_failed_tile_source_manifest_when_requested -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现报错 `TypeError: run_production_tile_stream_generation() got an unexpected keyword argument 'retry_failed_tiles'`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_retries_failed_tile_source_manifest_when_requested -v`
  - 结果：通过，`Ran 1 test in 0.549s OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 47 tests in 3.778s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/production_streaming.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4 production failed tile retry/resume 及其直接相关 generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.27 - 2026-05-25

### 用户需求

- 用户要求继续开发前再次查看 `AGENTS.md`，并在 conda 环境 `MultiCenterWSIGenerator` 中开发。
- 用户要求不要删除共享 prefix 的 `MultiCenterWSIGenerator` 环境；本轮再次确认 `mamba env list` 与 `conda env list` 指向同一目录，因此保留环境并统一使用 `conda run -n MultiCenterWSIGenerator ...`。
- 用户要求减少 smoke test 级别代码开发，直接推进真正 gigabyte 级 WSI 生成相关能力；本轮聚焦 `production-tile-stream` 外部 backend 的 per-tile request manifest 输入合同。

### 已做改动

- 版本号升级到 `v0.72.27`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `production-tile-stream` 的 `production_tile_source_manifest.json` 新增顶层 `request_manifest_type="production_tile_request_v1"`，每条 tile record 新增稳定 `tile_request_path`。
- 外部 tile backend 执行前写出 `production_tile_requests/level-*-tile-*.request.json`，记录 generated id、random seed、condition packet path、tile 坐标/shape/write region、RGB/mask 输出路径、prior、checkpoint 和 backend 摘要。
- `external_tile_generator_v1` 命令模板新增 `{tile_request_path}` 占位符，允许真实外部 backend 通过单个 request JSON 消费完整 tile 请求，而不是只依赖零散命令行占位符。
- production tile source resume 校验把 `request_manifest_type` 与每条 `tile_request_path` 纳入不可变合同，避免恢复时混用旧 request。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.27`；继续明确本轮不是内置 production diffusion/ControlNet/DiT 模型，也不是同一 OME-TIFF 文件内部 partial tile 续写。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/production_streaming.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_writes_tile_request_manifests -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现报错 `external tile backend command has unknown placeholder: 'tile_request_path'`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_production_tile_stream_generation_writes_tile_request_manifests -v`
  - 结果：通过，`Ran 1 test in 0.352s OK`。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 46 tests in 2.730s OK`。
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/production_streaming.py`
  - 结果：通过，无输出。
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无输出。
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4 production tile request manifest contract 及其直接相关 generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.26 - 2026-05-25

### 用户需求

- 用户要求继续开发前再次查看 `AGENTS.md`，并在 conda 环境 `MultiCenterWSIGenerator` 中开发。
- 用户要求删除 mamba 环境 `MultiCenterWSIGenerator`；本轮确认 mamba 与 conda 列出的该环境是同一个 prefix，因此未删除要保留的 conda 环境，后续验证统一使用 `conda run -n MultiCenterWSIGenerator ...`。
- 用户要求减少 smoke test 级别开发，继续推进真正 gigabyte 级 WSI 生成相关能力；本轮聚焦 P4 OME streaming writer 在发布阶段的恢复能力。

### 已做改动

- 版本号升级到 `v0.72.26`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `write_pyramid_ome_tiff_streaming_from_tile_sources()` 在新写入前读取既有 `<target>.transaction.json`，识别上次 `started` transaction 留下的完整临时 OME-TIFF。
- 新增 started transaction temporary publish recovery：当 transaction 目标路径、tile source manifest 路径和临时 OME-TIFF pyramid shapes 均与当前 plan 匹配时，跳过 tile iterator 重写，直接原子发布该临时文件。
- completed transaction 新增 `recovery_action="published_existing_temporary_ome_tiff"`；返回报告新增 `streaming_write_report.recovered_from_temporary`，用于审计是否发生恢复发布。
- 临时 OME-TIFF 不可读或 pyramid shape 不匹配时，writer 不接受该临时文件，而是清理后基于完整 tile source 重新写出。
- README、需求记录、审计验收清单、审计决策、实施计划、开发附录和研究设计同步到 `v0.72.26`；明确本轮不是同一 OME-TIFF 文件内部 append/resume，`resume_capable=false` 继续保留。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- 版本断言更新涉及 `tests/*.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_publishes_recovered_temporary_ome -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现会尝试重新读取 tile iterator。
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_publishes_recovered_temporary_ome -v`
  - 结果：通过，`Ran 1 test ... OK`
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 80 tests in 2.615s OK`
- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py`
  - 结果：通过，无输出
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮暂未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4 OME streaming temporary publish recovery 及其直接相关 writer/generation/schema/CLI/version 闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.25 - 2026-05-25

### 用户需求

- 用户要求继续开发前再次查看 `AGENTS.md`，并在 `conda` 环境 `MultiCenterWSIGenerator` 中开发。
- 用户要求确认代码过关之后，再更新设计文档和开发文档的代码追踪块；当前生产 tile-stream 闭环已经实现，本轮补齐相关最小章节 trace。
- 继续按“开发文档代码里程碑完成后集中验证”的节奏推进，不新增额外 helper 级测试。

### 已做改动

- 版本号升级到 `v0.72.25`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 重新读取并更新 `AGENTS.md`，固化里程碑集中验证、减少 helper 级测试、以及功能实现/修改后维护设计与开发文档最小章节代码追踪块的约束。
- 确认 `mamba env list` 与 `conda env list` 中的 `MultiCenterWSIGenerator` 指向同一个 prefix：`/home/muhengliao/miniconda3/envs/MultiCenterWSIGenerator`；因此未删除该目录，后续验证命令改用 `conda run -n MultiCenterWSIGenerator ...`。
- 补齐开发附录 `4.5 输出契约`、`7.4 推理与 OME-TIFF 重建`、`10. 测试与验收` 的 Implementation Trace，记录 production tile-stream 真实代码路径、依赖链、测试和验证命令。
- 补齐研究设计 `9.1 输出文件结构`、`9.2 必填 metadata 字段`、`9.3 成功标准与失败信号`、`10.1 QC 定位`、`10.4 QC 结果解释` 的 Relevant Code，记录 production tile-stream 输出、metadata、diagnostics、QC 与当前边界。
- README、需求记录、审计验收清单、审计决策和实施计划同步到 `v0.72.25`；明确本轮是文档追踪块和审计基线同步，不新增内置 production diffusion 模型或 OME-TIFF 文件级中断续写。

### 影响文件

- `AGENTS.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_layout_mask_sampler.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_qc_review.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_ui_workflow.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `tests/test_wsi_tissue_overview.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/DECISIONS.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/production_streaming.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/cli.py src/he_wsi_generator/cli_commands.py src/he_wsi_generator/schemas.py`
  - 结果：通过，无输出
- `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 45 tests in 2.458s OK`
- `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未执行全量单元测试、editable install、CLI 版本、包元数据检查或真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 production tile-stream 与追踪块同步相关主功能闭环，真实 SVS 复跑和发布包检查属于更大范围验收。

## v0.72.24 - 2026-05-25

### 用户需求

- 用户要求减少 smoke test 级别代码开发，直接着手真正 gigabyte 级别 WSI 的生成开发。
- 继续按“功能闭环完成后集中验证”的节奏推进；本轮只围绕 production tile-stream WSI 生成主功能补测试。
- 设计文档与开发文档中的代码追踪块继续等所有开发里程碑结束后统一补充。

### 已做改动

- 版本号升级到 `v0.72.24`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 新增 `src/he_wsi_generator/generation/production_streaming.py`，定义 `production-tile-stream` 外部 tile generator 合同、逐 tile 命令执行、可恢复 `production_tile_source_manifest.json`、GB 级未压缩字节估算、memmap mask 写出和 streaming QC。
- `run-generation` 新增 `production-tile-stream` backend；只接受 production-ready checkpoint，checkpoint artifact 必须声明 `external_tile_generator_v1` 命令合同。
- production tile-stream backend 按四层 pyramid tile grid 写出磁盘 `.npy` tile source 和 level0 mask tile，不构造整张 level0 canvas，再复用现有 tiled iterator writer 原子发布 OME-TIFF。
- diagnostics schema 接受 `production-tile-stream`，metadata / generation run summary / diagnostics 会记录 writer、tile source、mask 和 QC 状态。
- README、需求和审计文档同步记录当前边界：本轮实现外部 production tile backend 接入与磁盘级 WSI 生成执行合同，不实现内置 production diffusion 模型或 OME-TIFF 文件级中断续写。
- 按当前 `AGENTS.md` 约束，本轮未更新设计文档和开发文档的章节级代码追踪块；待所有开发里程碑结束后统一补充。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/generation/production_streaming.py`
- `tests/test_generation_runner.py`
- `tests/test_version.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - 结果：通过，`Ran 45 tests in 2.807s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出

## v0.72.23 - 2026-05-25

### 用户需求

- 用户要求继续循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 推进设计文档与开发附录覆盖的任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户最新目标要求根据开发文档优先完成功能实现代码；每完成开发节点中的里程碑后，再对主功能集中测试；不要增加额外测试；设计文档与开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4.5 production prior 与采样策略：让 texture prior 输出可审计 fitted embedding-cluster codebook、prototype `texture_token` 和 `morphology_latent`，并让 sampled texture policy / condition packet / generation summary 保留该条件对象。

### 已做改动

- 版本号升级到 `v0.72.23`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `texture_prior.json` 新增 `texture_codebook`，记录 `fitted_embedding_cluster_codebook_v1`、token schema、morphology latent schema 和 `condition_outputs=["texture_token","morphology_latent"]`。
- `texture_prototypes` 新增 `texture_token` 与标准化 `morphology_latent`，让每个 cluster prototype 同时携带离散 token 和 morphology latent 条件对象。
- `sample_texture_policy_from_prior()` 新增 `texture_token` / `morphology_latent` 校验与输出，并写入 `texture_codebook_reference`。
- `build_generation_condition_packet()` 会校验 sampled texture policy 的 `morphology_latent`，并把 token、latent 和 codebook reference 写入 `conditions.texture_token`。
- smoke generation summary 与 torch smoke summary 继续保留 sampled texture policy 的 `morphology_latent`、`texture_token` 和 codebook reference。
- README、需求和审计文档同步记录当前边界：本轮是 fitted embedding-cluster codebook / morphology latent contract，不是 trainable texture codebook、VQ-VAE 或 production morphology token sampler。
- 按当前 `AGENTS.md` 约束，本轮未更新设计文档和开发文档的章节级代码追踪块；待所有开发里程碑结束后统一补充。

### 影响文件

- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/texture.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_texture_prior.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`
- `tests/test_version.py`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_texture_prior tests.test_generation_conditioning tests.test_generation_runner tests.test_torch_training tests.test_version -v`
  - 结果：通过，`Ran 69 tests in 20.023s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过
- `git diff --check`
  - 结果：通过
- 未执行全量单元测试和真实 SVS 全链路复跑；原因是本轮按里程碑测试节奏只验证 P4.5 texture prior / sampled policy / condition summary 主功能闭环，真实 SVS 复跑属于更大范围验收。

## v0.72.22 - 2026-05-25

### 用户需求

- 用户要求继续循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 推进设计文档与开发附录覆盖的任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户最新目标要求根据开发文档优先完成功能实现代码；每完成开发节点中的里程碑后，再对主功能集中测试；不要增加额外测试；设计文档与开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4.5 production prior 与采样策略：让 style prior 输出可审计 fitted style latent encoder 和 tile-level `style_latent`，而不是只保留 RGB 均值统计。

### 已做改动

- 版本号升级到 `v0.72.22`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `build_style_prior_from_training_index()` 新增 `fitted_rgb_stats_pca_v1`，用 tile RGB mean/std 归一化特征拟合固定 3 维 style latent encoder。
- `style_prior.json` 新增 `style_latent_encoder`，记录 feature schema、feature mean、PCA components、explained variance、condition outputs 和限制说明。
- `tile_style_records` 新增 `style_latent`，让每个 tile-level style record 同时携带 RGB 均值和可被条件包引用的 latent。
- `sample_style_policy_from_prior()` 新增 `style_latent` 校验与输出，并写入 `style_latent_encoder_reference`。
- README、需求和审计文档同步记录当前边界：本轮是 fitted RGB-stat style latent，不是深度 trainable style encoder、VAE style latent、style transfer 模型或 production style conditioning backend。
- 按当前 `AGENTS.md` 里程碑执行约束，设计文档和开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充；本轮未新增追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/style.py`
- `tests/test_style_prior.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior.StylePriorTests.test_build_style_prior_from_training_index_writes_rgb_statistics tests.test_style_prior.StylePriorTests.test_sample_style_policy_from_prior_writes_selected_style_artifact -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 `style_latent_encoder` 和 `style_latent`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior.StylePriorTests.test_build_style_prior_from_training_index_writes_rgb_statistics tests.test_style_prior.StylePriorTests.test_sample_style_policy_from_prior_writes_selected_style_artifact -v`
  - 结果：通过，`Ran 2 tests in 0.137s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior tests.test_version -v`
  - 结果：通过，`Ran 8 tests in 0.413s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮暂未执行真实 deep trainable style encoder 训练、VAE style latent、production style conditioning backend、真实 production 推理或真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.21 - 2026-05-25

### 用户需求

- 用户要求继续循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 推进设计文档与开发附录覆盖的任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户最新目标要求根据开发文档优先完成功能实现代码；每完成开发节点中的里程碑后，再对主功能集中测试；不要增加额外测试；设计文档与开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P5 prior 边界：让 `prior_manifest.production_readiness.production_ready=true` 必须由 production prior component contract v1、condition outputs 和训练证据 artifact path/hash 对齐共同支撑。

### 已做改动

- 版本号升级到 `v0.72.21`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `validate_prior_manifest()` 在 `production_ready=true` 时继续拒绝 statistical/proxy backend，并进一步要求 layout/style/texture component 声明 `contract_version="production_prior_component_v1"`。
- production prior component contract 新增 `condition_outputs` 校验：layout/mask prior 需输出 `layout` / `mask`，style prior 需输出 `style_seed` / `style_latent`，texture prior 需输出 `texture_token` / `morphology_latent`。
- production prior component contract 新增 `training_evidence` 校验，要求 `training_run_id` 非空，并要求 `artifact_path` / `artifact_sha256` 与 manifest 中对应 artifact 完全匹配。
- README、需求和审计文档同步记录当前边界：本轮是 production prior component contract interface，不是 trainable layout/mask generator、trainable style encoder、texture codebook、VQ-VAE 或 morphology token sampler。
- 按当前 `AGENTS.md` 里程碑执行约束，设计文档和开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充；本轮未新增追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_priors.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_priors tests.test_version -v`
  - 结果：通过，`Ran 14 tests in 0.090s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮暂未执行真实 production prior 训练、真实 production 推理或真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.20 - 2026-05-25

### 用户需求

- 用户要求继续循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 推进设计文档与开发附录覆盖的任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 本批次继续推进 P3 / M5 训练与生成骨架：让 `init-training-run` 在已有 production training dataset contract、training index JSONL 证据核对和 training objective/loss/QC mapping contract 之后写出可审计的 production training plan artifact。
- 本轮维护相关设计文档和开发附录的章节级代码追踪块，明确当前仍是 plan-only，不是 production 训练 loop。

### 已做改动

- 版本号升级到 `v0.72.20`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `create_training_run()` 新增 `training_plan.json` 写出，artifact 类型为 `production_training_plan`。
- `training_plan.json` 记录 `prior_ready -> image_generator -> wsi_consistency` 三阶段、每阶段 objectives、条件输入、输出占位和 QC 映射。
- `training_run.json` 和 skeleton `checkpoint_manifest.json` 新增 `training_plan_path` 引用，使 run / plan / checkpoint 形成可追踪闭环。
- README、需求和审计文档同步记录当前边界：本轮是 production training plan artifact，不是真实 production latent diffusion / ControlNet / DiT 训练、production checkpoint 或 production sampler。
- 设计文档 §7.1、§7.4、§7.5、§7.6 和开发附录 §7.1、§7.2 更新本轮真实 `Relevant Code` / `Implementation Trace`。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现缺少 `training_plan_path`，触发 `KeyError: 'training_plan_path'`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint -v`
  - 结果：通过，`Ran 1 test in 0.002s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint tests.test_version -v`
  - 结果：通过，`Ran 3 tests in 0.002s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_version -v`
  - 结果：通过，`Ran 36 tests in 0.100s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未执行真实 production diffusion 训练、真实 production 推理或真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.19 - 2026-05-25

### 用户需求

- 用户要求继续循环使用 `project-remediation-audit` 和 `codex-worker-orchestration` 推进设计文档与开发附录覆盖的任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户最新目标要求根据开发文档优先完成功能实现代码；每完成开发节点中的里程碑后，再对主功能集中测试；不要增加额外测试；设计文档与开发文档中的节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4 / M6 自动 QC：补充 stain / focus proxy，让 `qc.json` 能暴露近单色染色缺失和局部边缘对比缺失。

### 已做改动

- 版本号升级到 `v0.72.19`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `build_qc_report()` 的 WSI 级 metrics 新增 `stain_color_separation_proxy`，用 RGB 通道平均分离度暴露近单色输出。
- `build_qc_report()` 的 tile 级 metrics 新增 `focus_edge_density_proxy`，用局部边缘对比暴露无焦点/大面积平坦输出。
- 新增主功能测试覆盖低 stain/focus proxy fail，并扩展已有 QC 输出质量测试，确认新增 metrics 被写入。
- `AGENTS.md` 更新为最新里程碑执行约束：优先完成功能实现，里程碑闭环后集中验证主功能，不额外增加测试，节点代码追踪块等所有开发里程碑结束后再统一补充。
- 设计文档 §10.2 / §10.3 和开发附录 §8 更新本轮真实 `Relevant Code` / `Implementation Trace`。
- README、需求和审计文档同步记录当前边界：本轮是轻量 stain/focus QC proxy，不是专家级 stain/focus 模型、production diffusion backend 或真实 production QC。

### 影响文件

- `AGENTS.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/engine.py`
- `tests/test_outputs_qc_archive.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_flags_low_stain_and_focus_proxy -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现只到 `overall_status=warning`，未把低 stain/focus proxy 暴露为 fail
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_flags_low_stain_and_focus_proxy -v`
  - 结果：通过，`Ran 1 test in 0.006s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_reads_outputs_and_records_quality_metrics -v`
  - 结果：通过，`Ran 1 test in 0.010s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_version -v`
  - 结果：通过，`Ran 36 tests in 0.105s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.18 - 2026-05-25

### 用户需求

- 用户要求继续根据设计文档和开发附录推进未完成任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户要求根据开发文档优先完成功能实现代码，每完成开发节点中的里程碑后再对主功能集中测试，不额外增加测试；节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4 / M6 输出可靠性：让自动 QC 的 `seam_score_proxy` 使用 writer chunk/tile grid 的真实内部边界，而不是只检查图像中线，避免漏掉非中线 tile seam 突变。

### 已做改动

- 版本号升级到 `v0.72.18`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `build_qc_report()` 将 `pyramid_report` 传入图像质量指标计算，使 seam proxy 能读取 writer 报告。
- `_seam_score_proxy()` 优先读取 `pyramid_report.chunked_write_audit.levels[0].chunk_shape`、`pyramid_report.chunked_write_audit.chunk_shape` 或 `pyramid_report.streaming_write_report.tile_shape`，按 writer 的内部 chunk/tile 边界计算边界差异。
- 缺少可用 writer grid 或图像没有内部 writer 边界时，保留旧的图像中线 seam proxy 作为轻量回退。
- 新增主功能回归测试，覆盖非中线 writer tile 边界颜色突变会让 `seam_score_proxy` 进入 fail。
- README、需求和审计文档同步记录当前边界：本轮是 writer tile-grid seam QC proxy，不是专家级 morphology seam detector、production diffusion backend 或可恢复 OME-TIFF 文件续写。
- 按用户最新要求，本轮不更新设计文档和开发附录中的章节级代码追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/engine.py`
- `tests/test_outputs_qc_archive.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_uses_writer_tile_grid_for_seam_proxy -v`
  - 结果：开发过程中 RED 失败符合预期，旧实现只检查中线，未能让非中线 writer tile seam 进入 fail
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_uses_writer_tile_grid_for_seam_proxy -v`
  - 结果：通过，`Ran 1 test in 0.006s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_version -v`
  - 结果：通过，`Ran 35 tests in 0.098s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.17 - 2026-05-25

### 用户需求

- 用户要求继续根据设计文档和开发附录推进未完成任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户要求根据开发文档优先完成功能实现代码，每完成开发节点中的里程碑后再对主功能集中测试，不额外增加测试；节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4 / M6 输出可靠性：让 `torch-diffusion-smoke` backend 也能选择 `--wsi-writer tile-streaming`，把已有 PyTorch smoke cascade sample previews 物化为四层磁盘 tile source，并复用受限 tiled iterator writer 写出 OME-TIFF。

### 已做改动

- 版本号升级到 `v0.72.17`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `run_torch_diffusion_smoke_generation()` 新增 `wsi_writer` 参数，支持 `array` 与 `tile-streaming` 两种 writer。
- 新增 `_write_torch_diffusion_smoke_tile_source_manifest()`，将四层 PyTorch smoke cascade sample preview 物化为 `tile_source_manifest.streaming.json` 与 `streaming_tiles/*.npy`。
- `torch-diffusion-smoke` 的 `tile-streaming` 路径调用 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 写出 OME-TIFF，并在 plan、metadata、generation run summary 和 diagnostics 中保留 writer 与 tile source 状态。
- CLI `run-generation --backend torch-diffusion-smoke --wsi-writer tile-streaming` 不再被 writer gating 拒绝；`--resume-tile-manifest` 仍只支持 `smoke-cascade`。
- README、需求和审计文档同步记录当前边界：本轮是 PyTorch smoke backend 到磁盘 tile source writer 的接入，不是 production diffusion backend 或可恢复 OME-TIFF 文件续写。
- 按用户最新要求，本轮不更新设计文档和开发附录中的章节级代码追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_torch_training.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_uses_tile_streaming_writer -v`
  - 结果：RED 失败符合预期，旧实现不接受 `wsi_writer` 参数
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_uses_tile_streaming_writer -v`
  - 结果：通过，`Ran 1 test in 3.115s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_uses_tile_streaming_writer tests.test_generation_runner.GenerationRunnerTests.test_cli_requires_training_index_for_torch_diffusion_smoke_tile_streaming tests.test_version -v`
  - 结果：通过，`Ran 4 tests in 2.566s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training tests.test_generation_runner tests.test_version -v`
  - 结果：通过，`Ran 53 tests in 15.011s OK`
- `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.16 - 2026-05-25

### 用户需求

- 用户要求继续根据设计文档和开发附录推进未完成任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户要求根据开发文档优先完成功能实现代码，每完成开发节点中的里程碑后再对主功能集中测试，不额外增加测试；节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次继续推进 P4 / M6 输出可靠性：让 smoke-cascade 显式 `--wsi-writer tile-streaming` 的四层 direct tile source 物化过程支持从已有 `tile_source_manifest.streaming.json` 继续完成 pending tile，避免重跑时覆盖已完成 streaming tile。

### 已做改动

- 版本号升级到 `v0.72.16`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `_write_smoke_direct_multilevel_tile_source_manifest()` 现在先写入 pending 状态 manifest，再逐 tile 生成 `.npy` 并刷新 `completed_tile_count`、`pending_tile_count`、`failed_tile_count` 和 `generation_status`。
- 新增 `_load_resumable_smoke_direct_tile_source_manifest()`，重跑时校验已有 streaming tile source manifest 与当前 generation plan 完全匹配，并复用已完成 tile。
- 新增 `_ensure_smoke_direct_tile_source_file()` 和 `_refresh_smoke_direct_tile_source_manifest()`，确保 completed 记录对应文件存在、shape/dtype 匹配，并集中刷新 resume 状态。
- 新增主功能测试覆盖 partial streaming tile source manifest resume：已完成的 streaming tile 不会被重写，pending tile 会补齐并让 manifest 进入 completed 状态。
- README、需求和审计文档同步记录当前边界：本轮是 smoke direct tile source 物化恢复能力，不是可恢复 OME-TIFF 文件续写或 production diffusion backend。
- 按用户最新要求，本轮不更新设计文档和开发附录中的章节级代码追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_tile_streaming_resumes_partial_tile_source_manifest -v`
  - 结果：RED 失败符合预期，旧实现覆盖了已完成 streaming tile
- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_tile_streaming_resumes_partial_tile_source_manifest -v`
  - 结果：通过，`Ran 1 test in 0.098s OK`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
  - 结果：通过，`Ran 24 tests in 1.315s OK`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner tests.test_version -v`
  - 结果：通过，`Ran 26 tests in 1.301s OK`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.15 - 2026-05-25

### 用户需求

- 用户要求继续根据设计文档和开发附录推进未完成任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 用户要求根据开发文档优先完成功能实现代码，每完成开发节点中的里程碑后再对主功能集中测试，不额外增加测试；节点代码追踪块等所有开发里程碑结束后再统一补充。
- 本批次选择 P4 / M6 输出可靠性的保守增量：让 smoke-cascade 显式 `--wsi-writer tile-streaming` 路径直接生成四层磁盘 tile source，避免为了 tiled iterator writer 先构造整张 blended canvas。

### 已做改动

- 版本号升级到 `v0.72.15`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `run_smoke_generation(..., wsi_writer="tile-streaming")` 改为调用直接 tile source 生成路径，不再为 tile-streaming writer 调用 `blend_rgb_tiles()` 构造整张 level-0 canvas。
- 新增 `_write_smoke_direct_multilevel_tile_source_manifest()`，按 pyramid level 和 TIFF tile grid 直接写出四层 `.npy` tile source 与 `tile_source_manifest.streaming.json`。
- `_prepare_smoke_tile_outputs()` 增加受控的 `keep_tile_images` 参数，默认 `array` writer 仍保留旧行为；tile-streaming 路径只保留 tile manifest/path 契约，不把已完成 tile 图像堆在内存中。
- README、需求和审计文档同步记录当前边界：本轮是 smoke tile-streaming writer 内存路径改进，不是 production diffusion backend、可恢复 OME-TIFF 续写或真实 gigapixel 生产推理。
- 按用户最新要求，本轮不更新设计文档和开发附录中的章节级代码追踪块。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_tile_streaming_does_not_blend_full_canvas -v`
  - 结果：RED 失败符合预期，旧实现触发 `tile-streaming must not build a full blended canvas`
- `python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_tile_streaming_does_not_blend_full_canvas -v`
  - 结果：通过，`Ran 1 test in 0.048s OK`
- `python -m unittest tests.test_generation_runner -v`
  - 结果：通过，`Ran 23 tests in 1.263s OK`
- `PYTHONPATH=src python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner tests.test_version -v`
  - 结果：通过，`Ran 25 tests in 1.246s OK`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过，`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.14 - 2026-05-25

### 用户需求

- 用户要求继续根据设计文档和开发附录推进未完成任务；本轮不启动 multiagent，由主会话直接推进一个可独立验收的功能闭环。
- 本批次选择 P4 / M6 输出可靠性的保守增量：为 generation run 新增集中 `generation_output_diagnostics.json`，汇总 WSI、mask、metadata、QC、batch index、tile manifest、tile source manifest、writer report 和 QC 状态，避免用户只能从多个分散 JSON 中手工判断一次生成是否完整。
- 用户要求代码与测试确认过关之后，再更新设计文档和开发文档中的章节级代码追踪块。

### 已做改动

- 版本号升级到 `v0.72.14`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `run_smoke_generation()` 与 `run_torch_diffusion_smoke_generation()` 写出 `generation_output_diagnostics.json`，并让 metadata output、`generation_run.json` 和函数返回值引用该 manifest。
- diagnostics manifest 记录 `manifest_type=generation_output_diagnostics`、artifact 路径、pyramid 摘要、writer 摘要、tile execution 摘要、tile source 摘要和 QC 摘要。
- smoke-cascade 路径汇总 `tile_manifest.json` 与 `tile_source_manifest.json` 的 completed/pending/failed 计数；tile-streaming 路径记录 transaction manifest path、`atomic_publish` 和 `resume_capable=false`；torch-diffusion-smoke 路径显式记录 `tile_execution.applicable=false`。
- `validate_generation_output_diagnostics()` 与 `he-wsi-gen validate generation-output-diagnostics` / `output-diagnostics` 支持校验 diagnostics manifest 的关键字段和状态边界。
- metadata schema 要求 `output.diagnostics_manifest_path`，UI output summary 同步保留该路径。
- README、`docs/audit/`、设计文档和开发附录同步记录当前能力边界：本轮是 output diagnostics manifest contract，不是 production backend 磁盘级逐 tile 生成或可恢复 OME-TIFF 续写。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_generation_runner.py`
- `tests/test_schemas.py`
- `tests/test_cli.py`
- `tests/test_torch_training.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `tests/test_ui_workflow.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `.agent/reports/p4-generation-output-diagnostics-contract-20260525.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
  - 结果：通过，`Ran 1 test in 0.066s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract tests.test_schemas.SchemaValidationTests.test_generation_output_diagnostics_rejects_invalid_status -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_cli.CliValidationTests.test_cli_validates_generation_output_diagnostics_file -v`
  - 结果：通过，`Ran 1 test in 0.049s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer -v`
  - 结果：通过，`Ran 1 test in 0.147s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_schemas tests.test_cli tests.test_generation_runner -v`
  - 结果：通过，`Ran 40 tests in 1.706s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_qc_review tests.test_ui_workflow tests.test_ui -v`
  - 结果：通过，`Ran 80 tests in 0.559s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`
  - 结果：通过，`Ran 26 tests in 19.133s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 287 tests in 22.283s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable wheel `multi_center_wsi_generator-0.72.14-0.editable-py3-none-any.whl` 构建并安装，卸载旧 `0.72.13` 后安装 `0.72.14`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.14`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 结果：包元数据 `0.72.14`，`PROJECT_VERSION=v0.72.14`，`PACKAGE_VERSION=0.72.14`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.13 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/`、设计文档和开发附录中的未完成项推进开发；本轮不启动 multiagent。
- 本批次选择 `AC-MISS-04` / P3 production 级生成模型缺口的保守增量：将现有 PyTorch diffusion smoke 训练产物接入统一 generation planning 的 inference artifact 契约，避免训练出的 checkpoint 只能被 sampler 私有消费而不能进入上层推理规划。
- 用户最新要求：整个项目开发完成之后，再统一补充或更新设计文档和开发文档中的代码追踪块；本轮不提前更新 `Relevant Code` / `Implementation Trace`。

### 已做改动

- 版本号补丁升级到 `v0.72.13`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/models/torch_training_contracts.py` 让 `diffusion_checkpoint_manifest()` 写入 `usable_for_inference=true` 和 `inference_contract`，并限定 `compatible_generation_backends=["torch-diffusion-smoke"]`。
- 新增 `_diffusion_smoke_inference_contract()`，记录 `production_ready=false`、非 production limitation、模型架构契约和七类条件输入契约：mask、style seed、texture token、coord、structure anchor、source condition、previous scale。
- `src/he_wsi_generator/generation/planner.py` 支持通过 `generation_backend` 参数校验 checkpoint/backend compatibility，并在 generation plan 中保留 checkpoint inference contract 摘要。
- `src/he_wsi_generator/generation/executor.py` 在 `torch-diffusion-smoke` run summary plan 中记录 checkpoint inference contract 摘要。
- `tests/test_torch_training.py` 增加 smoke checkpoint 可进入 `torch-diffusion-smoke` planning 且拒绝 `smoke-cascade` 的闭环测试，并扩展 manifest/run summary contract 断言。
- README、`docs/DEMANDS.MD` 和 `docs/audit/` 同步记录当前能力边界：本轮是 smoke checkpoint inference planning contract 接通，不是 production latent diffusion / ControlNet / DiT 训练或真实 production 推理 backend。
- 按用户最新要求，设计文档和开发附录的代码追踪块等整个项目开发完成后再统一补充，本轮不更新。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_torch_training.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `.agent/reports/p3-torch-diffusion-smoke-inference-planning-20260525.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample tests.test_torch_training.TorchSmokeTrainingTests.test_torch_diffusion_smoke_checkpoint_can_plan_torch_generation_backend_only tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
  - 结果：通过，`Ran 3 tests in 2.084s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`
  - 结果：通过，`Ran 26 tests in 11.825s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner tests.test_version -v`
  - 结果：通过，`Ran 59 tests in 1.485s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 284 tests in 14.265s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable wheel `multi_center_wsi_generator-0.72.13-0.editable-py3-none-any.whl` 构建并安装，卸载旧 `0.72.12` 后安装 `0.72.13`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.13`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 结果：包元数据 `0.72.13`，`PROJECT_VERSION=v0.72.13`，`PACKAGE_VERSION=0.72.13`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.12 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/`、设计文档和开发附录中的未完成项推进开发；本轮不启动 multiagent。
- 本批次选择 `AC-MISS-05` / P5 prior 的保守增量：为 prior manifest 增加 production readiness contract gate，避免统计型 layout/style/texture prior 被误标记为 production-ready trainable prior。
- 用户最新要求：整个项目开发完成之后，再统一补充或更新设计文档和开发文档中的代码追踪块；本轮不提前更新 trace 内容。

### 已做改动

- 版本号补丁升级到 `v0.72.12`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/priors/artifacts.py` 在 `build_prior_manifest_from_artifacts()` 输出中新增 `production_readiness` 摘要，明确当前统计型 layout/style/texture prior 均为非 production-ready proxy。
- `validate_prior_manifest()` 新增 production readiness contract gate：`production_ready=true` 时必须声明 layout/style/texture component contract，且不能使用 statistical/proxy backend 或仍含非 production limitation。
- `tests/test_priors.py` 增加 prior manifest production readiness 写入与 production-ready 缺 component contract 失败覆盖。
- README、`docs/audit/` 同步记录当前能力边界：本轮是 prior manifest contract gate，不是 production trainable style encoder、texture codebook、VQ-VAE 或 morphology token sampler。
- 按用户最新要求，设计文档和开发附录的代码追踪块等整个项目开发完成后再统一补充，本轮不更新。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_priors.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `.agent/reports/p5-prior-production-readiness-contract-20260525.md`

### 验证结果

- RED evidence：新增 `test_build_prior_manifest_from_artifacts_writes_valid_manifest` 的 production readiness 断言后，旧实现返回 `KeyError: 'production_readiness'`。
- RED evidence：新增 `test_prior_manifest_rejects_production_ready_without_component_contracts` 后，旧实现返回 `AssertionError: PriorArtifactError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_priors.PriorArtifactTests.test_build_prior_manifest_from_artifacts_writes_valid_manifest tests.test_priors.PriorArtifactTests.test_prior_manifest_rejects_production_ready_without_component_contracts -v`
  - 结果：通过，`Ran 2 tests in 0.001s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_priors -v`
  - 结果：通过，`Ran 10 tests in 0.235s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 283 tests in 22.987s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable wheel `multi_center_wsi_generator-0.72.12-0.editable-py3-none-any.whl` 构建并安装，卸载旧 `0.72.11` 后安装 `0.72.12`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.12`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 结果：包元数据 `0.72.12`，`PROJECT_VERSION=v0.72.12`，`PACKAGE_VERSION=0.72.12`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.11 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/`、设计文档和开发附录中的未完成项推进开发；本轮不启动 multiagent。
- 本批次选择 P4 / Phase 6 自动 QC 的保守增量：为 QC report 增加 mask 与生成图像组织区域一致性代理指标，帮助暴露“mask 区域和图像内容不匹配”的失败类型。
- 用户当时要求整个项目开发完成之后，再统一补充设计文档和开发文档中的代码追踪块；该要求在当前会话继续生效。

### 已做改动

- 版本号补丁升级到 `v0.72.11`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/qc/engine.py` 新增 `mask_image_tissue_alignment_proxy`：从生成 WSI 首层估计明亮背景/组织区域 proxy，并与 `.npy` mask 的 `mask > 0` 区域计算一致性分数。
- 当 mask 组织区域与图像组织区域明显错位时，`levels.mask_region.status` 与 `overall_status` 会进入 `fail`；不可判定场景保留可解释 message，不把 proxy 表述为专家级语义 QC。
- `tests/test_outputs_qc_archive.py` 增加 mask/image tissue alignment 的成功与失败路径覆盖，并扩展现有 QC metrics 断言。
- README、`docs/audit/` 同步记录能力边界：该轮是 P4 QC proxy 增量，不是 production 模型、真实 segmentation 或专家级语义判读。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/engine.py`
- `tests/test_outputs_qc_archive.py`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `.agent/reports/p4-mask-image-tissue-alignment-qc-20260525.md`

### 验证结果

- RED evidence：新增 `test_build_qc_report_flags_mask_image_tissue_alignment_mismatch` 后，旧实现因缺少 `mask_image_tissue_alignment_proxy` 返回 `KeyError: 'mask_image_tissue_alignment_proxy'`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_flags_mask_image_tissue_alignment_mismatch -v`
  - 结果：通过，`Ran 1 test in 0.007s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
  - 结果：通过，`Ran 32 tests in 0.096s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 282 tests in 20.835s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable wheel `multi_center_wsi_generator-0.72.11-0.editable-py3-none-any.whl` 构建并安装，卸载旧 `0.72.10` 后安装 `0.72.11`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.11`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 结果：包元数据 `0.72.11`，`PROJECT_VERSION=v0.72.11`，`PACKAGE_VERSION=0.72.11`
- `git diff --check`
  - 结果：通过，无输出
- 本轮未重新执行真实 SVS 全链路；真实 SVS smoke/proxy 复跑证据仍来自历史 v0.72.1 验证目录。

## v0.72.10 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/`、设计文档和开发附录中的未完成项推进开发；本轮仍不启动 multiagent。
- 本批次继续选择 `AC-MISS-04` / P3 的保守契约增量：为 `usable_for_inference=true` checkpoint 增加 inference architecture/condition contract gate，避免 generation planning 只凭 backend 名称判断 checkpoint 兼容性。

### 已做改动

- 版本号补丁升级到 `v0.72.10`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/models/training.py` 加固 `inference_contract`：`usable_for_inference=true` checkpoint 现在必须声明 `model_architecture_contract` 和 `condition_input_contract`。
- `src/he_wsi_generator/generation/planner.py` 将 checkpoint architecture/condition contract 摘要写入 generation plan，并让每层 `condition_inputs` 显式包含 `source_condition` 和 `previous_scale`。
- `tests/test_models_generation.py` 新增缺失模型架构契约、缺失必需条件输入的失败覆盖，并扩展成功路径断言；`tests/test_generation_runner.py` 同步 smoke fixture 的 inference contract 字段。
- README、`docs/audit/` 同步记录当前能力边界：本轮只是 inference architecture/condition contract gate，不是 production 模型推理 backend。按用户最新要求，设计文档和开发附录的代码追踪块等整个项目开发完成后再统一补充，本轮不更新。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/generation/planner.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p3-inference-architecture-condition-contract-20260525.md`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- RED evidence：新增 `test_generation_plan_rejects_checkpoint_without_model_architecture_contract` 后，旧实现返回 `AssertionError: ModelRunError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_without_model_architecture_contract tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_missing_required_condition_input tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_accepts_trained_checkpoint_manifest -v`
  - 结果：通过，`Ran 3 tests in 0.002s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner -v`
  - 结果：通过，`Ran 57 tests in 1.446s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 281 tests in 20.749s OK`
- `git diff --check`
  - 结果：通过，无输出
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable wheel `multi_center_wsi_generator-0.72.10-0.editable-py3-none-any.whl` 构建并安装，卸载旧 `0.72.9` 后安装 `0.72.10`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.10`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 结果：包元数据 `0.72.10`，`PROJECT_VERSION=v0.72.10`，`PACKAGE_VERSION=0.72.10`

## v0.72.9 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`；本轮仍不启动 multiagent。
- 本批次继续选择 `AC-MISS-04` / P3 的保守契约增量：为 `usable_for_inference=true` checkpoint 增加 generation backend compatibility contract gate，避免 checkpoint 只凭泛化 inference contract 被错误 backend 消费。

### 已做改动

- 版本号补丁升级到 `v0.72.9`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/models/training.py` 加固 `inference_contract`：`usable_for_inference=true` checkpoint 现在必须声明非空 `compatible_generation_backends` 字符串列表。
- `src/he_wsi_generator/generation/planner.py` 新增 generation backend compatibility gate：`create_generation_plan()` 默认按 `smoke-cascade` 校验 checkpoint 是否允许当前 backend 消费，并把 `generation_backend` 与 `checkpoint_inference_contract` 摘要写入 generation plan。
- `tests/test_models_generation.py` 新增缺失 `compatible_generation_backends` 的失败覆盖，并更新可推理 checkpoint fixture；`tests/test_generation_runner.py` 同步为 smoke checkpoint fixture 声明 `compatible_generation_backends=["smoke-cascade"]`。
- README、`docs/audit/`、设计文档和开发附录同步记录当前能力边界：本轮只是 checkpoint/backend compatibility contract gate，不是 production 模型推理 backend。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/generation/planner.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p3-backend-compatibility-contract-20260525.md`
- 版本断言更新涉及 `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- RED evidence：新增 `test_generation_plan_rejects_checkpoint_without_compatible_generation_backend` 后，旧实现返回 `AssertionError: ModelRunError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner -v`
  - 结果：通过，`Ran 55 tests in 1.516s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 279 tests in 17.022s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error 输出
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.9`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.9`
- 包元数据检查：
  - `metadata.version('multi-center-wsi-generator') = 0.72.9`
  - `PROJECT_VERSION = v0.72.9`
  - `PACKAGE_VERSION = 0.72.9`

## v0.72.8 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`；本轮仍不启动 multiagent。
- 本批次继续选择 `AC-MISS-04` / P3 的保守契约增量：为 `init-training-run` 增加训练目标 / loss / QC 映射契约 gate，覆盖设计文档 `7.5 训练约束` 和 `7.6 训练约束与自动 QC 的对应关系`。

### 已做改动

- 版本号补丁升级到 `v0.72.8`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/models/training.py` 新增 `training_objective_contract` 校验，要求声明五类训练约束：`diffusion_generation`、`semantic_mask_consistency`、`cross_scale_consistency`、`tile_seam_consistency` 和 `slide_style_consistency`。
- `training_objective_contract` 现在必须声明非负 `loss_weights`、`image_generator` / `wsi_consistency` 阶段目标映射，以及五类训练约束到 QC 指标的映射；缺失或不一致会显式抛出 `ModelRunError`。
- `create_training_run()` 现在把通过校验的 `training_objective_contract` 写入 `training_run.json`，并在 skeleton checkpoint manifest 中写入 `training_objective_contract_summary`；checkpoint 仍保持 `status=not_trained` 与 `usable_for_inference=false`。
- `tests/test_models_generation.py` 新增训练目标契约覆盖：缺失 contract、缺失 loss weight、缺失阶段映射和 QC 映射不完整；成功路径断言 run/checkpoint 写入训练目标契约摘要。
- README、`docs/audit/`、设计文档和开发附录同步记录当前能力边界：本轮只是 training objective/loss/QC mapping contract gate，不是 production 模型训练 loop、真实 production checkpoint 或 production inference backend。

### 影响文件

- `README.md`
- `.agent/reports/p3-training-objective-contract-20260525.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_layout_mask_sampler.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_qc_review.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `tests/test_wsi_tissue_overview.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- RED evidence：新增 `test_create_training_run_rejects_missing_training_objective_contract` 后，旧实现返回 `AssertionError: ModelRunError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_rejects_missing_training_objective_contract -v`
  - 结果：通过，`Ran 1 test in 0.001s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 结果：通过，`Ran 30 tests in 0.100s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 277 tests in 21.053s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error 输出
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.8`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.8`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata.version(...) ... PY`
  - 结果：包元数据 `0.72.8`，`PROJECT_VERSION` 为 `v0.72.8`，`PACKAGE_VERSION` 为 `0.72.8`

## v0.72.7 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-MISS-04` / P3 的保守契约增量：在 v0.72.6 的 production training dataset contract gate 基础上，要求 `init-training-run` 读取并核对实际 `training_index_path` JSONL，避免只靠手写 `dataset_contract` 汇总字段绕过训练数据覆盖检查。
- 用户补充测试节奏：按“功能闭环完成后集中验证”，避免为每个内部 helper 追加大量细碎测试；最终回复需说明本次闭环、已执行测试和未执行测试原因。

### 已做改动

- 版本号补丁升级到 `v0.72.7`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- `src/he_wsi_generator/models/training.py` 为 `dataset_contract` 增加实际 training index JSONL 证据核对：文件必须存在、非空、逐行 JSON object，record `schema_version` 必须匹配当前版本。
- `create_training_run()` 现在会核对 `dataset_contract.sample_count`、`records_by_split`、`records_by_level` 是否与实际 training index record 数、split 计数和 cascade level 计数完全一致。
- training index record 现在必须提供 tile 坐标、6 类 mask class mapping 和 conditioning 字段证据；缺少 `structure_anchor_policy`、`style_seed_source`、`texture_token_source` 或 mask mapping 不覆盖 6 类时显式抛出 `ModelRunError`。
- `src/he_wsi_generator/models/training_index.py` 生成的 training index record 现在写入 `conditioning.texture_token_source`，保证项目自身 `build-training-index` 输出能通过 v0.72.7 的 evidence gate。
- `tests/test_models_generation.py` 新增 actual training index mismatch 覆盖：sample_count mismatch、split mismatch、condition evidence 缺失和 mask mapping mismatch；成功路径改为写入最小真实 training index fixture。
- `tests/test_training_index.py` 新增断言，验证 `build_training_index()` 输出包含 `texture_token_source`。
- README、`docs/audit/`、设计文档和开发附录同步记录当前能力边界：本轮只是 training index evidence contract gate，不是 production 模型训练 loop、真实 production checkpoint 或 production inference backend。
- `AGENTS.md`、`docs/DEMANDS.MD` 和 README 同步记录“功能闭环完成后集中验证”的测试节奏。
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md` 更新 `7.4 三阶段训练协议`、`7.4.1 训练样本构造` 和 `Phase 4：三阶段生成模型训练` 的 `Relevant Code`。
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md` 更新 `7.2 训练阶段` 的 `Implementation Trace`。

### 影响文件

- `.agent/reports/p3-production-training-contract-20260525.md`
- `README.md`
- `AGENTS.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/models/training_index.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_layout_mask_sampler.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_qc_review.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `tests/test_wsi_tissue_overview.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- RED evidence：新增 `test_create_training_run_rejects_dataset_contract_sample_count_mismatch_with_index` 后，旧实现返回 `AssertionError: ModelRunError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 结果：通过，`Ran 26 tests in 0.210s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index -v`
  - 结果：通过，`Ran 3 tests in 0.042s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 273 tests in 20.181s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.7`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.7`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/version check ... PY`
  - 结果：包元数据 `0.72.7`，`PROJECT_VERSION` 为 `v0.72.7`，`PACKAGE_VERSION` 为 `0.72.7`

## v0.72.6 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 `AC-MISS-04` / P3 的保守契约增量：不直接实现 production latent diffusion / ControlNet / DiT 训练本体，而是先让 `init-training-run` 的训练配置具备可审计的 production training dataset contract，避免没有真实数据规模、split、cascade 覆盖、条件输入和目标 backend 约束的配置进入 run manifest。

### 已做改动

- 版本号补丁升级到 `v0.72.6`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建 P3 worker 任务 `.agent/tasks/p3-production-training-contract-20260525.md`；worker 在 `.worktrees/p3-production-training-contract-20260525` 长时间停滞且没有实现 diff，主 orchestrator 接管实现与复审计，并写入 `.agent/reports/p3-production-training-contract-20260525.md`。
- `src/he_wsi_generator/models/training.py` 为 `create_training_run()` 增加 `training_backend=latent_diffusion_unet` 和 `dataset_contract` 校验。
- `dataset_contract` 现在必须声明并校验 training index path、production readiness、最小样本数、样本数、train split、四层 cascade 记录数、必需条件输入和 6 类 `integer_index` mask schema；非法、缺失或不一致字段会显式抛出 `ModelRunError`。
- `training_run.json` 写入通过校验的 `training_backend` 与 `dataset_contract`；skeleton checkpoint manifest 写入 `training_backend`、`target_type` 和 `dataset_contract_summary`，但继续保持 `status=not_trained` 与 `usable_for_inference=false`。
- `tests/test_models_generation.py` 新增缺失 dataset contract、缺 cascade level、样本数不足、mask schema mismatch、unsupported backend、training index mismatch、readiness 缺失、缺必需条件输入和缺 train split 的失败覆盖。
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md` 为 `7.4 三阶段训练协议`、`7.4.1 训练样本构造` 和 `Phase 4：三阶段生成模型训练` 补充 `Relevant Code`，标明当前为部分实现。
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md` 为 `7.2 训练阶段` 补充 `Implementation Trace`，记录 training dataset contract gate 的完整项目内依赖、调用链和验证命令。
- README 与 `docs/audit/` 同步记录当前能力边界：本轮只是 production training dataset contract gate，不是 production 模型训练 loop、真实 production checkpoint 或 production inference backend。

### 影响文件

- `.agent/tasks/p3-production-training-contract-20260525.md`
- `.agent/reports/p3-production-training-contract-20260525.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_layout_mask_sampler.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_qc_review.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `tests/test_wsi_tissue_overview.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- RED evidence：新增 `test_create_training_run_rejects_missing_dataset_contract` 后，旧实现返回 `AssertionError: ModelRunError not raised`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 结果：通过，`Ran 21 tests in 0.092s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
  - 结果：通过，`Ran 23 tests in 1.608s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 268 tests in 16.985s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.6`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.6`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/version check ... PY`
  - 结果：包元数据 `0.72.6`，`PROJECT_VERSION` 为 `v0.72.6`，`PACKAGE_VERSION` 为 `0.72.6`

## v0.72.5 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-MISS-06` / P4 的保守可靠性增量：不把当前 writer 宣称为可恢复 OME-TIFF production writer，而是先为 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 增加可审计的写入事务与原子发布证据，避免失败或中断时半成品被误认为完整输出。

### 已做改动

- 版本号补丁升级到 `v0.72.5`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并审查 P4 worker 任务：
  - `.agent/tasks/p4-streaming-publish-transaction-20260525.md`
  - `.agent/reports/p4-streaming-publish-transaction-20260525.md`
- `src/he_wsi_generator/outputs/ome_tiff.py` 为 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 增加同目录临时 OME-TIFF 写入、发布前 OME/pyramid shape 校验、`Path.replace()` 原子发布和 `<target>.transaction.json` 事务 manifest。
- transaction manifest 记录 `schema_version`、writer 类型、目标路径、临时路径、tile source manifest 摘要、started/completed/failed 状态、时间戳、失败原因、`atomic_publish=true` 和 `resume_capable=false`。
- 失败路径会清理临时 OME-TIFF、写入 failed transaction manifest，并保持既有目标文件不被半成品覆盖；成功 report、`streaming_contract` 和 `streaming_write_report` 均记录 `transaction_manifest_path` 与 `atomic_publish=true`。
- `tests/test_outputs_qc_archive.py` 新增 transaction manifest、atomic publish、失败目标保留和 pyramid order 失败事务记录测试。
- README 与 `docs/audit/` 同步记录当前能力边界：本轮只是 tile iterator streaming writer 的原子发布事务补丁，不是 production backend 磁盘级逐 tile 生成，也不是可恢复 OME-TIFF 逐 tile 写入。

### 影响文件

- `.agent/tasks/p4-streaming-publish-transaction-20260525.md`
- `.agent/reports/p4-streaming-publish-transaction-20260525.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `git diff --check`
  - 结果：通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
  - 结果：通过，`Ran 31 tests in 0.242s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
  - 结果：通过，`Ran 23 tests in 1.381s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 259 tests in 18.804s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.5`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.5`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/version check ... PY`
  - 结果：包元数据 `0.72.5`，`PROJECT_VERSION` 为 `v0.72.5`，`PACKAGE_VERSION` 为 `0.72.5`

## v0.72.4 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 `AC-MISS-04` / P3 的保守契约增量：不直接实现 production latent diffusion / ControlNet / DiT 模型本体，而是先收紧 checkpoint manifest 的 inference 可用性判定，避免任意手写薄 JSON 只要设置 `usable_for_inference=true` 就能通过 generation plan。

### 已做改动

- 版本号补丁升级到 `v0.72.4`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并审查 P3 worker 任务：
  - `.agent/tasks/p3-checkpoint-inference-contract-20260525.md`
  - `.agent/reports/p3-checkpoint-inference-contract-20260525.md`
- `src/he_wsi_generator/models/training.py` 加固 `usable_for_inference=true` checkpoint manifest 契约：要求 `status=trained`、非空 `training_backend` / `target_type` / `checkpoint_path` / `checkpoint_sha256`、checkpoint 文件存在且 SHA-256 匹配，并显式声明 `inference_contract.backend_type`、`artifact_role`、`production_ready` 和 `limitations`。
- `usable_for_inference=false` 的 skeleton / smoke checkpoint manifest 继续可加载，但 generation plan 仍拒绝其用于推理。
- `tests/test_models_generation.py` 新增薄 inference manifest、缺失 checkpoint 文件、hash mismatch、缺失 `inference_contract`、矛盾 status/usable 状态和相对 checkpoint artifact path 的显式测试，并更新可推理 checkpoint fixture 为真实小文件 + matching SHA-256 + 非 production inference contract。
- `tests/test_generation_runner.py` 更新 smoke generation checkpoint fixture，使既有 smoke generation 路径满足新的 checkpoint inference artifact contract。
- README 与 `docs/audit/` 同步记录当前能力边界：本轮只是 checkpoint inference contract gate，不是 production 生成模型或真实 production inference backend。

### 影响文件

- `.agent/tasks/p3-checkpoint-inference-contract-20260525.md`
- `.agent/reports/p3-checkpoint-inference-contract-20260525.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 结果：通过，`Ran 12 tests in 0.143s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
  - 结果：通过，`Ran 23 tests in 1.578s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 257 tests in 16.210s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.4`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.4`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/version check ... PY`
  - 结果：包元数据 `0.72.4`，`PROJECT_VERSION` 为 `v0.72.4`，`PACKAGE_VERSION` 为 `0.72.4`

## v0.72.3 - 2026-05-25

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-DEV-04` / P4 的保守增量：在不改变 `blend_rgb_tiles()` 输出语义、tile traversal contract、smoke generation / resumable manifest 行为的前提下，降低 `src/he_wsi_generator/generation/tiling.py` 中 tile blending 的中间内存占用。

### 已做改动

- 版本号补丁升级到 `v0.72.3`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 更新 `docs/DEMANDS.MD` 顶部，新增 v0.72.3 P4 tile blending 内存收敛需求。
- `src/he_wsi_generator/generation/tiling.py` 的 `blend_rgb_tiles()` 改为按 channel-by-channel 累积中间结果，减少 RGB tile blending 的 float64 临时数组峰值，保持 blending 语义不变。
- `tests/test_generation_tiling.py` 新增回归测试，验证 `blend_rgb_tiles()` 不再对整块 RGB tile 先做 float64 cast。
- `tests/test_generation_runner.py` 的既有 tile-streaming 顺序物化回归测试继续通过，确认本轮内存优化未改变 smoke tile-streaming 路径。
- 更新 README 与 `docs/audit/`，将当前状态继续维持为 smoke/proxy 和 P4 contract 边界，不把该优化描述成 production writer。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/tiling.py`
- `tests/test_generation_tiling.py`
- `tests/test_generation_runner.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling -v`
  - 结果：通过，`Ran 12 tests in 0.001s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_streaming_materializes_pyramid_levels_sequentially -v`
  - 结果：通过，`Ran 1 test in 0.063s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.3`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.3`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 结果：通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 251 tests in 17.664s OK`

## v0.72.2 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-DEV-04` / P4 的保守增量：让 `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 在生成四层 tile source manifest 时按 pyramid level 顺序逐层物化，不再一次性持有四层 `pyramid_levels` 数组，继续保持现有输出 artifact、writer contract 和 CLI 行为不变。

### 已做改动

- 版本号补丁升级到 `v0.72.2`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 更新 `docs/DEMANDS.MD` 顶部，新增 v0.72.2 P4 smoke tile-streaming 顺序物化需求。
- `src/he_wsi_generator/generation/executor.py` 的 smoke `tile-streaming` 路径改为按 high-to-low pyramid 顺序逐层物化 smoke canvas 生成的四层 level，再写出 `tile_source_manifest.streaming.json` 和四层 OME-TIFF。
- `tests/test_generation_runner.py` 新增回归测试，验证 tile-streaming 路径传入的是可迭代的 levels 生成器，而非 `list/tuple` 容器，并按 `[512, 512, 3] -> [128, 128, 3] -> [32, 32, 3] -> [16, 16, 3]` 顺序消费。
- 更新 README 与 `docs/audit/`，将 P4 状态调整为“smoke 四层 tile source streaming 已完成 / tile-streaming 路径已顺序物化 / 仍缺失 production backend streaming 和可恢复 OME-TIFF 写入”，继续保留非 production 边界。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_version -v`
  - 结果：通过，`Ran 24 tests in ... OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，后续将再次复跑以覆盖本轮全部文档同步后的最终状态

## v0.72.1 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本轮选择 `AC-VER-03`：在当前 `MultiCenterWSIGenerator` conda 环境和当前代码基线上，使用真实 SVS `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新执行 smoke/proxy 全链路验证，避免只引用历史 `build/validation/v0.62.0-291288/` 工件。

### 已做改动

- 版本号补丁升级到 `v0.72.1`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 更新 `docs/DEMANDS.MD` 顶部，新增 v0.72.1 真实 SVS 当前环境复跑验证需求。
- 在 `build/validation/v0.72.1-291288/` 下重新生成真实 SVS smoke/proxy 验证工件：
  - `input_manifest.json`
  - `wsi_tissue_overview.json`
  - `qc_reference_distribution.json`
  - `prior/prior_manifest.json`
  - `sampled-layout/sampled_layout_mask.json`
  - `sampled-policy/sampled_style_policy.json`
  - `sampled-policy/sampled_texture_policy.json`
  - `condition_packet.json`
  - `generated/gen-291288-smoke-sampled-policy-v0721/metadata.json`
  - `generated/gen-291288-smoke-sampled-policy-v0721/qc.json`
  - `generated/gen-291288-smoke-sampled-policy-v0721/qc_review.json`
  - `generated/gen-291288-smoke-sampled-policy-v0721/generation_run.json`
  - `generated/gen-291288-smoke-sampled-policy-v0721/batch.jsonl`
  - `generated/gen-291288-smoke-sampled-policy-v0721/generated.ome.tiff`
  - `generated/gen-291288-smoke-sampled-policy-v0721/generated_mask/mask.npy`
- 当前验证结果：
  - `he-wsi-gen --version` 返回 `v0.72.1`
  - 默认 generation config 校验通过
  - `inspect-output-summary` 返回 `qc_status=pass`
  - `qc_review.json` 为 `artifact_type=qc_review`、`review_required=false`、`decision=accepted`
  - `generated.ome.tiff` 为 4 层 pyramid，`generated_mask/mask.npy` 覆盖 6 类 mask id
- 当前不改变 production 模型、production prior、production writer 或默认生成行为。

### 影响文件

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `build/validation/v0.72.1-291288/`（ignored 验证工件）

### 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
  - 结果：通过，editable 安装升级到 `multi-center-wsi-generator 0.72.1`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.72.1`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate manifest build/validation/v0.72.1-291288/input_manifest.json`
  - 结果：通过
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen build-wsi-tissue-overview ...`
  - 结果：`WSI tissue overview written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen build-qc-reference ...`
  - 结果：`qc reference distribution written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen build-prior-manifest ...`
  - 结果：`prior manifest written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen sample-layout-mask ...`
  - 结果：`sampled layout mask written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen sample-style-policy ...`
  - 结果：`sampled style policy written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen sample-texture-policy ...`
  - 结果：`sampled texture policy written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen build-condition-packet ...`
  - 结果：`condition packet written`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen run-generation ... --backend smoke-cascade ...`
  - 结果：`generation run completed`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate metadata ...`
  - 结果：通过
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate qc ...`
  - 结果：通过
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen create-qc-review ...`
  - 结果：通过，0 review items
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen apply-qc-review-decision ...`
  - 结果：`accepted`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate qc-review ...`
  - 结果：通过
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen inspect-output-summary ...`
  - 结果：`qc_status=pass`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version tests.test_generation_conditioning tests.test_generation_runner tests.test_style_prior tests.test_texture_prior tests.test_layout_mask_sampler tests.test_priors -v`
  - 结果：通过，`Ran 60 tests in 1.999s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 249 tests in 13.496s OK`
- `git diff --check`
  - 结果：通过，无 whitespace error

## v0.72.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-MISS-05` 的保守可交付子集：在 v0.71.0 已能把 sampled style/texture policy 写入 condition packet 的基础上，让 smoke generation 和 torch diffusion smoke 输出继续保留 selected style/token 的可审计摘要，同时保持非 production 边界。

### 已做改动

- 版本号升级到 `v0.72.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并合并 P5 worker 任务：
  - `.agent/tasks/p5-generation-sampled-policy-summary-20260524.md`
  - `.agent/reports/p5-generation-sampled-policy-summary-20260524.md`
- `src/he_wsi_generator/generation/executor.py` 的 condition packet summary 现在会在 `style_seed.source=sampled_style_policy` / `texture_token.source=sampled_texture_policy` 时保留 sampled policy 摘要。
- `src/he_wsi_generator/models/torch_training.py` 同步保留 sampled policy 摘要，使 torch condition packet loader、sample manifest、generation metadata 和 run summary 字段一致。
- 新增测试覆盖 smoke generation metadata/run summary、torch sample manifest、torch smoke generation metadata/run summary 的 sampled policy 摘要贯通，以及缺少 `selected_style` / `representative_embedding_index` 时的显式失败。
- 当前不改变 condition feature vector 编码，不自动调用 policy sampler，不改变 smoke/torch generation backend 生成行为。

### 影响文件

- `.agent/tasks/p5-generation-sampled-policy-summary-20260524.md`
- `.agent/reports/p5-generation-sampled-policy-summary-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.72.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_torch_training -v`
    - 结果：红灯符合预期，写生产代码前失败原因为 `KeyError: 'sampled_style_policy'`，且缺失 sampled style `selected_style` 未触发 `GenerationExecutionError`；实现后通过，`Ran 47 tests in 11.914s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error
- Orchestrator 文档/版本同步后最终验证：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，卸载 `multi-center-wsi-generator 0.71.0` 并安装 editable `multi-center-wsi-generator 0.72.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.72.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata / PROJECT_VERSION / PACKAGE_VERSION ... PY`
    - 结果：`0.72.0`、`v0.72.0`、`0.72.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_torch_training tests.test_generation_conditioning tests.test_style_prior tests.test_texture_prior tests.test_priors -v`
    - 结果：通过，`Ran 78 tests in 11.879s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 249 tests in 15.117s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.71.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 `AC-MISS-05` 的保守可交付子集：在 v0.70.0 已能生成 `sampled_style_policy` / `sampled_texture_policy` 的基础上，让 `build-condition-packet` 可选读取这些 policy artifact，并写入 condition packet 的可审计条件摘要，同时保持非 production 边界。

### 已做改动

- 版本号升级到 `v0.71.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并合并 P5 worker 任务：
  - `.agent/tasks/p5-condition-sampled-policy-20260524.md`
  - `.agent/reports/p5-condition-sampled-policy-20260524.md`
- `build_generation_condition_packet()` 新增可选 `sampled_style_policy_path` 和 `sampled_texture_policy_path`，读取并校验 sampled policy JSON。
- `he-wsi-gen build-condition-packet` 新增 `--sampled-style-policy` 和 `--sampled-texture-policy` 参数。
- condition packet 现在会在 `artifact_inputs.sampled_style_policy` / `artifact_inputs.sampled_texture_policy` 记录 policy artifact，并在 `conditions.style_seed` / `conditions.texture_token` 中记录 sample id、seed、selection policy、selected style/token 摘要和 limitations。
- sampled policy 校验覆盖 schema version、artifact type、source prior path、RGB triplet、selected texture token、representative embedding index 等关键字段；source prior path 必须匹配当前 prior manifest 对应 artifact path。
- 更新 README、`docs/DEMANDS.MD` 与 `docs/audit/`，将 `AC-MISS-05` 进一步调整为“sampled policy artifact 与 condition packet 审计链部分完成 / 仍缺失 production prior”，并明确当前不是 trainable style encoder、texture codebook、VQ-VAE 或 runtime generation model。

### 影响文件

- `.agent/tasks/p5-condition-sampled-policy-20260524.md`
- `.agent/reports/p5-condition-sampled-policy-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `tests/test_generation_conditioning.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.71.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning -v`
    - 结果：红灯符合预期，写生产代码前失败原因包括 `build_generation_condition_packet() got an unexpected keyword argument 'sampled_style_policy_path'`，CLI 子进程未写出 condition packet；实现后通过，`Ran 10 tests in 0.082s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning tests.test_style_prior tests.test_texture_prior tests.test_priors -v`
    - 结果：通过，`Ran 31 tests in 0.649s OK`
- Orchestrator 文档/版本同步后最终验证：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，卸载 `multi-center-wsi-generator 0.70.0` 并安装 editable `multi-center-wsi-generator 0.71.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.71.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata / PROJECT_VERSION / PACKAGE_VERSION ... PY`
    - 结果：`0.71.0`、`v0.71.0`、`0.71.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning tests.test_style_prior tests.test_texture_prior tests.test_priors -v`
    - 结果：通过，`Ran 31 tests in 0.594s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 245 tests in 13.985s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.70.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 `AC-MISS-05` 的保守可交付子集：在已有统计型 style/texture prior 基础上，补齐可复现、可审计的 sampled style policy 和 sampled texture policy artifact，同时保持非 production 边界。

### 已做改动

- 版本号升级到 `v0.70.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建两个 P5 worker 任务：
  - `.agent/tasks/p5-style-sampling-policy-20260524.md`
  - `.agent/tasks/p5-texture-sampling-policy-20260524.md`
- 回收两个 P5 worker 报告：
  - `.agent/reports/p5-style-sampling-policy-20260524.md`
  - `.agent/reports/p5-texture-sampling-policy-20260524.md`
- `sample_style_policy_from_prior()` 从 `style_prior` 中按 deterministic seed policy 选择 tile-level style record，写出 `sampled_style_policy` JSON，并记录 RGB 统计引用和非 production limitations。
- `sample_texture_policy_from_prior()` 从 `texture_prior` 中按 deterministic seed policy 选择 texture prototype，写出 `sampled_texture_policy` JSON，并记录 representative embedding index、cluster 摘要和非 production limitations。
- CLI 新增 `sample-style-policy` 与 `sample-texture-policy`，用于从已有统计型 prior 生成可审计 policy artifact。
- 更新 README、`docs/DEMANDS.MD` 与 `docs/audit/`，将 `AC-MISS-05` 调整为“部分完成 / 仍缺失 production prior”，并明确当前不是 trainable style encoder、texture codebook、VQ-VAE 或 production texture/style model。

### 影响文件

- `.agent/tasks/p5-style-sampling-policy-20260524.md`
- `.agent/tasks/p5-texture-sampling-policy-20260524.md`
- `.agent/reports/p5-style-sampling-policy-20260524.md`
- `.agent/reports/p5-texture-sampling-policy-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/priors/texture.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.70.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior -v`
    - 结果：红灯符合预期，写生产代码前失败原因为 `sample_style_policy_from_prior helper is missing`；实现后通过，`Ran 5 tests in 0.236s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_texture_prior -v`
    - 结果：红灯符合预期，写生产代码前失败原因为 `sample_texture_policy_from_prior helper is missing`；实现后通过，`Ran 5 tests in 0.074s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior tests.test_texture_prior tests.test_priors tests.test_generation_conditioning -v`
    - 结果：通过，`Ran 26 tests in 0.594s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior tests.test_texture_prior -v`
    - 结果：通过，`Ran 12 tests in 0.423s OK`
- Orchestrator 文档/版本同步后最终验证：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，卸载 `multi-center-wsi-generator 0.69.0` 并安装 editable `multi-center-wsi-generator 0.70.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.70.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata / PROJECT_VERSION / PACKAGE_VERSION ... PY`
    - 结果：`0.70.0`、`v0.70.0`、`0.70.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior tests.test_texture_prior tests.test_priors tests.test_generation_conditioning -v`
    - 结果：通过，`Ran 28 tests in 0.554s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 242 tests in 15.756s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.69.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 P4 输出可靠性，在 v0.68.0 受限 tiled iterator writer 与 smoke-cascade 显式 writer 选择基础上，补齐 smoke `tile-streaming` 当前只写 level0 的缺口，并加固 streaming writer 对 pyramid level 顺序和报告契约的校验。

### 已做改动

- 版本号升级到 `v0.69.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建两个 P4 worker 任务：
  - `.agent/tasks/p4-smoke-multilevel-tile-source-20260524.md`
  - `.agent/tasks/p4-streaming-writer-pyramid-contract-20260524.md`
- 回收两个 worker 报告：
  - `.agent/reports/p4-smoke-multilevel-tile-source-20260524.md`
  - `.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`
- `write_pyramid_ome_tiff_streaming_from_tile_sources()` 加固 streaming manifest pyramid level 契约：levels 必须按 high-to-low resolution 声明，缺失 level shape、重复 level index 或后续 level height/width 大于前一层会显式失败。
- streaming writer report/contract 新增 `pyramid_order`、`level_order` 和每层 `pyramid_position`，并继续保留 `resume_capable=false` 与 `ome_tiff_file_resume_not_supported`。
- `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 现在会为四层 smoke pyramid 物化 `tile_source_manifest.streaming.json` 和 `streaming_tiles/*.npy`，再通过 tiled iterator writer 写出四层 OME-TIFF。
- 默认 `--wsi-writer array` 行为不变，仍使用原 level0 `tile_source_manifest.json` 作为 array writer contract gate；`torch-diffusion-smoke` 仍显式拒绝 `--wsi-writer tile-streaming`。
- 更新 README 与 `docs/audit/`，将 P4 状态调整为“smoke 四层 tile source streaming 已完成 / 仍缺失 production backend streaming 和可恢复 OME-TIFF 文件写入”，继续保留非 production 边界。

### 影响文件

- `.agent/tasks/p4-smoke-multilevel-tile-source-20260524.md`
- `.agent/tasks/p4-streaming-writer-pyramid-contract-20260524.md`
- `.agent/reports/p4-smoke-multilevel-tile-source-20260524.md`
- `.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.69.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 29 tests in 0.088s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
    - 结果：通过，`Ran 20 tests in 1.420s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 31 tests in 1.521s OK`
- Orchestrator 合并后复核：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 60 tests in 1.386s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error
- Orchestrator 文档/版本同步后最终验证：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，卸载 `multi-center-wsi-generator 0.68.0` 并安装 editable `multi-center-wsi-generator 0.69.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.69.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata / PROJECT_VERSION / PACKAGE_VERSION ... PY`
    - 结果：`0.69.0`、`v0.69.0`、`0.69.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 60 tests in 1.554s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 236 tests in 15.862s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.68.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 P4 输出可靠性，在 v0.67.0 磁盘 tile source contract/assembly 基础上，推进不先组装完整 level array 的 tiled iterator streaming 写出，以及 smoke-cascade 显式接入。

### 已做改动

- 版本号升级到 `v0.68.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建两个 P4 worker 任务：
  - `.agent/tasks/p4-tile-iterator-writer-20260524.md`
  - `.agent/tasks/p4-smoke-streaming-writer-integration-20260524.md`
- 回收两个 worker 报告：
  - `.agent/reports/p4-tile-iterator-writer-20260524.md`
  - `.agent/reports/p4-smoke-streaming-writer-integration-20260524.md`
- `src/he_wsi_generator/outputs/ome_tiff.py` 新增 `write_pyramid_ome_tiff_streaming_from_tile_sources()`，复用磁盘 `.npy` tile source contract 后，按 `tifffile` tiled writer 的 tile grid 从磁盘逐 tile iterator 写出 OME-TIFF。
- 新 writer 不分配完整 level array；它要求 `chunk_shape` 满足 tiled TIFF 约束，每个 tile source record 精确映射到一个 TIFF tile grid cell，并拒绝 gap、overlap、越界、shape/dtype/status 不一致。
- 新 writer 报告 `write_mode=tile_iterator_streaming_write`、`production_streaming=true`、`resume_capable=false`，明确它仍不支持中断后续写同一个 OME-TIFF 文件。
- `run-generation --backend smoke-cascade` 新增 `--wsi-writer {array,tile-streaming}`；默认 `array` 保持既有 in-memory pyramid 写出路径，`tile-streaming` 使用磁盘 tile source iterator writer。
- `torch-diffusion-smoke` backend 显式拒绝 `--wsi-writer tile-streaming`。
- smoke tile source manifest 的 level0 `levels[]` 现在记录 `shape`，以满足 streaming writer 覆盖校验。
- 更新 README 与 `docs/audit/`，将 P4 状态调整为“受限 tiled iterator streaming writer 已完成 / 仍缺失完整四层 production streaming 和 OME-TIFF resume”，并继续保留 production 边界。

### 影响文件

- `.agent/tasks/p4-tile-iterator-writer-20260524.md`
- `.agent/tasks/p4-smoke-streaming-writer-integration-20260524.md`
- `.agent/reports/p4-tile-iterator-writer-20260524.md`
- `.agent/reports/p4-smoke-streaming-writer-integration-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.68.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 27 tests in 0.086s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
    - 结果：通过，`Ran 20 tests in 1.284s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 31 tests in 1.309s OK`
- Orchestrator 合并后复核：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 58 tests in 1.370s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error
- Orchestrator 文档/版本同步后最终验证：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，卸载 `multi-center-wsi-generator 0.67.0` 并安装 editable `multi-center-wsi-generator 0.68.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.68.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata / PROJECT_VERSION / PACKAGE_VERSION ... PY`
    - 结果：`0.68.0`、`v0.68.0`、`0.68.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 58 tests in 1.569s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 234 tests in 17.266s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.67.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次继续选择 P4 输出可靠性，在 v0.66.0 可恢复 tile manifest contract 与磁盘 tile source contract 基础上，推进 smoke tile resume execution 和磁盘 tile source 组装写出。

### 已做改动

- 版本号升级到 `v0.67.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建两个 P4 worker 任务：
  - `.agent/tasks/p4-generation-resume-execution-20260524.md`
  - `.agent/tasks/p4-disk-tile-assembly-writer-20260524.md`
- 回收两个 worker 报告：
  - `.agent/reports/p4-generation-resume-execution-20260524.md`
  - `.agent/reports/p4-disk-tile-assembly-writer-20260524.md`
- `run_smoke_generation()` 新增 `resume_tile_manifest_path` 参数；`run-generation --backend smoke-cascade` 新增 `--resume-tile-manifest`。
- smoke generation 现在写出 `tiles/tile-*.npy`、`tile_manifest.json` 和 `tile_source_manifest.json`，并把路径写入 plan、metadata 和 generation run summary。
- resume execution 会拒绝 failed tile、非 row-major completion gap、缺失 completed tile 文件、与当前 generation plan 不匹配的 manifest 和最终不完整 manifest。
- `torch-diffusion-smoke` backend 显式拒绝 `--resume-tile-manifest`，避免把 smoke-only resume contract 误用于 torch smoke sampler。
- `src/he_wsi_generator/outputs/ome_tiff.py` 新增 `write_pyramid_ome_tiff_from_tile_sources()`，可从磁盘 `.npy` tile source manifest 校验 level shape、tile origin、write region 和 coverage 后内存组装 pyramid 并写出 OME-TIFF。
- 新增/更新测试，覆盖 smoke 首次 tile manifest 写出、partial resume、bad resume manifest、CLI resume、磁盘 tile source 组装写出、coverage gap/overlap/越界和 shape/status 失败路径。
- 更新 README 与 `docs/audit/`，将 P4 状态调整为“smoke resume 与磁盘 tile source assembly 已完成 / 仍缺失 production writer”，并继续保留非 production streaming 边界。

### 影响文件

- `.agent/tasks/p4-generation-resume-execution-20260524.md`
- `.agent/tasks/p4-disk-tile-assembly-writer-20260524.md`
- `.agent/reports/p4-generation-resume-execution-20260524.md`
- `.agent/reports/p4-disk-tile-assembly-writer-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.67.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 25 tests in 0.082s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v`
    - 结果：通过，`Ran 18 tests in 1.116s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 29 tests in 1.143s OK`
- Orchestrator 合并后复核：
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，editable package 从 `0.66.0` 刷新安装为 `0.67.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.67.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：通过，默认 generation config valid
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata.version(...) ... PY`
    - 结果：package metadata `0.67.0`，`PROJECT_VERSION` 为 `v0.67.0`，`PACKAGE_VERSION` 为 `0.67.0`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 54 tests in 1.197s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 230 tests in 14.495s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.66.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P4 输出可靠性，推进 `AC-MISS-06` 中的可恢复 tile 状态、磁盘 tile source 校验和不完整输出显式失败能力。

### 已做改动

- 版本号升级到 `v0.66.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建两个 P4 worker 任务：
  - `.agent/tasks/p4-resumable-tile-manifest-20260524.md`
  - `.agent/tasks/p4-ome-tiff-streaming-contract-20260524.md`
- 回收两个 worker 报告：
  - `.agent/reports/p4-resumable-tile-manifest-20260524.md`
  - `.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`
- `src/he_wsi_generator/generation/tiling.py` 新增可恢复 tile manifest contract helper：
  - `build_resumable_tile_manifest()`
  - `update_resumable_tile_manifest()`
  - `validate_resumable_tile_manifest()`
  - `require_complete_tile_manifest()`
- `src/he_wsi_generator/outputs/ome_tiff.py` 新增磁盘 `.npy` tile source contract 校验，可在写出前拒绝 pending/failed/missing/duplicate tile、缺文件和 shape/dtype 不一致。
- OME-TIFF 返回报告新增 `production_streaming=false` 与 `streaming_contract.partial_contract_only=true`，明确当前仍是 in-memory writer + contract gate，不是 production 逐 tile streaming writer。
- 新增/更新测试，覆盖 resumable tile manifest 状态更新、非连续 row-major 完成、失败/待执行完成门控，以及磁盘 tile source contract 的正向与负向路径。
- 更新 README 与 `docs/audit/`，将 `AC-MISS-06` 从“缺失”调整为“部分完成 / 仍缺失 production writer”，并保留 production streaming 未完成边界。

### 影响文件

- `.agent/tasks/p4-resumable-tile-manifest-20260524.md`
- `.agent/tasks/p4-ome-tiff-streaming-contract-20260524.md`
- `.agent/reports/p4-resumable-tile-manifest-20260524.md`
- `.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_tiling.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.66.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker / orchestrator 定向验证：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling -v`
    - 结果：通过，`Ran 11 tests in 0.001s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
    - 结果：通过，`Ran 23 tests in 0.081s OK`
- Orchestrator 合并后复核：
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.66.0`
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：通过，editable package 从 `0.64.0` 刷新安装为 `0.66.0`
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... importlib.metadata.version ... PY`
    - 结果：package metadata `0.66.0`，`PROJECT_VERSION` 为 `v0.66.0`，`PACKAGE_VERSION` 为 `0.66.0`
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_tiling tests.test_generation_runner -v`
    - 结果：通过，`Ran 47 tests in 0.794s OK`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 223 tests in 13.671s OK`
  - `git diff --check`
    - 结果：通过，无 whitespace error

## v0.65.1 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P6 维护性收敛，降低 `src/he_wsi_generator/cli.py` 与 `src/he_wsi_generator/models/torch_training.py` 两个大文件的后续维护风险。

### 已做改动

- 版本号升级到 `v0.65.1`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并派发两个 P6 worker 任务：
  - `.agent/tasks/p6-cli-dispatch-20260524.md`
  - `.agent/tasks/p6-torch-training-helpers-20260524.md`
- 回收两个 worker 报告：
  - `.agent/reports/p6-cli-dispatch-20260524.md`
  - `.agent/reports/p6-torch-training-helpers-20260524.md`
- `src/he_wsi_generator/cli.py` 保留 parser 构建、`main()` 和 `run-local-job` 特殊解析，命令执行分发迁到 `src/he_wsi_generator/cli_commands.py`。
- 新增 `src/he_wsi_generator/cli_commands.py`，集中承载原 `main()` 的命令执行分支，保持命令、参数、输出和返回码不变。
- `src/he_wsi_generator/models/torch_training.py` 保留训练/采样 loop 与公开 API，纯 manifest/schema/validation helper 迁到 `src/he_wsi_generator/models/torch_training_contracts.py`。
- 新增/更新测试，覆盖 CLI dispatcher 回归和 torch training contracts 纯 helper 字段保持。
- 更新 README 与 `docs/audit/`，把本轮维护性收敛状态、版本号和行为边界同步为 `v0.65.1`。

### 影响文件

- `.agent/tasks/p6-cli-dispatch-20260524.md`
- `.agent/tasks/p6-torch-training-helpers-20260524.md`
- `.agent/reports/p6-cli-dispatch-20260524.md`
- `.agent/reports/p6-torch-training-helpers-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`
- `tests/test_cli.py`
- `tests/test_torch_training.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version tests.test_cli tests.test_torch_training tests.test_ui -v`
  - 结果：通过，`Ran 55 tests in 11.026s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 215 tests in 13.121s OK`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.65.1`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`
- `git diff --check`
  - 结果：通过，无 whitespace error

## v0.65.0 - 2026-05-24

### 用户需求

- 用户要求继续根据 `docs/audit/` 中的未完成项推进开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P2 剩余 GUI flow，补齐 GUI 内执行 queued job、刷新 job 状态和查看 metadata/QC/qc_review 输出摘要。

### 已做改动

- 版本号升级到 `v0.65.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并派发两个 P2 worker 任务：
  - `.agent/tasks/p2-ui-job-flow-helper-20260524.md`
  - `.agent/tasks/p2-ui-pyside-job-flow-20260524.md`
- 两个 worker 未独立完成；orchestrator 停止 worker 后接手实现，并写入报告：
  - `.agent/reports/p2-ui-job-flow-helper-20260524.md`
  - `.agent/reports/p2-ui-pyside-job-flow-20260524.md`
- `src/he_wsi_generator/ui/workflow.py` 新增 GUI flow helper：
  - `load_generation_job_status()`
  - `run_queued_generation_job()`
  - `collect_generation_job_output_summary()`
- `src/he_wsi_generator/ui/pyside_app.py` 新增执行 queued job、刷新 job 状态、加载输出摘要按钮，以及 job/output 摘要展示 label。
- 新增/更新测试，覆盖 helper 执行 queued job、读取 completed job 输出摘要、未完成 job/缺失输出显式失败，以及 PySide6 offscreen 的按钮、状态展示、输出摘要展示和错误显示。
- 更新 README 和 `docs/audit/`，将 GUI 内同步执行/刷新/输出查看从缺失项调整为已完成，同时保留后台 daemon、运行中取消、production 模型、生产级 WSI streaming 和真实 SVS 复跑边界。

### 影响文件

- `.agent/tasks/p2-ui-job-flow-helper-20260524.md`
- `.agent/tasks/p2-ui-pyside-job-flow-20260524.md`
- `.agent/reports/p2-ui-job-flow-helper-20260524.md`
- `.agent/reports/p2-ui-pyside-job-flow-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/ui/workflow.py`
- `tests/test_ui.py`
- `tests/test_ui_workflow.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- RED：`mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow -v`
  - 结果：初次失败于 `ImportError: cannot import name 'collect_generation_job_output_summary'`，证明 helper 缺口存在。
- GREEN：`mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow -v`
  - 结果：通过，`Ran 13 tests ... OK`。
- RED：`QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui.PySideFormTests -v`
  - 结果：初次失败于缺少 `run_job_button`、`run_queued_generation_job`、`load_generation_job_status` 和 `collect_generation_job_output_summary`，证明 PySide GUI flow 缺口存在。
- GREEN：`QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui.PySideFormTests -v`
  - 结果：通过，`Ran 9 tests ... OK`。
- Orchestrator 合并后复核：
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.65.0`。
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`。
  - `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui tests.test_ui_workflow tests.test_version -v`
    - 结果：通过，`Ran 41 tests in 0.250s OK`。
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 213 tests in 17.486s OK`。
  - `git diff --check`
    - 结果：通过，无 whitespace error。

## v0.64.0 - 2026-05-24

### 用户需求

- 用户要求根据 `docs/audit/` 中的未完成项继续开发，并循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`。
- 本批次选择 P2“可交互 PySide6 自定义配置页”，优先补齐只读 UI 骨架缺口。

### 已做改动

- 版本号升级到 `v0.64.0`，同步 `VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`configs/generation.default.json` 和测试断言。
- 创建并派发两个 P2 worker：
  - `.agent/tasks/p2-ui-form-20260524.md`
  - `.agent/tasks/p2-ui-job-command-20260524.md`
- 回收 worker 报告：
  - `.agent/reports/p2-ui-form-20260524.md`
  - `.agent/reports/p2-ui-job-command-20260524.md`
- 新增 `src/he_wsi_generator/ui/workflow.py`，提供非 Qt helper：从 UI form state 构建 generation config、`run-generation` 命令和 queued local job record。
- `src/he_wsi_generator/ui/pyside_app.py` 从只读展示窗口升级为可交互单页表单，支持保存 generation config、填写 run-generation 参数、编辑 6 类 label mapping，并通过 `JobRunner` 创建 queued job record。
- 新增/更新 UI 测试，覆盖 PySide6 offscreen 表单控件、保存配置、非法 label mapping、缺失必填参数、torch backend 缺 training index 和 workflow helper 成功/失败路径。
- 更新 README 和 `docs/audit/`，把“真实可交互 PySide6 自定义配置页”从缺失项调整为已完成，同时保留 GUI 内执行/监控/输出查看未完成边界。

### 影响文件

- `.agent/tasks/p2-ui-form-20260524.md`
- `.agent/tasks/p2-ui-job-command-20260524.md`
- `.agent/reports/p2-ui-form-20260524.md`
- `.agent/reports/p2-ui-job-command-20260524.md`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/__init__.py`
- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/ui/workflow.py`
- `tests/test_ui.py`
- `tests/test_ui_workflow.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.64.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker `p2-ui-form-20260524`：
  - RED：`QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui.PySideFormTests -v` 初次失败于旧窗口缺少目标表单控件。
  - GREEN：`QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui -v` 通过，`Ran 22 tests ... OK`。
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v` 通过。
  - `git diff --check` 通过。
- Worker `p2-ui-job-command-20260524`：
  - GREEN：`mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow tests.test_job_runner -v` 通过，`Ran 23 tests ... OK`。
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v` 通过。
  - `git diff --check` 通过。
- Orchestrator 合并后复核：
  - `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui tests.test_ui_workflow -v`
    - 结果：通过，`Ran 32 tests ... OK`。
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
    - 结果：主 worktree editable install 成功，包版本为 `0.64.0`。
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
    - 结果：`v0.64.0`。
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`。
  - `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python - <<'PY' ... create_main_window() ... PY`
    - 结果：窗口标题为 `MultiCenterWSIGenerator`，`generation_config_path_input` 存在，保存按钮可用，widget count 为 `126`。
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 206 tests in 18.622s OK`。
  - `git diff --check`
    - 结果：通过，无 whitespace error。
  - `git status --short`
    - 结果：v0.64.0 基线提交后主工作区干净。
  - `git log -1 --oneline`
    - 结果：最新提交信息包含版本号 `v0.64.0 interactive PySide configuration page`。

## Audit Snapshot - 2026-05-24（v0.63.0 conda 环境验证）

### 用户需求

- 用户要求创建独立 conda 环境 `MultiCenterWSIGenerator`，安装全部项目依赖，包括 PyTorch。
- 用户要求基于该环境继续循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`，完成 `docs/audit/` 中显示的未完成开发。

### 已做改动

- 创建 conda 环境 `MultiCenterWSIGenerator`，并通过 `pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'` 安装完整可选依赖集合。
- 确认该环境中的 Python、OpenSlide、PySide6、PyTorch/CUDA 和项目 CLI 可用。
- 在新环境中重新执行 PyTorch/UI 定向测试和全量单元测试，消除前一轮“当前环境缺少 torch/PySide6”的未验证项。
- 更新 `docs/DEMANDS.MD`、`docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md` 和 README 的环境化验证说明。
- 将 v0.63.0 工作区收口为 `main` 分支基线提交，便于后续 worker worktree 从正确版本启动；尚未 tag 或打包发布。
- 未修改 `src/`、`tests/`、`configs/` 运行时代码，未升级版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba create -y -n MultiCenterWSIGenerator -c conda-forge python=3.11 pip openslide`
  - 结果：环境创建成功。
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
  - 结果：完整可选依赖安装成功。
- `mamba run -n MultiCenterWSIGenerator python -c 'import torch, PySide6, openslide, yaml, tifffile, PIL, numpy'`
  - 结果：导入成功；Python `3.11.15`，PyTorch `2.12.0+cu130`，CUDA 可用，GPU 为 `NVIDIA GeForce RTX 5060 Ti`。
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.63.0`。
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training tests.test_ui -v`
  - 结果：通过，`Ran 39 tests ... OK`。
- `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python - <<'PY' ... create_main_window() ... PY`
  - 结果：窗口标题为 `MultiCenterWSIGenerator`，central widget 存在，widget count 为 `88`；该结果只证明当前 PySide6 依赖和窗口创建可用，不代表真实交互式配置页已完成。
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 191 tests in 19.932s OK`。
- `git status --short`
  - 结果：v0.63.0 基线提交后主工作区干净。
- `git log -1 --oneline`
  - 结果：最新提交信息包含版本号 `v0.63.0 contract remediation and env audit`。

## Audit Snapshot - 2026-05-24（v0.63.0 复审计）

### 用户需求

- 用户显式调用 `project-remediation-audit`，要求基于当前仓库状态进行补救审计。
- 本轮只做审计和审计工件维护，不开始新的实现修复。

### 已做改动

- 更新 `docs/DEMANDS.MD`，新增本轮 v0.63.0 复审计需求。
- 更新 `docs/audit/ACCEPTANCE_CHECKLIST.md`，补充当前工作区状态、未提交/未 tag 风险、worker worktree 遗留状态和本轮验证结果。
- 更新 `docs/audit/IMPLEMENTATION_PLAN.md`，新增 P0.5 交付收口任务包。
- 更新 `docs/audit/DECISIONS.md`，记录当前 v0.63.0 仍是未提交工作区状态，不能表述为已发布 release。
- 未修改 `src/`、`tests/`、`configs/` 运行时代码，未升级版本号。

### 影响文件

- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `git status --short`
  - 结果：当前 `v0.63.0` 仍是未提交工作区状态，包含版本、代码、测试、README、`.agent/` 和 `docs/audit/` 改动；旧根目录审计文件在 git 状态中显示为删除，新 `docs/audit/` 显示为未跟踪。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 191 tests ... OK (skipped=21)`；跳过项均为当前环境缺少 PyTorch 的 torch smoke 测试。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.63.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- `python -c` 导入依赖检查：
  - 结果：当前环境缺少 `torch` 与 `PySide6`，因此 PyTorch smoke 路径和真实 PySide6 GUI 启动仍未验证。

## v0.63.0 - 2026-05-24

### 用户需求

- 用户要求根据 `docs/audit/` 中的审计内容继续开发，并使用 `codex-worker-orchestration` 进行并行 worker 编排。
- 本轮选择 P1“契约一致性与文档诚实度”作为补救批次。

### 已做改动

- 版本号升级到 `v0.63.0`。
- 创建 worker 任务文件：
  - `.agent/tasks/p1-qc-review-validate-20260524.md`
  - `.agent/tasks/p1-output-summary-contract-20260524.md`
- 创建并派发两个 worker worktree：
  - `.worktrees/p1-qc-review-validate` / `worker/p1-qc-review-validate`
  - `.worktrees/p1-output-summary-contract` / `worker/p1-output-summary-contract`
- 回收 worker 报告：
  - `.agent/reports/p1-qc-review-validate-20260524.md`
  - `.agent/reports/p1-output-summary-contract-20260524.md`
- `he-wsi-gen validate` 新增 `qc-review` schema kind，并复用现有 `validate_qc_review()`；非法 `qc_review` artifact 会走 CLI 明确错误输出。
- `collect_output_summary()` 现在对 metadata 执行 schema 校验，并显式校验 metadata/QC/可选 `qc_review` 的 `generated_id` 一致性。
- 新增仓库实体 `AGENTS.md`，固化本仓库工作规则。
- 更新 README 的当前版本、schema kind 列表、输出摘要契约说明、M5/M7 里程碑边界和当前边界说明。
- 更新 `docs/audit/`，把已解决的 P1 项从“缺失/偏离”调整为“已完成”，并保留未完成项。

### 影响文件

- `AGENTS.md`
- `.agent/tasks/p1-qc-review-validate-20260524.md`
- `.agent/tasks/p1-output-summary-contract-20260524.md`
- `.agent/reports/p1-qc-review-validate-20260524.md`
- `.agent/reports/p1-output-summary-contract-20260524.md`
- `.gitignore`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.63.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker `p1-qc-review-validate`：
  - RED：`PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_cli_accepts_qc_review_artifact tests.test_qc_review.QCReviewTests.test_validate_cli_rejects_invalid_qc_review_artifact_type -v` 初次失败于 `qc-review` 不是 CLI valid choice。
  - GREEN：`PYTHONPATH=src python -m unittest tests.test_cli tests.test_qc_review -v` 通过，`Ran 12 tests ... OK`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json` 通过。
  - `git diff --check` 通过。
- Worker `p1-output-summary-contract`：
  - RED：`PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_collect_output_summary_rejects_invalid_metadata_contract tests.test_ui.UITests.test_collect_output_summary_rejects_metadata_qc_generated_id_mismatch -v` 初次失败于未校验 metadata schema 和 generated id mismatch。
  - GREEN：`PYTHONPATH=src python -m unittest tests.test_ui -v` 通过，`Ran 17 tests ... OK`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json` 通过。
  - `git diff --check` 通过。
- Orchestrator 复核：
  - 已重新检查两个 worker 的 report、`git status --short` 和 diff，并在各自 worktree 重新运行关键验证。
  - `PYTHONPATH=src python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 191 tests ... OK (skipped=21)`；跳过项均为当前环境缺少 PyTorch 的 torch smoke 测试。
  - `PYTHONPATH=src python -m he_wsi_generator.cli --version`
    - 结果：`v0.63.0`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`。
  - `git diff --check`
    - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（One-time Parallel Developer 整合 Skill）

### 用户需求

- 用户认为“每循环一个问题”会降低并行效率，确认循环粒度应改为“一个补救主题或优先级批次”，批次内部并行派发多个 worker。
- 用户要求将 `codex-worker-orchestration` 和 `project-remediation-audit` 整合到一个 `one-time-parallel-developer` 大 skill 中。
- 用户要求同时确保 `codex-worker-orchestration` 和 `project-remediation-audit` 仍然可以被单独调用。

### 已做改动

- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/one-time-parallel-developer`。
- `one-time-parallel-developer` 定义完整闭环：`Audit -> Batch -> Task -> Worker -> Review -> Merge -> Re-audit -> Repeat/Stop`。
- `one-time-parallel-developer` 明确循环粒度为一个补救主题或优先级批次，每批建议 2-5 个可并行 worker。
- `one-time-parallel-developer` 明确了适合并行、不适合并行、每轮最小交付物和停止条件。
- 更新 `codex-worker-orchestration`，新增“独立调用与整合调用”说明，保留单独 worker 编排能力。
- 更新 `project-remediation-audit`，新增“独立调用与整合调用”说明，保留单独审计能力。
- 更新 README，记录三个相关个人 Codex skills 的职责边界。
- 更新 `docs/DEMANDS.MD`，记录本轮整合 skill 需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/one-time-parallel-developer/SKILL.md`
- `/home/muhengliao/.codex/skills/one-time-parallel-developer/agents/openai.yaml`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`

### 验证结果

- `find /home/muhengliao/.codex/skills/one-time-parallel-developer /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 2 -type f`
  - 结果：三个 skill 的 `SKILL.md` / `agents/openai.yaml` 均存在，`codex-worker-orchestration` 的 assets 模板仍存在。
- 手工 frontmatter 校验：
  - 结果：`one-time-parallel-developer`、`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `rg -n "one-time-parallel-developer|独立调用与整合调用|Audit -> Batch -> Task -> Worker -> Review -> Merge -> Re-audit -> Repeat/Stop" /home/muhengliao/.codex/skills/one-time-parallel-developer /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：整合 skill 包含完整闭环状态机；两个子 skill 均包含“独立调用与整合调用”说明，并指向 `one-time-parallel-developer`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（Worker 模板与 Skill 中文化）

### 用户需求

- 用户确认 worker final report 是每个子任务一份后，要求把两个 skill、子任务模板、子任务报告模板都改为中文。

### 已做改动

- 将 `.agent/templates/worker_task.md` 中文化。
- 将 `.agent/templates/worker_report.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/agents/openai.yaml` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/project-remediation-audit/agents/openai.yaml` 中文化。
- 更新 `docs/DEMANDS.MD`，记录本轮中文化需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `.agent/templates/worker_task.md`
- `.agent/templates/worker_report.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/agents/openai.yaml`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/agents/openai.yaml`

### 验证结果

- `rg -n "Assignment|Role|Goal|Required Context|Scope|Constraints|Final Report|Preconditions|Worker Contract|Workflow|Common Failure|Project Remediation|Overview|Use when" .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：无输出，未发现旧英文流程标题或关键短语残留。
- 手工 frontmatter 校验：
  - 结果：`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `find .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 3 -type f`
  - 结果：两个仓库模板、两个 skill 的 `SKILL.md` / `agents/openai.yaml`、并行开发 skill assets 中的两个模板均存在。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（Codex worker 并行开发与审计 skill）

### 用户需求

- 用户要求生成 Codex worker 子任务文件模板和子报告模板。
- 用户要求把“主 Codex orchestrator + 独立 Codex exec worker + 任务文件 + 结果报告 + git worktree 隔离区”的并行开发流程固化为 skill。
- 用户要求把前面的项目补救审计流程固化为 skill。

### 已做改动

- 新增 `.agent/templates/worker_task.md`，定义 worker task file 的字段、角色、范围、验证命令和停止条件。
- 新增 `.agent/templates/worker_report.md`，定义 worker final report 的状态、变更、验证、风险和 orchestrator 后续动作格式。
- 更新 `.gitignore`，忽略 `.worktrees/` 和 `.agent/logs/`。
- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/codex-worker-orchestration`。
- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/project-remediation-audit`。
- `codex-worker-orchestration` 同步保存 worker task/report 模板到 skill assets，便于跨项目复用。
- 更新 README 的协作模板入口。
- 更新 `docs/DEMANDS.MD`，记录本轮并行开发与审计 skill 固化需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `.gitignore`
- `.agent/templates/worker_task.md`
- `.agent/templates/worker_report.md`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`

### 验证结果

- `codex exec --help`
  - 结果：可用，显示 `Run Codex non-interactively` 和 `-C, --cd <DIR>` / `-o, --output-last-message <FILE>` 等参数。
- `find .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 3 -type f`
  - 结果：能找到两个仓库模板、两个 skill 的 `SKILL.md` / `agents/openai.yaml`，以及并行开发 skill assets 中的两个模板。
- 手工 frontmatter 校验：
  - 结果：`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `rg -n "TODO|\[TODO\]" .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：无遗留 TODO。
- `git check-ignore -q .worktrees/probe` 和 `git check-ignore -q .agent/logs/probe.log`
  - 结果：均命中忽略规则。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.62.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- `python /home/muhengliao/.codex/skills/.system/skill-creator/scripts/quick_validate.py ...`
  - 结果：当前主环境缺少 PyYAML，失败于 `ModuleNotFoundError: No module named 'yaml'`；未在主环境安装依赖，后续可在隔离环境补跑。

## Audit Snapshot - 2026-05-24（审计文件迁移与项目进度）

### 用户需求

- 用户要求先把 `docs/ACCEPTANCE_CHECKLIST.md`、`docs/IMPLEMENTATION_PLAN.md`、`docs/DECISIONS.md` 移动到 `docs/audit/`。
- 用户要求读取现有设计说明、开发指南、README、`docs/` 目录和当前代码结构，总结当前项目开发进度，并明确距离完整项目成果还有多远。
- 用户要求把审计结果更新到 `docs/audit/` 的相关文件中。

### 已做改动

- 新建 `docs/audit/` 并迁移三个审计文件。
- 更新 `docs/audit/ACCEPTANCE_CHECKLIST.md`，按“已完成 / 缺失 / 偏离 / 未验证”重写当前项目进度审计，并明确当前仍是 core/CLI 骨架和 smoke/proxy 验证链，不是完整 production 生成器。
- 更新 `docs/audit/IMPLEMENTATION_PLAN.md`，把补救拆成审计归位、契约一致性、可交互 UI、production 模型、生产级 WSI 输出、环境化验证和维护性收敛任务包。
- 更新 `docs/audit/DECISIONS.md`，记录完整项目成果定义、关键设计决策和禁止变更项。
- 更新 `docs/DEMANDS.MD`，把本轮审计文件迁移与项目进度审计需求置顶记录。
- 更新 `README.md`，在核心文档列表中加入审计验收清单、补救计划和决策文件入口。
- 未修改 `src/`、`tests/`、`configs/` 中的实现逻辑，未升级版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `find docs -maxdepth 2 -type f \( -path 'docs/audit/*' -o -name 'ACCEPTANCE_CHECKLIST.md' -o -name 'IMPLEMENTATION_PLAN.md' -o -name 'DECISIONS.md' \) -printf '%p\n' | sort`
  - 结果：仅返回 `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/DECISIONS.md`、`docs/audit/IMPLEMENTATION_PLAN.md`。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.62.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Audit Snapshot - 2026-05-24（基于 v0.62.0）

### 用户需求

- 用户要求进入项目补救审计模式。
- 本轮先输出偏差审计，再给出最小补救计划；在确认前不开始修代码。

### 已做改动

- 未修改 `src/`、`tests/`、`configs/` 中的实现代码。
- 更新 `docs/DEMANDS.MD`，把本轮审计需求置顶记录。
- 新增 `docs/ACCEPTANCE_CHECKLIST.md`，把当前基线拆成“已完成 / 缺失 / 偏离 / 未验证”的可验收项。
- 新增 `docs/IMPLEMENTATION_PLAN.md`，整理补救任务包和优先级。
- 新增 `docs/DECISIONS.md`，冻结当前审计基线、关键设计决策和禁止变更项。
- 本轮审计额外确认：
  - 当前仓库内不存在实体 `AGENTS.md` 文件。
  - `qc_review` 具备内部校验函数，但尚未接入通用 `validate` CLI/schema kind。
  - `collect_output_summary()` 当前只校验 QC/review，不校验 metadata schema。
  - 当前环境缺少 `torch` 和 `PySide6`，所以 PyTorch 路径和真实 GUI 启动未在本轮复跑验证。

### 影响文件

- `docs/DEMANDS.MD`
- `docs/ACCEPTANCE_CHECKLIST.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DECISIONS.md`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_version -v`
  - 结果：2 个测试通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：187 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 `torch` 被跳过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate-prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-output-summary --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --qc-review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
  - 结果：返回 `qc_status=pass`、三级状态全 `pass`、`review_required=false`、`decision=accepted`。
- `python - <<'PY' import torch ...`
  - 结果：`ModuleNotFoundError`。
- `python - <<'PY' import PySide6 ...`
  - 结果：`ModuleNotFoundError`。
- `python - <<'PY' import openslide ...`
  - 结果：可导入。

## v0.62.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 用户要求代码开发完成后使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 验证，并确保所有输出能正常交付。
- 本次版本需要把自动 QC 的 warning/fail 结果落盘为可追踪、可更新决策的 `qc_review` artifact，并让输出摘要能合并审阅状态。

### 已做改动

- 版本号升级到 `v0.62.0`。
- 新增 `src/he_wsi_generator/qc/review.py`，实现 `qc_review` artifact 的构建、读取、验证与决策更新。
- `build_qc_review()` 读取 `metadata.json` 与 `qc.json`，输出 `schema_version`、`artifact_type=qc_review`、`generated_id`、输入路径与 sha256、QC overall/level 状态、`review_required`、`decision=pending`、`created_at` 和待审阅 metric 列表。
- `review_required` 现在与 QC `overall_status` 强一致：`warning`/`fail` 为 `true`，`pass` 为 `false`。
- warning/fail metric 会保留 level、metric name、status、value、reference、message/reason（若存在）。
- `apply_qc_review_decision()` 仅接受 `accepted`、`rejected`、`needs_rerun`，只允许更新 `pending` 审阅单，并记录 `reviewer`、`note`、`reviewed_at`。
- CLI 新增 `create-qc-review` 与 `apply-qc-review-decision`，`inspect-output-summary` 新增可选 `--qc-review`。
- `collect_output_summary()` 现在可合并 `qc_review` 状态，输出 `review_required`、`decision`、`reviewer` 和 `review_item_count`。
- README 补充 `qc_review` 命令、输出摘要的 review 合并行为和本次边界说明。
- 需求记录 `docs/DEMANDS.MD` 顶部补充 v0.62.0 结构化需求。

### 影响文件

- `VERSION`
- `README.md`
- `docs/CHANGELOG.md`
- `docs/DEMANDS.MD`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/review.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.62.0`）

### 验证结果

- TDD 红灯记录：
  - 新增 `tests/test_qc_review.py` 初次运行因 `he_wsi_generator.qc.review` 模块不存在而失败。
  - 新增 `collect_output_summary(..., qc_review_path=...)` 测试初次运行因函数签名不支持 `qc_review_path` 而失败。
  - 新增 `inspect-output-summary --qc-review` 测试初次运行因 CLI 参数未实现而失败。
  - 新增 `review_required` 强一致性测试初次运行因校验逻辑未实现而失败。
- `PYTHONPATH=src python -m unittest tests.test_qc_review -v`
  - 结果：8 个测试通过。
- `PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_collect_output_summary_includes_qc_review_status tests.test_ui.UITests.test_cli_inspects_output_summary_with_qc_review -v`
  - 结果：2 个测试通过。
- `PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_qc_review_rejects_mismatched_review_required -v`
  - 结果：初次失败，随后补齐 `review_required` 一致性校验并转绿。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：187 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.62.0 验证链路：
  - `validate manifest build/validation/v0.62.0-291288/input_manifest.json`
  - `validate qc build/validation/v0.62.0-291288/reference-qc/qc-reference-291288.json`
  - `build-wsi-tissue-overview build/validation/v0.62.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.62.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.62.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.62.0-291288/prior --prior-id prior-291288-v062 --dataset-id pancancer-fanhong-breast-291288-validation --input-manifest build/validation/v0.62.0-291288/input_manifest.json --training-data-version validation-v0.62.0 --wsi-id 291288 --random-seed 7 --layout-mask-prior build/validation/v0.62.0-291288/layout_mask_prior.json --style-prior build/validation/v0.62.0-291288/style_prior.json --texture-prior build/validation/v0.62.0-291288/texture_prior.json --qc-reference-distribution build/validation/v0.62.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.62.0-291288/layout_mask_prior.json --output-dir build/validation/v0.62.0-291288/sampled-layout --sample-id 291288-v062-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json --output build/validation/v0.62.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.62.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.62.0-291288/trained-checkpoint.json --output-root build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062 --generated-id gen-291288-smoke-sampled-mask-v062 --condition-packet build/validation/v0.62.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json`
  - `validate qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json`
  - `create-qc-review --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --output build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
  - `apply-qc-review-decision --review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json --decision accepted --reviewer "Dr. Chen" --note "Real SVS validation reviewed."`
  - `inspect-output-summary --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --qc-review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json`、`qc.json` 和 `qc_review.json` 均为 `schema_version=v0.62.0`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `qc_review.json` 返回 `artifact_type=qc_review`、`review_required=false`、`decision=accepted`、`reviewer=Dr. Chen`，`review_item_count=0`。
  - `generated_mask/mask.npy` shape 为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取，level count 为 4，首层 shape 为 `[512, 512, 3]`。
  - 输出目录 `build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`qc_review.json`、`generation_run.json` 和 `batch.jsonl`。

## v0.61.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 用户要求代码开发完成后使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 验证，并确保所有输出能正常交付。
- 本次版本在 v0.60.0 的分层 `qc_reference_distribution` artifact 基础上，推进运行时消费能力：生成/QC 链路需要能根据当前样本的可追踪上下文选择匹配 stratum 阈值，而不是永远只使用全局 `metrics`。

### 已做改动

- 版本号升级到 `v0.61.0`。
- `build_qc_report()` 新增可选 `qc_reference_context` 参数，并在启用 `qc_reference_distribution.stratification` 时按 context 构造 exact stratum key。
- 当 context 匹配 stratum 时，QC metric 使用该 stratum 的阈值，并在 `reference` 中记录 `selection=stratified`、`stratum_key`、`stratification_fields` 和 `group_values`。
- 当 context 缺失、不完整、非法或找不到 stratum 时，QC metric 显式回退全局阈值，并记录 `selection=global_fallback`、`fallback_reason` 和 `stratification_fields`。
- 未启用分层 reference 时，QC 仍消费全局 `metrics`，并记录 `selection=global`，保持既有全局阈值行为。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 从 condition packet summary 提取 `metadata.cancer_type`、`metadata.tissue_type`、`metadata.center_id`、`metadata.split` 作为 QC reference context。
- `build_generation_condition_packet()` 在 `conditions.layout.wsi_tissue_overview.records[*]` 中保留运行时 QC 分层需要的 manifest 摘要字段。
- `build-wsi-tissue-overview` 产物在输入 manifest 含 `center_id` 时保留该字段，便于后续按中心分层。
- 嵌套 stratum metrics 类型错误现在会报告实际 JSON 路径，避免误报成全局 `qc_reference_distribution.metrics`。
- README 同步说明运行时分层 QC exact-match 选择、global fallback 审计和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/priors/tissue.py`
- `src/he_wsi_generator/qc/engine.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_schemas.py`
- `tests/test_wsi_tissue_overview.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.61.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- TDD 红灯记录：
  - 新增 QC engine 分层 reference 测试最初因 `build_qc_report()` 不支持 `qc_reference_context` 而失败。
  - 新增 context 缺失 fallback 测试最初因 metric reference 未记录 `selection=global_fallback` 而失败。
  - 新增 smoke generation 分层 QC 测试最初因 condition packet summary 未传入 QC context 而失败。
  - 新增 condition packet manifest 摘要测试最初因 `conditions.layout.wsi_tissue_overview.records[*]` 未保留 manifest 字段而失败。
  - 新增 WSI tissue overview `center_id` 测试最初因 artifact 未保留输入 manifest 的 `center_id` 而失败。
  - 新增嵌套 stratum metrics 错误路径测试最初因报错仍指向全局 `qc_reference_distribution.metrics` 而失败。
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_generation_conditioning tests.test_wsi_tissue_overview tests.test_schemas tests.test_ui tests.test_version -v`
  - 结果：68 个测试通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：178 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.61.0 验证链路：
  - `validate manifest build/validation/v0.61.0-291288/input_manifest.json`
  - `validate qc build/validation/v0.61.0-291288/reference-qc/qc-reference-291288.json`
  - `build-wsi-tissue-overview build/validation/v0.61.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.61.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.61.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.61.0-291288/prior ... --qc-reference-distribution build/validation/v0.61.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.61.0-291288/layout_mask_prior.json --output-dir build/validation/v0.61.0-291288/sampled-layout --sample-id 291288-v061-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json --output build/validation/v0.61.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.61.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.61.0-291288/trained-checkpoint.json --output-root build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v061 --condition-packet build/validation/v0.61.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.61.0`。
  - `wsi_tissue_overview.records[0].manifest` 保留 `cancer_type=breast_cancer`、`tissue_type=breast`、`center_id=fanhong`、`split=test`。
  - `condition_packet.conditions.layout.wsi_tissue_overview.records[0].manifest` 保留运行时 QC context 所需字段。
  - `qc_reference_distribution.stratification.enabled=true`，`fields=["metadata.cancer_type"]`，`stratum_count=1`，包含 `metadata.cancer_type=breast_cancer` stratum。
  - Prior manifest 的 `qc_reference_distribution` artifact metadata 记录 `stratification_fields=["metadata.cancer_type"]`、`stratum_count=1` 和 `metric_count=2`。
  - 输出目录 `build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `qc.json` 中 `mean_red` 和 `mask_tissue_fraction` 均记录 `reference.selection=stratified`、`stratum_key=metadata.cancer_type=breast_cancer` 和 `group_values={"metadata.cancer_type":"breast_cancer"}`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`；最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取，包含 OME metadata，level count 为 4，首层 shape 为 `[512, 512, 3]`。
  - `generation_run.json.pyramid_report.chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - `batch.jsonl` 包含 1 条 generated sample 索引。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.60.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“按组织区域、疾病类型或中心分层统计/QC”的工程落地：`qc_reference_distribution` 需要支持显式分层阈值估计，在保留全局阈值兼容性的同时，为癌种、中心、组织类型等元数据分组写出独立 warning/fail 区间和审计记录。

### 已做改动

- 版本号升级到 `v0.60.0`。
- `build_qc_reference_distribution()` 新增可选 `stratify_by` 参数，接受一个或多个 dot-path 字段，例如 `metadata.cancer_type`、`metadata.center_id` 或 `metadata.tissue_type`。
- 未传 `stratify_by` 时，继续保留既有全局 `metrics`、`outlier_policy` 和 `outlier_audit` 行为兼容。
- 传入 `stratify_by` 时，输出 JSON 新增 `stratification` 和 `strata` 字段。
- 每个 stratum 独立使用同一 estimator、outlier policy 和 `min_samples` 规则估计 metric 阈值，并写出该分组的样本 id、group values 和 outlier audit。
- 分层字段缺失、为 `null`、为空字符串或值类型不适合做分组时，builder 会显式报错，不会静默归入 unknown bucket。
- CLI `build-qc-reference` 新增可重复参数 `--stratify-by <dot.path>`。
- Prior manifest 的 `qc_reference_distribution` artifact metadata 新增 `stratification_fields` 和 `stratum_count` 摘要。
- README 同步说明 `--stratify-by` 用法、输出字段、兼容关系和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_qc_reference.py`
- `tests/test_priors.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.60.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- TDD 红灯记录：
  - 新增分层 reference 测试最初因 `build_qc_reference_distribution()` 不支持 `stratify_by` 参数而失败。
  - CLI 测试最初因 `build-qc-reference` 不支持 `--stratify-by` 而未能写出输出文件。
  - Prior manifest 测试最初因 `qc_reference_distribution` artifact metadata 未记录 `stratification_fields` 而失败。
- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_priors tests.test_version -v`
  - 结果：23 个测试通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：174 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.60.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.60.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.60.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.60.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.60.0-291288/prior ... --qc-reference-distribution build/validation/v0.60.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.60.0-291288/layout_mask_prior.json --output-dir build/validation/v0.60.0-291288/sampled-layout --sample-id 291288-v060-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json --output build/validation/v0.60.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.60.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.60.0-291288/trained-checkpoint.json --output-root build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v060 --condition-packet build/validation/v0.60.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.60.0`。
  - `qc_reference_distribution.stratification.enabled=true`，`fields=["metadata.cancer_type"]`，`stratum_count=1`。
  - `strata["metadata.cancer_type=breast_cancer"].metrics.mean_red.median=127.5`，分层 metric 使用 `robust_mad_z_score` estimator。
  - Prior manifest 的 `qc_reference_distribution` artifact metadata 记录 `stratification_fields=["metadata.cancer_type"]`、`stratum_count=1` 和 `metric_count=2`。
  - 输出目录 `build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取并包含 OME metadata。
  - `generation_run.json.pyramid_report.chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`。

## v0.59.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持 robust z-score 风格的全局阈值估计，让颜色、清晰度、组织比例等数值 metric 能用 median/MAD 生成抗离群的 warning/fail 区间。

### 已做改动

- 版本号升级到 `v0.59.0`。
- `build_qc_reference_distribution()` 的 `estimator` 新增 `robust_mad_z_score`。
- `robust_mad_z_score` 基于排序后的参考 QC 数值计算 median、MAD 和 scaled MAD。
- `robust_mad_z_score` 输出 `median`、`mad`、`scaled_mad`、`warning_z_score`、`fail_z_score`、observed min/max、sample count 和 estimator 字段。
- Warning 区间使用 `median ± 3.0 * scaled_mad`，fail 区间使用 `median ± 6.0 * scaled_mad`。
- MAD 为 0 时使用有限非零 margin，避免阈值坍缩到单点。
- `robust_mad_z_score` 与既有 `outlier_policy` 兼容；显式启用 `robust_iqr_filter` 时会先过滤参考样本，再用保留样本估计 MAD/z-score 阈值。
- CLI `build-qc-reference --estimator` 新增 `robust_mad_z_score` 可选值。
- README 同步说明 MAD/z-score estimator 的用法、输出字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.59.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：12 个测试通过。
- TDD 红灯记录：
  - 新增 MAD/z-score estimator 测试最初因 `build_qc_reference_distribution()` 不支持 `robust_mad_z_score` estimator 而失败。
  - CLI 测试最初因 `build-qc-reference --estimator` 不支持 `robust_mad_z_score` 而未能写出输出文件。
- CLI 实测：
  - `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json ... <tmp>/qc-5.json --metric mean_red --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.59.0`，`outlier_policy=robust_iqr_filter`，`mean_red.estimator=robust_mad_z_score`，过滤后 `sample_count=4`、`observed_max=106.0`、`median=103.0`、`mad=2.0`、`scaled_mad=2.9652`、`warning_z_score=3.0`、`fail_z_score=6.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：172 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.59.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.59.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.59.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --output build/validation/v0.59.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.59.0-291288/prior ... --qc-reference-distribution build/validation/v0.59.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.59.0-291288/layout_mask_prior.json --output-dir build/validation/v0.59.0-291288/sampled-layout --sample-id 291288-v059-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json --output build/validation/v0.59.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.59.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.59.0-291288/trained-checkpoint.json --output-root build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v059 --condition-packet build/validation/v0.59.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.59.0`。
  - `qc_reference_distribution.outlier_policy=robust_iqr_filter`，`metrics.mean_red.estimator=robust_mad_z_score`，单样本验证 reference 中 `mean_red.sample_count=1`、`median=127.5`、`mad=0.0`、`scaled_mad=12.75`、`warning_z_score=3.0`、`fail_z_score=6.0`。
  - `outlier_audit.metrics.mean_red` 记录原始 1 个样本、保留 1 个样本、排除 0 个样本。
  - 输出目录 `build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.58.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持显式的参考 QC 异常值过滤策略，在生成阈值前排除少量明显离群参考样本，同时保留完整审计记录，避免静默丢弃数据。

### 已做改动

- 版本号升级到 `v0.58.0`。
- `build_qc_reference_distribution()` 新增 `outlier_policy` 参数，默认 `none`，保持既有行为兼容。
- 新增 `robust_iqr_filter` policy：对每个 metric 的参考 QC 数值计算 Q1、Q3 和 IQR，并使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 作为保留区间。
- `robust_iqr_filter` 会在阈值估计前按 metric 排除 fence 外的参考样本；过滤结果只影响当前 metric，不会删除或改写原始 QC 文件。
- 输出 JSON 新增 `outlier_policy` 和 `outlier_audit`，记录每个 metric 的原始样本数、保留样本数、排除样本数、filter fence 和被排除样本的 `generated_id`、metric name、value。
- 若过滤后样本数低于 `min_samples`，builder 会显式报错，不会回退到未过滤样本。
- 非法 `outlier_policy` 会通过 `QCReferenceBuildError` 显式报错。
- CLI `build-qc-reference` 新增 `--outlier-policy` 参数，支持 `none` 和 `robust_iqr_filter`。
- README 同步说明 reference outlier filtering 的用法、审计字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.58.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：10 个测试通过。
- TDD 红灯记录：
  - 新增 outlier policy 测试最初因 `build_qc_reference_distribution()` 不支持 `outlier_policy` 参数而失败。
  - CLI 测试最初因 `build-qc-reference` 不支持 `--outlier-policy` 而未能写出输出文件。
- CLI 实测：
  - `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json ... <tmp>/qc-5.json --metric mean_red --estimator robust_iqr --outlier-policy robust_iqr_filter --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.58.0`，`outlier_policy=robust_iqr_filter`，`mean_red.sample_count=4`，`mean_red.observed_max=106.0`，`outlier_audit` 记录原始 5 个样本、保留 4 个样本、排除 1 个样本，排除样本为 `gen-cli-005` 且数值为 `500.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：170 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.58.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.58.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.58.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_iqr --outlier-policy robust_iqr_filter --output build/validation/v0.58.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.58.0-291288/prior ... --qc-reference-distribution build/validation/v0.58.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.58.0-291288/layout_mask_prior.json --output-dir build/validation/v0.58.0-291288/sampled-layout --sample-id 291288-v058-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json --output build/validation/v0.58.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.58.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.58.0-291288/trained-checkpoint.json --output-root build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v058 --condition-packet build/validation/v0.58.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.58.0`。
  - `qc_reference_distribution.outlier_policy=robust_iqr_filter`，`metrics.mean_red.estimator=robust_iqr`，单样本验证 reference 中 `mean_red.sample_count=1`。
  - `outlier_audit.metrics.mean_red` 记录原始 1 个样本、保留 1 个样本、排除 0 个样本。
  - 输出目录 `build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.57.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“训练分布自适应阈值”的稳健估计能力：`qc_reference_distribution` 需要支持 IQR-based robust threshold estimator，避免少量离群参考 QC 把 warning/fail 区间过度拉宽。

### 已做改动

- 版本号升级到 `v0.57.0`。
- `build_qc_reference_distribution()` 新增 `estimator` 参数，默认保持既有 `observed_min_max_with_range_margin`，以兼容旧调用。
- 新增 `robust_iqr` estimator，按排序值计算 Q1、median、Q3 和 IQR。
- `robust_iqr` 输出 `q1`、`median`、`q3`、`iqr`、observed min/max、sample count 和 estimator 字段。
- `robust_iqr` 使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 生成 warning 区间，使用 `[Q1 - 3.0*IQR, Q3 + 3.0*IQR]` 生成 fail 区间。
- 零 IQR 时使用有限非零 margin，避免阈值坍缩到单点。
- 非法 estimator 会通过 `QCReferenceBuildError` 显式报错，不做静默回退。
- CLI `build-qc-reference` 新增 `--estimator` 参数，并限制为 `observed_min_max_with_range_margin` 或 `robust_iqr`。
- README 同步说明 robust IQR estimator 的用法、输出字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.57.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：7 个测试通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json <tmp>/qc-2.json <tmp>/qc-3.json --metric mean_red --metric mask_tissue_fraction --estimator robust_iqr --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.57.0`，`mean_red.estimator=robust_iqr`，并记录 `q1=101.0`、`median=102.0`、`q3=103.0`、`iqr=2.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：167 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `git pull --ff-only origin main`
  - 结果：`Already up to date.`，远端 `origin/main` 与本地 `HEAD` 均为 `59557b19672f4b9806e600c9a1db271280795513`。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.57.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.57.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.57.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_iqr --output build/validation/v0.57.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.57.0-291288/prior ... --qc-reference-distribution build/validation/v0.57.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.57.0-291288/layout_mask_prior.json --output-dir build/validation/v0.57.0-291288/sampled-layout --sample-id 291288-v057-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json --output build/validation/v0.57.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.57.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.57.0-291288/trained-checkpoint.json --output-root build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v057 --condition-packet build/validation/v0.57.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.57.0`。
  - `qc_reference_distribution.metrics.mean_red.estimator=robust_iqr`，并记录 robust quartile 字段；单样本验证 reference 中 `mean_red.q1=127.5`。
  - 输出目录 `build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.56.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 和 README 中 `chunked_pyramid_write` 的输出侧前置能力：OME-TIFF writer 需要输出可审计的 chunked write plan / BigTIFF 决策记录，减少 generation plan 与实际 writer 报告之间的语义落差。

### 已做改动

- 版本号升级到 `v0.56.0`。
- `write_pyramid_ome_tiff()` 新增 `chunk_shape` 和 `bigtiff_threshold_bytes` 参数。
- OME-TIFF writer 的 `pyramid_report.write_mode` 现在记录为 `chunked_pyramid_write`。
- `pyramid_report.chunked_write_audit` 记录 writer backend、BigTIFF 决策、估算总字节数、chunk shape、每层 chunk grid / chunk count / edge chunk shape。
- 非法 `chunk_shape` 和非法 BigTIFF 阈值会显式报错。
- Audit 明确记录 `production_streaming=false` 和 `streaming_limitations`，避免把当前内存数组 writer 伪装成生产级 gigapixel streaming writer。
- Smoke generation 的 `generation_run.json.pyramid_report` 会保留同一份 chunked write audit，便于最终交付物审计。
- README 同步说明 OME-TIFF writer 的 chunked write audit 能力和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.56.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_records_chunked_write_audit tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_rejects_invalid_chunk_shape tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
  - TDD 红灯：新增测试最初因 `write_pyramid_ome_tiff()` 不支持 `chunk_shape`、`pyramid_report.write_mode` 仍为 `small_pyramid_smoke_writer` 而失败；实现后同一命令通过。
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_version tests.test_schemas -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：165 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.56.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.56.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `build-prior-manifest --output-dir build/validation/v0.56.0-291288/prior ... --wsi-tissue-overview build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.56.0-291288/layout_mask_prior.json --output-dir build/validation/v0.56.0-291288/sampled-layout --sample-id 291288-v056-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json --output build/validation/v0.56.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.56.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.56.0-291288/trained-checkpoint.json --output-root build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v056 --condition-packet build/validation/v0.56.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.schema_version=v0.56.0`，真实 thumbnail tissue fraction 保留为 `0.156499895`。
  - `sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `v0.56.0`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`、`production_streaming=false`、`bigtiff=false`、`estimated_total_bytes=839424`、`chunk_shape=[512, 512]`、level0 `chunk_grid=[1, 1]` 且 `chunk_count=1`。
  - `chunked_write_audit.streaming_limitations` 明确记录 `in_memory_array_writer`、`chunk_plan_is_audit_metadata_only` 和 `not_a_resume_capable_gigapixel_streaming_writer`。

## v0.55.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本为 v0.54.0 的 sampled layout mask 条件输出补齐 QC 审计，确认最终 generated mask 是否忠实保留 sampled mask 条件。

### 已做改动

- 版本号升级到 `v0.55.0`。
- `build_qc_report()` 新增可选 `sampled_layout_mask_summary` 参数。
- QC 的 `non_copy_report.metrics` 新增 `sampled_layout_mask_match_proxy`，读取 sampled layout `.npy` 与最终 generated mask 逐像素比较，记录 matched pixel fraction。
- sampled mask 与 generated mask 尺寸不一致但都是二维时，会用 nearest resize 对齐后计算匹配率。
- 缺失 sampled mask 文件、不可读 `.npy` 或非二维 mask 会显式报错。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition summary 包含 `sampled_layout_mask` 时，会把该摘要传给 QC builder。
- README 同步说明 sampled mask 条件现在有 QC match proxy 审计。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.55.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：163 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.55.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.55.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `build-prior-manifest --output-dir build/validation/v0.55.0-291288/prior ... --wsi-tissue-overview build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.55.0-291288/layout_mask_prior.json --output-dir build/validation/v0.55.0-291288/sampled-layout --sample-id 291288-v055-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json --output build/validation/v0.55.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.55.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.55.0-291288/trained-checkpoint.json --output-root build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v055 --condition-packet build/validation/v0.55.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.schema_version=v0.55.0`，真实 thumbnail tissue fraction 保留为 `0.156499895`。
  - `sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `v0.55.0`。
  - 输出目录 `build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `metadata.json` 和 `generation_run.json` 均记录 `sampled_layout_mask` 与 `wsi_tissue_overview` 条件摘要。

## v0.54.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 v0.53.0 的 `sampled_layout_mask` 从独立 artifact 接入 generation condition packet 和 smoke generation 输出，使统计型 sampled layout mask 能作为实际 mask 条件交付。

### 已做改动

- 版本号升级到 `v0.54.0`。
- `build_generation_condition_packet()` 新增可选 `sampled_layout_mask_path` 参数；CLI `build-condition-packet` 新增 `--sampled-layout-mask`。
- Condition packet 的 `artifact_inputs.sampled_layout_mask` 记录 sampled layout artifact path、kind、sample id、mask path 和 mask shape。
- Condition packet 的 `conditions.mask` 支持 `source=sampled_layout_mask`，记录 mask path、sample id、class counts/fractions 和 limitations。
- `run_smoke_generation()` 遇到 sampled layout mask 条件时读取 `.npy` mask，校验二维和 0-5 类 id，必要时 nearest resize 到输出 canvas，并写为最终 mask。
- `metadata.json` 与 `generation_run.json` 的 condition summary 记录 sampled layout mask 摘要，便于追踪最终输出 mask 来源。
- README 同步说明 sampled layout mask 现在可进入 condition packet 并驱动 smoke generation mask 输出。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.54.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning tests.test_generation_runner tests.test_layout_mask_sampler tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 对应验证 artifact 重建 v0.54 prior manifest，执行 `sample-layout-mask`、`build-condition-packet --sampled-layout-mask` 和 `run-generation --backend smoke-cascade --condition-packet`，确认最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，且 `metadata.json` / `generation_run.json` 均记录 `sampled_layout_mask` 摘要。

## v0.53.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 Phase 1 layout/mask prior 的可执行能力：把统计型 `layout_mask_prior` 转成可复现的 sampled layout mask artifact，使低 anchor / fully de novo 路径有可交付的结构条件输入。

### 已做改动

- 版本号升级到 `v0.53.0`。
- 新增 `sample_layout_mask_from_prior()`，从 `layout_mask_prior.json` 读取 6 类比例和 tile layout records，输出 `.npy` sampled layout mask 与 `sampled_layout_mask.json` manifest。
- CLI 新增 `sample-layout-mask`，支持指定输出目录、sample id、mask height/width、random seed 和可选 `wsi_tissue_overview`。
- 可选 tissue overview 会把第一条 thumbnail tissue proxy 的 tissue fraction、bounding box 和 connected component count 记录到 manifest，并用 bounding box 限定 sampled mask 的非背景 footprint。
- 输出 manifest 记录 class counts/fractions、source prior path、可选 tissue overview path 和 limitations，明确该产物不是 mask diffusion 或语义分割模型。
- README 同步新增 sampled layout mask 用法和当前边界说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/sampler.py`
- `tests/test_layout_mask_sampler.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.53.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_layout_mask_sampler tests.test_layout_mask_prior tests.test_priors tests.test_generation_conditioning tests.test_generation_runner tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 既有验证 artifact 中的真实 `wsi_tissue_overview.json` 执行 `sample-layout-mask`，生成 `build/validation/v0.53.0-291288/sampled-layout/sampled_layout_mask.npy` 与 `sampled_layout_mask.json`，确认 `tissue_overview_reference.tissue_fraction=0.156499895`、mask shape 为 `[512, 512]` 且 6 类 class counts/fractions 可读取。

## v0.52.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把已进入 generation condition summary 的 `wsi_tissue_overview` 接入 QC 报告，形成生成 mask 组织比例与真实 WSI thumbnail tissue fraction 的轻量一致性审计。

### 已做改动

- 版本号升级到 `v0.52.0`。
- `build_qc_report()` 新增可选 `wsi_tissue_overview_summary` 参数；传入时会校验 summary 基础结构。
- QC 的 `non_copy_report.metrics` 新增 `wsi_tissue_fraction_reference_proxy`，记录生成 mask tissue fraction 与真实 thumbnail tissue fraction 的接近程度。
- `wsi_tissue_fraction_reference_proxy.reference.tissue_fraction` 保留 `wsi_tissue_overview` 源 artifact 的原始数值精度，真实 SVS 验证中确认 `0.156499895` 不再被舍入为 `0.1565`。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition packet summary 包含 `wsi_tissue_overview` 时，会把该摘要传入 QC builder。
- 缺失 `wsi_tissue_overview` 时保持既有 QC 路径兼容。
- 坏的 tissue overview summary 会显式报错，不会静默写入 QC。
- README 同步说明 tissue overview 进入 QC non-copy metrics 的审计边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.52.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_records_wsi_tissue_fraction_reference_proxy tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_rejects_invalid_wsi_tissue_overview_summary tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_wsi_tissue_overview_qc_proxy -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`、组装 prior manifest、构建 condition packet，并运行 `run-generation --backend smoke-cascade --condition-packet`，确认真实 tissue overview 进入最终 QC 的 `wsi_tissue_fraction_reference_proxy`。

## v0.51.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 condition packet 中已记录的可选 `wsi_tissue_overview` 摘要继续写入 generation 交付物，使真实 WSI 低倍组织轮廓 proxy 能从 prior artifact 追踪到 `metadata.json` 和 `generation_run.json`。

### 已做改动

- 版本号升级到 `v0.51.0`。
- `run_smoke_generation()` 在 condition packet 包含 `conditions.layout.wsi_tissue_overview` 时，会把该摘要写入 `metadata["generation"]["condition_summary"]["wsi_tissue_overview"]`。
- `generation_run.json` 的 `condition_packet.summary` 会记录同一份 tissue overview 摘要，便于批量审计。
- PyTorch diffusion smoke 的 condition packet loader 同步保留该摘要，避免 smoke / torch 两条条件包摘要链路分叉。
- 缺失 `wsi_tissue_overview` 时保持既有 condition packet 兼容路径，不要求该字段。
- `tests/test_generation_runner.py` 新增 smoke generation metadata/run summary 的 tissue overview 摘要测试。
- `tests/test_torch_training.py` 新增不依赖 PyTorch 安装的 condition packet loader 摘要测试。
- README 同步说明 smoke generation 会把 tissue overview proxy 摘要保留到最终交付物。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.51.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_wsi_tissue_overview_condition_summary tests.test_torch_training.TorchSmokeTrainingTests.test_torch_condition_packet_loader_records_wsi_tissue_overview_summary -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_condition_packet tests.test_generation_conditioning.GenerationConditioningTests.test_build_generation_condition_packet_records_wsi_tissue_overview_layout_summary tests.test_priors.PriorArtifactTests.test_build_prior_manifest_from_artifacts_records_optional_wsi_tissue_overview -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`、组装 prior manifest、构建 condition packet，并运行 `run-generation --backend smoke-cascade --condition-packet`，确认真实 tissue overview 摘要进入最终 `metadata.json` 和 `generation_run.json`。

## v0.50.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 prior manifest 中可选的 `wsi_tissue_overview` 继续接入 generation condition packet，使真实 WSI 低倍组织轮廓 proxy 能进入生成条件审计链路。

### 已做改动

- 版本号升级到 `v0.50.0`。
- `build_generation_condition_packet()` 在 prior manifest 包含 `wsi_tissue_overview` 时，会读取并校验该 artifact。
- `conditions.layout.wsi_tissue_overview` 现在记录 artifact path、record count、source backend、thumbnail max size，以及每张 WSI 的 tissue fraction、bounding box 和 connected component count。
- `artifact_inputs` 继续记录可选 `wsi_tissue_overview` 的 path/hash/size，便于从 condition packet 追踪源 artifact。
- 缺失 `wsi_tissue_overview` 时保持旧路径兼容，不要求该 artifact。
- `tests/test_generation_conditioning.py` 新增带 tissue overview 的 condition packet 测试和坏 artifact 失败路径测试。
- README 同步更新 condition packet 对 tissue overview 的审计说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `tests/test_generation_conditioning.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.50.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`，通过 `build-prior-manifest --wsi-tissue-overview` 组装 prior manifest，再用 `build-condition-packet` 确认真实 tissue overview 摘要进入 `conditions.layout`。

## v0.49.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 `v0.48.0` 新增的 `wsi_tissue_overview` 接入 prior manifest，使真实 WSI 低倍组织轮廓 artifact 能被统一 manifest 追踪、校验和复现。

### 已做改动

- 版本号升级到 `v0.49.0`。
- `build_prior_manifest_from_artifacts()` 新增可选 `wsi_tissue_overview_path` 参数；传入时会校验并写入 `artifacts.wsi_tissue_overview`。
- `build-prior-manifest` CLI 新增可选 `--wsi-tissue-overview <path>`。
- `validate_prior_manifest()` 继续要求四类核心 prior artifact，同时允许可选 `wsi_tissue_overview` 并继续拒绝其它未知 artifact type。
- `wsi_tissue_overview` artifact 校验 `artifact_type=wsi_tissue_overview`，manifest metadata 记录 artifact schema version、record count、source backend 和 thumbnail max size。
- `tests/test_priors.py` 新增可选 tissue overview manifest 组装测试，并更新 CLI 构建测试覆盖 `--wsi-tissue-overview`。
- README 同步更新 prior manifest 构建说明和可选 tissue overview 追踪边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/priors/__init__.py`
- `tests/test_priors.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.49.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_priors -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`，再通过 `build-prior-manifest --wsi-tissue-overview` 确认真实 artifact 可被 prior manifest 追踪。

## v0.48.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐真实 WSI 低倍组织概览 artifact：从输入 manifest 读取真实 WSI thumbnail，输出可审计的 tissue contour proxy，为 layout/mask prior、QC 和后续 de novo layout 采样建立 WSI-level 组织轮廓基础。

### 已做改动

- 版本号升级到 `v0.48.0`。
- 新增 `src/he_wsi_generator/priors/tissue.py`，提供 `build_wsi_tissue_overview_from_manifest()`，可从 OpenSlide 或 fixture reader 读取 WSI metadata / thumbnail 并写出 `wsi_tissue_overview` JSON。
- CLI 新增 `build-wsi-tissue-overview`，支持指定 reader backend、thumbnail max size 和输出路径。
- `wsi_tissue_overview` artifact 记录 slide metadata、manifest 摘要、thumbnail RGB 统计、tissue/background pixel count、tissue fraction、bounding box 和 connected component count，并明确其不是语义分割 mask。
- 新增 `tests/test_wsi_tissue_overview.py`，覆盖函数成功路径、空白 thumbnail 显式失败和 CLI 成功路径。
- README 同步新增 WSI tissue overview 用法和边界说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/tissue.py`
- `tests/test_wsi_tissue_overview.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.48.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_wsi_tissue_overview -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 执行 `build-wsi-tissue-overview --backend openslide`，确认可写出真实 `wsi_tissue_overview.json`。

## v0.47.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐 UI 配置的 YAML 支持，让 `write-ui-config` / `launch-ui` 相关配置能按路径后缀读写 JSON/YAML，并在缺少 PyYAML 时显式报错。

### 已做改动

- 版本号升级到 `v0.47.0`。
- `src/he_wsi_generator/ui/config.py` 按路径后缀支持 JSON/YAML 读写；`.yaml` / `.yml` 路径在缺少 PyYAML 时会显式报错。
- `tests/test_ui.py` 新增 YAML roundtrip 与缺依赖失败路径测试。
- README 同步更新 UI 配置格式说明和 YAML 使用示例。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/config.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.47.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_ui tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`

## v0.46.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐输出摘要的 CLI 入口：UI controller 已有 `collect_output_summary()`，但命令行还没有一个可复现方式把 metadata + QC 汇总成稳定 JSON。

### 已做改动

- 版本号升级到 `v0.46.0`。
- CLI 新增 `inspect-output-summary --metadata <metadata.json> --qc <qc.json>`。
- `inspect-output-summary` 复用 `collect_output_summary()`，把 metadata + QC 汇总成 JSON 输出；坏输入会返回非零退出码并输出明确错误。
- 新增 CLI output summary 成功路径和坏 QC 失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.46.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_cli_inspects_output_summary tests.test_ui.UITests.test_cli_rejects_invalid_output_summary_qc -v`
- `PYTHONPATH=src python -m unittest tests.test_ui tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（137 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.45.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 执行命令的工作目录透传：`JobRunner.create_job()` 已支持 `cwd`，但 `run-local-job` 还没有暴露这个能力。

### 已做改动

- 版本号升级到 `v0.45.0`。
- `run-local-job` CLI 新增可选 `--cwd <path>`，并透传给 `JobRunner.create_job()`。
- 使用 `--cwd` 时，job record 现在会持久化 `cwd`，且命令在指定目录执行。
- 新增 `run-local-job --cwd` 成功路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.45.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_runs_local_job_with_cwd -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（135 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.44.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的批量查看入口：在 `run-local-job`、`cancel-local-job` 和 `inspect-local-job` 之外，再提供一个可复现的 list 命令，直接列出 job_root 下的持久化 job 状态。

### 已做改动

- 版本号升级到 `v0.44.0`。
- CLI 新增 `list-local-jobs <job_root>`。
- `list-local-jobs` 复用 `JobRunner.list_jobs()` 读取持久化 job record，并以 JSON 数组输出；坏记录不会被静默跳过。
- 新增 CLI list 成功路径和损坏记录失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/jobs.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.44.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_lists_local_jobs tests.test_job_runner.JobRunnerTests.test_cli_rejects_listing_corrupt_local_job_record -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（134 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.43.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的查看入口：在 `run-local-job` 和 `cancel-local-job` 之外，再提供一个可复现的 inspect 命令，把持久化 job 记录导出为 JSON，便于排障和状态查看。

### 已做改动

- 版本号升级到 `v0.43.0`。
- CLI 新增 `inspect-local-job <job_root> --job-id <id>`。
- `inspect-local-job` 复用 `JobRunner.load_job()` 读取持久化 job record；未知 job、非法 job id 或损坏 JSON 会返回非零退出码并输出明确错误。
- 成功时把完整 job record 以 JSON 输出到 stdout，便于脚本和人工查看。
- 新增 CLI inspect 成功路径、未知 job 失败路径和损坏记录失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.43.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_inspects_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_inspecting_unknown_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_inspecting_corrupt_local_job_record -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（132 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.42.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地任务取消的 CLI 入口，使已排队 job 可以通过可复现命令显式持久化为 `cancelled`。

### 已做改动

- 版本号升级到 `v0.42.0`。
- CLI 新增 `cancel-local-job <job_root> --job-id <id> [--message <message>]`。
- `cancel-local-job` 复用 `JobRunner.cancel_job()`，仅允许取消 queued job；非 queued job、未知 job 或非法 job id 会返回非零退出码并输出明确错误。
- 取消成功时写出 `job.json`、空 `stdout.txt` / `stderr.txt`，并在 stdout 输出 `local job cancelled` 和记录路径。
- 新增 CLI 取消成功路径和非 queued job 失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.42.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_cancels_queued_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_cancelling_non_queued_local_job -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（129 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.41.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐生成完成态审计：成功输出的 smoke generation 结果必须把 `tile_traversal_plan` 物化成完成态，避免把已完成样本保留为 pending 计划。

### 已做改动

- 版本号升级到 `v0.41.0`。
- 新增 `complete_tile_traversal_plan`，支持把 traversal plan 转换为完成态，并保留对部分完成状态的显式记录。
- `run_smoke_generation` 在写出 metadata 和 generation run summary 前，将 tile traversal plan 切换为完成态，成功样本现在能直接看到 `completed_tile_count`、`pending_tile_count`、`resume_index`、`next_tile_index` 和每个 tile 的完成状态。
- `run_smoke_generation` 同步把 `plan.stages` 切换为 completed，确保 generation run summary 反映真实执行态，而不是保留 planned 阶段状态。
- 新增针对 partial completion helper 的单元测试，并更新 smoke generation 端到端测试断言完成态字段。
- `build_qc_report` 现在会为 non-copy report 额外写入 thumbnail / tissue contour / mask layout / global embedding 四类 similarity proxy metrics，保留轻量审计但不做全量近邻检索。
- `build_qc_report` 还会写入 tile 级 seam score proxy 和 WSI 级 style consistency proxy，并把 tile 级 metrics 纳入 overall status。
- `run_smoke_generation` 现在会按 `canvas_size_40x` 真正拼接 1/1 canvas，再输出 pyramid 和 mask，而不是固定写死 512 方块。
- `JobRunner` 新增 `cancel_job`，可把 queued job 显式转成 `cancelled` 并持久化终态记录。
- 同步更新 README、VERSION、pyproject、默认配置和版本断言。

### 影响文件

- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_tiling.py`
- `tests/test_generation_runner.py`
- `src/he_wsi_generator/constants.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `tests/*.py`（版本字符串与断言同步到 `v0.41.0`）

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_models_generation -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（127 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`

## v0.40.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进生成输出的可审计性：把 `tile_traversal_plan` 写入 smoke generation metadata，便于从单个产物直接追溯 traversal / resume / write-region 信息。

### 已做改动

- 版本号升级到 `v0.40.0`。
- `run_smoke_generation` 在 metadata 的 `generation` 字段中写入 `tile_traversal_plan`，与 run summary 中的物化 plan 保持一致。
- `tile_traversal_plan` 直接复用 `create_generation_plan` 的输出，不在 metadata 层重建。
- 新增/更新 `tests/test_generation_runner.py`，覆盖 metadata 里的 `tile_traversal_plan`、tile count 和 tile origin。
- 更新 README 当前能力描述，说明 smoke metadata 现在也记录物化 traversal plan。
- 更新 `docs/DEMANDS.MD`，记录 v0.40.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_generation_tiling.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling -v`
- `PYTHONPATH=src python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_config_rejects_invalid_canvas_size -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_models_generation tests.test_schemas tests.test_version -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.39.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.4 中 production cascade sampler 的前置执行能力：把 `tile traversal`、`resume index` 和 `overlap weighted blending` 从 generation plan 的字符串说明推进为可测试、可审计的基础设施。

### 已做改动

- 版本号升级到 `v0.39.0`。
- 新增 `src/he_wsi_generator/generation/tiling.py`，提供 `create_tile_traversal_plan` 和 `blend_rgb_tiles`。
- `create_tile_traversal_plan` 按 40x canvas、模型 tile size 和 overlap 生成 row-major traversal plan，记录 resume index、tile 总数、已完成/待处理 tile 数、下一待处理 tile、tile origin、write region、stride、状态和 edge crop 策略。
- Traversal 对 canvas、tile size、overlap 和 resume index 做显式校验，非法输入通过 `GenerationTilingError` 报错。
- `blend_rgb_tiles` 支持按 tile origin 把多个 uint8 RGB tile 写入 canvas，并对 overlap 区域执行权重平均；非 RGB、非 uint8、非法 origin、空 tile 列表和未覆盖完整 canvas 会显式报错。
- `create_generation_plan` 新增 `tile_traversal_plan` 字段，同时保留既有 `tile_traversal`、`blending` 和 `write_mode` 字段。
- `validate_generation_config` 支持并校验可选 `canvas_size_40x`；默认生成配置写入 `[512, 512]`。
- 新增 `tests/test_generation_tiling.py`，覆盖 traversal/resume/edge crop、overlap weighted blending 和未覆盖 canvas 错误路径。
- 更新 `tests/test_models_generation.py` 和 `tests/test_schemas.py`，覆盖 generation plan 物化 traversal plan 与 `canvas_size_40x` 校验。
- README 更新 v0.39.0 当前能力、tiling/blending 基础设施和非 production 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.39.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_generation_tiling.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_accepts_trained_checkpoint_manifest -v`
- `PYTHONPATH=src python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_config_rejects_invalid_canvas_size -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_models_generation tests.test_schemas tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.38\.0|version = "0\.38\.0"|PROJECT_VERSION = "v0\.38\.0"|PACKAGE_VERSION = "0\.38\.0"' VERSION README.md pyproject.toml configs src tests`

## v0.38.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.4 的推理顺序要求：`torch-diffusion-smoke` generation backend 必须按 `1/32 -> 1/16 -> 1/4 -> 1/1` 执行级联采样，并保存每层中间状态。

### 已做改动

- 版本号升级到 `v0.38.0`。
- `run_torch_diffusion_smoke_generation` 从单次 `1/1` sampling 改为四层 cascade sampling。
- 每个 cascade level 写入独立 sample 目录和 `sample_manifest.json`。
- `1/32` 使用默认 zero previous-scale condition；`1/16`、`1/4`、`1/1` 将上一层 `sample_preview.npy` 作为 `previous_scale_condition_path` 传给 sampler。
- `generation_run.json` 和 metadata generation 字段新增 `cascade_sample_manifests`，记录每层 level、sample manifest、sample preview、cross-scale condition source 和 previous-scale path。
- OME-TIFF pyramid 由四层 cascade sample preview 分别 resize 组装，不再只从最终 `1/1` preview 派生所有层。
- Torch diffusion smoke plan stage 的 condition inputs 新增 `previous_scale_rgb_proxy` 和 `condition_feature_channels`，并记录四层状态为 completed。
- 新增/更新 `tests/test_torch_training.py`，覆盖 cascade sample manifests、metadata/run summary 记录、previous-scale path 链式传递、condition packet 在四层 sampler 中复用和 OME-TIFF 层级输出。
- README 更新四层级联 smoke generation 行为和当前非 production 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.38.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.37\.0|version = "0\.37\.0"|PROJECT_VERSION = "v0\.37\.0"|PACKAGE_VERSION = "0\.37\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.38\.0|version = "0\.38\.0"|cascade_sample_manifests|torch_diffusion_cascade_samples|previous_scale_rgb_proxy' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.37.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1 的“上一尺度图像 / latent”条件输入要求：让 PyTorch diffusion smoke denoiser 接收可审计的上一尺度 RGB proxy 条件通道。

### 已做改动

- 版本号升级到 `v0.37.0`。
- Diffusion smoke checkpoint payload、checkpoint manifest 和 sampler manifest 新增 `cross_scale_condition_schema`。
- `train_torch_diffusion_smoke_model` 在 denoiser 输入中拼接 3 个上一尺度 RGB proxy 条件通道。
- 训练期 cross-scale condition 从真实 RGB tile 构建：非根层级先降采样到上一 cascade proxy 尺度，再上采样到 latent grid；`1/32` 根层级使用显式 zero previous-scale condition。
- Denoiser input channels 与 `denoiser_architecture.input_channels` 同步包含 current latent、previous-scale RGB proxy、6 类 mask、timestep 和 7 个 condition feature channels。
- `sample_torch_diffusion_smoke_model` 新增可选 `previous_scale_condition_path`，支持读取 `.npy` RGB preview 作为 previous-scale condition；未提供时显式记录 `cross_scale_condition_source=default_zero_previous_scale`。
- CLI `sample-torch-diffusion-smoke` 新增 `--previous-scale-condition` 参数。
- Sampling 校验 checkpoint manifest/payload 中的 `cross_scale_condition_schema`，缺失或不匹配时显式报错。
- 新增/更新 `tests/test_torch_training.py`，覆盖训练 manifest/payload schema、input channel 增量、VAE latent 兼容、sampler 默认 zero source、显式 previous-scale source、CLI 参数和缺失 schema 错误路径。
- README 更新 cross-scale condition 用法、`--previous-scale-condition` 参数和 smoke-only 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.37.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_writes_proxy_preview tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_previous_scale_condition tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_rejects_missing_cross_scale_condition_schema tests.test_torch_training.TorchSmokeTrainingTests.test_cli_samples_torch_diffusion_smoke_model -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.36\.0|version = "0\.36\.0"|PROJECT_VERSION = "v0\.36\.0"|PACKAGE_VERSION = "0\.36\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.37\.0|version = "0\.37\.0"|cross_scale_condition_schema|previous_scale_condition|--previous-scale-condition|previous_scale_rgb_proxy' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.36.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1 的 `latent_diffusion_unet` 主干要求：把 PyTorch diffusion smoke denoiser 从简单卷积堆栈升级为带 downsample、bottleneck、upsample 和 skip connection 的 smoke U-Net。

### 已做改动

- 版本号升级到 `v0.36.0`。
- `_MaskConditionedLatentDenoiser` 从普通卷积堆栈升级为 smoke latent U-Net，包含 `encoder_block`、`downsample`、`bottleneck`、`upsample`、`decoder_block` 和 `output_block`。
- Smoke latent U-Net 采用 32 个 base channels、64 个 bottleneck channels、1 个 downsample stage，并通过 encoder/decoder concat skip connection 保留空间条件信息。
- Diffusion checkpoint payload 与 checkpoint manifest 新增 `denoiser_architecture`，记录 architecture 名称、base/bottleneck channels、downsample stages、skip connection 语义、input source、input/output channels、支持的 latent sources 和 smoke-only production 状态。
- `sample_torch_diffusion_smoke_model` 采样前校验 checkpoint manifest 与 payload 的 `denoiser_architecture`，缺失、不匹配或旧结构 checkpoint 会显式报错。
- Sampler manifest 新增 `denoiser_architecture`，便于审计当前 sample 使用的 denoiser 结构。
- 保持 `rgb_downsample_proxy` 和 `trainable_vae_smoke` 两条 latent 路径可用，U-Net output channels 按 latent channel 数配置。
- 新增/更新 `tests/test_torch_training.py`，覆盖架构记录、state_dict 中 U-Net block key、VAE latent output channel 兼容，以及 manifest/payload 缺失 `denoiser_architecture` 的错误路径。
- README 更新 PyTorch diffusion smoke U-Net 行为、checkpoint 架构契约和当前 smoke-only 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.36.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_rejects_missing_denoiser_architecture -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.35\.0|version = "0\.35\.0"|PROJECT_VERSION = "v0\.35\.0"|PACKAGE_VERSION = "0\.35\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.36\.0|version = "0\.36\.0"|denoiser_architecture|smoke_latent_unet|encoder_decoder_concat|smoke latent U-Net' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.35.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 v0.34.0 VAE smoke checkpoint 与 diffusion smoke 的连接：让 diffusion smoke trainer/sampler 可以选择使用 `trainable_vae_smoke` latent，而不是只能使用 `rgb_downsample_proxy`。

### 已做改动

- 版本号升级到 `v0.35.0`。
- `train_torch_diffusion_smoke_model` 新增可选 `vae_checkpoint_manifest_path` 参数。
- CLI `train-torch-diffusion-smoke` 新增 `--vae-checkpoint-manifest` 参数。
- 使用 VAE checkpoint 时，diffusion trainer 会加载并校验 VAE smoke checkpoint，通过 VAE encoder 的 `mu` 构造 latent batch。
- Diffusion checkpoint payload/manifest 在 VAE latent 路径下记录 `latent_source=trainable_vae_smoke`、`vae_checkpoint_manifest_path`、VAE checkpoint hash、latent channel 数、latent batch shape、input channels 和 output channels。
- Denoiser 输出通道从固定 3 改为按 latent channel 数配置，兼容 RGB proxy latent 和 VAE latent。
- `sample_torch_diffusion_smoke_model` 遇到 `latent_source=trainable_vae_smoke` 时加载 VAE checkpoint，通过 VAE decoder 将 sampled latent 解码成 RGB preview。
- `sample_manifest.json` 新增 `latent_sample_shape`，并在 VAE latent 路径下记录 VAE checkpoint 路径与 hash。
- 旧的 `rgb_downsample_proxy` diffusion smoke 训练/采样路径保持可用；未提供 VAE checkpoint 时不伪装为 VAE latent。
- 新增/更新 `tests/test_torch_training.py`，覆盖 VAE latent diffusion 直接训练、采样解码、CLI 训练参数和 manifest 字段。
- README 更新 VAE latent diffusion smoke 用法，并明确当前仍是 smoke 级 VAE/diffusion 闭环，不是 production WSI latent diffusion generator。
- 更新 `docs/DEMANDS.MD`，记录 v0.35.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_decodes_vae_latent_preview tests.test_torch_training.TorchSmokeTrainingTests.test_cli_trains_torch_diffusion_smoke_model_with_vae_latent -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.34\.0|version = "0\.34\.0"|PROJECT_VERSION = "v0\.34\.0"|PACKAGE_VERSION = "0\.34\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.35\.0|version = "0\.35\.0"|--vae-checkpoint-manifest|vae_checkpoint_manifest_path|trainable_vae_smoke|latent_sample_shape|vae_checkpoint_sha256' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.34.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1/7.2 的 VAE latent 缺口：新增 PyTorch VAE smoke trainer，使项目不再只有 RGB downsample proxy latent，而是具备可训练、可审计的 latent autoencoder 工程入口。

### 已做改动

- 版本号升级到 `v0.34.0`。
- 新增 `train_torch_vae_smoke_model`，从 training-index 读取真实 RGB image tile，训练小型 PyTorch VAE smoke autoencoder。
- VAE smoke trainer 包含 encoder、reparameterization 和 decoder，并真实执行 reconstruction loss + KL loss 的反向传播。
- 新增 CLI `train-torch-vae-smoke <training-index.jsonl> --output-dir <dir> --batch-size <n>`，支持 split、cascade level、epochs、learning rate、random seed、device、latent channels、latent size 和 KL weight。
- `model.pt` payload 记录 `target_type=vae_rgb_reconstruction`、`latent_source=trainable_vae_smoke`、latent channels、latent size、latent batch shape、loss histories 和 KL weight。
- `checkpoint_manifest.json` 记录 checkpoint hash、training log、latent/reconstruction preview、batch summary、loss summary 和 `usable_for_inference=false`。
- Trainer 写出 `latent_preview.npy` 与 `reconstruction_preview.npy`，用于审计 latent shape 和 smoke 重建输出。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用、checkpoint payload、manifest 字段、preview 文件形状和 CLI 行为。
- README 更新 VAE smoke training 用法，并明确当前 VAE 只验证 trainable latent autoencoder 路径，尚未接入 diffusion trainer/sampler，也不是 production WSI VAE。
- 更新 `docs/DEMANDS.MD`，记录 v0.34.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_vae_smoke_model_writes_latent_autoencoder_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_cli_trains_torch_vae_smoke_model -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.33\.0|version = "0\.33\.0"|PROJECT_VERSION = "v0\.33\.0"|PACKAGE_VERSION = "0\.33\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.34\.0|version = "0\.34\.0"|train-torch-vae-smoke|train_torch_vae_smoke_model|trainable_vae_smoke|vae_rgb_reconstruction|latent_preview|reconstruction_preview' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.33.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 6.3 与 7.1 的条件注入路径：让 PyTorch diffusion smoke denoiser 不再只记录 `generation_condition_packet`，而是把条件包中的 style、texture、coordinate、source 和 structure anchor 摘要编码为空间条件通道参与训练/采样。

### 已做改动

- 版本号升级到 `v0.33.0`。
- 新增 PyTorch diffusion smoke condition feature schema，固定记录 7 个条件特征：style seed、texture cluster、tile origin x/y、cascade level、source enabled 和 structure anchor。
- `train_torch_diffusion_smoke_model` 的 denoiser 输入从 RGB proxy latent + mask + timestep 扩展为 RGB proxy latent + mask + timestep + condition feature channels。
- 训练期 condition feature 使用 training-index tile 坐标/cascade 和零值 style/texture/source/anchor 默认策略，避免伪造 production prior。
- Checkpoint payload 和 checkpoint manifest 记录 `condition_feature_schema`，`input_channels` 同步包含 7 个 condition feature channels。
- `sample_torch_diffusion_smoke_model` 在提供 condition packet 时把条件摘要编码为 `condition_feature_vector`，并作为 constant spatial condition channels 拼接到 denoiser 输入。
- 未提供 condition packet 时，sampler 显式记录 `condition_feature_source=default_zero` 和全零 `condition_feature_vector`。
- `sample_manifest.json` 新增 `condition_feature_schema`、`condition_feature_source` 和 `condition_feature_vector`。
- Sampling 校验 checkpoint manifest/payload 的 condition feature schema，缺失或不匹配时显式报错。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 通过 sampler 使用同一份 condition feature vector，并继续保持 sampler manifest、metadata 和 generation run summary 可审计。
- 新增/更新 `tests/test_torch_training.py`，覆盖训练 manifest、checkpoint payload、sampler manifest 和 generation 中的 condition feature schema/vector。
- README 更新 PyTorch diffusion smoke condition feature channel 行为，并明确当前仍不是 production VAE latent、完整 U-Net/ControlNet 或多倍率真实条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.33.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_writes_proxy_preview tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.32\.0|version = "0\.32\.0"|PROJECT_VERSION = "v0\.32\.0"|PACKAGE_VERSION = "0\.32\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.33\.0|version = "0\.33\.0"|condition_feature_schema|condition_feature_vector|condition_feature_source|CONDITION_FEATURES|condition feature channels' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.32.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本把 v0.30.0/v0.31.0 的 `generation_condition_packet` 记录链路从 `smoke-cascade` 扩展到 PyTorch diffusion smoke sampling/generation：`sample-torch-diffusion-smoke` 和 `run-generation --backend torch-diffusion-smoke` 可以显式消费、校验并记录同一份条件包。

### 已做改动

- 版本号升级到 `v0.32.0`。
- `sample_torch_diffusion_smoke_model` 新增可选 `condition_packet_path` 和 `expected_prior_id` 参数。
- PyTorch diffusion smoke sampler 新增 condition packet 读取与校验：检查 schema version、condition packet type、必要条件对象，并在需要时检查 `prior_id`。
- `sample_manifest.json` 新增 `condition_packet_path` 和 `condition_summary`，记录 cascade level、tile origin、style seed、texture cluster、source condition 和 structure anchor 摘要。
- CLI `sample-torch-diffusion-smoke` 新增 `--condition-packet` 参数。
- `run_torch_diffusion_smoke_generation` 新增可选 `condition_packet_path` 参数，并传给 PyTorch smoke sampler。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 会要求条件包 `prior_id` 与当前 prior manifest 一致；不一致时显式报错。
- PyTorch diffusion smoke generation 的 metadata、`generation_run.json` 和 sampler `sample_manifest.json` 记录同一份 condition packet 路径与摘要。
- 未提供 condition packet 时保持既有 PyTorch diffusion smoke 行为，不伪造条件包。
- 新增/更新 `tests/test_torch_training.py`，覆盖 sampler 直接调用、sampler CLI、generation 直接调用、generation CLI、metadata/run summary/sample manifest 记录和 prior id mismatch 错误路径。
- README 更新 PyTorch diffusion smoke sampling/generation 的 `--condition-packet` 用法，并明确当前只是审计记录，不是 production layout/style/texture 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.32.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_cli_samples_torch_diffusion_smoke_model_with_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_rejects_condition_prior_mismatch -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.31\.0|version = "0\.31\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.32\.0|version = "0\.32\.0"|sample-torch-diffusion-smoke|condition_packet_path|condition_summary|--condition-packet' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.31.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 v0.30.0 条件包与生成执行链路的连接：让 `run-generation --backend smoke-cascade` 可以显式消费 `generation_condition_packet`，并把条件包路径与关键条件摘要写入 metadata 和 generation run summary。

### 已做改动

- 版本号升级到 `v0.31.0`。
- `run_smoke_generation` 新增可选 `condition_packet_path` 参数。
- CLI `run-generation` 新增可选 `--condition-packet` 参数，传给 `smoke-cascade` backend。
- Smoke generation 新增 condition packet 读取与校验：检查 schema version、condition packet type、prior id 和必要条件对象。
- 条件包 `prior_id` 与当前 prior manifest 的 `prior_id` 不一致时显式报错。
- Metadata 的 `generation` 字段新增 `condition_packet_path` 和 `condition_summary`，记录 cascade level、tile origin、style seed、texture cluster、source condition 和 structure anchor 摘要。
- `generation_run.json` 新增 condition packet 路径和同一份摘要，便于批量审计。
- 未提供 condition packet 时保持既有 smoke backend 行为，不静默伪造条件包。
- 新增/更新 `tests/test_generation_runner.py`，覆盖直接函数调用、CLI `--condition-packet`、metadata/run summary 记录和 prior id mismatch 错误路径。
- README 更新 smoke generation 记录 condition packet 的用法，并说明当前仍不是 production diffusion 条件采样。
- 更新 `docs/DEMANDS.MD`，记录 v0.31.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.30\.0|version = "0\.30\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.31\.0|version = "0\.31\.0"|--condition-packet|condition_packet_path|condition_summary|generation_condition_packet' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.30.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 6.3 的 prior 与生成模型连接：把 `prior_manifest.json` 和 generation config 解析为可审计的 generation condition packet，使 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 成为明确 JSON 条件对象。

### 已做改动

- 版本号升级到 `v0.30.0`。
- 新增 `build_generation_condition_packet`，从 generation config、prior manifest、cascade level 和 40x tile 坐标构建条件包 JSON。
- 新增 `GenerationConditionError`，将 artifact 缺失、artifact 非 JSON、artifact 类型不匹配、缺失 texture prototypes、非法 cascade level 或负坐标等错误显式暴露。
- Builder 复用 `validate_generation_config` 和 `load_prior_manifest`，继续执行 schema、artifact 文件、hash 与 size 校验。
- Builder 读取四类 artifact JSON，校验 `layout_mask_prior` / `style_prior` / `texture_prior` 的 `prior_type`，以及 `qc_reference_distribution.source`。
- Condition packet 显式记录 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition`、`structure_anchor` 和 QC reference 摘要。
- `style_seed=auto` 时采用 deterministic `random_seed` 解析并记录来源；整数 style seed 原样记录。
- `texture_token` 从 `texture_prior.texture_prototypes` 按 random seed 确定性选择，记录 cluster id、selection policy 和 representative embedding index。
- 新增 CLI `build-condition-packet <generation-config> --prior-manifest <prior_manifest.json> --output <condition_packet.json> --cascade-level <level> --tile-origin-x <x> --tile-origin-y <y>`。
- 新增 `tests/test_generation_conditioning.py`，覆盖直接函数调用、CLI 行为、condition packet 字段、auto style seed 解析、texture token 选择、source condition 和错误路径。
- README 更新 `build-condition-packet` 用法，并说明当前输出是可审计条件包契约，不是 production diffusion 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.30.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.29\.0|version = "0\.29\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.30\.0|version = "0\.30\.0"|build-condition-packet|build_generation_condition_packet|GenerationConditionError|generation_condition_packet|texture_token' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.29.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 prior artifact 汇总能力：把已可独立生成的 `layout_mask_prior`、`style_prior`、`texture_prior` 和 `qc_reference_distribution` JSON 组装为统一、可校验、可复现的 `prior_manifest.json`，减少后续训练/生成入口对手工 manifest 编写的依赖。

### 已做改动

- 版本号升级到 `v0.29.0`。
- 新增 `build_prior_manifest_from_artifacts`，从四类 prior artifact JSON 构建并写出 `prior_manifest.json`。
- Builder 复用既有 `create_prior_artifact_entry`、`save_prior_manifest` 和 `load_prior_manifest` 校验契约，继续记录 artifact path、kind、sha256、size_bytes 和 metadata。
- Builder 读取 artifact JSON 并校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type`，校验 `qc_reference_distribution` 的 `source` 和 `metrics`。
- Artifact metadata 新增 artifact type、artifact schema version、sample/embedding/cluster 等可直接审计的摘要字段。
- 新增 CLI `build-prior-manifest`，支持输出目录、prior id、dataset id、input manifest、training data version、可重复 WSI id、random seed 和四类 artifact 路径参数。
- 新增/更新 `tests/test_priors.py`，覆盖直接函数调用、CLI 行为、manifest roundtrip 校验、artifact metadata 摘要和 artifact 类型不匹配错误路径。
- README 更新 `build-prior-manifest` 用法，并说明当前只做 prior manifest 汇总，不实现 prior 采样策略或 production diffusion 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.29.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_priors -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.28\.0|version = "0\.28\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.29\.0|version = "0\.29\.0"|build-prior-manifest|build_prior_manifest_from_artifacts|prior_manifest.json|qc_reference_distribution' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.28.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `texture_prior` 的工程基础：从 embedding cache 和 cluster report 中读取真实 patch embedding 与聚类标签，构建可审计的统计型 texture prior JSON，供 prior manifest、texture/morphology 条件和后续 non-copy/global similarity QC 复用。

### 已做改动

- 版本号升级到 `v0.28.0`。
- 新增 `build_texture_prior_from_embedding_cache`，从 embedding cache 与 cluster report 构建 `texture_prior.json`。
- 新增 `TexturePriorBuildError`，将缺失 cache、cluster report 非 JSON、labels 数量不匹配、embedding dim 不匹配、cluster counts 不一致和非有限 embedding 等错误显式暴露。
- 新增 CLI `build-texture-prior --cache-dir <dir> --cache-key <key> --cluster-report <cluster-report.json> --output <texture_prior.json>`。
- Texture prior JSON 记录 schema version、prior type、embedding cache 来源、embedding metadata、cluster report summary、embedding count、embedding dim 和 cluster count。
- Texture prior JSON 记录 global embedding mean/std，以及每个 cluster 的 sample count、fraction、mean embedding、embedding std 和 representative embedding index。
- 新增 `tests/test_texture_prior.py`，覆盖直接函数调用、CLI 行为、prototype 统计、global embedding 统计、metadata 记录和 label count mismatch 错误路径。
- README 更新 `build-texture-prior` 用法，并说明当前产物是统计型 texture prior，不是 trainable texture codebook、VQ-VAE 或 morphology token sampler。
- 更新 `docs/DEMANDS.MD`，记录 v0.28.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/layout.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/priors/texture.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_texture_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.27.0|version = \"0.27.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.28.0|version = \"0.28.0\"|build-texture-prior|build_texture_prior_from_embedding_cache|TexturePriorBuildError|texture_prior|texture_prototypes" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.27.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `layout_mask_prior` 的工程基础：从 training-index 中真实读取 6 类 mask tile，构建可审计的统计型 layout/mask prior JSON，供 prior manifest、de novo layout 采样和后续 generation conditioning 复用。

### 已做改动

- 版本号升级到 `v0.27.0`。
- 新增 `build_layout_mask_prior_from_training_index`，从 training-index batch 读取真实 mask tile 并写出 `layout_mask_prior.json`。
- 新增 `LayoutMaskPriorBuildError`，将缺失 mask、非法 batch size、未知 split/level、mask 维度非法和 label mapping 不完整等 training batch 错误显式暴露。
- 新增 CLI `build-layout-mask-prior <training-index.jsonl> --batch-size <n> --output <layout_mask_prior.json>`，支持 `--split` 和 `--cascade-level`。
- Layout/mask prior JSON 记录 schema version、prior type、training-index 来源、batch size、split、cascade level、sample ids、WSI ids、tile records、mask batch shape、mask class ids 和 batch summary。
- Layout/mask prior JSON 记录 6 类名称、每类 pixel count、fraction、present flag、non-background fraction 和 tile-level dominant class。
- Layout/mask prior JSON 记录每个 tile 的 class fractions、source WSI id，并统计横向/纵向相邻类别 pair counts。
- 输出不写入完整 `mask_batch`，避免把训练 mask 数组直接塞进 prior JSON。
- 新增 `tests/test_layout_mask_prior.py`，覆盖直接函数调用、CLI 行为、统计字段、tile-level layout records、adjacency counts 和缺失 mask 错误路径。
- README 更新 `build-layout-mask-prior` 用法，并说明当前产物是统计型 layout/mask prior，不是可采样 layout generator、mask diffusion 或 source-anchor layout mixing 模型。
- 更新 `docs/DEMANDS.MD`，记录 v0.27.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/layout.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_layout_mask_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.26.0|version = \"0.26.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.27.0|version = \"0.27.0\"|build-layout-mask-prior|build_layout_mask_prior_from_training_index|LayoutMaskPriorBuildError|layout_mask_prior|adjacency_counts" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.26.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `global_imaging_style_prior` 的工程基础：从 training-index 中真实读取 RGB tile，构建可审计的统计型 `style_prior` JSON，供 prior manifest 和后续 generation style conditioning 复用。

### 已做改动

- 版本号升级到 `v0.26.0`。
- 新增 `build_style_prior_from_training_index`，从 training-index batch 读取真实 RGB image tile 并写出 `style_prior.json`。
- 新增 `StylePriorBuildError`，将缺失 WSI、非法 batch size、未知 split/level、无法读取 RGB tile 等 training batch 错误显式暴露。
- 新增 CLI `build-style-prior <training-index.jsonl> --batch-size <n> --output <style_prior.json>`，支持 `--split` 和 `--cascade-level`。
- Style prior JSON 记录 schema version、prior type、training-index 来源、batch size、split、cascade level、sample ids、WSI ids、tile records、image batch shape/dtype 和 batch summary。
- Style prior JSON 记录 RGB mean/std/min/max、归一化 mean/std，以及每个 tile 的 mean RGB 和 source WSI id。
- 输出不写入完整 `image_batch`，避免把训练图像数组直接塞进 prior JSON。
- 新增 `tests/test_style_prior.py`，覆盖直接函数调用、CLI 行为、统计字段、tile-level style records 和缺失 WSI 错误路径。
- README 更新 `build-style-prior` 用法，并说明当前产物是统计型 style prior，不是 trainable style encoder、VAE style latent 或风格迁移模型。
- 更新 `docs/DEMANDS.MD`，记录 v0.26.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_style_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.25.0|version = \"0.25.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.26.0|version = \"0.26.0\"|build-style-prior|build_style_prior_from_training_index|StylePriorBuildError|style_prior|mean_rgb_normalized" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.25.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进完整生成输出链路：在已有 PyTorch diffusion smoke sampler 基础上，新增 `torch-diffusion-smoke` generation backend，使 PyTorch sampler 输出能够进入 OME-TIFF、mask、metadata、QC 和 batch index 归档链路。

### 已做改动

- 版本号升级到 `v0.25.0`。
- 新增 `run_torch_diffusion_smoke_generation`，用于从 generation config、prior manifest、diffusion smoke checkpoint 和 training-index 生成完整 smoke sample 对象。
- CLI `run-generation` 新增 backend 选择 `torch-diffusion-smoke`。
- `run-generation` 新增 `--training-index` 和 `--batch-size` 参数，`torch-diffusion-smoke` backend 缺少 `--training-index` 时显式报错。
- Backend 调用 `sample_torch_diffusion_smoke_model`，复用 generation config 中的 `sample_steps` 和 `random_seed`。
- Backend 读取 sampler 的 `sample_preview.npy`，用 nearest resize 构造 `1/1`、`1/4`、`1/16`、`1/32` 四层小型 pyramid。
- Backend 从 training-index batch 读取 mask，写出与 `1/1` 输出对齐的 `.npy` mask。
- Backend 复用现有 `write_pyramid_ome_tiff`、`write_mask_array`、`build_qc_report` 和 `archive_sample` 写出 OME-TIFF、mask、metadata、QC、batch index 和 generation run summary。
- Metadata 记录 `generation_backend=torch-diffusion-smoke`，generation run summary 记录 sample manifest 路径。
- QC non-copy report 记录该 backend 是 PyTorch diffusion smoke backend，不是 production WSI diffusion generator。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用和 CLI 行为，验证 metadata、QC、batch index、sample manifest、OME-TIFF pyramid shape 和 backend 标记。
- README 更新 `torch-diffusion-smoke` generation 用法和当前仍未实现 production inference、VAE decode、tile stitching、gigapixel chunked OME-TIFF 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.25.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend torch-diffusion-smoke --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/torch-diffusion-run/checkpoint_manifest.json" --training-index "$tmpdir/training-index.jsonl" --output-root "$tmpdir/generated/gen-torch-smoke" --generated-id gen-torch-smoke --batch-size 1`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.24.0|version = \"0.24.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.25.0|version = \"0.25.0\"|torch-diffusion-smoke|run_torch_diffusion_smoke_generation|sample_manifest_path|training-index" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.24.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进推理/采样链路：在已有 DDPM-style diffusion smoke trainer 基础上，新增一个可审计的 PyTorch diffusion smoke sampler，用于验证 checkpoint 加载、mask 条件输入、反向 DDPM-style 采样和 preview 输出链路。

### 已做改动

- 版本号升级到 `v0.24.0`。
- 新增 `sample_torch_diffusion_smoke_model`，支持从 diffusion smoke checkpoint manifest 和 training-index mask 条件执行 proxy latent smoke sampling。
- 新增 CLI `sample-torch-diffusion-smoke <checkpoint_manifest.json> <training-index.jsonl> --output-dir <dir> --batch-size <n>`。
- Sampler 校验 checkpoint manifest 必须为 `torch-smoke-mask-conditioned-latent-diffusion` 且 `target_type=diffusion_noise`。
- Sampler 读取 checkpoint payload，恢复 `_MaskConditionedLatentDenoiser` 的 `state_dict`，复用 `linear_ddpm` schedule 和 `rgb_downsample_proxy` latent shape。
- Sampler 通过 `load_training_batch(..., include_image=False)` 读取 mask 条件，并构造下采样 6 类 mask 条件和 timestep channel。
- Sampler 执行反向 DDPM-style smoke update，输出 `sample_preview.npy` 和 `sample_manifest.json`。
- `sample_manifest.json` 记录 sampling backend、checkpoint 来源、sample path、shape、dtype、sample steps、random seed、diffusion schedule、batch summary，并明确 `usable_for_production=false`。
- 新增 checkpoint manifest/payload/schedule 校验，缺失 checkpoint、非 diffusion smoke checkpoint、非法 sample steps、sample steps 超过 diffusion timesteps 或 schedule 不合法时显式报错。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用、CLI 行为、preview `.npy` shape/dtype、sample manifest 字段和 non-production 标记。
- README 更新 diffusion smoke sampling 用法和当前仍未实现 production sampler、VAE decoder、`run-generation` 接入、OME-TIFF 输出的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.24.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli sample-torch-diffusion-smoke "$tmpdir/torch-diffusion-run/checkpoint_manifest.json" "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-diffusion-sample" --batch-size 2 --split train --cascade-level 1/1 --sample-steps 4`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.23.0|version = \"0.23.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.24.0|version = \"0.24.0\"|sample-torch-diffusion-smoke|sample_torch_diffusion_smoke_model|torch-smoke-mask-conditioned-latent-diffusion-sampler|sample_preview|usable_for_production" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.23.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 M5 中的 latent diffusion 训练目标：在已有 RGB training batch 与 PyTorch smoke training 基础上，新增一个真实执行 DDPM-style 加噪和噪声预测 loss 的 mask-conditioned latent diffusion smoke trainer。

### 已做改动

- 版本号升级到 `v0.23.0`。
- 新增 `train_torch_diffusion_smoke_model`，用于从 training-index 执行 PyTorch diffusion smoke training。
- 新增 CLI `train-torch-diffusion-smoke`，支持 `--diffusion-timesteps`、`--beta-start`、`--beta-end` 和 `--latent-size`。
- Trainer 继续通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch。
- 新增下采样 RGB proxy latent 构造，manifest 中记录 `latent_source=rgb_downsample_proxy`，避免伪装成 VAE latent。
- 新增线性 DDPM smoke schedule，记录 `scheduler=linear_ddpm`、`timesteps`、`beta_start`、`beta_end` 和 `latent_batch_shape`。
- 训练输入包含 noisy latent、下采样 6 类 mask 条件和 timestep channel，训练目标为加入的噪声，loss 名称为 `mse_noise_prediction`。
- 新增极小 mask-conditioned latent denoiser，真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 `.pt` checkpoint 写出。
- `model.pt` payload 和 `checkpoint_manifest.json` 新增 `target_type=diffusion_noise`、`input_channels=10`、`output_channels=3`、diffusion schedule 与 image batch summary。
- Checkpoint manifest 继续明确 `usable_for_inference=false`，说明它不是 VAE latent diffusion generator。
- PyTorch 缺失错误信息泛化为 torch training commands，覆盖两个 PyTorch 训练命令。
- `tests/test_torch_training.py` 新增直接函数和 CLI 覆盖，断言 backend、diffusion target、scheduler、latent shape、checkpoint payload、image batch summary 和 finite loss。
- README 更新 PyTorch diffusion smoke training 用法和当前仍未实现 production latent diffusion U-Net、VAE latent、采样器、多倍率条件注入、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.23.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-diffusion-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-diffusion-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01 --diffusion-timesteps 8 --latent-size 64`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.22.0|version = \"0.22.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.23.0|version = \"0.23.0\"|train-torch-diffusion-smoke|torch-smoke-mask-conditioned-latent-diffusion|diffusion_noise|linear_ddpm|mse_noise_prediction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.22.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 PyTorch 训练链路：把 `train-torch-smoke` 从只训练 mask autoencoder，升级为消费 RGB image tile 的 mask-conditioned RGB reconstruction smoke backend，使训练 loop 开始学习 mask 条件到 H&E 图像像素的映射。

### 已做改动

- 版本号升级到 `v0.22.0`。
- `train_torch_smoke_model` 改为调用 `load_training_batch(..., include_image=True)`，训练前同时读取 mask batch 与 RGB image batch。
- PyTorch smoke backend 名称升级为 `torch-smoke-mask-conditioned-rgb-reconstructor`。
- 训练输入从 mask one-hot tensor 构造，训练目标从 RGB image tile 转为 `[0, 1]` 浮点 tensor。
- 模型从 mask autoencoder 改为极小的 mask-conditioned RGB reconstructor，输出 3 通道 sigmoid RGB，并使用 `mse_rgb_reconstruction` loss。
- `model.pt` payload 新增 `target_type=rgb_image`、`input_channels=6`、`output_channels=3` 和 `image_dtype`。
- `checkpoint_manifest.json` 新增 target type、输入/输出通道、loss 名称和 image batch summary，并继续明确 `usable_for_inference=false`。
- `tests/test_torch_training.py` 改为生成真实 fixture RGB slide，覆盖 backend 名称、RGB target、image batch summary、checkpoint payload 和 CLI 行为。
- 去除测试夹具中 Pillow 已弃用的 `mode` 参数，避免新版本 Pillow 输出 deprecation warning。
- README 更新 PyTorch smoke training 当前语义和仍未实现 latent diffusion、VAE latent、生产级图像重建/扩散损失、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.22.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-rgb-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.21.0|version = \"0.21.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.22.0|version = \"0.22.0\"|torch-smoke-mask-conditioned-rgb-reconstructor|target_type|image_batch_shape|mse_rgb_reconstruction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.21.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实图像训练输入能力：在 training batch loader 中新增可选 RGB image tile 读取，使后续 PyTorch 图像生成训练不再只有 mask 条件输入。

### 已做改动

- 版本号升级到 `v0.21.0`。
- `load_training_batch` 新增 `include_image` 参数，默认保持只读 mask，显式启用时读取 RGB image tile。
- Training batch loader 使用 training-index 中的 `wsi_path`、tile 坐标和 source backend 读取图像 tile。
- 对 `fixture-image` backend，使用 Pillow 读取 PNG/TIFF 等小图并裁剪 RGB tile。
- 对 `openslide` backend，使用 OpenSlide `read_region` 读取 level0 tile 并转为 RGB。
- Loader 输出新增 `image_batch`、`image_batch_shape` 和 `image_dtype`。
- `training_batch_summary` 会排除完整 `mask_batch` 和 `image_batch` 数组，只保留 shape、dtype 和审计字段。
- 缺失 WSI 文件、图像不可读、tile 超出图像范围、未知 backend 或 OpenSlide 缺依赖时显式报错。
- CLI `inspect-training-batch` 新增 `--include-image`，用于训练前同时审计 mask 和 RGB tile 输入。
- `pyproject.toml` 中 `training` 和 `torch` 可选依赖补充 `Pillow>=9.0`。
- 新增/更新 `tests/test_training_batch.py`，覆盖 fixture image tile 读取、summary 不写完整 image batch、缺失 WSI 报错和 CLI `--include-image` 行为。
- 更新 README，说明 RGB/mask training batch loader 用法和当前仍未实现 VAE latent、图像重建损失、stain normalization、OpenSlide 多层采样策略的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.21.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training_batch.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_batch -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-training-batch "$tmpdir/training-index.jsonl" --batch-size 2 --split train --cascade-level 1/1 --include-image --output "$tmpdir/batch-summary.json"`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.21.0|version = \"0.21.0\"|include-image|image_batch_shape|image_dtype|RGB/mask training batch" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.20.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实 PyTorch 训练 backend：在既有 training-index batch loader 基础上，新增一个真实调用 PyTorch 的 smoke training backend，用于验证训练 loop、loss、optimizer、checkpoint 写出和 manifest 记录链路。

### 已做改动

- 版本号升级到 `v0.20.0`。
- 新增 `he_wsi_generator.models.torch_training` 模块，提供 `train_torch_smoke_model` 和 `TorchTrainingError`。
- 新增 `torch-smoke-mask-autoencoder` backend，真实执行 `torch.nn.Module`、cross entropy loss、AdamW optimizer、反向传播和权重更新。
- Trainer 复用 `load_training_batch` 读取 training-index batch，并将 `.npy` mask batch 转成 torch tensor 和 one-hot 输入。
- Trainer 写出 `model.pt`、`training_log.jsonl`、`training_run.json` 和 `checkpoint_manifest.json`。
- Checkpoint manifest 记录 `training_backend`、`torch_version`、training parameters、loss summary、batch summary、checkpoint path 和 sha256。
- Smoke checkpoint 明确 `status=trained` 且 `usable_for_inference=false`，避免伪装成真实 latent diffusion 推理权重。
- PyTorch 未安装时，trainer 会显式报错，不静默回退到 numpy。
- CLI 新增 `he-wsi-gen train-torch-smoke <training-index.jsonl> --output-dir <dir> --batch-size <n>`，支持 `--split`、`--cascade-level`、`--epochs`、`--learning-rate`、`--random-seed` 和 `--device`。
- `pyproject.toml` 新增可选依赖组 `torch = ["numpy>=1.24", "torch>=2.5"]`。
- 新增 `tests/test_torch_training.py`，覆盖 PyTorch smoke trainer 产物、manifest 校验和 CLI 行为；无 torch 环境中真实 torch 用例会跳过。
- 更新 README，说明 PyTorch smoke training 用法和仍未实现 diffusion U-Net、噪声调度、VAE latent、图像重建、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.20.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-smoke-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.20.0|version = \"0.20.0\"|train-torch-smoke|TorchTrainingError|train_torch_smoke_model|torch-smoke-mask-autoencoder" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.19.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实 PyTorch 训练 backend 的前置输入能力：新增 training-index batch loader，使后续训练 loop 可以从 JSONL 样本索引读取、校验、抽样并形成可审计 batch，而不是只停留在索引文件。

### 已做改动

- 版本号升级到 `v0.19.0`。
- 新增 `he_wsi_generator.models.training_batch` 模块，提供 `load_training_batch`、`training_batch_summary`、`write_training_batch_summary` 和 `TrainingBatchError`。
- Batch loader 支持从 training-index JSONL 读取样本，并按可选 `split` 和 `cascade_level` 过滤。
- Loader 读取 `.npy` mask，按 training-index tile 坐标裁剪 batch mask，并按 label mapping 转成项目 6 类 id。
- Loader 输出包含 schema version、batch size、sample ids、cascade levels、WSI ids、tile records、mask batch shape、mask class ids、conditioning 和 source records。
- 对空 training-index、非法 JSON、缺失字段、非法 batch size、未知 split、未知 cascade level、缺失 mask、非法 mask 维度、非整数 mask id 和 tile 越界显式报错。
- 新增 CLI `he-wsi-gen inspect-training-batch <training-index.jsonl> --batch-size <n> --output <summary.json>`，支持 `--split` 和 `--cascade-level`。
- `pyproject.toml` 新增可选依赖组 `training = ["numpy>=1.24"]`。
- 新增 `tests/test_training_batch.py`，覆盖 batch 读取和 class id 映射、缺失 mask 报错和 CLI summary 写出。
- 更新 README，说明训练 batch loader 用法和当前仍未实现 PyTorch Dataset/DataLoader、GPU tensor、loss 和 checkpoint 权重更新的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.19.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training_batch.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_batch -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-training-batch "$tmpdir/training-index.jsonl" --batch-size 2 --split train --cascade-level 1/1 --output "$tmpdir/batch-summary.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.19.0|version = \"0.19.0\"|inspect-training-batch|TrainingBatchError|load_training_batch|training batch" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.18.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 PySide6 本地控制台所需的长任务调度基础：新增可持久化本地 job runner，使 CLI/core 工作流能被创建为 job、同步执行、记录 stdout/stderr、保存状态和结果，供 UI 后续调用。

### 已做改动

- 版本号升级到 `v0.18.0`。
- 新增 `he_wsi_generator.ui.jobs` 模块，提供 `JobRunner` 和 `JobRunnerError`。
- `JobRunner` 支持创建本地 job 目录，持久化 `job.json`、`stdout.txt` 和 `stderr.txt`。
- Job record 记录 `queued`、`running`、`completed`、`failed`、`cancelled` 状态集合中的状态，以及 command、cwd、created/updated/started/finished 时间戳、return code 和消息。
- 空 job id、包含路径分隔符的 job id、空命令、重复 job id、未知 job id、非法状态和损坏 JSON record 会显式报错。
- 命令返回非零时 job 状态落盘为 `failed`；命令启动失败时也会写入 stderr 并落盘为 `failed`，避免遗留 stale `running` 状态。
- CLI 新增 `he-wsi-gen run-local-job <job_root> --job-id <id> -- <command...>`，用于创建并同步执行一个本地 job。
- `run-local-job` 成功时输出 job record 路径并返回 0；job 失败或参数非法时返回非零退出码。
- 新增 `tests/test_job_runner.py`，覆盖成功 job、非零退出 job、命令启动失败、重复 job 拒绝和 CLI 行为。
- 更新 README，说明本地 job runner 用法和当前不支持 daemon、并发队列、取消执行、跨机器调度或 PySide6 事件循环绑定。
- 更新 `docs/DEMANDS.MD`，记录 v0.18.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/ui/__init__.py`
- `src/he_wsi_generator/ui/jobs.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-local-job "$tmpdir/jobs" --job-id job-smoke -- python -c "print('job smoke')"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.18.0|version = \"0.18.0\"|run-local-job|JobRunner|JobRunnerError|local job" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.17.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `qc_reference_distribution` 的自动生成能力：从一组训练/参考 QC JSON 抽取数值 metrics，估计区间阈值并输出可作为 prior artifact 使用的 reference distribution JSON。

### 已做改动

- 版本号升级到 `v0.17.0`。
- 新增 `he_wsi_generator.qc.reference` 模块。
- 新增 `build_qc_reference_distribution`，输入为多个 QC report、metric 名称列表、输出 JSON 路径和最小样本数。
- Builder 复用现有 QC schema 校验，显式拒绝空输入、空 metric 列表、非法 min samples、缺失 metric 和样本数不足。
- 输出 JSON 包含 schema version、创建时间、来源、总样本数和 `metrics` 对象。
- 每个 metric 记录 `warning_min`、`warning_max`、`fail_min`、`fail_max`、`sample_count`、observed min/max 和 estimator 名称。
- 当前估计器使用 observed min/max 作为 warning 边界，并按 observed range 扩展 fail 边界，保持结果直接可解释。
- CLI 新增 `he-wsi-gen build-qc-reference <qc...> --metric <name> --output <qc_reference_distribution.json>`，支持重复 `--metric` 和 `--min-samples`。
- 新增 `tests/test_qc_reference.py`，覆盖 reference distribution 写出、缺失 metric 报错和 CLI 行为。
- 更新 README，说明 `build-qc-reference` 用法和估计器边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.17.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference "$tmpdir/qc-1.json" "$tmpdir/qc-2.json" "$tmpdir/qc-3.json" --metric mean_red --metric mask_tissue_fraction --output "$tmpdir/qc_reference_distribution.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.17.0|version = \"0.17.0\"|build-qc-reference|build_qc_reference_distribution|QCReferenceBuildError|observed_min_max_with_range_margin" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.16.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进自动 QC 的训练分布自适应阈值能力：让 QC engine 使用 prior artifact 中的 `qc_reference_distribution` 对已计算指标进行 warning/fail 判定，而不是只使用固定规则。

### 已做改动

- 版本号升级到 `v0.16.0`。
- `build_qc_report` 新增可选 `qc_reference_distribution` 参数。
- 新增 `QCReferenceError`，用于显式报告 reference distribution 格式非法、阈值非数值或边界顺序不合法。
- 支持 JSON reference distribution 格式：`{"metrics": {"metric_name": {"warning_min": number, "warning_max": number, "fail_min": number, "fail_max": number}}}`。
- 对数值 QC metric 应用 reference 阈值：超出 fail 区间为 `fail`，超出 warning 区间为 `warning`，否则为 `pass`。
- 被 reference 阈值判定的 metric 会记录 `reference` 字段，包含 warning/fail 边界和 `source=qc_reference_distribution`。
- `run-generation` 自动从 prior manifest 的 `qc_reference_distribution` artifact 读取 JSON，并传入 QC engine。
- 新增测试覆盖 reference 阈值 warning/fail、非法阈值报错，以及端到端 smoke generation 使用 prior reference。
- 更新 README，说明当前支持消费 reference distribution，但尚不自动估计训练分布阈值。
- 更新 `docs/DEMANDS.MD`，记录 v0.16.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.16.0|version = \"0.16.0\"|qc_reference_distribution|QCReferenceError|reference distribution|warning_min" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.15.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进自动 QC 的真实指标能力：从只检查文件存在，扩展为读取生成 OME-TIFF 和 mask，输出 WSI/tile/mask-region 三级可解释指标，为后续真实生成样本筛选建立基础。

### 已做改动

- 版本号升级到 `v0.15.0`。
- 增强 `he_wsi_generator.qc.engine.build_qc_report`。
- QC engine 读取 OME-TIFF pyramid 首层，记录 `wsi_readable`、实际 level count、RGB 均值和 `rgb_dynamic_range`。
- QC engine 新增 tile 级轻量指标：`sharpness_laplacian_proxy` 和 `tile_proxy_sample_count`。
- QC engine 读取 `.npy` mask，记录 `mask_readable`、`mask_classes_present`、`mask_unique_class_ids`、`mask_shape_matches_wsi` 和 `mask_tissue_fraction`。
- OME-TIFF 不可读、mask 不可读、mask 维度非法或 mask 与 WSI 首层尺寸不一致时，QC 显式 fail。
- 低动态范围、空组织比例等非硬错误场景返回 warning，避免静默通过。
- 新增 QC 单元测试，覆盖真实 OME-TIFF/mask 指标写入和 mask-WSI 尺寸错位 fail。
- 更新 README，说明当前 QC 指标能力和训练分布自适应阈值未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.15.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.15.0|version = \"0.15.0\"|sharpness_laplacian_proxy|mask_shape_matches_wsi|rgb_dynamic_range|mask_tissue_fraction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.14.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实训练 backend 的前置能力：把输入 manifest、manifest audit 和 label mapping 转成四层 cascade training-index JSONL，使后续 PyTorch latent diffusion 训练 loop 有可审计的训练样本输入。

### 已做改动

- 版本号升级到 `v0.14.0`。
- 新增 `he_wsi_generator.models.training_index` 模块。
- 新增 `build_training_index`，输入为 input manifest、manifest audit、一个或多个 label mapping、输出 JSONL 路径。
- Training index builder 复用现有 manifest 和 label mapping schema 校验。
- Builder 显式拒绝缺失 audit record、audit status 非 `ok`、缺失 mapped/validated mask annotation、缺失匹配 label mapping、mask 文件不存在和无法切出完整 40x tile 的输入。
- 每条 JSONL 记录包含 dataset、WSI、split、cancer type、cascade level、40x tile 坐标、source metadata、mask annotation、6 类 label mapping 和 conditioning 约定。
- 对每个完整 512x512 40x tile 写出 `1/32`、`1/16`、`1/4`、`1/1` 四层记录，保持与生成模型级联训练顺序一致。
- CLI 新增 `he-wsi-gen build-training-index <manifest> --audit <audit.json> --label-mapping <mapping.json> --output <training-index.jsonl>`，并支持重复传入 `--label-mapping`。
- 新增 `tests/test_training_index.py`，覆盖 training index 写出、缺失 label mapping 拒绝和 CLI 行为。
- 更新 README，说明 training index 用法和真实 PyTorch 训练尚未实现的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.14.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training_index.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_index -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli build-training-index "$tmpdir/manifest.json" --audit "$tmpdir/audit.json" --label-mapping "$tmpdir/label-mapping.json" --output "$tmpdir/training-index.jsonl"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.14.0|version = \"0.14.0\"|build-training-index|build_training_index|TrainingIndexError|training-index" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.13.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进完整核心系统中的“可运行生成任务”缺口：在既有 schema、prior、checkpoint、OME-TIFF、mask、metadata、QC 和 batch index 基础上，新增明确标记的端到端 smoke generation backend，用于验证生成任务可以产出完整 WSI 数据对象。

### 已做改动

- 版本号升级到 `v0.13.0`。
- 新增 `he_wsi_generator.generation.executor` 模块。
- 新增 `run_smoke_generation`，接收 generation config、prior manifest、trained checkpoint manifest、output root 和 generated id。
- Executor 复用 `create_generation_plan` 校验，显式拒绝未训练 checkpoint、缺失 prior artifact 或非法 generation config。
- 新增 `smoke-cascade` backend，按 `1/32 -> 1/16 -> 1/4 -> 1/1` 构造可审计四层 cascade smoke 输出，并以 `1/1 -> 1/4 -> 1/16 -> 1/32` 顺序写出 OME-TIFF pyramid。
- 生成输出新增完整样本目录：`generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`batch.jsonl` 和 `generation_run.json`。
- Metadata 记录 `generation_backend=smoke-cascade`、prior/checkpoint 路径、prior id、cascade、seed、anchor、采样步数和 overlap，避免把 smoke backend 伪装为真实 diffusion 输出。
- CLI 新增 `he-wsi-gen run-generation <generation-config> --backend smoke-cascade --prior-manifest <prior_manifest.json> --checkpoint-manifest <checkpoint_manifest.json> --output-root <dir> --generated-id <id>`。
- 新增 `tests/test_generation_runner.py`，覆盖端到端输出、未训练 checkpoint 拒绝和 CLI 生成行为。
- 更新 README，说明端到端 smoke generation 用法和真实 diffusion 未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.13.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.13.0|version = \"0.13.0\"|run-generation|smoke-cascade|run_smoke_generation|GenerationExecutionError" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.12.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M7：PySide6 本地单页控制台，为数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出查看建立可复现的 UI 配置与控制层。

### 已做改动

- 版本号升级到 `v0.12.0`。
- 新增 `he_wsi_generator.ui` 模块。
- 新增 UI config 创建、保存、读取和校验能力，覆盖 `data_input`、`label_mapping`、`prior_model`、`generation_parameters`、`task_status` 和 `qc_output` 六个单页控制台区域。
- 新增 job state store，支持 `queued`、`running`、`completed`、`failed`、`cancelled`，并对空 job id 或非法状态显式报错。
- 新增 output summary 读取能力，从 metadata/QC JSON 提取 `generated_id`、总体 QC 状态、三级 QC 状态和核心输出路径。
- 新增可选 PySide6 单页控制台入口；若未安装 PySide6，`launch-ui` 明确报错并提示安装 `.[ui]`。
- CLI 新增 `he-wsi-gen write-ui-config <output>`，用于写出默认 UI 配置 JSON。
- CLI 新增 `he-wsi-gen launch-ui --config <ui-config.json>`，用于启动可选 PySide6 本地控制台。
- `pyproject.toml` 新增可选依赖组 `ui`，包含 `PySide6>=6.7`。
- 新增 M7 单元测试，覆盖 UI config roundtrip、任务状态、输出摘要、CLI config 写出和 PySide6 缺依赖错误。
- 更新 README，说明 M1-M7 当前能力、UI CLI 用法、可选依赖和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M7 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/__init__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/__init__.py`
- `src/he_wsi_generator/ui/config.py`
- `src/he_wsi_generator/ui/controller.py`
- `src/he_wsi_generator/ui/pyside_app.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_ui -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli write-ui-config "$tmpdir/ui-config.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.12.0|version = \"0.12.0\"|write-ui-config|launch-ui|create_default_ui_config|JobStateStore|UIUnavailableError" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.11.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M6：OME-TIFF 与 QC，建立小尺寸 pyramid 写出、QC JSON 和 batch JSONL 归档基础。

### 已做改动

- 版本号升级到 `v0.11.0`。
- 新增 `he_wsi_generator.outputs` 模块。
- 新增小尺寸 pyramid OME-TIFF smoke writer，使用 `tifffile` 写出多层 pyramid TIFF 并验证层级尺寸。
- 新增 6 类 mask `.npy` 输出和 mask metadata 写出。
- 新增 `he_wsi_generator.qc` 模块，构建 WSI/tile/mask-region 三级 QC JSON 和轻量 non-copy report。
- 新增 `he_wsi_generator.metadata` 模块，支持 per-WSI metadata 写出、batch JSONL 追加和单样本归档。
- CLI 新增 `he-wsi-gen archive-sample <output-root> --metadata <metadata.json> --qc <qc.json>`。
- `pyproject.toml` 新增可选依赖组 `outputs`，包含 `numpy` 和 `tifffile`。
- 新增 M6 单元测试，覆盖 pyramid OME-TIFF smoke 写出与读取、QC JSON 校验、metadata 写出、batch JSONL 追加和 CLI 归档行为。
- 更新 README，说明 M6 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M6 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/metadata/__init__.py`
- `src/he_wsi_generator/metadata/archive.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `src/he_wsi_generator/outputs/masks.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.11.0|version = \"0.11.0\"|archive-sample|write_pyramid_ome_tiff|build_qc_report|archive_sample" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.10.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M5：训练与生成骨架，为后续真实 latent diffusion 训练和级联生成提供可审计入口。

### 已做改动

- 版本号升级到 `v0.10.0`。
- 新增 `he_wsi_generator.models` 模块，提供训练 run 初始化和 checkpoint manifest 读取/校验。
- 新增训练 run manifest，记录 model family、prior manifest、training index、random seed、cascade levels、tile size、训练阶段和输出路径。
- 新增 checkpoint manifest placeholder，明确状态为 `not_trained` 且 `usable_for_inference=false`，避免伪装成真实模型权重。
- 新增 `he_wsi_generator.generation` 模块，提供四层 cascade generation plan。
- Generation plan 记录 `1/32 -> 1/16 -> 1/4 -> 1/1` 生成顺序、tile traversal、resume index、overlap、blending 和 write mode。
- Generation plan 拒绝未训练 checkpoint、缺失 prior manifest、非法 cascade 或 source-anchored 配置缺 source。
- CLI 新增 `he-wsi-gen init-training-run <training-config>`。
- CLI 新增 `he-wsi-gen plan-generation <generation-config> --prior-manifest <prior_manifest.json> --checkpoint-manifest <checkpoint_manifest.json> --output <generation-plan.json>`。
- 新增 M5 单元测试，覆盖 training manifest、未训练 checkpoint、generation plan、非法 checkpoint 和 CLI 行为。
- 更新 README，说明 M5 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M5 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_models_generation -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.10.0|version = \"0.10.0\"|init-training-run|plan-generation|create_training_run|create_generation_plan" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.9.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M4：prior artifact，为 layout/style/texture/QC priors 建立统一 manifest、文件校验和可追溯基础。

### 已做改动

- 版本号升级到 `v0.9.0`。
- 新增 `he_wsi_generator.priors` 模块。
- 新增 prior artifact manifest 创建、保存、读取与校验能力。
- Prior manifest 记录 `prior_id`、版本、创建时间、训练输入、随机种子和 artifact 清单。
- Artifact 清单要求覆盖 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`。
- 每个 artifact 记录路径、kind、sha256、size_bytes 和 metadata。
- 校验 manifest 时显式拒绝缺失 artifact、缺失文件、hash 不匹配、非法 seed、非法 artifact type 和重复路径。
- CLI 新增 `he-wsi-gen validate-prior-manifest <prior_manifest.json>`。
- 新增 M4 单元测试，覆盖 manifest roundtrip、缺失必需 artifact、hash mismatch、重复路径和 CLI 校验。
- 更新 README，说明 M4 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M4 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.9.0|version = \"0.9.0\"|validate-prior-manifest|PriorArtifactError|create_prior_artifact_entry|validate_prior_manifest" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.8.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M3：patch embedding 与伪 mask 基础能力，为后续 prior artifact 和聚类伪 mask 工作流提供接口、缓存和 cluster report。

### 已做改动

- 版本号升级到 `v0.8.0`。
- 新增 `he_wsi_generator.embeddings` 模块。
- 新增 `CheckpointPatchEmbedder`，要求用户提供 JSON checkpoint；缺 checkpoint、checkpoint 损坏、embedding 维度非法或输出非有限值时显式报错。
- 新增 `FixturePatchEmbedder`，仅用于 smoke test，并在 metadata 中标记 `embedding_confidence=low`。
- 新增 `EmbeddingResult` 数据结构，统一返回 embedding array 与 metadata。
- 新增 embedding cache，支持保存/读取 `.npy` embedding array 和 JSON metadata。
- 新增轻量 `cluster_embeddings`，输出 labels、cluster counts、inertia、embedding count 和 embedding dim。
- `pyproject.toml` 新增可选依赖组 `embeddings`。
- 新增 M3 单元测试，覆盖缺 checkpoint、合法 checkpoint embedding metadata、cache roundtrip、cluster report 和错误路径。
- 更新 README，说明 M3 能力、可选依赖和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M3 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/embeddings/__init__.py`
- `src/he_wsi_generator/embeddings/cache.py`
- `src/he_wsi_generator/embeddings/cluster.py`
- `src/he_wsi_generator/embeddings/embedder.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.8.0|version = \"0.8.0\"|CheckpointPatchEmbedder|FixturePatchEmbedder|cluster_embeddings|save_embedding_cache" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.7.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M2：WSI 与 mask I/O，建立真实输入审计、thumbnail smoke、mask label mapping 和坐标对齐基础。

### 已做改动

- 版本号升级到 `v0.7.0`。
- 新增 `he_wsi_generator.io` 模块，包含 `OpenSlideReader`、`FixtureImageSlideReader`、`SlideMetadata` 和 `WSIReadError`。
- 新增 manifest audit 能力，支持读取 manifest 后输出每张 WSI 的路径、尺寸、level、MPP、倍率、backend、状态和错误信息。
- CLI 新增 `he-wsi-gen audit-manifest <manifest> --backend <openslide|fixture-image> --output <audit.json>`。
- 新增 `he_wsi_generator.annotations` 模块，支持 PNG/TIFF/numpy mask label 读取、6 类 label mapping 应用和未映射编号显式报错。
- 新增 mask alignment 校验，基于 `transform_to_level0` 的 scale/offset 判断 mask 是否落在 WSI level0 范围内。
- `pyproject.toml` 新增可选依赖组 `wsi`，包含 `numpy`、`Pillow` 和 `openslide-python`。
- 新增 M2 单元测试，覆盖 WSI metadata、thumbnail、manifest audit、mask 编号读取、mapping 应用和坐标对齐错误。
- 更新 README，说明 M2 能力、可选依赖、CLI audit 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M2 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/annotations/__init__.py`
- `src/he_wsi_generator/annotations/alignment.py`
- `src/he_wsi_generator/annotations/masks.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/io/__init__.py`
- `src/he_wsi_generator/io/audit.py`
- `src/he_wsi_generator/io/readers.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli audit-manifest "$tmpdir/manifest.json" --backend fixture-image --output "$tmpdir/audit.json"`（临时 fixture image manifest）
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.7.0|version = \"0.7.0\"|audit-manifest|FixtureImageSlideReader|OpenSlideReader|validate_mask_alignment" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.6.0 - 2026-05-23

### 用户需求

用户要求根据 `docs/` 中的项目设计和开发指南完成本项目开发。当前版本从开发附录 M1 开始，先实现数据契约与 schema 校验，为后续 WSI I/O、mask 映射、prior、训练生成、QC 和 PySide6 UI 提供可测试基础。

### 已做改动

- 版本号升级到 `v0.6.0`。
- 新增 Python package `he_wsi_generator`。
- 新增 `pyproject.toml`，声明 package metadata、CLI 入口和可选 YAML 依赖。
- 新增 CLI：`he-wsi-gen validate <kind> <path>` 与 `he-wsi-gen init-generation-config <output>`。
- 新增 schema validator，覆盖 input manifest、label mapping、generation config、metadata 和 QC report。
- 新增默认生成配置 `configs/generation.default.json`，默认值与开发附录保持一致。
- 新增单元测试，覆盖 schema 成功路径、显式错误路径、CLI 返回码和版本一致性。
- 更新 README，说明当前 M1 能力、安装方式、CLI 用法、开发路线和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录本轮代码实现需求和边界。

### 影响文件

- `.gitignore`
- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/__init__.py`
- `src/he_wsi_generator/__main__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_cli.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.6.0|version = \"0.6.0\"|he_wsi_generator|generation.default.json|he-wsi-gen" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.5.1 - 2026-05-23

### 用户需求

用户要求将本地文件夹重命名为 `MultiCenterWSIGenerator`，并将当前仓库内容同步到 GitHub 仓库 `Liao-MH/MultiCenterWSIGenerator`。

### 已做改动

- 版本号升级到 `v0.5.1`。
- README 项目标题更新为 `MultiCenterWSIGenerator`，并新增 GitHub 仓库链接。
- 新增 `.gitignore`，忽略 `.DS_Store` 和常见 Python 缓存目录。
- 记录远端同步要求、空仓库检查结果和鉴权边界。

### 影响文件

- `.gitignore`
- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `git ls-remote https://github.com/Liao-MH/MultiCenterWSIGenerator.git`
- `ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com`
- `rg "v0.5.1|MultiCenterWSIGenerator|Liao-MH/MultiCenterWSIGenerator" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md`
- `git status --short`
- `git push -u origin main`

## v0.5.0 - 2026-05-23

### 用户需求

用户要求保存第一版开发指南，将现有 H&E WSI 生成器 proposal 转换为可开发规格，并记录已经确认的工程默认值、数据契约、模块边界、模型路线、QC、UI 和测试验收要求。

### 已做改动

- 版本号升级到 `v0.5.0`。
- 新增 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`，作为第一版开发附录。
- 开发附录明确 v1 工程默认：Python core/CLI + PySide6，OpenSlide+tifffile，PyTorch latent diffusion U-Net，可插拔 PatchEmbedder。
- 开发附录补充输入 manifest、annotation record、label mapping、generation config、输出文件、模块契约、prior artifact、模型训练、推理重建、QC、UI、测试验收和 v1 不做内容。
- 更新 `README.md`，新增开发附录入口并把项目状态更新为研究设计 + 开发规格阶段。
- 更新 `docs/DEMANDS.MD`，新增 `v0.5.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.5.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- `test -s docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `rg "v0.5.0|OpenSlide|tifffile|PySide6|latent diffusion U-Net|PatchEmbedder|structure_anchor" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `rg "^## |^### " docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `python3 - <<'PY' ...`（检查版本一致性、开发附录链接和核心章节）
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

## v0.4.0 - 2026-05-21

### 用户需求

用户希望把 conditional priors learning 的数理逻辑、产物类型和约束机制写入 proposal，明确这些 prior 如何通过条件输入、loss、guidance 和 QC 落到实际生成模型中。

### 已做改动

- 版本号升级到 `v0.4.0`。
- 在 `docs/plans/2026-05-18-he-wsi-generator-study-design.md` 新增 `Conditional Priors 的产物与约束机制` 小节，补充联合分布、prior 产物类型、条件注入方式和扩散目标。
- 补充 conditional priors 与 `structure_anchor` 的数学关系，明确 `alpha` 不是像素插值，而是条件强度和 loss 权重的连续调节。
- 在三阶段训练协议中补充说明：layout、mask、style seed 和 `structure_anchor` 都是 conditional priors 的实例化结果，而不是临时拼接特征。
- 更新 `README.md` 的当前版本和更新重点。
- 更新 `docs/DEMANDS.MD`，新增 `v0.4.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.4.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.4.0|2026-05-21" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（检查版本字段、conditional priors 小节和 metadata 示例）

## v0.3.0 - 2026-05-18

### 用户需求

用户希望现有 proposal 文档更完整地覆盖前期讨论达成的所有细节共识，并加强因果分析、设计取舍说明、训练协议、自动 QC、metadata、LLM 边界和系统完成标准。

### 已做改动

- 版本号升级到 `v0.3.0`。
- 扩写 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，新增细节共识总表，系统整理全部关键决策。
- 补充因果假设、反事实边界和被放弃路线，解释为什么当前主线选择结构锚定多分辨率条件扩散，而不是普通增强、CycleGAN、GAN、纯随机生成、先高倍后拼接或文本 prompt 入模。
- 扩写总体架构，补充数据流和因果依赖，明确 thumbnail、mask、patch embedding、style prior、source relation 和 QC reference distribution 的作用。
- 扩写 mask 体系，补充无标注场景、聚类伪 mask、用户映射流程和可信度层级。
- 扩写 `structure_anchor`，补充训练与推理语义、不同 anchor 区间的因果解释。
- 扩写生成模型部分，补充 backbone 选择原则、四层 pyramid 责任分工、训练样本构造、训练约束与 QC 映射。
- 扩写本地桌面单页控制台、高级参数、LLM 角色、metadata 双层 manifest、自动 QC 判定逻辑和非复制报告解释规则。
- 新增核心系统完成标准，明确完整 H&E WSI 生成器必须具备的输出和审计能力。
- 更新 `README.md`，增加 `v0.3.0` 更新重点。
- 更新 `docs/DEMANDS.MD`，新增 `v0.3.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.3.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.3.0|2026-05-18" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（metadata / structure / format checks）

## v0.2.0 - 2026-05-18

### 用户需求

用户要求根据 `research-design-ladder` 技能，将前期已确认的 H&E WSI 数据生成器方案写入正式研究设计文档，并同步更新项目版本、README、需求记录和开发日志。

### 已做改动

- 版本号升级到 `v0.2.0`。
- 新增 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，按完整 proposal / study design 结构写入 H&E WSI 数据生成器研究设计。
- 新研究设计文档明确当前系统边界：只做 H&E WSI 生成器，不把下游训练/测试作为当前成败标准。
- 新研究设计文档纳入结构锚定多分辨率条件扩散框架、`structure_anchor`、`global_imaging_style_prior`、疾病无关 6 类 mask、40x 四层级联生成、自动 QC、metadata/schema、本地桌面单页控制台、风险矩阵和最终逻辑链。
- 更新 `README.md`，将项目入口、当前定位、核心输出、关键技术路线和边界说明同步到 `v0.2.0`。
- 更新 `docs/DEMANDS.MD`，新增 `v0.2.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.2.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.2.0|2026-05-18" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（metadata / structure / format checks）
- `ls -l VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`

## v0.1.0 - 2026-05-16

### 用户需求

用户希望设计一个面向 H&E 染色 WSI 数据的多中心数据生成器，用于缓解真实多中心数据收集困难，并要求按 `research-design-ladder` 方法生成完整研究设计。

### 已做改动

- 初始化项目文档版本 `v0.1.0`。
- 新增研究设计文档，系统整理研究定位、核心问题、生成器架构、数据协议、验证方案、风险矩阵、执行顺序、交付版本和候选标题。
- 新增需求记录文件，结构化保存本次用户需求与设计边界。
- 新增 README，说明项目目标、当前状态、核心文档和后续实现阶段的环境原则。
- 新增 VERSION 文件，记录当前文档设计版本。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`

### 验证结果

- `find . -maxdepth 3 -type f | sort`
- `grep -R "v0.1.0" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`
