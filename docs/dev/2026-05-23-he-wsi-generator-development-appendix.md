# H&E WSI 数据生成器开发附录：v1 可开发规格

日期：2026-05-23
版本：v0.5.0
状态：开发指南初版 / development appendix v1
关联研究设计：[2026-05-18-he-wsi-generator-study-design.md](../plans/2026-05-18-he-wsi-generator-study-design.md)

---

## 1. 文档目的

本附录把现有 proposal 转换为第一版开发指南。proposal 负责说明研究逻辑、系统边界和因果主张；本附录负责说明开发者如何把系统拆成可实现、可测试、可追踪的工程模块。

当前版本仍然只写文档，不实现训练代码、推理代码或图形界面。它的目标是让后续开发者不需要重新决定系统形态、主要模块、数据契约、默认技术路线和验收标准。

本附录的核心原则如下：

| 原则 | 开发含义 |
|---|---|
| Core first | 先实现可测试 Python core 和 CLI，再接入桌面 UI |
| 明确契约 | 每个模块必须有输入、输出、错误和验收标准 |
| 显式失败 | 缺少 WSI、MPP、mask transform、embedding checkpoint 等关键输入时应显式报错 |
| 可追溯 | 每个输出 WSI 必须能追踪到 source、seed、model、prior、QC 和配置 |
| 不静默回退 | fallback 只能用于明确的 smoke test 或低置信流程，不能掩盖真实失败 |

## 2. v1 工程默认值

第一版开发采用“Python core library + CLI + PySide6 桌面控制台”的结构。这样可以保证训练、生成、QC 和 schema 检查先成为可测试的核心能力，再由桌面 UI 调用这些能力。UI 不应直接包含核心业务逻辑。

| 类别 | v1 默认选择 | 说明 |
|---|---|---|
| 语言 | Python 3.11 | 后续创建独立 conda 环境，不在主环境安装依赖 |
| Core 形态 | Python package | 未来建议包名为 `he_wsi_generator` |
| CLI | `he-wsi-gen` | 用于数据审计、prior 学习、训练、生成和 QC |
| 桌面 UI | PySide6 | 本地单页控制台，调用 core/CLI 能力 |
| WSI 读取 | OpenSlide | 支持 OpenSlide 可读取的 WSI 格式，不支持时显式报错 |
| OME-TIFF 写出 | tifffile | 写出 pyramid OME-TIFF 和必要 metadata |
| 深度学习框架 | PyTorch | v1 采用原生 PyTorch 训练 loop，分布式训练后续扩展 |
| 生成模型 | latent diffusion U-Net | DiT 保留为后续替换路线 |
| patch embedding | 可插拔 `PatchEmbedder` | 默认要求用户提供 checkpoint；通用 fallback 只允许用于 smoke test |

第一版不应在 UI 里绕过 CLI/core 直接读写文件。所有 UI 操作都应生成可复现的配置对象，并由 core 层执行。

## 3. 建议工程结构

后续进入代码实现时，建议采用以下结构。当前版本只作为开发规格，不创建这些代码目录。

```text
src/he_wsi_generator/
  io/                 # WSI 读取、pyramid 解析、OME-TIFF 写出
  annotations/        # PNG / numpy / ROI annotation 读取与 label mapping
  embeddings/         # PatchEmbedder 接口、patch 抽取、embedding 缓存
  priors/             # layout/mask/style/texture/QC prior 学习与保存
  models/             # latent diffusion U-Net、条件注入、训练 loop
  generation/         # cascade 生成、tile traversal、overlap blending
  qc/                 # WSI/tile/mask region QC 与非复制报告
  metadata/           # manifest、metadata、batch JSONL 写出与校验
  ui/                 # PySide6 本地单页控制台
configs/
tests/
```

核心约束是依赖方向：`ui` 可以调用 core，core 不应依赖 `ui`。`metadata` 和 `qc` 可以被训练、生成和 UI 共同调用，但它们不应反向调用模型训练代码。

## 4. 数据契约

### 4.1 输入 manifest

输入 manifest 是所有后续流程的入口。它应记录 WSI、可选 annotation、中心标签和癌种/组织信息。

```json
{
  "schema_version": "v0.5.0",
  "dataset_id": "string",
  "created_at": "YYYY-MM-DDTHH:MM:SS",
  "records": [
    {
      "wsi_id": "string",
      "wsi_path": "path/to/slide.svs",
      "center_id": "string or null",
      "cancer_type": "string",
      "tissue_type": "string or null",
      "mpp_x": 0.25,
      "mpp_y": 0.25,
      "max_magnification": "40x",
      "split": "train|val|test|unassigned",
      "annotations": []
    }
  ]
}
```

必填字段为 `wsi_id`、`wsi_path`、`cancer_type` 和 `split`。`mpp_x`、`mpp_y`、`max_magnification` 可以从 WSI metadata 读取；若读取失败，系统应进入数据审计错误状态，而不是静默假设倍率。

### 4.2 Annotation record

annotation 可以来自 PNG、numpy、ROI 或后续交互修正文件。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `annotation_id` | string | 是 | 同一 WSI 内唯一 |
| `annotation_path` | string | 是 | PNG、npy、npz、json 或 ROI 文件路径 |
| `annotation_type` | enum | 是 | `png_mask`、`numpy_mask`、`roi_json`、`cluster_pseudo_mask` |
| `coordinate_level` | string/int | 是 | annotation 对应的 WSI level 或 `40x_level0` |
| `label_encoding` | string | 是 | `integer_index` 或其他明确编码 |
| `transform_to_level0` | object | 是 | scale / offset / affine 信息 |
| `status` | enum | 是 | `raw`、`mapped`、`validated`、`rejected` |

若 annotation 文件中的数字编号无法映射到 6 类 mask，系统应阻止训练/生成继续，并要求用户完成 label mapping。

### 4.3 Label mapping

label mapping 把用户 annotation 中的数字编号映射到疾病无关 6 类。

```json
{
  "schema_version": "v0.5.0",
  "wsi_id": "string",
  "source_annotation_id": "string",
  "classes": {
    "0": "background",
    "1": "tissue",
    "2": "target_pathology",
    "3": "supporting_tissue",
    "4": "necrosis_debris",
    "5": "artifact"
  },
  "mapping_source": "manual|roi|cluster|mixed",
  "confidence": {
    "0": "high",
    "1": "high"
  }
}
```

有效类别固定为：`background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact`。其他类别不得直接进入生成模型，必须先由用户映射或标记为 `rejected`。

### 4.4 生成配置

生成配置必须保存为 JSON 或 YAML，并进入 run-level manifest。

```yaml
schema_version: v0.5.0
random_seed: 0
model_family: latent_diffusion_unet
max_magnification: 40x
tile_size_40x: [512, 512]
cascade_levels: ["1/32", "1/16", "1/4", "1/1"]
structure_anchor: 0.0
anchor_preset: fully_de_novo
style_seed: auto
source_wsi_id: null
sample_steps: 50
overlap_px_40x: 64
non_copy_patch_nearest_neighbor_search: false
```

允许用户覆盖 `random_seed`、`structure_anchor`、`style_seed`、`sample_steps`、`overlap_px_40x`、输出路径和 checkpoint 路径。`cascade_levels`、`tile_size_40x` 和 `max_magnification` 可以作为高级参数暴露，但默认值必须与 proposal 保持一致。

### 4.5 输出契约

每个生成 WSI 至少输出：

| 文件 | 说明 |
|---|---|
| `generated.ome.tiff` | OME-TIFF pyramid WSI |
| `generated_mask/` | 与 WSI 对齐的 6 类 mask |
| `metadata.json` | 单个 WSI 的生成配置、source、seed、model、prior 和路径 |
| `qc.json` | 自动 QC 结果和非复制报告 |
| `batch.jsonl` | 批量任务索引，每行对应一个 generated sample |
| `generation_output_diagnostics.json` | 汇总输出完整性、writer 状态、tile manifest/source 状态和 QC 摘要 |

