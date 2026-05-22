# DEMANDS

## v0.5.1 - 2026-05-23

### 用户需求

- 用户要求将本地仓库文件夹重命名为 `MultiCenterWSIGenerator`。
- 用户要求将当前文件夹内容同步到 GitHub 仓库 `Liao-MH/MultiCenterWSIGenerator`。
- 用户要求同步本地项目展示名称与远端仓库名称。

### 结构化需求

- README 项目标题更新为 `MultiCenterWSIGenerator`。
- README 增加 GitHub 仓库链接。
- 版本号升级为 `v0.5.1`。
- 新增 `.gitignore`，避免 `.DS_Store` 和 Python 缓存进入远端仓库。
- 初始化本地 git 仓库，将当前内容提交并推送到 `https://github.com/Liao-MH/MultiCenterWSIGenerator.git`。

### 边界说明

- 当前远端仓库经 `git ls-remote` 检查未返回 refs，按空仓库处理。
- 当前 `gh` 未登录，SSH 公钥不可用；若 HTTPS push 被拒绝，需要用户完成 GitHub 鉴权后再重试推送。
- 不使用强推，不覆盖远端已有历史。

## v0.5.0 - 2026-05-23

### 用户需求

- 用户要求保存第一版开发指南，将现有 proposal 转换为可开发规格。
- 用户已确认开发附录采用单文件形态，细节深度达到“可开发规格”，首版重点为全链路骨架。
- 用户已确认工程默认：Python core/CLI + PySide6 桌面控制台，OpenSlide+tifffile WSI I/O，v1 使用 latent diffusion U-Net，可插拔 PatchEmbedder，严格字段契约，训练/生成配置采用默认值加可覆盖项。

### 结构化需求

