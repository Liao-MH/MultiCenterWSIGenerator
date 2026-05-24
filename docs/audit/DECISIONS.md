# 审计决策与禁止变更项

## 当前审计基线

- 原始审计基线为 `v0.62.0`；当前补救开发版本为 `v0.72.4`。
- v0.72.4 允许修改 P3 checkpoint inference contract 相关的 `src/he_wsi_generator/models/training.py`、generation/model 测试、配置、README 和审计文档；同时继承 P4 输出可靠性、P5 可审计 style/texture policy helper、condition packet sampled policy 集成与 generation 输出摘要贯通等既有补救边界。
- 审计文件统一维护在 `docs/audit/`，不再放在 `docs/` 根目录。
- 本轮按仓库版本规则升级版本号，因为 checkpoint inference manifest contract gate 新增了向后兼容的审计/实现补丁。
- 截至本次复审计，v0.72.4 作为 `main` 分支补救基线提交，但不是已 tag 或打包发布的 release；不能表述为已经发布。
- 当前审计周期已创建 conda 环境 `MultiCenterWSIGenerator` 并验证 PyTorch、CUDA、PySide6 依赖和全量单元测试；真实 SVS smoke/proxy 链路复跑证据来自历史 v0.72.1 轮次。该结论只覆盖当前机器环境，不替代 production 验收。

## 完整项目成果定义

完整项目成果以研究设计文档为准，至少包括：

- 本地桌面单页控制台，支持 WSI/mask 导入、编号映射、模型训练/加载、生成参数、任务状态和输出查看。
- 结构锚定的多分辨率 mask-conditioned latent diffusion / ControlNet / DiT 级生成模型。
- 40x 四层级联生成：`1/32 -> 1/16 -> 1/4 -> 1/1`。
- OME-TIFF pyramid WSI、6 类 mask、metadata JSON、QC JSON 和 batch JSONL index。
- 自动 QC、非复制审计、可追踪 seed/model/prior/source/config。

当前 `v0.72.4` 不能被表述为完整项目成果，只能表述为可审计工程骨架、smoke/proxy 级验证链、可交互配置页、本地同步 GUI flow、首轮维护性收敛结果、P3 checkpoint inference artifact contract gate，以及 P4 可恢复 tile 状态、smoke resume execution、磁盘 tile source 发布前校验、内存组装写出、受限 tiled iterator streaming writer、streaming writer pyramid contract、smoke 四层 tile source streaming 写出、tile-streaming 顺序物化、tile blending 的 channel-wise 内存收敛、P5 deterministic sampled style/texture policy artifact、sampled policy condition packet 条件摘要接入、generation 输出摘要保留和真实 SVS smoke/proxy 复跑结果。

## 关键设计决策

1. 保持 core/CLI 优先
   - UI 只负责配置、调度和展示，不把核心业务逻辑藏在界面事件里。

2. 保持 CLI 自动化入口
   - 未经用户确认，不让 `run-generation` 默认弹出 GUI，以免破坏脚本化和批处理使用。
   - 图形配置页优先通过 `launch-ui` 落地。

3. 保持 smoke / proxy 边界显式可见
   - `smoke-cascade`、`torch-diffusion-smoke`、统计 prior、preview sampling 不能被描述为 production WSI generator。

4. 保持 6 类疾病无关 mask 体系
   - `background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact` 是当前统一语义契约。

5. 保持 metadata / QC / qc_review 分离
   - `metadata.json` 回答“如何生成”。
   - `qc.json` 回答“质量如何”。
   - `qc_review.json` 回答“人工是否接受”。

6. 保持显式失败优先
   - 对非法输入、缺失依赖、schema 不一致、artifact 不匹配，继续显式报错，不引入 silent fallback。

7. 保持可选依赖隔离
   - `torch`、`PySide6`、`openslide`、`PyYAML` 继续通过可选依赖或独立环境安装，不回写到基础依赖集合。
   - 当前验证环境命名为 `MultiCenterWSIGenerator`，安装完整 extras 后用于后续审计和 worker 复验。

8. 保持行为保持拆分
   - `cli_commands.py` 与 `torch_training_contracts.py` 只能承载纯分发或纯 helper 逻辑，不改变命令参数、错误消息、manifest 字段或训练/采样公开函数的行为。

