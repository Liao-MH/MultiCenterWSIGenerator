# MultiCenterWSIGenerator

- 当前版本：v0.72.3
- 当前状态：训练索引、RGB/mask training batch loader、WSI tissue overview、统计型 layout/mask、style/texture prior、prior manifest builder、generation condition packet 与 smoke/PyTorch diffusion smoke 条件包记录、sampled style/texture policy condition packet 条件摘要接入、sampled style/texture policy generation 输出摘要保留、PyTorch diffusion smoke 条件通道注入、PyTorch diffusion smoke cross-scale condition、PyTorch VAE smoke latent autoencoder、smoke latent U-Net denoiser、VAE latent diffusion smoke training/sampling、PyTorch diffusion smoke generation、generation tile traversal / overlap blending 基础设施、`blend_rgb_tiles` 的 channel-wise 累积内存优化、可恢复 tile manifest contract、smoke tile resume execution、OME-TIFF chunked write audit、磁盘 `.npy` tile source contract 校验、磁盘 tile source 内存组装写出、磁盘 tile source tiled iterator streaming 写出、smoke 四层 tile source streaming 写出（tile-streaming 路径已按 pyramid level 顺序逐层物化）、streaming writer pyramid level contract、可审计 sampled style/texture policy artifact、QC reference robust IQR/MAD z-score estimator、outlier audit、显式分层阈值 artifact 与运行时 exact-match stratum QC 消费、自动 QC、文件级 `qc_review` 审阅工作流、`qc-review` 通用校验入口、本地 job runner/CLI 任务取消/查看/列表/cwd/输出摘要 metadata/QC/review 契约校验、可交互 PySide6 单页配置页、GUI 内同步执行/刷新 queued job 与输出摘要查看阶段；v0.72.3 另外完成当前环境真实 SVS smoke/proxy 复跑验证
- GitHub 仓库：[Liao-MH/MultiCenterWSIGenerator](https://github.com/Liao-MH/MultiCenterWSIGenerator)

本项目用于开发一个面向 H&E 染色 Whole Slide Image（WSI）的本地化数据生成器。最终系统目标是从真实 WSI 学习组织 layout、疾病无关区域 mask、成像风格和多倍率纹理分布，生成新的 OME-TIFF pyramid WSI，并同步输出 mask、metadata、QC JSON 与 batch JSONL index。

## 当前已实现

v0.72.3 在 v0.72.1 sampled policy condition packet 集成基础上继续补齐输出审计链，并完成当前环境真实 SVS smoke/proxy 复跑验证：smoke generation metadata、`generation_run.json`、torch diffusion smoke sample manifest 和 torch smoke generation metadata/run summary 现在会继续保留 `sampled_style_policy` / `sampled_texture_policy` 的 selected style/token 摘要、sample id、artifact path、seed、selection policy 和 limitations；缺失关键摘要字段会显式失败。`run-generation --backend smoke-cascade --wsi-writer tile-streaming` 现在按 high-to-low pyramid 顺序逐层物化四层 smoke pyramid level，再写出 tile source manifest 和四层 OME-TIFF；`blend_rgb_tiles` 现在也改为按 channel-wise 累积减少中间内存峰值。它仍基于内存中生成的 smoke canvas，不支持 OME-TIFF 中断续写。当前能力仍是可审计摘要贯通，不是 production style encoder、texture codebook、VQ-VAE 或生成模型。

- Python core package：`he_wsi_generator`
- CLI 入口：`he-wsi-gen`
- Schema validator：
  - input manifest
  - label mapping
  - generation config
  - per-WSI metadata
  - QC report
  - QC review artifact
- 默认生成配置：`configs/generation.default.json`
- WSI metadata reader：
  - `OpenSlideReader`：真实 WSI 读取入口，缺文件、缺 MPP 或 OpenSlide 无法读取时显式报错
  - `FixtureImageSlideReader`：仅用于小型 PNG/TIFF smoke test
- Manifest audit：读取 manifest 后输出 WSI 尺寸、level、MPP、倍率、backend 和错误状态
- Mask utilities：读取 PNG/TIFF/numpy mask 编号，应用 6 类 label mapping，并拒绝未映射编号
- Mask alignment：基于 `transform_to_level0` 的 scale/offset 校验 mask 是否落在 WSI level0 范围内
- Patch embedding：
  - `CheckpointPatchEmbedder`：要求用户提供 JSON checkpoint，缺失或损坏时显式报错
  - `FixturePatchEmbedder`：仅用于 smoke test，metadata 标记 `embedding_confidence=low`
  - embedding cache：保存/读取 `.npy` embedding array 与 JSON metadata
  - cluster report：输出 labels、cluster counts、inertia、embedding count 和 embedding dim
- Prior artifact：
  - prior manifest 记录 `prior_id`、版本、创建时间、训练输入、随机种子和 artifact 清单
  - artifact 清单覆盖 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`
  - 每个 artifact 记录路径、kind、sha256、size_bytes 和 metadata
  - 校验时拒绝缺失 artifact、缺失文件、hash 不匹配、非法 seed、非法 artifact type 和重复路径
  - `build-wsi-tissue-overview` 从真实 WSI thumbnail 构建 `wsi_tissue_overview` JSON，记录 RGB 统计、组织占比、组织 bounding box 和连通组件数量
  - `build-prior-manifest` 从四类 prior artifact JSON 构建统一 `prior_manifest.json`，并记录 artifact schema version、类型与关键摘要
  - `build-layout-mask-prior` 从 training-index 读取真实 mask tile，输出 6 类比例、tile-level layout records 和横向/纵向邻接计数
  - `sample-layout-mask` 从统计型 `layout_mask_prior` 采样可复现 `.npy` layout mask，并可用 `wsi_tissue_overview` 的 thumbnail bounding box 限制非背景 footprint
  - `build-style-prior` 从 training-index 读取真实 RGB tile，输出 per-channel RGB mean/std/min/max、归一化统计和 tile-level style records
  - `build-texture-prior` 从 embedding cache 和 cluster report 读取真实 patch embedding，输出 cluster prototype、global embedding 统计和 representative embedding index
  - `sample-style-policy` 从 `style_prior` 以 deterministic seed policy 选择 tile-level style record，输出 `sampled_style_policy` JSON
  - `sample-texture-policy` 从 `texture_prior` 以 deterministic seed policy 选择 texture prototype，输出 `sampled_texture_policy` JSON
- Training / generation skeleton：
  - `init-training-run` 校验训练配置和 prior manifest，并写出 training run manifest
  - `build-training-index` 从 manifest audit 和 label mapping 写出四层 cascade 训练样本 JSONL
  - training index 记录 40x tile 坐标、cascade level、mask annotation、6 类 mapping、source metadata 和 conditioning 约定
  - `build-condition-packet` 从 generation config 与 prior manifest 构建 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 条件对象；若 prior manifest 包含 `wsi_tissue_overview`，会把低倍组织轮廓 proxy 摘要写入 `conditions.layout`；若传入 `--sampled-layout-mask`，会把 sampled mask 写入 `conditions.mask`；若传入 `--sampled-style-policy` / `--sampled-texture-policy`，会把 sampled policy artifact 写入 `artifact_inputs` 并覆盖对应 style/texture 条件摘要
  - `inspect-training-batch` 从 training-index JSONL 读取 batch，裁剪 `.npy` mask tile，并按 label mapping 转成项目 6 类 id
  - `inspect-training-batch --include-image` 可同步读取 `fixture-image` 或 `openslide` backend 的 RGB image tile
  - training batch summary 记录 sample ids、cascade levels、WSI ids、tile records、mask/image batch shape、mask class ids、conditioning 和 source records
  - `train-torch-smoke` 执行真实 PyTorch smoke training loop，以 6 类 mask one-hot 为条件输入、RGB tile 为重建目标，包含 `torch.nn.Module`、loss、optimizer、反向传播和 `.pt` checkpoint 写出
  - `train-torch-vae-smoke` 执行真实 PyTorch VAE smoke training loop，从 RGB tile 训练 encoder/reparameterization/decoder，写出 latent/reconstruction preview、checkpoint 和 manifest
  - `train-torch-diffusion-smoke` 执行真实 DDPM-style PyTorch smoke training loop，可在下采样 RGB proxy latent 或 VAE smoke latent 上加噪，并以 previous-scale RGB proxy、mask、timestep 和固定 condition feature channels 通过 smoke latent U-Net denoiser 预测噪声
  - `sample-torch-diffusion-smoke` 从 diffusion smoke checkpoint、training-index mask 条件、可选 previous-scale `.npy` preview 和可选 condition packet 执行反向 DDPM-style smoke sampling；对 VAE latent checkpoint 会调用 VAE decoder 写出 RGB preview，并记录 cross-scale schema/source、condition feature schema/vector 和 denoiser architecture
  - PyTorch smoke checkpoint manifest 记录 torch version、目标类型、输入/输出通道、denoiser architecture、cross-scale condition schema、condition feature schema 或 VAE latent schema、训练参数、image batch summary、diffusion schedule/loss summary、checkpoint path/hash，并明确 `usable_for_inference=false`
  - checkpoint manifest placeholder 明确标记 `status=not_trained` 和 `usable_for_inference=false`
  - `plan-generation` 在 checkpoint 已训练时生成四层 cascade plan
  - generation plan 记录 tile traversal、resume index、overlap、blending 和 write mode，并写入物化的 `tile_traversal_plan`
  - `create_tile_traversal_plan` 按 40x canvas、512x512 tile 和 overlap 生成 row-major tile plan，记录 edge crop write region、tile status 和下一待处理 tile
  - `build_resumable_tile_manifest` / `update_resumable_tile_manifest` / `validate_resumable_tile_manifest` / `require_complete_tile_manifest` 提供可恢复 tile 状态 contract，记录 completed/pending/failed 计数、`resume_index`、`next_tile_index`、attempt count、输出路径和错误信息；不完整、失败、计数不一致或打破 row-major resume 语义的 manifest 会显式报错
  - `blend_rgb_tiles` 按 tile origin 将 RGB tile 写入 canvas，并对 overlap 区域执行权重平均；未覆盖完整 canvas、非法 origin 或非 uint8 RGB tile 会显式报错
- End-to-end smoke generation：
  - `run-generation --backend smoke-cascade` 复用 generation plan 校验并拒绝未训练 checkpoint
  - `run-generation --backend smoke-cascade` 写出 `tile_manifest.json`、`tile_source_manifest.json` 和 `tiles/tile-*.npy`，metadata 与 generation run summary 记录 manifest 路径；`--resume-tile-manifest` 可从已有 partial manifest 继续 pending tile，failed/gapped/missing completed tile 会显式失败
  - `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 可显式选择磁盘 tile source tiled iterator writer，并写出四层 `tile_source_manifest.streaming.json`、`streaming_tiles/*.npy` 和四层 OME-TIFF；generation run summary 记录 `write_mode=tile_iterator_streaming_write`、`production_streaming=true`、`resume_capable=false` 和四层 streaming write report；默认 `--wsi-writer array` 行为不变，`torch-diffusion-smoke` 不支持该 writer
  - `run-generation --backend smoke-cascade --condition-packet <condition_packet.json>` 会校验 condition packet，并在 metadata 与 generation run summary 中记录路径和条件摘要；若条件包包含 `wsi_tissue_overview`，最终输出也会保留该组织轮廓 proxy 摘要
  - 当 condition packet 的 `conditions.mask.source=sampled_layout_mask` 时，smoke generation 会读取对应 `.npy` mask，校验 0-5 类 id，并把它写为最终 `generated_mask/mask.npy`
  - `run-generation --backend torch-diffusion-smoke --condition-packet <condition_packet.json>` 会校验 condition packet 的版本、类型、必要条件对象和 `prior_id`，把条件摘要编码为空间条件通道，并把同一份摘要写入 sampler manifest、metadata 与 generation run summary
  - `run-generation --backend torch-diffusion-smoke` 按 `1/32 -> 1/16 -> 1/4 -> 1/1` 复用 PyTorch diffusion smoke sampler 执行四层级联 preview sampling，并写出 OME-TIFF、mask、metadata、QC 和 batch index
  - deterministic smoke backend 生成四层 cascade 图像、6 类 mask、OME-TIFF、metadata、QC 和 batch index
  - metadata 明确记录实际 smoke backend，避免伪装为 production diffusion 输出
- Output / QC / archive：
  - OME-TIFF writer 基于 `tifffile` 写出小型 pyramid，并在 `pyramid_report.chunked_write_audit` 记录 chunk plan、BigTIFF 决策、估算字节数和非生产流式写入限制
  - `write_pyramid_ome_tiff(..., tile_source_manifest=...)` 可校验磁盘 `.npy` tile source manifest，检查 expected tile count、level/tile index、路径存在、shape、dtype 和 completed 状态；pending、failed、missing、duplicate 或文件契约不一致会显式抛出 `OutputWriteError`
  - `write_pyramid_ome_tiff_from_tile_sources(...)` 可从磁盘 `.npy` tile source manifest 组装 pyramid 并写出 OME-TIFF，要求 level shape、tile origin、write region 和 coverage 明确且无 overlap/gap/越界；报告记录 `assembly_mode=in_memory_disk_tile_assembly`，仍不是 production streaming writer
  - `write_pyramid_ome_tiff_streaming_from_tile_sources(...)` 可从完整磁盘 `.npy` tile source manifest 按 tiled iterator 写出 OME-TIFF，不分配完整 level array；要求 `chunk_shape` 符合 tiled TIFF 约束、manifest levels 按 high-to-low resolution 顺序声明、每个 tile 精确映射到一个 TIFF tile grid cell、无 gap/overlap/越界，报告记录 `pyramid_order`、`level_order` 和 `resume_capable=false`
  - `pyramid_report.streaming_contract` 明确记录 `production_streaming=false`、`partial_contract_only=true`、tile source 覆盖率和限制，避免把当前内存数组 writer 误表述为 production 级 gigapixel streaming writer
  - 6 类 mask `.npy` 写出和 mask metadata
  - QC report builder 输出 WSI/tile/mask-region 三级状态、non-copy report 和轻量质量指标
  - QC 读取 OME-TIFF pyramid 首层，记录可读性、level count、RGB 均值、动态范围和清晰度 proxy
  - QC 读取 `.npy` mask，记录类别数量、类别 id、组织占比，并在 mask 与 WSI 尺寸错位时 fail
  - 若 generation condition summary 包含 `wsi_tissue_overview`，QC non-copy metrics 会记录 `wsi_tissue_fraction_reference_proxy`，审计生成 mask tissue fraction 与真实 thumbnail tissue fraction 的接近程度；其中 `reference.tissue_fraction` 保留源 artifact 原始数值精度，便于真实 SVS 交付核验
  - 若 condition summary 包含 `sampled_layout_mask`，QC non-copy metrics 会记录 `sampled_layout_mask_match_proxy`，逐像素审计最终 generated mask 是否忠实保留 sampled mask 条件
  - `build-qc-reference` 可从多个 QC JSON 抽取数值 metrics，使用 observed min/max range-margin、`robust_iqr` 或 `robust_mad_z_score` 估计器生成 `qc_reference_distribution` JSON，并可显式启用 `robust_iqr_filter` 过滤参考 QC 离群值且写入 `outlier_audit`；也可用 `--stratify-by` 按 QC report 元数据字段写出分层阈值和分层审计
  - QC 可消费 prior artifact 中的 `qc_reference_distribution`，按 metric 区间阈值输出 pass/warning/fail，并在 metric 中记录 reference 来源；启用 `stratification` 且 condition packet 提供匹配上下文时，按 exact stratum key 使用分层阈值并记录 `selection=stratified`、`stratum_key`、`stratification_fields` 和 `group_values`；上下文缺失、不完整或找不到 stratum 时回退全局阈值并记录 `selection=global_fallback` 与 `fallback_reason`
  - per-WSI `metadata.json` 写出前执行 schema 校验
  - `batch.jsonl` 追加 generated sample 索引
- UI controller：
  - UI config 覆盖 data input、label mapping、prior/model、generation parameters、task status、QC/output，并支持 `.json` / `.yaml` / `.yml`
  - job state 支持 `queued`、`running`、`completed`、`failed`、`cancelled`
  - local job runner 支持创建 job、同步执行本地命令、持久化 stdout/stderr、记录 return code 和时间戳
  - `run-local-job` / `cancel-local-job` / `inspect-local-job` / `list-local-jobs` CLI 支持本地 job 的执行、取消、查看、批量列表和 `cwd` 透传
  - job runner 对空 job id、空命令、重复 job id、未知 job id、非法状态和命令启动失败显式报错或落盘为 failed
  - output summary 从 metadata/QC JSON 提取 generated id、QC 状态和核心输出路径
  - PySide6 单页控制台可保存 generation config、创建 queued job、同步执行 queued job、刷新 job 状态，并展示 metadata/QC/可选 qc_review 输出摘要
  - `launch-ui` 需要可选 PySide6 依赖，缺依赖时明确报错
- 单元测试：`tests/`
- 版本断言：`VERSION`、package 常量和测试保持一致

## 快速开始

建议使用独立 conda 环境，不在主环境中安装依赖。本轮审计验证环境为 `MultiCenterWSIGenerator`：

```bash
conda create -n MultiCenterWSIGenerator -c conda-forge python=3.11 pip openslide
conda activate MultiCenterWSIGenerator
python -m pip install -e ".[embeddings,outputs,training,torch,ui,yaml,wsi]"
he-wsi-gen --version
he-wsi-gen validate generation-config configs/generation.default.json
```

上述完整环境已在当前机器验证：Python `3.11.15`、PyTorch `2.12.0+cu130`、CUDA 可用、GPU 为 `NVIDIA GeForce RTX 5060 Ti`，并通过 `python -m unittest discover -s tests -v` 的 `249` 个测试，同时完成当前环境真实 SVS smoke/proxy 复跑。若只需要最小 CLI/schema 功能，也可以安装基础包：

```bash
python -m pip install -e .
```

基础 schema/CLI 功能只依赖 Python 标准库。若要校验 YAML 文件，可单独安装可选依赖：

```bash
python -m pip install -e ".[yaml]"
```

若要使用 M2 的 OpenSlide、fixture image 和 mask 工具，可安装 WSI 相关可选依赖：

```bash
python -m pip install -e ".[wsi]"
```

若只使用 M3 的 embedding/cache/cluster 工具，可安装 embedding 相关可选依赖：

```bash
python -m pip install -e ".[embeddings]"
```

若要使用训练 batch loader，可安装训练输入相关可选依赖：

```bash
python -m pip install -e ".[training]"
```

若要运行 PyTorch smoke training，可在隔离 PyTorch 环境中安装：

```bash
python -m pip install -e ".[torch]"
```

若要使用 M6 的 OME-TIFF smoke writer 和输出归档工具，可安装输出相关可选依赖：

```bash
python -m pip install -e ".[outputs]"
```

若要启动 PySide6 本地控制台，可安装 UI 可选依赖：

```bash
python -m pip install -e ".[ui]"
```

不安装包时，也可以直接用源码路径运行：

```bash
PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

## CLI 用法

校验默认 generation config：

```bash
he-wsi-gen validate generation-config configs/generation.default.json
```

支持的 schema kind：

```text
manifest
input-manifest
label-mapping
generation-config
metadata
qc
qc-report
qc-review
```

生成默认配置文件：

```bash
he-wsi-gen init-generation-config path/to/generation-config.json
```

根据 manifest 读取 WSI 元数据并写出审计 JSON：

```bash
he-wsi-gen audit-manifest path/to/manifest.json --backend openslide --output path/to/audit.json
```

`fixture-image` 后端只用于小型 smoke test：

```bash
he-wsi-gen audit-manifest tests/fixtures/manifest.json --backend fixture-image --output audit.json
```

校验 prior manifest 及其引用的 artifact 文件：

```bash
he-wsi-gen validate-prior-manifest path/to/prior_manifest.json
```

从参考 QC 报告构建 `qc_reference_distribution`：

```bash
he-wsi-gen build-qc-reference path/to/qc-001.json path/to/qc-002.json \
  --metric mean_red \
  --metric rgb_dynamic_range \
  --metric mask_tissue_fraction \
  --estimator robust_mad_z_score \
  --outlier-policy robust_iqr_filter \
  --stratify-by metadata.cancer_type \
  --output path/to/qc_reference_distribution.json
```

默认估计器仍使用 observed min/max 和 range margin 生成 warning/fail 区间，默认 `--outlier-policy none` 不过滤任何参考样本，以保持既有行为兼容。传入 `--estimator robust_iqr` 时，输出会记录 Q1、median、Q3、IQR，并使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 作为 warning 区间、`[Q1 - 3.0*IQR, Q3 + 3.0*IQR]` 作为 fail 区间。传入 `--estimator robust_mad_z_score` 时，输出会记录 median、MAD、scaled MAD、warning z-score 和 fail z-score，并使用 `median ± 3*scaled_mad` / `median ± 6*scaled_mad` 生成 warning/fail 区间；零 MAD 时会使用有限非零 margin，避免阈值坍缩。传入 `--outlier-policy robust_iqr_filter` 时，builder 会先按每个 metric 的 IQR fence 排除离群参考样本，并在 `outlier_audit` 中记录原始/保留/排除样本数、filter fence 和被排除样本；过滤后样本数低于 `--min-samples` 会显式失败，不会回退到未过滤样本。传入一个或多个 `--stratify-by <dot.path>` 时，输出会新增 `stratification` 和 `strata`，每个 stratum 独立使用相同 estimator、outlier policy 与 `--min-samples` 规则估计阈值；分层字段缺失、为 `null`、为空字符串或不是字符串/数字会显式失败。结果可作为 prior manifest 的 `qc_reference_distribution` artifact，manifest metadata 会记录分层字段和 stratum 数量。

从真实 WSI thumbnail 构建 `wsi_tissue_overview`：

```bash
he-wsi-gen build-wsi-tissue-overview path/to/input-manifest.json \
  --backend openslide \
  --thumbnail-max-size 1024 \
  --output path/to/wsi_tissue_overview.json
```

该命令会通过指定 reader 读取 WSI metadata 和低倍 thumbnail，输出每张 WSI 的 thumbnail RGB 统计、轻量 tissue mask proxy、组织像素占比、组织 bounding box 和连通组件数量。当前产物用于审计低倍组织轮廓和后续 layout/mask prior / QC 接入；它不是语义分割、tumor/stroma 分类、6 类 mask 推断或可采样 layout generator。若 thumbnail 中没有检测到组织像素，命令会显式失败。

从训练 mask tile 构建统计型 `layout_mask_prior`：

```bash
he-wsi-gen build-layout-mask-prior path/to/training-index.jsonl \
  --batch-size 8 \
  --split train \
  --cascade-level 1/1 \
  --output path/to/layout_mask_prior.json
```

该命令会通过 training-index 读取真实 6 类 mask tile，输出全局类别 pixel count/fraction、non-background fraction、tile-level dominant class 和横向/纵向相邻类别计数。当前产物是可审计统计 JSON，可作为 prior manifest 的 `layout_mask_prior` artifact；它不是 mask diffusion 或 source-anchor layout mixing 模型。

从统计型 `layout_mask_prior` 采样一个可复现 layout mask artifact：

```bash
he-wsi-gen sample-layout-mask path/to/layout_mask_prior.json \
  --output-dir path/to/sampled-layout \
  --sample-id layout-001 \
  --height 512 \
  --width 512 \
  --random-seed 7 \
  --wsi-tissue-overview path/to/wsi_tissue_overview.json
```

该命令会写出 `sampled_layout_mask.npy` 和 `sampled_layout_mask.json`。未传 `--wsi-tissue-overview` 时，采样器按 `layout_mask_prior.class_fractions_by_id` 控制 6 类比例；传入时，会记录第一条 thumbnail tissue proxy 的 tissue fraction、bounding box 和连通组件数量，并将非背景区域限制在该低倍 bounding box 映射到输出 mask 后的 footprint 内。当前采样器是可审计、可复现的统计型结构条件生成器，不是 mask diffusion、语义分割模型或 production 级 de novo layout generator。

从训练 RGB tile 构建统计型 `style_prior`：

```bash
he-wsi-gen build-style-prior path/to/training-index.jsonl \
  --batch-size 8 \
  --split train \
  --cascade-level 1/1 \
  --output path/to/style_prior.json
```

该命令会通过 training-index 读取真实 RGB image tile，输出全局 RGB mean/std/min/max、归一化统计、tile-level mean RGB 和 source tile 记录。当前产物是可审计统计 JSON，可作为 prior manifest 的 `style_prior` artifact；它不是 trainable style encoder、VAE style latent 或风格迁移模型。

从统计型 `style_prior` 采样一个可复现 style policy artifact：

```bash
he-wsi-gen sample-style-policy path/to/style_prior.json \
  --output path/to/sampled_style_policy.json \
  --sample-id style-001 \
  --random-seed 7
```

该命令会写出 `sampled_style_policy.json`，记录被选中的 tile-level style record、RGB 统计引用和 deterministic selection policy。当前产物是可审计统计 policy artifact，不是 trainable style encoder、VAE style latent 或风格迁移模型。

从 embedding cache 和 cluster report 构建统计型 `texture_prior`：

```bash
he-wsi-gen build-texture-prior \
  --cache-dir path/to/embedding-cache \
  --cache-key slide-001 \
  --cluster-report path/to/cluster-report.json \
  --output path/to/texture_prior.json
```

该命令会读取真实 embedding cache 和聚类报告，输出 cluster-level texture prototype、全局 embedding mean/std、cluster counts 和 representative embedding index。当前产物是可审计统计 JSON，可作为 prior manifest 的 `texture_prior` artifact；它不是 trainable texture codebook、VQ-VAE 或 morphology token sampler。

从统计型 `texture_prior` 采样一个可复现 texture policy artifact：

```bash
he-wsi-gen sample-texture-policy \
  path/to/texture_prior.json \
  --output path/to/sampled_texture_policy.json \
  --sample-id texture-001 \
  --random-seed 7
```

该命令会写出 `sampled_texture_policy.json`，记录被选中的 texture prototype、代表性 embedding index 和 deterministic selection policy。当前产物是可审计统计 policy artifact，不是 trainable texture codebook、VQ-VAE 或 morphology token sampler。

从四类 prior artifact 构建统一 `prior_manifest.json`：

```bash
he-wsi-gen build-prior-manifest \
  --output-dir path/to/prior \
  --prior-id prior-demo \
  --dataset-id dataset-demo \
  --input-manifest path/to/input-manifest.json \
  --training-data-version train-v1 \
  --wsi-id slide-001 \
  --wsi-id slide-002 \
  --random-seed 7 \
  --layout-mask-prior path/to/layout_mask_prior.json \
  --style-prior path/to/style_prior.json \
  --texture-prior path/to/texture_prior.json \
  --qc-reference-distribution path/to/qc_reference_distribution.json \
  --wsi-tissue-overview path/to/wsi_tissue_overview.json
```

该命令会校验四类核心 artifact 文件存在且为 JSON，检查 layout/style/texture 的 `prior_type` 与 artifact 类型一致，检查 QC reference 的来源字段，并写出带 sha256、size_bytes 和 artifact metadata 摘要的 `prior_manifest.json`。`--wsi-tissue-overview` 是可选项；传入时会校验 `artifact_type=wsi_tissue_overview`，并把 record count、reader backend 和 thumbnail max size 写入 manifest metadata，便于后续 layout prior / QC 追踪真实 WSI 低倍组织轮廓来源。

从 generation config 和 prior manifest 构建条件包：

```bash
he-wsi-gen build-condition-packet path/to/generation-config.json \
  --prior-manifest path/to/prior_manifest.json \
  --output path/to/condition_packet.json \
  --cascade-level 1/1 \
  --tile-origin-x 0 \
  --tile-origin-y 0 \
  --sampled-layout-mask path/to/sampled-layout/sampled_layout_mask.json \
  --sampled-style-policy path/to/sampled_style_policy.json \
  --sampled-texture-policy path/to/sampled_texture_policy.json
```

该命令会读取 prior manifest 中的核心 artifact JSON，构建 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 条件对象。若 prior manifest 包含可选 `wsi_tissue_overview`，`conditions.layout.wsi_tissue_overview` 会记录真实 WSI thumbnail tissue proxy 的 record count、reader backend、thumbnail max size、tissue fraction、组织 bounding box、连通组件数量，以及用于运行时 QC 分层选择的 manifest 摘要字段（当前保留 `cancer_type`、`tissue_type`、`center_id` 和 `split` 中存在且非空的字符串）。若传入 `--sampled-layout-mask`，`conditions.mask` 会切换为 `source=sampled_layout_mask`，记录 mask path、sample id、mask shape 和 6 类统计；后续 smoke generation 会使用该 `.npy` 作为最终 mask 输出。若传入 `--sampled-style-policy` 或 `--sampled-texture-policy`，condition packet 会校验 policy 的 schema version、artifact type、source prior path 和关键 selected 字段，并把 policy path、sample id、seed、selection policy、selected style/token 摘要和 limitations 写入 `artifact_inputs` 与 `conditions.style_seed` / `conditions.texture_token`。当前输出是可审计 JSON 契约，用于连接 prior artifact 与后续生成接口；它不是 production latent diffusion 条件注入实现，也不会自动调用 sampler 或改变 smoke/torch backend 的条件特征编码方式。

执行 smoke generation 时记录已有条件包：

```bash
he-wsi-gen run-generation path/to/generation-config.json \
  --backend smoke-cascade \
  --prior-manifest path/to/prior_manifest.json \
  --checkpoint-manifest path/to/trained_checkpoint_manifest.json \
  --condition-packet path/to/condition_packet.json \
  --output-root path/to/generated/gen-001 \
  --generated-id gen-001
```

该命令会校验条件包版本、类型、`prior_id` 和必要条件对象，并把条件包路径、cascade level、tile origin、style seed、texture cluster、source condition、structure anchor 和 WSI overview manifest 摘要写入 `metadata.json` 与 `generation_run.json`。若 prior manifest 中的 `qc_reference_distribution` 启用了分层阈值，QC 会使用这些 manifest 摘要字段构造运行时 context；命中 stratum 时使用分层阈值，缺失或未命中时保留全局阈值 fallback 审计。当前 smoke backend 仍只验证工程链路，不代表真实 diffusion 条件采样。

初始化训练 run manifest：

```bash
he-wsi-gen init-training-run path/to/training-config.json
```

构建训练样本索引：

```bash
he-wsi-gen build-training-index path/to/manifest.json \
  --audit path/to/audit.json \
  --label-mapping path/to/label-mapping.json \
  --output path/to/training-index.jsonl
```

如有多个 annotation mapping，可重复传入 `--label-mapping`。索引构建会拒绝 audit 失败、缺少 mapped/validated mask、缺失 label mapping 或无法切出完整 512x512 40x tile 的输入。

抽检训练 batch：

```bash
he-wsi-gen inspect-training-batch path/to/training-index.jsonl \
  --batch-size 4 \
  --split train \
  --cascade-level 1/1 \
  --include-image \
  --output path/to/training-batch-summary.json
```

该命令会读取 `.npy` mask，按 training-index 中的 tile 坐标裁剪 batch，并把原始 mask 编号映射为项目 6 类 id。启用 `--include-image` 时，还会按 `wsi_path` 和 source backend 读取 RGB tile。输出 JSON 只包含 summary，不写出完整 mask/image batch 数组。

执行 PyTorch smoke training：

```bash
he-wsi-gen train-torch-smoke path/to/training-index.jsonl \
  --output-dir path/to/torch-smoke-run \
  --batch-size 4 \
  --split train \
  --cascade-level 1/1 \
  --epochs 2 \
  --learning-rate 0.001
```

该命令会写出 `model.pt`、`training_log.jsonl`、`training_run.json` 和 `checkpoint_manifest.json`。它真实执行 PyTorch 训练 loop，但只训练一个极小的 mask-conditioned RGB reconstruction smoke backend：6 类 mask one-hot 是输入，RGB image tile 是 MSE 重建目标；产物不可作为 latent diffusion 推理权重。

执行 PyTorch VAE smoke training：

```bash
he-wsi-gen train-torch-vae-smoke path/to/training-index.jsonl \
  --output-dir path/to/torch-vae-smoke-run \
  --batch-size 4 \
  --split train \
  --cascade-level 1/1 \
  --epochs 2 \
  --learning-rate 0.001 \
  --latent-channels 4 \
  --latent-size 64 \
  --kl-weight 0.0001
```

该命令会读取真实 RGB image tile，训练一个小型 VAE smoke autoencoder，执行 encoder、reparameterization、decoder、MSE reconstruction loss 和 KL loss，并写出 `model.pt`、`checkpoint_manifest.json`、`training_run.json`、`latent_preview.npy` 和 `reconstruction_preview.npy`。Manifest 记录 `latent_source=trainable_vae_smoke`、latent channels、latent size、latent batch shape、loss history 和 checkpoint hash；当前 VAE 可作为 diffusion smoke 的可选 latent 来源，但只在下采样 RGB tile 上验证 trainable latent autoencoder 路径，不是 production WSI VAE。

执行 PyTorch diffusion smoke training：

```bash
he-wsi-gen train-torch-diffusion-smoke path/to/training-index.jsonl \
  --output-dir path/to/torch-diffusion-smoke-run \
  --batch-size 4 \
  --split train \
  --cascade-level 1/1 \
  --epochs 2 \
  --learning-rate 0.001 \
  --diffusion-timesteps 16 \
  --latent-size 64 \
  --vae-checkpoint-manifest path/to/torch-vae-smoke-run/checkpoint_manifest.json
```

该命令会写出同样的训练产物，并真实执行线性 DDPM smoke schedule、latent 加噪和噪声预测 MSE loss。默认未提供 `--vae-checkpoint-manifest` 时使用 `rgb_downsample_proxy` latent；提供 VAE smoke checkpoint 时，会校验并加载 VAE，使用 encoder `mu` 构造 `trainable_vae_smoke` latent，并在 diffusion manifest/payload 记录 `vae_checkpoint_manifest_path`、latent channel 数、latent batch shape、input/output channels 和 checkpoint hash。Denoiser 输入通道由当前 latent、上一尺度 RGB proxy、6 类 mask、timestep 和 7 个 condition feature channels 组成；上一尺度 proxy 在训练期从真实 RGB tile 降采样到上一 cascade 尺度再上采样到 latent grid，`1/32` 根层级使用显式 zero condition。模型结构为 smoke latent U-Net，包含 encoder、downsample、bottleneck、upsample、concat skip、decoder/output blocks；checkpoint payload/manifest 记录 `denoiser_architecture` 和 `cross_scale_condition_schema`。当前仍是 smoke 级训练，不是 production latent diffusion 权重。

执行 PyTorch diffusion smoke sampling：

```bash
he-wsi-gen sample-torch-diffusion-smoke path/to/checkpoint_manifest.json path/to/training-index.jsonl \
  --output-dir path/to/torch-diffusion-smoke-sample \
  --batch-size 4 \
  --split train \
  --cascade-level 1/1 \
  --sample-steps 8 \
  --previous-scale-condition path/to/previous-scale-preview.npy \
  --condition-packet path/to/condition_packet.json
```

该命令会读取 diffusion smoke checkpoint 和 training-index 中的 mask 条件，执行反向 DDPM-style smoke sampling，并写出 `sample_preview.npy` 与 `sample_manifest.json`。采样前会校验 checkpoint manifest/payload 的 `denoiser_architecture`、`cross_scale_condition_schema` 与 condition feature schema，避免旧结构 checkpoint 静默采样。传入 `--previous-scale-condition` 时会读取 `[batch, height, width, 3]` 或 `[height, width, 3]` 的 `.npy` RGB preview，并作为上一尺度条件通道；未传入时会记录 `cross_scale_condition_source=default_zero_previous_scale`。传入 `--condition-packet` 时会校验条件包版本、类型和必要条件对象，把 style seed、texture cluster、tile origin、cascade level、source enabled 和 structure anchor 编码为 7 个 constant spatial condition channels，并在 `sample_manifest.json` 记录 `condition_packet_path`、`condition_summary`、`condition_feature_schema`、`condition_feature_vector`、`cross_scale_condition_schema`、cross-scale source 和 `denoiser_architecture`。若 checkpoint 使用 `trainable_vae_smoke` latent，sampler 会加载记录的 VAE checkpoint，通过 decoder 将 sampled latent 解码为 RGB preview，并记录 `latent_sample_shape`；若 checkpoint 使用 `rgb_downsample_proxy`，则保持原有 RGB proxy preview。`sample_manifest.json` 会标记 `usable_for_production=false`。

执行 PyTorch diffusion smoke generation：

```bash
he-wsi-gen run-generation path/to/generation-config.json \
  --backend torch-diffusion-smoke \
  --prior-manifest path/to/prior_manifest.json \
  --checkpoint-manifest path/to/diffusion_smoke/checkpoint_manifest.json \
  --training-index path/to/training-index.jsonl \
  --output-root path/to/generated/gen-torch-smoke \
  --generated-id gen-torch-smoke \
  --batch-size 1 \
  --condition-packet path/to/condition_packet.json
```

该 backend 会调用 diffusion smoke sampler，按 `1/32 -> 1/16 -> 1/4 -> 1/1` 执行四层级联 smoke sampling；`1/32` 使用默认 zero previous-scale condition，后续层级把上一层 `sample_preview.npy` 作为 `--previous-scale-condition` 传入。每层都会写出独立 `sample_manifest.json`，`metadata.json` 和 `generation_run.json` 记录 `cascade_sample_manifests`，最终用四层 sample preview resize 组装小型 OME-TIFF pyramid，并写出 mask、QC 和 batch index。传入 `--condition-packet` 时会额外要求条件包 `prior_id` 与当前 prior manifest 一致，并让每层 sampler 使用同一份 condition feature vector；路径和摘要会同步写入 sampler manifest、`metadata.json` 和 `generation_run.json`。它只验证 PyTorch sampler 到输出归档的工程链路，不是 production latent diffusion inference，也尚未实现 production U-Net/ControlNet、多倍率真实条件注入或 WSI consistency fine-tuning。

生成级联推理计划：

```bash
he-wsi-gen plan-generation path/to/generation-config.json \
  --prior-manifest path/to/prior_manifest.json \
  --checkpoint-manifest path/to/checkpoint_manifest.json \
  --output path/to/generation-plan.json
```

执行端到端 smoke generation：

```bash
he-wsi-gen run-generation path/to/generation-config.json \
  --backend smoke-cascade \
  --prior-manifest path/to/prior_manifest.json \
  --checkpoint-manifest path/to/trained_checkpoint_manifest.json \
  --output-root path/to/generated/gen-001 \
  --generated-id gen-001
```

`smoke-cascade` 只验证工程链路和输出契约。它要求 checkpoint manifest 显式为 `status=trained` 且 `usable_for_inference=true`，但不会执行真实 diffusion 推理。

归档单个生成样本的 metadata、QC 和 batch index：

```bash
he-wsi-gen archive-sample path/to/generated-sample \
  --metadata path/to/metadata-input.json \
  --qc path/to/qc-input.json
```

写出默认 UI 配置：

```bash
he-wsi-gen write-ui-config path/to/ui-config.json
```

将输出路径后缀换成 `.yaml` 或 `.yml` 时，CLI 会写出 YAML；缺少 PyYAML 时会显式报错。

启动 PySide6 单页控制台：

```bash
he-wsi-gen launch-ui --config path/to/ui-config.yaml
```

`launch-ui` 会打开可交互单页表单，用于填写 generation config 保存路径、prior/checkpoint/output/generated id、backend、anchor preset、structure anchor、seed、sample steps、overlap、condition packet、training index、QC non-copy 开关和 6 类 label mapping。点击“保存配置”会写出 generation config JSON；点击“创建运行命令/任务”会在 `<output-root>/ui_jobs/<generated-id>/job.json` 创建 queued local job record。该 UI 不会自动执行生成任务；执行仍通过现有 `run-local-job` / CLI workflow 完成。当前 schema 仍会显式拒绝 `non_copy_patch_nearest_neighbor_search=true`，因此勾选 QC non-copy 时会阻塞保存/排队，直到后续版本实现对应能力。

创建并同步执行一个本地 job：

```bash
he-wsi-gen run-local-job path/to/jobs --job-id job-001 -- \
  python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
```

该命令会写出 `path/to/jobs/job-001/job.json`、`stdout.txt` 和 `stderr.txt`。命令返回非零时 job 状态为 `failed`，CLI 也返回非零退出码。

要在指定目录执行命令，可以加上 `--cwd`：

```bash
he-wsi-gen run-local-job path/to/jobs --job-id job-001 --cwd path/to/workdir -- \
  python -c "from pathlib import Path; print(Path.cwd())"
```

取消一个已排队但尚未运行的本地 job：

```bash
he-wsi-gen cancel-local-job path/to/jobs --job-id job-001 --message "user cancelled"
```

该命令只取消 `queued` 状态的 job，成功后会把 `job.json` 更新为 `cancelled`，并写出空的 `stdout.txt` / `stderr.txt`。未知 job、非法 job id 或已运行/已完成 job 会返回非零退出码并输出明确错误。

查看一个已持久化的本地 job 记录：

```bash
he-wsi-gen inspect-local-job path/to/jobs --job-id job-001
```

该命令会把完整 job record 以 JSON 输出到 stdout。未知 job、非法 job id 或损坏的 `job.json` 会返回非零退出码并输出明确错误。

列出一个 job_root 下的所有本地 job：

```bash
he-wsi-gen list-local-jobs path/to/jobs
```

该命令会把 job_root 下的所有持久化 job 记录以 JSON 数组输出到 stdout。损坏的 `job.json` 会返回非零退出码并输出明确错误。

查看一个 metadata + QC 输出摘要：

```bash
he-wsi-gen inspect-output-summary --metadata path/to/metadata.json --qc path/to/qc.json
```

该命令会先校验 metadata 与 QC schema，并要求 metadata、QC 和可选 `qc_review` 的 `generated_id` 一致；随后把 `generated_id`、QC 状态和核心输出路径汇总为 JSON 输出到 stdout。若额外传入 `--qc-review`，还会附带 `review_required`、`decision`、`reviewer` 和 `review_item_count`。损坏的 metadata、QC 或 review JSON 会返回非零退出码并输出明确错误。

生成 QC 审阅文件：

```bash
he-wsi-gen create-qc-review --metadata path/to/metadata.json --qc path/to/qc.json --output path/to/qc_review.json
```

该命令会把 warning/fail 的 QC metric 提取为 `qc_review` artifact；`pass` QC 也会生成 pending 审阅单，但 `review_required=false`。

更新 QC 审阅决策：

```bash
he-wsi-gen apply-qc-review-decision --review path/to/qc_review.json --decision accepted --reviewer "Dr. Chen" --note "Reviewed."
```

该命令只接受 `accepted`、`rejected` 或 `needs_rerun`，并只允许更新 `pending` 的审阅单。

校验失败时 CLI 会返回非零退出码，并在 stderr 输出明确错误原因，例如缺少必填字段、非法 mask 类别、`structure_anchor` 越界、source 追踪缺失或 QC 层级不完整。

校验 QC review artifact：

```bash
he-wsi-gen validate qc-review path/to/qc_review.json
```

## 核心文档

- [v0.4.0 研究设计文档](docs/plans/2026-05-18-he-wsi-generator-study-design.md)
- [v0.5.0 开发附录](docs/dev/2026-05-23-he-wsi-generator-development-appendix.md)
- [需求记录](docs/DEMANDS.MD)
- [开发日志](docs/CHANGELOG.md)
- [审计验收清单](docs/audit/ACCEPTANCE_CHECKLIST.md)
- [审计补救计划](docs/audit/IMPLEMENTATION_PLAN.md)
- [审计决策与禁止变更项](docs/audit/DECISIONS.md)

## 协作模板

- [Codex worker 任务模板](.agent/templates/worker_task.md)
- [Codex worker 报告模板](.agent/templates/worker_report.md)

相关个人 Codex skills：

- `one-time-parallel-developer`：整合补救审计、批次拆分、worker 并行开发、审查合并和复审计。
- `project-remediation-audit`：可单独执行项目补救审计。
- `codex-worker-orchestration`：可单独执行 worker 任务派发、worktree 隔离和报告回收。

## 开发路线

后续开发继续按开发附录的 M1-M7 推进：

| 里程碑 | 状态 | 目标 |
|---|---|---|
| M1 | 已实现 | manifest / mapping / config / metadata / QC schema 校验 |
| M2 | 已实现基础能力 | WSI metadata、thumbnail、mask 对齐和 label mapping |
| M3 | 已实现基础能力 | PatchEmbedder 接口、embedding 缓存、cluster report |
| M4 | 已实现基础能力 + WSI tissue overview + 统计型 layout/mask、style、texture prior 构建器与 manifest builder | layout/style/texture/QC prior manifest |
| M5 | 已实现 smoke/proxy 骨架 + condition packet + training index + batch loader + PyTorch RGB/VAE/diffusion smoke training/sampling/generation + 四层 smoke cascade generation 链路 + tile traversal/blending 基础设施；production 模型未完成 | production LDM U-Net/ControlNet 训练入口、production cascade sampler |
| M6 | 已实现基础能力 + 可恢复 tile manifest / smoke resume execution / 磁盘 tile source contract / 磁盘 tile source 内存组装写出 / 受限 tiled iterator streaming 写出 / smoke 四层 tile source streaming 写出；完整 production backend streaming/resume 未完成 | pyramid 写出、QC JSON、batch JSONL |
| M7 | 已实现控制层 + 同步本地 job runner + queued job CLI 取消/查看 + 输出摘要契约校验 + 可交互 PySide6 配置页 + GUI 内同步执行/刷新/输出摘要查看；后台 daemon 和运行中取消未完成 | PySide6 单页控制台 |

## 当前边界

v0.72.3 继续完成上述工程骨架，并新增 streaming writer pyramid level contract、sampled style/texture policy artifact、condition packet 对 sampled style/texture policy 的显式消费、generation 输出对 sampled style/texture policy 摘要的保留，以及 smoke-cascade 显式 `--wsi-writer tile-streaming` 的四层 OME-TIFF 写出能力；该路径现在按 pyramid level 顺序逐层物化，不再一次性构造四层 `pyramid_levels` 容器，但 smoke 四层 tile source 仍来自内存中生成的 smoke canvas，且 writer 不支持中断后续写同一个 OME-TIFF 文件。v0.72.3 另外完成当前环境真实 SVS smoke/proxy 复跑验证。当前仅实现 thumbnail 级 tissue contour proxy、统计 prior、统计型 layout mask 采样、sampled mask 条件归档和匹配审计、sampled style/texture policy 条件与输出摘要归档、轻量 tissue fraction QC proxy、全局 IQR/MAD 阈值估计、全局 IQR reference outlier filtering、reference artifact 级分层阈值审计、运行时 exact-match stratum 阈值选择、smoke 级上一尺度 RGB proxy 条件、smoke 级 latent U-Net denoiser、preview 级四层 cascade sampling、内存级 tile blending 基础设施、可恢复 tile 状态 contract、smoke tile resume execution、OME-TIFF chunk/tile source contract 审计、磁盘 tile source 内存组装写出、受限 tile iterator streaming writer、smoke 四层 tile source streaming 接入，以及 deterministic sampled style/texture policy artifact；不实现 production-scale latent diffusion U-Net/ControlNet、production cascade sampler、production VAE latent、VAE-diffusion 联合训练、mask diffusion、trainable style encoder、style sampling policy、trainable texture codebook、VQ-VAE、生产级噪声调度和采样器、多倍率真实条件注入、WSI 一致性训练、真实推理 backend、真实训练集批量 QC 采集、基于层级优先级或相似度的自动最佳 stratum 选择、mask class 内部像素级分层阈值、权限/签名系统、数据库或远端协作审阅、production backend 磁盘级逐 tile 生成、可恢复 OME-TIFF 逐 tile 写入或生产级 gigapixel chunked OME-TIFF；job runner 也只支持同步本地执行和 queued job 取消/查看/列表，不包含后台 daemon、并发队列、运行中进程终止、跨机器调度或线程化 PySide6 事件循环绑定。