- 新建 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`。
- 开发附录需覆盖数据契约、工程结构、模块契约、conditional priors 工程落地、模型训练、推理重建、QC、UI、测试验收和 v1 边界。
- 开发附录需明确不实现代码，只保存开发规格。
- README 需要新增开发附录入口，并把项目状态更新为研究设计 + 开发规格阶段。
- 版本号升级到 `v0.5.0`，并同步更新需求记录和开发日志。

### 边界说明

- 当前版本仍不实现训练代码、推理代码或图形界面。
- 当前版本不新增 IHC、免疫荧光、临床/分子标签、下游训练验证、专家盲评、DiT 主干或文本 embedding 入模。
- 当前目录不是 git 仓库，因此不执行 git commit。

## v0.4.0 - 2026-05-21

### 用户需求

- 用户希望把 conditional priors learning 的数理逻辑写进 proposal，明确它实际会学到什么结果，以及这些结果如何在模型中形成约束。
- 用户希望把 prior 的输出类型、条件注入方式、训练目标、`structure_anchor` 权重语义和 QC 作用一起写清楚，避免停留在概念层。
- 用户要求继续在同一 proposal 路径上增补内容，不改变当前课题方向。

### 结构化需求

- 在研究设计文档中新增 conditional priors 的联合分布定义，明确 `layout`、`mask`、`style`、`texture`、`artifact`、`source-anchor` 和 `QC reference` 的关系。
- 补充 prior 产物类型的清单，说明哪些输出是分布参数、哪些输出是 sampleable condition、哪些输出只用于 QC。
- 补充 prior 如何进入生成模型的实际机制，包括条件输入、采样边界、训练损失、推理 guidance 和自动 QC。
- 明确 `structure_anchor` 在数学上对应条件强度与 loss 权重的连续控制，而不是像素插值。
- 在三阶段训练协议中注明 conditional priors 的实例化条件，避免把 priors 误写成临时拼接特征。
- 同步更新版本号、README、CHANGELOG 和 proposal 主文档中的版本字段。

### 边界说明

- 当前版本仍只更新文档，不实现训练代码、推理代码或图形界面。
- 当前版本不新增下游训练验证、真人专家盲评、IHC、免疫荧光或临床/分子标签条件。
- 当前版本保持同一文档路径 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，通过版本号表达内容增强。

## v0.3.0 - 2026-05-18

### 用户需求

- 用户希望 proposal 文档覆盖前期讨论达成的所有细节共识。
- 用户希望研究设计文档比 v0.2.0 更详细，尤其是因果分析、设计取舍、训练协议、QC 逻辑、metadata 和 LLM 边界。
- 用户要求在现有 proposal 基础上增强内容，而不是改变课题方向。

### 结构化需求

- 在研究设计文档中补充共识总表，集中记录系统目标、模型路线、生成路径、`structure_anchor`、`global_imaging_style_prior`、mask、LLM、UI、QC、非复制检测和后续扩展边界。
- 补充“因果假设与反事实边界”，解释为什么 WSI 生成器不能只做 patch 或颜色增强。
- 补充“设计选择与被放弃路线”，说明为什么 GAN、CycleGAN、纯随机生成、先高倍后拼接和文本 prompt 入模不作为当前主线。
- 补充数据流与因果依赖，明确 thumbnail、6 类 mask、patch embedding、style statistics、source relation 和 QC reference distribution 的作用。
- 细化 mask 生成与映射流程，记录人工标注、ROI、聚类伪标签和用户确认的可信度层级。
- 细化 `structure_anchor` 的训练与推理语义，明确 anchor=1 是重扫描模拟，anchor=0 是 fully de novo。
- 细化多分辨率级联生成模型，补充 backbone 选择原则、四层责任分工、训练样本构造、训练约束与 QC 映射。
- 细化本地桌面单页控制台和高级参数暴露范围。
- 细化 LLM 角色，限定为知识约束与交互编排，不承担像素真实性和专家判断。
- 细化 metadata，增加 run-level manifest 与 per-WSI metadata 的分工。
- 细化自动 QC 的 warning/fail 逻辑、训练分布自适应阈值、轻量非复制报告解释规则和核心系统完成标准。

### 边界说明

- 当前版本仍只更新文档，不实现训练代码、推理代码或图形界面。
- 当前版本不新增下游训练验证、真人专家盲评、IHC、免疫荧光或临床/分子标签条件。
- 当前版本保持同一文档路径 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，通过版本号表达内容增强。

## v0.2.0 - 2026-05-18

### 用户需求

- 用户要求根据 `research-design-ladder` 技能，将前期多轮讨论形成的 H&E WSI 数据生成器课题方案写入正式研究设计文档。
- 用户要求新建 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，保留旧草案，不覆盖历史版本。
- 用户要求同步更新版本号、README、需求记录和开发日志。

### 结构化需求

- 研究对象：H&E 染色 Whole Slide Image（WSI）的本地化数据生成器。
- 核心目标：设计一个可训练、可配置、可追溯、可自动质控的 WSI 生成系统。
- 主模型路线：结构锚定的多分辨率 mask-conditioned latent diffusion / diffusion transformer。
- 生成路径：从低倍到高倍级联生成，层级为 `1/32 -> 1/16 -> 1/4 -> 1/1`，最高主动生成层为 40x。
- Tile 规格：40x 主动生成 tile 为 `512 x 512`。
- 控制变量：保留 `structure_anchor`，删除用户可见 `domain_shift`，内部使用 `global_imaging_style_prior`。
- 输出内容：OME-TIFF pyramid WSI、疾病无关 6 类 mask、per-WSI metadata JSON、QC JSON、batch JSONL index。
- Mask 类别：`background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact`。
- 标注策略：支持 PNG/numpy mask 和 ROI；无标注时使用 patch embedding 聚类生成伪 mask，并由用户映射到 6 类。
- 软件形态：本地桌面工具，单页控制台，暴露完整高级参数。
- 自动 QC：覆盖 WSI 级、tile 级和 mask 区域级，输出 `pass`、`warning`、`fail`；阈值采用训练分布自适应。
- 非复制检测：作为强制 QC 报告内容，但第一版不做全量 patch 近邻检索，也不自动触发 fail。

### 边界说明

- 当前版本只完成研究设计，不实现训练代码、推理代码或图形界面。
- 当前系统边界只覆盖 H&E WSI 生成器本身，不把下游训练/测试作为当前成败标准。
- IHC、免疫荧光、临床/分子标签、真人专家盲评和下游训练验证均作为后续可选扩展。
- LLM 仅作为知识约束与交互编排模块，不作为像素级病理真实性依据，也不做文本 embedding 入模。

## v0.1.0 - 2026-05-16

### 用户需求

- 用户希望基于多中心病理数据收集困难这一现实限制，设计一个面向 H&E 染色 WSI 数据的多中心数据生成器。
- 用户显式要求使用 `research-design-ladder` 技能，将初始想法整理成完整的研究设计文档。

### 结构化需求

- 研究对象：H&E 染色 Whole Slide Image（WSI）。
- 核心问题：如何在真实多中心数据难以收集的情况下，生成可控、可信、可验证的多中心样式数据。
- 主要目标：构建一个生成器设计方案，使其能够模拟不同中心之间的染色、扫描和图像处理差异，同时尽量保持诊断相关形态与标签不变。
- 证据重点：形态保真、中心域覆盖、下游跨中心泛化提升、隐私与泄漏控制、病理专家可接受性。
- 输出形式：完整 Markdown 研究设计文档，并同步生成项目 README、需求记录和变更日志。

### 边界说明

- 当前版本只完成研究设计，不实现训练代码、推理代码或图形界面。
- 当前版本不承诺合成数据可替代真实多中心临床验证。
- 当前版本不扩展到 IHC、特殊染色或非病理影像，除非后续用户提出新的迭代需求。