9. 保持 P4 输出 contract 与 production writer 边界
   - 可恢复 tile manifest 与磁盘 `.npy` tile source contract 只能表述为发布前校验和恢复状态基础设施。
   - 当前 `write_pyramid_ome_tiff()` 仍是 in-memory tifffile pyramid writer；在真正逐 tile OME-TIFF backend 完成前，必须继续返回并记录 `production_streaming=false` / `partial_contract_only=true`。
   - `write_pyramid_ome_tiff_from_tile_sources()` 只能表述为磁盘 tile source 的内存组装写出接口；它不是 production gigapixel streaming writer。
   - `write_pyramid_ome_tiff_streaming_from_tile_sources()` 可表述为受限的磁盘 tile source tiled iterator writer；它不组装完整 level array，但仍要求完整 tile source manifest、high-to-low pyramid level order，且 `resume_capable=false`。
   - `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 可表述为 smoke 四层 tile source streaming 接入和顺序物化；不能表述为 production backend streaming，因为四层 tile source 来自已在内存中构建的 smoke canvas。

10. 保持 P5 sampled policy 与 production prior 边界
   - `sampled_style_policy` / `sampled_texture_policy` 可以被 condition packet 显式消费并记录为可审计条件摘要。
   - smoke/torch generation 输出可以继续保留 sampled policy 的 selected style/token 摘要，作为审计链证据。
   - 该接入与输出保留不能被描述为 production style encoder、texture codebook、VQ-VAE、morphology token sampler、runtime sampler 自动调用或真实生成模型条件学习。
   - sampled policy source prior path 必须匹配当前 prior manifest 中的对应 artifact path；不允许用 silent fallback 混用来源不一致的 policy。

11. 保持 P3 checkpoint inference contract 与 production 模型边界
   - `usable_for_inference=true` 必须由真实 checkpoint 文件、matching SHA-256 和显式 `inference_contract` 支撑，不能再由薄 JSON 布尔字段冒充。
   - `inference_contract.production_ready=false` 的 smoke/test fixture 只能表述为契约就绪的非 production artifact；不能表述为 production latent diffusion / ControlNet / DiT backend。
   - smoke / torch smoke checkpoint 默认继续保持 `usable_for_inference=false`，除非后续接入真实 production inference backend 并补齐 payload 语义校验。

## 禁止变更项

- 未经确认，不做与 P1 无关的实现重构、不改默认生成行为。
- 不把审计记录本身包装成新发布；只有实际功能补救才升级版本。
- 不删除现有 `build/validation/` 工件；它们是历史验证证据。
- 不把“现存工件仍可校验”表述成“本轮已重新执行真实 SVS 全链路”。
- 不把当前 v0.72.4 基线提交表述为已发布版本；tag、打包需另行执行并验证。
- 不把当前 PySide6 GUI flow 描述为后台任务系统；它支持同步本地 queued job 执行、刷新和输出摘要查看，但不包含后台 daemon、并发队列、运行中取消、跨机器调度或线程化 Qt 执行。
- 不把 v0.72.3 的 tile source contract/assembly/iterator writer 和 smoke 四层 tile source streaming 描述为完整 production gigapixel writer；当前 iterator writer 不组装完整 level array，但 smoke 接入仍基于内存中已生成的 smoke canvas，且不支持中断后续写同一个 OME-TIFF 文件。
- 不把 v0.72.3 的 sampled policy condition packet 集成或 generation 输出摘要保留描述为 production style/texture model；它只记录显式传入的 sampled policy artifact 摘要，不自动调用 sampler 或改变 generation backend。
- 不把 v0.72.4 的 checkpoint inference artifact contract gate 描述为 production 生成模型；它只加固 manifest 入口契约，不训练或运行真实 production backend。
- 不因为补救而扩展到当前系统边界外内容，例如 IHC/IF、临床分子标签、真人专家盲评、下游训练验证、权限/签名系统、数据库或远端协作审阅。

## 补救优先级决策

- 第一优先级：审计文件归位、文档诚实度、契约闭环。
- 第二优先级：真实可交互 PySide6 配置页与本地同步 GUI flow。
- 第三优先级：environment/真实 SVS 复跑验证。
- 第四优先级：production 级生成模型与 WSI 输出；P4 下一步应把 tile source streaming 扩展到 production backend 和可恢复 OME-TIFF 写入。
- 第五优先级：大文件拆分与维护性收敛。
