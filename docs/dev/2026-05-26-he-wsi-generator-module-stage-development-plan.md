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
| M26 | Stage 7 | 端到端 smoke test | 用小型 WSI 或 fixture 跑通输入、生成、输出、metadata、QC、UI config | E2E smoke result |

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

### Stage 7：本地控制台与端到端验收

Stage 7 将 core/CLI 能力接入 PySide6 本地单页控制台。UI 的目标是调度主体流程和展示核心输出，不在第一轮承担复杂解释系统。

| Module | 实现重点 | 最小验收 |
|---|---|---|
| M23 | 实现 PySide6 单页控制台 | 页面包含数据输入、mapping、model/prior、生成参数、状态和输出区域 |
| M24 | 保存 UI job config | UI 配置可被 CLI/core 复现 |
| M25 | 实现 job runner 和状态展示 | 能显示 queued/running/completed/failed |
| M26 | 跑通端到端 smoke test | 从 manifest 到 OME-TIFF、metadata、QC、UI config 的闭环成立 |

Stage Gate：
- 用户可以通过 UI 或 CLI 完成一次完整生成任务。
- UI 不直接实现 core 数据处理逻辑，只负责配置、调度和展示。
- 失败说明只需可操作，例如缺路径、缺 checkpoint、输出不可写；复杂解释后续再补。

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
| Stage 7 | UI config test、job runner smoke test、end-to-end smoke test |


## 9. 完成标准

模块化分阶段开发可视为完成，当且仅当：

1. Stage 1 到 Stage 7 按顺序完成。
2. 输入 WSI 能进入 manifest，并产生 thumbnail、pyramid metadata 和 6 类 mask。
3. 系统能学习或加载 layout/mask、style、texture priors。
4. 系统能训练或加载结构锚定的多倍率 latent diffusion U-Net checkpoint。
5. 系统能按 `1/32 -> 1/16 -> 1/4 -> 1/1` 级联生成 WSI。
6. 系统能写出 `generated.ome.tiff`、`generated_mask/`、`metadata.json`、`qc.json` 和 `batch.jsonl`。
7. PySide6 控制台能调度一次生成任务，并显示任务状态和输出路径。