`metadata.json` 与 `qc.json` 不应被合并。前者回答“这个样本如何生成”，后者回答“这个样本是否可用以及有哪些风险”。

Implementation Trace:
- 状态：部分实现（v0.72.32）。已实现 smoke / torch-smoke / `production-tile-stream` 输出归档：`generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`batch.jsonl`、`generation_run.json` 和 `generation_output_diagnostics.json` 均可写出；production backend 磁盘级逐 tile 生成已通过外部 tile generator contract 落地。v0.72.26 新增 OME streaming writer 对上次 `started` transaction 完整临时 OME-TIFF 的验证发布恢复；v0.72.27 新增 `production_tile_requests/*.request.json` per-tile request manifest 和 `{tile_request_path}` 外部 backend 输入合同；v0.72.28 新增 failed tile 显式 retry/resume，默认拒绝 failed manifest，显式 retry 时保留 retry 审计字段；v0.72.29 新增 completed transaction 已发布目标 OME-TIFF 验证复用，校验 target、tile source manifest 和 pyramid shapes 后可跳过 tile iterator 重写，并在 transaction/report/diagnostics 中记录 `validated_existing_target_ome_tiff` / `reused_existing_target=true`；v0.72.30 新增 OME streaming 写入前磁盘空间 preflight；v0.72.31 新增 production tile backend execution evidence，记录 request JSON、外部命令执行摘要和 RGB/mask 输出文件哈希，并在 tile source manifest 与 diagnostics 汇总覆盖统计；v0.72.32 新增 OME streaming writer progress sidecar，记录 planned/yielded/completed tile 数、当前 level/tile grid、last tile 和失败原因，并在 transaction/report/diagnostics 汇总 `progress_summary`。仍未实现同一 OME-TIFF 文件内部中断追加写入、精确 TIFF 文件大小预测或内置 production diffusion 模型。
- 主实现：
  - `src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`，编排 production-ready checkpoint、外部 tile backend、磁盘 tile source、OME-TIFF、mask、metadata、QC、batch index 和 diagnostics 输出。
- 完整依赖：
  - 入口与编排：
    - `src/he_wsi_generator/cli.py::build_parser`，将 `production-tile-stream` 暴露为 `run-generation` backend，并要求用户显式选择 writer。
    - `src/he_wsi_generator/cli_commands.py::run_command`，分发 `production-tile-stream`，并要求 `--wsi-writer tile-streaming`。
  - 输入契约：
    - `src/he_wsi_generator/generation/planner.py::create_generation_plan`，校验 checkpoint/backend compatibility、model architecture 和 condition contract。
    - `src/he_wsi_generator/generation/production_streaming.py::load_external_tile_backend_contract`，校验 `external_tile_generator_v1` artifact、命令模板、RGB tile 格式和 mask tile 格式。
  - 输出契约：
    - `src/he_wsi_generator/schemas.py::validate_metadata`，校验 metadata 输出结构。
    - `src/he_wsi_generator/schemas.py::validate_generation_output_diagnostics`，校验 diagnostics 中 artifact、writer、tile source、QC summary、`writer_summary.recovered_from_temporary` / `writer_summary.reused_existing_target` 布尔恢复字段、`writer_summary.disk_space_preflight` 磁盘空间预算字段、`writer_summary.progress_summary` 进度摘要，以及 `tile_source.backend_execution_summary` 执行证据摘要。
  - 核心逻辑：
    - `src/he_wsi_generator/generation/production_streaming.py::materialize_production_tile_sources`，按四层 pyramid tile grid 写出 per-tile request manifest 后调用外部 backend，维护 completed/pending/failed、attempt count、resume index、request evidence、backend execution evidence、output evidence 和 tile source manifest。
    - `src/he_wsi_generator/generation/production_streaming.py::_build_expected_tile_source_manifest`，生成 `production_tile_source_manifest.json` 的 levels、tiles、`tile_request_path`、GB 级估算和恢复语义。
    - `src/he_wsi_generator/generation/production_streaming.py::_execute_tile_backend_command`，在执行外部命令前写出 request JSON，支持 `{tile_request_path}` 命令占位符，并返回 command/cwd/return code/timeout/duration/stdout/stderr preview 执行证据。
    - `src/he_wsi_generator/generation/production_streaming.py::_tile_request_manifest`，构造 `production_tile_request_v1`，记录 tile、输出、prior、checkpoint、backend 和 condition packet 摘要。
    - `src/he_wsi_generator/generation/production_streaming.py::_ensure_completed_record`，校验 RGB/mask tile dtype、shape 和 class id，并生成输出文件大小与 SHA-256 证据。
    - `src/he_wsi_generator/generation/production_streaming.py::_backend_execution_summary`，汇总 completed tile 的 request / execution / output evidence 覆盖情况。
    - `src/he_wsi_generator/generation/production_streaming.py::write_streaming_mask_from_tile_sources`，用 memmap 从 level0 mask tiles 写出对齐 6 类 mask。
  - 配置与默认值:
    - `configs/generation.default.json`，提供当前 generation config schema version 和默认 tile/cascade 参数。
    - `src/he_wsi_generator/constants.py`，同步项目版本、cascade levels 和 mask class 常量。
  - 错误处理：
    - `src/he_wsi_generator/generation/production_streaming.py::ProductionTileStreamError`，暴露外部 backend artifact、tile 文件、mask tile、resume manifest 和命令执行错误。
    - `src/he_wsi_generator/generation/executor.py::GenerationExecutionError`，把 generation 入口失败转为 CLI 可读错误。
  - 输出与持久化：
    - `src/he_wsi_generator/outputs/ome_tiff.py::write_pyramid_ome_tiff_streaming_from_tile_sources`，从完整磁盘 tile source manifest 原子发布 OME-TIFF，写出 transaction manifest；若存在可恢复 completed transaction，则验证并复用已发布目标 OME-TIFF，若存在可恢复 started transaction，则验证发布完整临时 OME-TIFF；正常完整写出前执行磁盘空间 preflight，并在空间不足时阻断 tile iterator。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_disk_space_report`，按 raw pyramid byte estimate 加同等安全余量生成 `disk_space_preflight`，该估算是保守预算 guard，不是最终 TIFF 大小预测。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_load_existing_streaming_transaction_manifest`，读取既有 `<target>.transaction.json`，仅作为恢复候选，不把坏 JSON 当作可恢复状态。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_recover_completed_streaming_target`，对 completed transaction 指向的目标 OME-TIFF 做可读性和 pyramid shape 校验，成功时复用目标文件并避免重复读取 tile source iterator。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_is_recoverable_completed_transaction`，只接受 `completed`、无 failure reason、target 存在且与当前 plan 匹配的目标复用候选。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_recover_started_streaming_temporary`，校验 started transaction、目标路径、tile source manifest 路径和临时 OME-TIFF pyramid shape，成功时返回可发布临时文件，失败时清理不可用临时文件并回到正常写出路径。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_transaction_matches_current_plan`，统一校验 transaction manifest 类型、writer 类型、target path 和 tile source manifest path。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_read_validated_streaming_ome_level_shapes`，用 `tifffile` 验证临时 OME-TIFF 可读且 pyramid shapes 与当前 plan 一致。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_tile_iterator_streaming_report`，把 successful preflight 摘要写入 streaming writer report。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_progress_manifest`，构造 `<target>.progress.json` 初始进度 sidecar，记录计划 level/tile 数和 `progress_semantics`。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_record_streaming_progress_tile`，在 tile iterator yield 前更新当前 level/tile grid、last tile、yielded/completed tile count 和更新时间。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_finish_streaming_progress_manifest`，在 completed 或 failed transaction 前写入最终 status 与 failure reason。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_progress_summary`，生成写入 transaction/report/diagnostics 的紧凑 progress summary。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_write_streaming_progress_manifest`，持久化 progress sidecar。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_transaction_manifest`，把 successful 或 failed preflight 摘要、progress manifest path 和 progress summary 写入 transaction manifest，方便排查磁盘空间不足或 tile iterator 中断。
    - `src/he_wsi_generator/generation/executor.py::_writer_summary`，把 writer transaction 路径、atomic publish、`recovered_from_temporary`、`reused_existing_target`、`disk_space_preflight`、`progress_manifest_path` 和 `progress_summary` 写入 diagnostics。
    - `src/he_wsi_generator/generation/executor.py::_tile_source_summary`，把 tile source 的 `backend_execution_summary` 透传到 diagnostics。
    - `src/he_wsi_generator/metadata/archive.py::archive_sample`，写出 metadata、QC 和 batch JSONL index。
  - 测试覆盖：
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_writes_external_backend_tiles`，验证外部 backend tiles、mask、OME-TIFF、metadata、QC、diagnostics、tile source manifest、request evidence、backend execution evidence、output evidence 和 diagnostics execution summary。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_writes_tile_request_manifests`，验证外部 backend 通过 `{tile_request_path}` 读取 request JSON，并校验 tile/source/request 合同字段。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_rejects_non_production_checkpoint`，验证非 production checkpoint 被拒绝。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_retries_failed_tile_source_manifest_when_requested`，验证 failed tile 默认拒绝、显式 retry 后完成输出并保留 retry 审计字段。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_rejects_insufficient_disk_space`，验证磁盘空间不足时 writer 在 tile iterator 开始前失败，并写出 failed transaction。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_records_transaction_manifest`，验证成功 transaction 引用 progress sidecar，progress status/counts/last tile 与 streaming report summary 一致。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_failed_transaction_preserves_target`，验证 tile iterator 失败时保留既有目标文件，并在 failed transaction/progress sidecar 中记录失败前进度和 failure reason。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer`，验证 smoke tile-streaming 主流程 diagnostics 记录 successful `disk_space_preflight`。
    - `tests/test_schemas.py::SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract`，验证 diagnostics schema 接受并校验 `writer_summary.disk_space_preflight` 与 `writer_summary.progress_summary`。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_publishes_recovered_temporary_ome`，验证 started transaction 留下完整临时 OME-TIFF 时，writer 不重新读取 tile iterator，而是验证并发布该临时文件。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_reuses_completed_target_ome`，验证 completed transaction 指向的已发布目标 OME-TIFF 通过 shape 校验后被复用，且不重新读取 tile iterator。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer`，验证 diagnostics 默认写出 `recovered_from_temporary=false` 与 `reused_existing_target=false`。
    - `tests/test_cli.py::CliValidationTests.test_cli_validates_generation_output_diagnostics_file`，验证 diagnostics CLI validator。
  - 脚本与命令：
    - 不适用；本轮不新增项目脚本。
- 调用链 / 实现流程：
  `he-wsi-gen run-generation` -> `cli_commands.run_command` -> `run_production_tile_stream_generation` -> `create_generation_plan` / `load_external_tile_backend_contract` -> `materialize_production_tile_sources` -> `_tile_request_manifest` / `_execute_tile_backend_command` -> `write_pyramid_ome_tiff_streaming_from_tile_sources`（必要时 `_recover_completed_streaming_target` 复用已发布目标 OME，或 `_recover_started_streaming_temporary` 发布完整临时 OME） / `write_streaming_mask_from_tile_sources` -> `build_streaming_tile_source_qc_report` -> `archive_sample` -> `_generation_output_diagnostics`
- 外部关键依赖：
  - `numpy`，读写 `.npy` RGB/mask tile、memmap mask 和 streaming QC 抽样统计。
  - `tifffile`，写出并校验 OME-TIFF pyramid。
- 参考行号：
  - `src/he_wsi_generator/generation/executor.py` 420-592，production tile-stream 生成编排与输出归档。
  - `src/he_wsi_generator/generation/production_streaming.py` 77-167，外部 backend tile source 物化，并写入 request/backend execution/output evidence。
  - `src/he_wsi_generator/generation/production_streaming.py` 263-385，tile source manifest、`tile_request_path` 和 `request_manifest_type` 构造。
  - `src/he_wsi_generator/generation/production_streaming.py` 388-478，resume manifest 不可变字段校验，包含 `request_manifest_type`、`tile_request_path` 和历史 evidence 字段保留。
  - `src/he_wsi_generator/generation/production_streaming.py` 477-568，request JSON 写出、`{tile_request_path}` 占位符、命令执行和 execution evidence 构造。
  - `src/he_wsi_generator/generation/production_streaming.py` 648-678，RGB/mask tile 校验与 output evidence 构造。
  - `src/he_wsi_generator/generation/production_streaming.py` 681-725，`backend_execution_summary` 覆盖统计。
  - `src/he_wsi_generator/generation/production_streaming.py` 914-926，文件大小与 SHA-256 evidence 构造。
  - `src/he_wsi_generator/generation/production_streaming.py` 150-249，memmap mask 写出和 streaming QC report。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 124-318，streaming writer 读取既有 transaction、复用 completed target OME、发布完整临时 OME 或正常写出，并记录 `recovered_from_temporary` / `reused_existing_target` / `disk_space_preflight` / `progress_summary`。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 904-1112，tile iterator progress sidecar 构造、逐 tile 更新、完成/失败收口、summary 生成和持久化。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 380-404，`_streaming_disk_space_report` 磁盘空间预算；857-980，transaction 读取、completed target 判断、started transaction 判断、target/manifest 匹配和 OME pyramid shape 校验。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 1049-1086，transaction manifest 构建与 `recovery_action` / `disk_space_preflight` 记录。
  - `src/he_wsi_generator/generation/executor.py` 769-805，diagnostics writer summary 透传 transaction、disk-space preflight 和 progress summary。
  - `src/he_wsi_generator/generation/executor.py` 831-863，diagnostics tile source summary 透传 backend execution summary。
  - `src/he_wsi_generator/schemas.py` 393-425，diagnostics writer progress manifest path 与 progress summary 校验。
  - `src/he_wsi_generator/schemas.py` 429-458，diagnostics `tile_source.backend_execution_summary` 校验。
  - `tests/test_outputs_qc_archive.py` 538-619，started transaction 完整临时 OME 发布恢复测试。
  - `tests/test_outputs_qc_archive.py` 621-701，completed transaction 目标 OME 验证复用测试；703-755，磁盘空间不足 preflight 阻断测试。
  - `tests/test_generation_runner.py` 1068-1105，production tile backend execution evidence 主功能测试。
  - `tests/test_generation_runner.py` 1101-1155，production failed tile retry/resume 主功能测试。
- 验证命令：
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - `git diff --check`
- 验证结果：`conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v` 本轮已执行通过，`Ran 84 tests in 3.295s OK`；`outputs/ome_tiff.py` / `generation/executor.py` / `schemas.py` py_compile 通过，无输出；默认 generation config 校验输出 `generation-config valid: configs/generation.default.json`；`git diff --check` 通过，无输出。
- 更新时间：2026-05-25

## 5. 模块契约

| 模块 | 输入 | 输出 | 失败条件 |
|---|---|---|---|
| WSI reader | `input_manifest`、WSI path | pyramid metadata、thumbnail、level map | 文件不存在、OpenSlide 无法读取、MPP 缺失且无法推断 |
| Annotation loader | annotation record | raw mask / ROI object | annotation 文件损坏、坐标层级缺失 |
| Mask mapper | raw annotation、label mapping | 6 类 mask、confidence map | 编号未映射、mask 与 WSI 坐标不一致 |
| Patch extractor | WSI、mask、采样配置 | patch index、patch image batch | tile 越界、组织区域不足 |
| PatchEmbedder | patch batch、checkpoint | embedding array、embedding metadata | checkpoint 缺失、维度不一致 |
| Clusterer | embeddings、mask context | pseudo mask、cluster report | 聚类为空、类别无法映射 |
| Prior learner | mask、thumbnail、style stats、embeddings | layout/style/texture/QC priors | 样本不足、prior 输出不可采样 |
| Model trainer | training index、priors、configs | model checkpoint、training log | 条件缺失、loss 异常、checkpoint 写入失败 |
| Generator | checkpoint、priors、generation config | generated tiles、pyramid levels | 条件不完整、显存不足、tile 生成失败 |
| Reconstructor | tiles、level metadata、mask | OME-TIFF、mask 输出 | pyramid 层级不一致、写入失败 |
| QC engine | generated outputs、reference priors | `qc.json` | 输出缺失、硬错误、QC 指标无法计算 |
| UI controller | 用户配置、任务状态 | job config、progress、error report | 参数非法、任务中断、路径无权限 |

每个模块都应可被单独测试。UI 只能展示和调度模块结果，不能把核心数据处理逻辑藏在界面事件里。

## 6. Conditional Priors 的工程落地

### 6.1 Prior artifact

prior 学习完成后，应至少保存以下 artifact：

| artifact | 内容 | 用途 |
|---|---|---|
| `layout_mask_prior` | tissue contour、区域比例、邻接关系、6 类 mask 分布 | fully de novo 和低 anchor 生成 |
| `style_prior` | slide-level stain、focus、noise、artifact style latent | 控制同一 WSI 内成像风格 |
| `texture_prior` | patch cluster、class-conditioned texture codebook | 控制高倍局部纹理 |
| `qc_reference_distribution` | 颜色、清晰度、组织比例、seam、style consistency 的训练分布 | 自动 QC 阈值 |
| `prior_manifest` | prior 版本、训练数据、seed、生成时间 | 审计和复现 |

prior artifact 可以是 JSON、numpy、PyTorch checkpoint 或组合目录，但必须有统一 manifest。任何生成任务都必须记录使用了哪个 prior artifact。

### 6.2 PatchEmbedder 接口

`PatchEmbedder` 是可插拔接口，不在 v1 文档中绑定特定第三方 pathology foundation model。默认行为是要求用户提供 checkpoint 路径。

最小接口语义：

```text
input: patch tensor batch, magnification, normalization config
output: embedding array, embedding_dim, model_id, checkpoint_hash
error: missing checkpoint, unsupported patch shape, non-finite embedding
```

若开发者提供通用视觉模型 fallback，只能用于 smoke test 或低置信伪 mask，metadata 必须记录 `embedding_confidence: low`。不得在正式 prior 学习中静默使用 fallback。

### 6.3 Prior 与生成模型的连接

生成模型接收的条件包为：

```text
C = {layout, mask, style_seed, texture_token, coord, source_condition, structure_anchor}
```

v1 不要求所有 prior 都达到最终研究质量，但必须保证接口存在、metadata 可追踪、缺失时显式报错。若某个 prior 在当前任务中未使用，应在 generation config 中写明 `disabled` 和原因。

## 7. 模型、训练与推理规格

### 7.1 模型主干

v1 锁定 `latent_diffusion_unet`。DiT 仅作为未来模型族保留，不作为第一版实现目标。

模型条件输入包括：

| 条件 | 注入建议 |
|---|---|
| 当前尺度 6 类 mask | concat 或 ControlNet-like 空间条件分支 |
| 上一尺度图像 / latent | concat 或 cross-scale condition encoder |
| style seed / style latent | FiLM、AdaIN 或 cross-attention token |
| tile 坐标与倍率 | coordinate embedding |
| source WSI 条件 | 高 anchor 模式下的 source encoder |
| `structure_anchor` | scalar embedding + condition / loss 权重控制 |

Implementation Trace:
- 状态：部分实现（v0.72.20）。`latent_diffusion_unet` 已作为 training backend、target type 和 training plan artifact 的模型族契约落地，`training_plan.json` 会记录模型条件输入；尚未实现真实 production latent diffusion / ControlNet / DiT 训练或推理 backend。
- 主实现：
  - src/he_wsi_generator/models/training.py::create_training_run，初始化 production training run 并写出 `training_plan.json`、`checkpoint_manifest.json`、`training_run.json`。
  - src/he_wsi_generator/models/training.py::_training_plan_manifest，生成 `production_training_plan` artifact，记录模型族、target type、condition policy 和 plan-only 边界。
- 完整依赖：
  - 入口与编排:
    - src/he_wsi_generator/cli.py::build_parser，注册 `init-training-run` 命令。
    - src/he_wsi_generator/cli_commands.py::run_cli，读取训练配置并调用训练 run 初始化。
  - 输入契约:
    - src/he_wsi_generator/models/training.py::_validate_training_config，校验 `model_family`、`training_backend`、cascade levels、tile size、condition dropout 和 source condition。
    - src/he_wsi_generator/models/training.py::REQUIRED_INFERENCE_CONDITION_INPUTS，定义模型计划保留的条件输入集合。
  - 输出契约:
    - src/he_wsi_generator/models/training.py::_checkpoint_manifest，输出仍不可推理的 skeleton checkpoint，并引用 training plan。
  - 核心逻辑:
    - src/he_wsi_generator/models/training.py::_training_plan_stages，生成模型训练计划中的阶段条件输入。
  - 配置与默认值:
    - src/he_wsi_generator/constants.py::MODEL_FAMILY，锁定当前模型族为 `latent_diffusion_unet`。
    - src/he_wsi_generator/constants.py::CASCADE_LEVELS，锁定四层 cascade。
  - 错误处理:
    - src/he_wsi_generator/models/training.py::ModelRunError，暴露非法模型族、backend 或训练契约不一致。
  - 输出与持久化:
    - src/he_wsi_generator/models/training.py::create_training_run，写出 run / plan / checkpoint 三个 JSON artifact。
  - 测试覆盖:
    - tests/test_models_generation.py::ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint，验证 training plan artifact 与 checkpoint 引用。
  - 脚本与命令:
    - 不适用。
- 调用链 / 实现流程：
  CLI `init-training-run` -> `run_cli()` -> `create_training_run()` -> `_training_plan_manifest()` -> `_checkpoint_manifest()`
- 外部关键依赖：
  - 无。
- 参考行号：
  - src/he_wsi_generator/models/training.py 75-128，训练 run 初始化和 artifact 写出。
  - src/he_wsi_generator/models/training.py 549-638，production training plan artifact 和阶段条件输入。
- 验证命令：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_version -v`
- 更新时间：2026-05-25 17:07

### 7.2 训练阶段

训练阶段保持 proposal 中的三阶段：

1. Layout/mask prior 与 style prior 学习。
2. Mask-conditioned 多倍率图像生成训练。
3. WSI 一致性微调，重点处理 tile seam、跨倍率一致性和 slide-level style consistency。

训练配置必须记录：

| 配置 | 默认 | 说明 |
|---|---|---|
| `random_seed` | `0` | 所有采样、聚类、训练和生成都必须记录 seed |
| `cascade_levels` | `["1/32", "1/16", "1/4", "1/1"]` | 不应在 v1 默认删除层级 |
| `tile_size_40x` | `[512, 512]` | 与 proposal 保持一致 |
| `batch_size` | `auto_by_vram` | 实现时根据显存选择，不应硬编码不可运行数值 |
| `condition_dropout` | `enabled` | 用于训练模型响应不同 anchor |
| `source_condition` | `required_when_anchor_gt_0` | 高 anchor 生成必须记录 source |
| `loss_weights` | `configurable` | 不在文档中承诺最终最优权重 |

Implementation Trace:
- 状态：部分实现（v0.72.20）。三阶段训练、目标约束、loss weight、阶段目标映射和 QC 映射已被校验并写入 `training_plan.json`；尚未执行真实 production training loop、真实 loss 计算、WSI consistency finetuning 或 production checkpoint 训练。
- 主实现：
  - src/he_wsi_generator/models/training.py::_training_plan_stages，生成 `prior_ready`、`image_generator`、`wsi_consistency` 三阶段计划。
  - src/he_wsi_generator/models/training.py::_validate_training_objective_contract，校验五类训练目标、非负 loss weights、阶段目标映射和 QC 映射。
- 完整依赖：
  - 入口与编排:
    - src/he_wsi_generator/models/training.py::create_training_run，连接 prior manifest、dataset contract、objective contract 和 training plan 写出。
  - 输入契约:
    - src/he_wsi_generator/models/training.py::_validate_dataset_contract，校验 training index record 数、split/level 覆盖、必需条件输入和 6 类 mask schema。
    - src/he_wsi_generator/models/training.py::_summarize_training_index，读取实际 JSONL 训练索引作为 contract 证据。
  - 输出契约:
    - src/he_wsi_generator/models/training.py::_training_plan_manifest，定义 `production_training_plan` 输出结构。
    - src/he_wsi_generator/models/training.py::_training_objective_contract_summary，生成 run / plan / checkpoint 共用的训练目标摘要。
  - 核心逻辑:
    - src/he_wsi_generator/models/training.py::REQUIRED_OBJECTIVES_BY_STAGE，定义 image generator 与 WSI consistency 阶段目标。
    - src/he_wsi_generator/models/training.py::REQUIRED_QC_MAPPING，定义训练目标到 QC metric 的映射。
  - 配置与默认值:
    - src/he_wsi_generator/models/training.py::TRAINING_STAGES，定义三阶段顺序。
    - src/he_wsi_generator/models/training.py::TRAINING_OBJECTIVE_SCHEMA，定义训练目标契约版本。
  - 错误处理:
    - src/he_wsi_generator/models/training.py::_validate_training_index_record，拒绝缺少 tile、mask 或 conditioning 证据的训练记录。
    - src/he_wsi_generator/models/training.py::_require_non_negative_number，拒绝非法 loss weight。
  - 输出与持久化:
    - src/he_wsi_generator/models/training.py::create_training_run，写出 `training_plan.json` 并在 `training_run.json` 与 `checkpoint_manifest.json` 中记录 `training_plan_path`。
  - 测试覆盖:
    - tests/test_models_generation.py::ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint，验证 training plan 阶段、objectives 和 QC mapping。
    - tests/test_models_generation.py::ModelGenerationSkeletonTests.test_create_training_run_rejects_training_objective_qc_mapping_mismatch，验证 QC mapping 错误时显式失败。
    - tests/test_models_generation.py::ModelGenerationSkeletonTests.test_create_training_run_rejects_training_index_missing_condition_evidence，验证训练索引缺 conditioning 证据时显式失败。
  - 脚本与命令:
    - 不适用。
- 调用链 / 实现流程：
  `create_training_run()` -> `_validate_training_config()` -> `_validate_dataset_contract()` / `_validate_training_objective_contract()` -> `_training_plan_manifest()` -> `_training_plan_stages()` -> 写出 `training_plan.json`
- 外部关键依赖：
  - 无。
- 参考行号：
  - src/he_wsi_generator/models/training.py 280-546，训练配置、dataset contract 和 objective contract 校验。
  - src/he_wsi_generator/models/training.py 549-638，training plan artifact 与三阶段计划。
  - tests/test_models_generation.py 282-326，主功能测试断言 run / plan / checkpoint 闭环。
- 验证命令：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_writes_manifest_and_untrained_checkpoint -v`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_version -v`
- 更新时间：2026-05-25 17:07

### 7.3 Anchor presets

UI 可以提供四个预设，但底层仍是连续变量：

| 预设 | `structure_anchor` 默认值 | 语义 |
|---|---:|---|
| `rescan_simulation` | `0.95` | 同一源 WSI 的重扫描/重染色模拟 |
| `structure_preserving` | `0.80` | 保留源结构，允许局部重绘 |
| `layout_recombination` | `0.50` | 源结构与 prior 混合 |
| `fully_de_novo` | `0.05` | 不绑定单张源 WSI，使用 learned priors 生成 |

这些默认值是 UI 和配置起点，不代表研究结论。用户可以输入任意 0 到 1 的值，非法值必须报错。

### 7.4 推理与 OME-TIFF 重建

生成顺序固定为 `1/32 -> 1/16 -> 1/4 -> 1/1`。每层生成完成后应保存中间状态，以支持失败恢复和 QC 诊断。

推理默认：

| 参数 | 默认 |
|---|---|
| `sample_steps` | `50` |
| `overlap_px_40x` | `64` |
| `tile_traversal` | `row_major_with_resume_index` |
| `blending` | `overlap_weighted_average` |
| `write_mode` | `chunked_pyramid_write` |

若生成中断，系统应能通过 run manifest 判断已完成 tile 和未完成 tile。不得把不完整 OME-TIFF 标记为 `pass`。

Implementation Trace:
- 状态：部分实现（v0.72.32）。`smoke-cascade`、`torch-diffusion-smoke` 和 `production-tile-stream` 均能生成四层 OME-TIFF 输出链路；production tile-stream 已按 pyramid tile grid 逐 tile 物化磁盘 tile source，并可在 OME 发布前复用已完成 tile。当前 writer transaction manifest 支持原子发布审计，可在上次 `started` transaction 留下完整临时 OME-TIFF 时验证并发布该临时文件，也可在既有 `completed` transaction 与当前 target/manifest/shape 匹配时验证并复用已发布目标 OME-TIFF；v0.72.30 在正常完整写出前执行磁盘空间 preflight，空间不足时在 tile iterator 开始前失败并记录 transaction；v0.72.32 在正常完整 tile iterator 写出路径生成 progress sidecar，记录 planned/yielded/completed tile 数、当前 level/tile grid、last tile 和失败原因，并在 transaction/report/diagnostics 中保留 progress summary；v0.72.27 让外部 production tile backend 在每个 tile 执行前读取稳定 request manifest；v0.72.28 允许操作者显式重试 failed tile source record，但默认仍拒绝 failed manifest；v0.72.31 为每个新完成 tile 记录 request/backend execution/output evidence，并在 manifest/diagnostics 中汇总覆盖。同一 OME-TIFF 文件内部仍不可中断追加写入，progress sidecar 只用于中断诊断，磁盘空间 preflight 也不是精确 TIFF 文件大小预测。
- 主实现：
  - `src/he_wsi_generator/generation/executor.py::run_production_tile_stream_generation`，实现外部 production tile backend 到 OME-TIFF 重建的主流程。
  - `src/he_wsi_generator/outputs/ome_tiff.py::write_pyramid_ome_tiff_streaming_from_tile_sources`，按磁盘 tile source tiled iterator 写出 OME-TIFF 并原子发布。
  - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_progress_manifest`，创建 writer progress sidecar 初始结构，明确进度语义不是 OME 内部续写。
  - `src/he_wsi_generator/outputs/ome_tiff.py::_record_streaming_progress_tile`，在每个 tile yield 给 `tifffile` 前更新进度 sidecar。
  - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_disk_space_report`，在正常完整写出前生成磁盘空间预算报告。
  - `src/he_wsi_generator/outputs/ome_tiff.py::_recover_completed_streaming_target`，在 completed transaction 与当前 target/manifest/plan 匹配时验证并复用已发布目标 OME-TIFF，避免重复 tile iterator 写出。
  - `src/he_wsi_generator/outputs/ome_tiff.py::_recover_started_streaming_temporary`，在 started transaction 与当前 target/manifest/plan 匹配时发布完整临时 OME-TIFF，避免重复 tile iterator 写出。
- 完整依赖：
  - 入口与编排：
    - `src/he_wsi_generator/cli_commands.py::run_command`，根据 backend 分发 smoke、torch-smoke 或 production tile-stream 生成。
    - `src/he_wsi_generator/generation/executor.py::run_smoke_generation`，维护 smoke tile execution 和 direct tile source resume。
    - `src/he_wsi_generator/generation/executor.py::run_torch_diffusion_smoke_generation`，将四层 torch smoke preview 物化为磁盘 tile source 后写出 OME-TIFF。
  - 输入契约：
    - `src/he_wsi_generator/generation/planner.py::create_generation_plan`，统一校验 checkpoint 可推理性和 backend compatibility。
    - `src/he_wsi_generator/generation/production_streaming.py::load_external_tile_backend_contract`，校验 production tile backend command contract。
  - 输出契约：
    - `src/he_wsi_generator/generation/tiling.py::validate_resumable_tile_manifest`，校验 smoke tile execution resume 语义。
    - `src/he_wsi_generator/schemas.py::validate_generation_output_diagnostics`，校验 writer/tile/source/QC summary、writer 恢复复用布尔字段、`disk_space_preflight`、`progress_summary` 和 `tile_source.backend_execution_summary`。
  - 核心逻辑：
    - `src/he_wsi_generator/generation/production_streaming.py::materialize_production_tile_sources`，逐 tile 调用外部 backend 并维护 `production_tile_source_manifest.json`，同时写入 request/backend execution/output evidence。
    - `src/he_wsi_generator/generation/production_streaming.py::_load_resumable_tile_source_manifest`，校验并恢复 production tile source manifest。
    - `src/he_wsi_generator/generation/production_streaming.py::_execute_tile_backend_command`，在每个 tile 调用外部 backend 前写出 request manifest，展开 `{tile_request_path}`，并记录 command/cwd/return code/timeout/duration/stdout/stderr preview。
    - `src/he_wsi_generator/generation/production_streaming.py::_tile_request_manifest`，构造 production tile request 输入合同。
    - `src/he_wsi_generator/generation/production_streaming.py::_ensure_completed_record`，校验 production RGB/mask tile 并生成输出文件 evidence。
    - `src/he_wsi_generator/generation/production_streaming.py::_backend_execution_summary`，汇总 completed tile 的 request/execution/output evidence 覆盖。
    - `src/he_wsi_generator/generation/executor.py::_generation_output_diagnostics`，汇总 writer、tile execution/source 和 QC 状态。
    - `src/he_wsi_generator/generation/executor.py::_tile_source_summary`，把 backend execution summary 写入 diagnostics。
    - `src/he_wsi_generator/generation/executor.py::_writer_summary`，将 writer transaction manifest、atomic publish、`recovered_from_temporary`、`reused_existing_target`、`disk_space_preflight` 和 `progress_summary` 汇总到 diagnostics。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_tile_iterator_streaming_report`，把 preflight 摘要放入 streaming write report。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_progress_manifest`，记录 planned level/tile 数、target/temporary path、tile source manifest path 和 `progress_semantics`。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_record_streaming_progress_tile`，记录 current level、tile grid position、last tile 和 yielded/completed tile count。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_finish_streaming_progress_manifest`，把 progress sidecar 标记为 completed 或 failed，并写入 failure reason。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_progress_summary`，生成 transaction/report/diagnostics 共用的进度摘要。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_transaction_manifest`，把 preflight 摘要、progress manifest path 和 progress summary 写入 completed 或 failed transaction。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_load_existing_streaming_transaction_manifest`，读取既有 writer transaction manifest，供发布阶段恢复判断。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_is_recoverable_completed_transaction`，拒绝非 completed、失败状态、target 缺失或当前 plan 不匹配的已发布目标复用候选。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_streaming_transaction_matches_current_plan`，统一校验 transaction manifest 类型、writer 类型、目标路径和 tile source manifest 路径。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_read_validated_streaming_ome_level_shapes`，校验临时 OME-TIFF 可读且 pyramid shapes 与当前 plan 一致。
  - 配置与默认值：
    - `configs/generation.default.json`，保留 `1/32 -> 1/16 -> 1/4 -> 1/1`、512 tile 和默认 seed/anchor 参数。
  - 错误处理：
    - `src/he_wsi_generator/generation/production_streaming.py::ProductionTileStreamError`，拒绝 failed tiles、manifest mismatch、坏 `.npy` tile、坏 mask tile 和外部命令失败。
    - `src/he_wsi_generator/outputs/ome_tiff.py::OutputWriteError`，拒绝不完整 tile source、pyramid order/shape 错误、磁盘空间不足和写出失败。
  - 输出与持久化：
    - `src/he_wsi_generator/generation/production_streaming.py::_write_json`，持续写出 production tile source manifest 状态。
    - `src/he_wsi_generator/generation/production_streaming.py::_write_json`，写出 `production_tile_requests/*.request.json`。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_write_streaming_transaction_manifest`，写出 OME-TIFF streaming transaction manifest。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_build_streaming_transaction_manifest`，记录 started/completed/failed、`resume_capable=false`，并在恢复发布时记录 `recovery_action`。
    - `src/he_wsi_generator/outputs/ome_tiff.py::_write_streaming_progress_manifest`，写出 `<target>.progress.json`。
    - `src/he_wsi_generator/metadata/archive.py::archive_sample`，写出 per-sample metadata/QC/batch index。
  - 测试覆盖：
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_writes_external_backend_tiles`，验证 production tile-stream 输出闭环及 request/backend execution/output evidence。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_writes_tile_request_manifests`，验证 production tile request manifest 被外部 backend 消费。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_production_tile_stream_generation_retries_failed_tile_source_manifest_when_requested`，验证 failed tile 默认拒绝、显式 retry 后完成输出并保留 retry 审计字段。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_run_smoke_generation_tile_streaming_resumes_partial_tile_source_manifest`，验证 smoke direct tile source resume。
    - `tests/test_generation_runner.py::GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer`，验证 CLI tile-streaming writer，并断言默认 diagnostics writer 恢复复用字段为 false。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_publishes_recovered_temporary_ome`，验证完整临时 OME-TIFF 的 recovery publish，不调用 tile iterator。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_reuses_completed_target_ome`，验证 completed transaction 已发布目标 OME-TIFF 的 validation reuse，不调用 tile iterator。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_records_transaction_manifest`，验证 successful writer transaction 引用 progress sidecar，progress status/counts/last tile 与 report 一致。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_failed_transaction_preserves_target`，验证 writer 失败保留原目标文件，failed transaction/progress sidecar 记录失败前进度和 failure reason。
    - `tests/test_schemas.py::SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract`，验证 diagnostics schema 接受并校验 writer progress summary。
  - 脚本与命令：
    - 不适用；本轮不新增脚本。
- 调用链 / 实现流程：
  generation config + prior + checkpoint -> `create_generation_plan` -> tile request manifest + backend execution evidence + tile/source materialization -> tiled iterator OME writer（必要时复用已发布目标 OME，或发布上次完整临时 OME；正常完整写出时记录 progress sidecar） -> mask/QC/archive -> diagnostics
- 外部关键依赖：
  - `numpy`，用于 tile source、mask 和 QC 抽样。
  - `tifffile`，用于 OME-TIFF pyramid 写出和发布前校验。
- 参考行号：
  - `src/he_wsi_generator/generation/executor.py` 420-530，production tile-stream plan、tile source、writer、mask 和 QC 编排。
  - `src/he_wsi_generator/generation/executor.py` 831-863，diagnostics tile source summary 透传 backend execution summary。
  - `src/he_wsi_generator/generation/production_streaming.py` 263-365，production tile grid manifest、`tile_request_path`、request manifest type、GB 估算和恢复语义。
  - `src/he_wsi_generator/generation/production_streaming.py` 380-474，resume manifest 对 `request_manifest_type` 和 `tile_request_path` 的不可变校验。
  - `src/he_wsi_generator/generation/production_streaming.py` 77-167，production tile source 物化与 request/backend/output evidence 写入。
  - `src/he_wsi_generator/generation/production_streaming.py` 477-568，request JSON 写出、命令占位符、外部命令执行和 execution evidence 构造。
  - `src/he_wsi_generator/generation/production_streaming.py` 648-725，output evidence 校验与 backend execution summary 汇总。
  - `src/he_wsi_generator/generation/production_streaming.py` 914-926，文件大小与 SHA-256 evidence 构造。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 123-318，tile iterator streaming writer、transaction/progress manifest、completed target reuse、临时 OME 发布恢复和 `resume_capable=false` 报告。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 904-1112，tile iterator progress sidecar 构造、更新、完成/失败收口和 summary 生成。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 857-980，existing transaction 读取、completed/started recovery 判断、target/manifest 匹配和 OME shape 校验。
  - `src/he_wsi_generator/outputs/ome_tiff.py` 1275-1318，`recovery_action`、`disk_space_preflight` 和 `progress_summary` transaction manifest 字段。
  - `src/he_wsi_generator/generation/executor.py` 769-805，diagnostics writer summary 透传 progress manifest path 和 progress summary。
  - `src/he_wsi_generator/schemas.py` 393-425，diagnostics writer progress summary 校验。
  - `src/he_wsi_generator/schemas.py` 429-458，diagnostics backend execution summary 校验。
  - `src/he_wsi_generator/schemas.py` 337-355，diagnostics writer summary 恢复复用布尔校验。
  - `tests/test_outputs_qc_archive.py` 621-701，completed transaction 已发布目标 OME 验证复用测试。
- 验证命令：
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - `conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/generation/production_streaming.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py`
  - `conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v`
  - `conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - `git diff --check`
- 验证结果：`conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v` 本轮已执行通过，`Ran 84 tests in 3.295s OK`；`outputs/ome_tiff.py` / `generation/executor.py` / `schemas.py` py_compile 通过，无输出；默认 generation config 校验输出 `generation-config valid: configs/generation.default.json`；`git diff --check` 通过，无输出。
- 更新时间：2026-05-25

## 8. QC 与非复制报告

QC 输出分为 WSI 级、tile 级和 mask-region 级。状态固定为 `pass`、`warning`、`fail`。

| QC 项 | 粒度 | 默认处理 |
|---|---|---|
| 文件完整性 | WSI | 硬错误可直接 fail |
| pyramid 一致性 | WSI | 层级缺失或坐标错位 fail |
| 颜色 / stain 分布 | WSI/tile | 训练分布外 warning 或 fail |
| focus / blur | tile | 严重离群 fail |
| mask-image consistency | mask-region | 严重错配 fail |
| seam score | tile boundary | 超阈值 warning 或 fail |
| style consistency | WSI | 同 WSI 风格跳变 warning |
| non-copy report | WSI | 强制记录，不自动 fail |

轻量非复制报告包括 thumbnail 相似性、组织轮廓相似性、mask 布局相似性和全局 embedding 相似性。第一版不做全量 patch nearest-neighbor 检索，也不把相似性自动作为 fail 条件，因为高 anchor 模式本来就应与 source WSI 高度相关。

Implementation Trace:
- 状态：部分实现。`qc.json` 仍是详细 QC 与 non-copy report 的主产物；已实现文件/OME 层级、颜色均值/动态范围、stain/focus proxy、writer tile-grid seam proxy、mask-image tissue alignment proxy、reference distribution、non-copy 摘要和 diagnostics `qc_summary`。专家级语义 QC、production stain/focus/seam 模型和全量 patch nearest-neighbor 仍未完成。
- 主实现：
  - `src/he_wsi_generator/qc/engine.py::build_qc_report`，核心 QC report builder，输出 WSI/tile/mask-region 三级 status、metrics 和 non-copy report。
  - `src/he_wsi_generator/qc/engine.py::_image_quality_metrics`，读取 OME-TIFF 首层并生成 WSI/tile 图像质量 metrics。
- 完整依赖：
  - 入口与编排：
    - `src/he_wsi_generator/generation/executor.py::_generation_output_diagnostics`，把 QC summary 与 writer/tile/source 输出状态编排到 run-level diagnostics。
    - `src/he_wsi_generator/generation/executor.py::_qc_summary`，从 QC report 提取 overall、level status 和 non-copy report 摘要。
  - 输入契约：
    - `src/he_wsi_generator/qc/engine.py::build_qc_report`，要求 `generated_id`、WSI 路径、mask 路径、pyramid report、non-copy items 和可选 reference/context。
    - `src/he_wsi_generator/qc/engine.py::_select_qc_reference_thresholds`，校验并选择全局或分层 QC reference thresholds。
  - 输出契约：
    - `src/he_wsi_generator/schemas.py::validate_qc_report`，校验 QC JSON 的三层结构、status 和 metrics 列表。
    - `src/he_wsi_generator/schemas.py::validate_generation_output_diagnostics`，校验 diagnostics 中 `qc_summary` 的 status 契约。
  - 核心逻辑：
    - `src/he_wsi_generator/qc/engine.py::_stain_color_separation_proxy`，计算 RGB 通道平均分离度。
    - `src/he_wsi_generator/qc/engine.py::_focus_edge_density_proxy`，计算局部边缘对比。
    - `src/he_wsi_generator/qc/engine.py::_seam_score_proxy`，计算 writer grid seam proxy。
    - `src/he_wsi_generator/qc/engine.py::_mask_image_tissue_alignment_metric`，计算 mask 与图像组织区域一致性 proxy。
    - `src/he_wsi_generator/qc/engine.py::_apply_reference_thresholds`，让 QC reference distribution 覆盖 metric status。
  - 配置与默认值：
    - `src/he_wsi_generator/qc/engine.py::_stain_color_separation_metric`，定义 stain proxy 默认 fail/warning/pass 阈值。
    - `src/he_wsi_generator/qc/engine.py::_focus_edge_density_metric`，定义 focus proxy 默认 fail/warning/pass 阈值。
    - `configs/generation.default.json`，记录当前 schema version 和默认生成配置。
  - 错误处理：
    - `src/he_wsi_generator/qc/engine.py::QCReferenceError`，暴露 reference distribution、sampled mask 和 tissue overview 契约错误。
    - `src/he_wsi_generator/qc/engine.py::_image_quality_metrics`，在 WSI 不可读或图像 shape 不支持时返回 fail metric。
  - 输出与持久化：
    - `src/he_wsi_generator/qc/engine.py::write_qc_report`，写出 schema 校验后的 `qc.json`。
    - `src/he_wsi_generator/metadata/archive.py::archive_sample`，把 `qc.json` 与 metadata 和 batch index 归档。
  - 测试覆盖：
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_build_qc_report_reads_outputs_and_records_quality_metrics`，验证正常 QC 输出包含 stain/focus/seam/mask-image metrics。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_build_qc_report_flags_low_stain_and_focus_proxy`，验证近单色和无局部边缘对比输出触发 fail。
    - `tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_build_qc_report_uses_writer_tile_grid_for_seam_proxy`，验证 writer grid seam proxy。
    - `tests/test_qc_reference.py`，验证 QC reference artifact 构建。
  - 脚本与命令：
    - 不适用；本轮不新增脚本。
- 调用链 / 实现流程：
  `run_generation` / `archive_sample` 调用 QC -> `build_qc_report` -> `_image_quality_metrics` -> stain/focus/seam/mask metrics -> `_apply_reference_thresholds` -> `validate_qc_report` -> `write_qc_report` / diagnostics summary
- 外部关键依赖：
  - `numpy`，用于 RGB、mask 和 proxy 指标计算。
  - `tifffile`，用于读取 OME-TIFF 首层图像。
- 参考行号：
  - `src/he_wsi_generator/qc/engine.py` 13-83，构建 QC report、合并 status 并校验 schema。
  - `src/he_wsi_generator/qc/engine.py` 260-311，读取 OME-TIFF 首层并生成 WSI/tile 图像质量 metrics。
  - `src/he_wsi_generator/qc/engine.py` 642-691，新增 stain/focus proxy 与默认阈值。
  - `tests/test_outputs_qc_archive.py` 1063-1147，覆盖正常 metrics 和低 stain/focus fail。
- 验证命令：
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_flags_low_stain_and_focus_proxy -v`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_reads_outputs_and_records_quality_metrics -v`
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_version -v`
  - `mamba run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 更新时间：2026-05-25 16:52

## 9. 本地桌面控制台

PySide6 控制台采用单页布局，至少包含以下区域：

| 区域 | 功能 |
|---|---|
| 数据输入 | 选择 WSI manifest、annotation 文件、输出目录 |
| Label mapping | 识别 PNG/numpy 编号并弹窗映射到 6 类 |
| Prior / model | 选择学习 prior、加载 checkpoint 或启动训练 |
| 生成参数 | 设置生成数量、anchor、source WSI、seed、style strategy、采样参数 |
| 任务状态 | 展示 queued、running、completed、failed、cancelled |
| QC / 输出 | 展示 QC 状态、metadata 路径、OME-TIFF 路径和 batch index |

UI 必须把用户配置保存为 JSON/YAML。所有错误应显示为可操作信息，例如缺少 MPP、mask 未映射、checkpoint 缺失、输出目录无权限，而不是只显示通用失败。

## 10. 测试与验收

第一版开发应至少准备以下测试：

| 测试 | 验收标准 |
|---|---|
| schema validation | 输入 manifest、label mapping、generation config、metadata、QC JSON 均能校验 |
| WSI read smoke test | 能读取一个小型 WSI 或 fixture，并输出 pyramid metadata |
| mask alignment test | mask 与 WSI 坐标转换可复现 |
| PatchEmbedder interface test | 缺 checkpoint 显式报错，合法 checkpoint 输出 embedding metadata |
| prior artifact test | prior manifest 能记录版本、输入数据和 seed |
| generation config test | anchor、cascade、tile size、seed 等字段完整 |
| OME-TIFF write smoke test | 能写出小尺寸 pyramid OME-TIFF |
| QC JSON test | QC 输出包含三级状态、指标和 non-copy report |
| output diagnostics test | generation run 写出 diagnostics manifest，metadata/run summary/返回值均引用该路径，schema/CLI validator 可校验 |
| UI config test | UI 生成的配置可被 CLI/core 读取 |

Implementation Trace:
- 状态：部分实现（v0.72.32）。已新增 production failed tile retry/resume 主功能测试、production tile request manifest 主功能测试、production tile-stream 主功能测试、production tile backend execution evidence 主功能测试、output diagnostics schema/CLI validator 测试、smoke/torch tile-streaming 输出测试、OME streaming started transaction temporary publish recovery 主功能测试、OME streaming completed target validation reuse 主功能测试、OME streaming disk-space preflight 主功能测试，以及 OME streaming writer progress evidence 主功能测试；本轮按里程碑节奏集中验证 outputs / generation / schema / CLI / version 相关闭环，不增加额外 helper 级测试。真实 SVS 全链路本轮未重跑，仍引用历史 v0.72.1 证据。
- 代码：`tests/test_generation_runner.py`、`tests/test_schemas.py`、`tests/test_cli.py`、`tests/test_torch_training.py`、`tests/test_outputs_qc_archive.py`、`tests/test_ui.py`、`tests/test_ui_workflow.py`。
- 本轮新增测试重点：`tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_records_transaction_manifest` 验证成功 transaction/progress sidecar/report summary；`tests/test_outputs_qc_archive.py::OutputQCArchiveTests.test_write_pyramid_ome_tiff_streaming_from_tile_sources_failed_transaction_preserves_target` 验证 writer 失败保留目标文件并记录 failed progress；`tests/test_generation_runner.py::GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer` 验证 diagnostics writer progress summary；`tests/test_schemas.py::SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract` 验证 schema 接受 progress summary。开发过程中两个 outputs 主功能测试先在旧实现上 RED 失败，报错 `KeyError: 'progress_manifest_path'`，实现后转绿。
- 验证：`conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v` 通过，`Ran 84 tests in 3.295s OK`；`conda run -n MultiCenterWSIGenerator python -m py_compile src/he_wsi_generator/outputs/ome_tiff.py src/he_wsi_generator/generation/executor.py src/he_wsi_generator/schemas.py` 通过，无输出；`conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli validate generation-config configs/generation.default.json` 通过，输出 `generation-config valid: configs/generation.default.json`；收束审计补充执行 `conda run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v` 通过，`Ran 300 tests in 28.868s OK`；`conda run -n MultiCenterWSIGenerator python -m he_wsi_generator.cli --version` 输出 `v0.72.32`；`git diff --check` 通过，无输出。editable install、包元数据和真实 SVS 全链路本轮未执行，原因是本轮按 OME streaming writer progress evidence 里程碑和工作区收束做集中验证，未进入发布打包或真实数据全链路验收。

文档层面的验收标准是：开发者可以根据本附录创建任务拆分、schema 校验、模块接口和第一版 CLI/UI 骨架，而不需要重新决定系统主线。

## 11. v1 明确不做的内容

第一版开发指南不要求实现以下内容：

- IHC、免疫荧光或特殊染色。
- 临床标签、分子标签条件输入。
- 下游分类/分割训练验证。
- 真人病理专家盲评。
- DiT 主干实现。
- 文本 embedding 直接进入扩散模型。
- 全量 patch nearest-neighbor 非复制检索。
- 云端 Web 上传式系统。

这些内容可以作为后续 `v0.6.0+` 开发规格扩展，但不应混入当前 v1 核心工程边界。

## 12. 第一版开发里程碑

| 阶段 | 目标 | 可验收产物 |
|---|---|---|
| M1 | 数据契约与 schema 校验 | manifest / mapping / config / metadata / QC 示例和校验器 |
| M2 | WSI 与 mask I/O | WSI metadata、thumbnail、mask 对齐和 label mapping |
| M3 | patch embedding 与伪 mask | PatchEmbedder 接口、embedding 缓存、cluster report |
| M4 | prior artifact | layout/style/texture/QC prior manifest |
| M5 | 训练与生成骨架 | LDM U-Net 训练入口、cascade generation config |
| M6 | OME-TIFF 与 QC | pyramid 写出、QC JSON、batch JSONL |
| M7 | PySide6 控制台 | 单页任务配置、运行状态和输出查看 |

这些里程碑是工程实现顺序，不是研究结果排序。任何阶段都应优先保证契约、日志和错误清晰，而不是先追求视觉效果。
