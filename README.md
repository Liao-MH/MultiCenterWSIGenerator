# MultiCenterWSIGenerator

当前版本：v0.5.1
当前状态：研究设计 + 开发规格阶段
GitHub 仓库：[Liao-MH/MultiCenterWSIGenerator](https://github.com/Liao-MH/MultiCenterWSIGenerator)

本项目用于设计一个面向 H&E 染色 Whole Slide Image（WSI）的本地化数据生成器。当前方案不再把项目限定为简单多中心颜色增强或下游模型训练增强，而是把目标收束为一个完整的 WSI 数据生成系统：从真实 WSI 学习组织 layout、疾病无关区域 mask、成像风格和多倍率纹理分布，生成新的 OME-TIFF pyramid WSI，并同步输出 mask、metadata 与自动 QC JSON。

## 核心文档

- [v0.4.0 研究设计文档](docs/plans/2026-05-18-he-wsi-generator-study-design.md)
- [v0.5.0 开发附录](docs/dev/2026-05-23-he-wsi-generator-development-appendix.md)
- [v0.1.0 历史草案](docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md)
- [需求记录](docs/DEMANDS.MD)
- [开发日志](docs/CHANGELOG.md)

## 当前设计定位

本项目的当前定位是 **H&E WSI 数据生成器**，而不是普通 stain augmentation、下游训练脚本或无约束病理图像绘制器。系统核心是一个结构锚定的多分辨率 mask-conditioned latent diffusion / diffusion transformer 框架，通过 `structure_anchor` 控制从源 WSI 重扫描模拟到 fully de novo 生成的连续过渡。

当前设计删除用户可见的 `domain_shift` 控制项，改为内部学习 `global_imaging_style_prior`。这样可以适配多中心、多组织、多疾病输入数据，而不要求用户指定模糊的目标中心偏移方向。

## 核心输出

- OME-TIFF pyramid WSI。
- 疾病无关 6 类区域 mask：`background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact`。
- 每个生成 WSI 对应的 metadata JSON。
- 自动 QC JSON。
- 批量生成样本的 JSONL index。

## 关键技术路线

- 真实 WSI 数据导入、预处理和 patch embedding 聚类。
- PNG/numpy mask 数字编号自动读取，并由用户映射到疾病无关 6 类。
- Layout/mask prior 与 global imaging style prior 学习。
- `1/32 -> 1/16 -> 1/4 -> 1/1` 四层级联生成，最高主动生成层为 40x。
- 40x 生成 tile 尺寸为 `512 x 512`。
- 三阶段训练协议：layout/mask prior、mask-conditioned 多倍率图像生成、WSI 一致性微调。
- 自动 QC 覆盖 WSI 级、tile 级和 mask 区域级，状态为 `pass`、`warning`、`fail`。
- 轻量非复制报告写入 QC JSON，但第一版不做全量 patch 近邻检索。

## 当前边界

当前版本只完成研究设计，不实现训练代码、推理代码或图形界面。IHC、免疫荧光、临床/分子标签条件、真人专家盲评和下游训练验证均作为后续可选扩展，不进入当前系统成败标准。

## v0.5.1 更新重点

v0.5.1 将项目展示名称同步为 MultiCenterWSIGenerator，增加 GitHub 仓库入口，并新增 `.gitignore` 以避免 macOS 与 Python 缓存文件进入版本库。v0.5.0 新增第一版开发附录，把 proposal 转换为可开发规格，明确 Python core/CLI + PySide6 的工程形态、OpenSlide/tifffile 的 WSI I/O 路线、latent diffusion U-Net 的 v1 模型主干、可插拔 PatchEmbedder、严格数据契约、模块接口、训练/推理默认配置、QC 和测试验收标准。

## 环境说明

当前阶段尚未引入代码依赖。后续进入实现阶段时，应优先使用独立 conda 环境或其他隔离环境，不在主环境中直接安装项目依赖。
