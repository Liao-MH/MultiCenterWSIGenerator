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
