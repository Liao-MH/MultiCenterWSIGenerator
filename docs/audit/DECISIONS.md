# 审计决策与禁止变更项

## 当前审计基线

- 原始审计基线为 `v0.62.0`；当前补救开发版本为 `v0.72.32`。
- v0.72.32 允许修改版本配置、README、需求记录、审计文档，以及设计/开发文档中 OME streaming writer progress evidence 相关最小章节的代码追踪块。当前能力继承 v0.72.24 的 P4 production tile-stream WSI 生成实现、v0.72.26 OME streaming started transaction 完整临时 OME-TIFF 验证发布恢复、v0.72.27 per-tile request manifest 合同、v0.72.28 failed tile opt-in retry 语义、v0.72.29 completed target OME validation reuse、v0.72.30 OME streaming disk-space preflight 和 v0.72.31 production tile backend execution evidence；本轮在 `src/he_wsi_generator/outputs/ome_tiff.py` 中新增 `<target>.progress.json`，记录 tile iterator writer 已 yield 给 `tifffile` 的 tile 进度，并在 transaction manifest 与 diagnostics 中汇总。该 progress evidence 是 GB 级写出中断诊断，不是同一 OME-TIFF 文件内部 partial tile 续写，也不是内置 production latent diffusion / ControlNet / DiT 模型。
- 审计文件统一维护在 `docs/audit/`，不再放在 `docs/` 根目录。
- 本轮按仓库版本规则升级版本号，因为当前新增 OME streaming writer progress evidence contract，并同步设计/开发文档代码追踪块和审计基线。
- 截至本次复审计，v0.72.32 将作为当前补救基线提交，但不是已 tag 或打包发布的 release；不能表述为已经发布。
- 当前审计周期使用 conda 环境 `MultiCenterWSIGenerator`；mamba 与 conda 环境列表指向同一个 prefix，因此不删除该环境目录，后续验证统一使用 `conda run -n MultiCenterWSIGenerator ...`。真实 SVS smoke/proxy 链路复跑证据来自历史 v0.72.1 轮次。该结论只覆盖当前机器环境，不替代 production 验收。
- 按用户最新目标要求，应根据开发文档优先完成功能实现代码；每完成开发节点中的里程碑后，再对主功能集中测试；不要增加额外 helper 级测试；每次实现、修改或重构功能后，在确认代码和主功能验证过关后维护设计文档与开发文档中相关最小级标题下的代码追踪块，不得伪造实现位置或验证命令。

## 完整项目成果定义

完整项目成果以研究设计文档为准，至少包括：

- 本地桌面单页控制台，支持 WSI/mask 导入、编号映射、模型训练/加载、生成参数、任务状态和输出查看。
- 结构锚定的多分辨率 mask-conditioned latent diffusion / ControlNet / DiT 级生成模型。
- 40x 四层级联生成：`1/32 -> 1/16 -> 1/4 -> 1/1`。
- OME-TIFF pyramid WSI、6 类 mask、metadata JSON、QC JSON 和 batch JSONL index。
- 自动 QC、非复制审计、可追踪 seed/model/prior/source/config。

当前 `v0.72.32` 不能被表述为完整项目成果，只能表述为可审计工程骨架、smoke/proxy 级验证链、可交互配置页、本地同步 GUI flow、首轮维护性收敛结果、P3 checkpoint inference artifact contract gate、checkpoint/backend compatibility contract、inference architecture/condition contract、PyTorch diffusion smoke checkpoint inference planning contract、production training dataset contract、实际 training index JSONL 证据核对、training objective/loss/QC mapping contract、production training plan artifact，以及 P4 可恢复 tile 状态、smoke resume execution、磁盘 tile source 发布前校验、内存组装写出、受限 tiled iterator streaming writer、streaming writer pyramid contract、tile iterator streaming writer 原子发布事务 manifest、OME streaming writer progress sidecar、OME streaming started transaction temporary publish recovery、completed target OME validation reuse、OME streaming disk-space preflight、production per-tile request manifest、production failed tile 显式 retry/resume、production tile backend execution evidence、generation output diagnostics manifest、smoke 四层直接 tile source streaming 写出、direct tile source 物化 resume manifest、torch-diffusion-smoke tile-streaming writer 接入、`production-tile-stream` 外部 tile generator backend、writer tile-grid seam QC proxy、stain/focus QC proxy、mask-image tissue alignment QC proxy、tile blending 的 channel-wise 内存收敛、P5 deterministic sampled style/texture policy artifact、fitted style latent prior、fitted texture morphology latent/codebook contract、prior production readiness contract gate、production prior component contract interface、sampled policy condition packet 条件摘要接入、generation 输出摘要保留、OME streaming writer progress evidence 相关设计/开发文档 trace 同步和真实 SVS smoke/proxy 历史复跑结果。

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
   - `write_pyramid_ome_tiff_streaming_from_tile_sources()` 可表述为受限的磁盘 tile source tiled iterator writer；它不组装完整 level array，并通过同目录临时 OME-TIFF、发布前校验、原子替换、progress sidecar 和 transaction manifest 降低半成品污染风险。v0.72.26 允许在上次 `started` transaction 留下完整临时 OME-TIFF时，校验目标路径、tile source manifest 路径和 pyramid shapes 后直接发布该临时文件，并记录 `recovery_action=published_existing_temporary_ome_tiff` / `recovered_from_temporary=true`；v0.72.29 允许在既有 `completed` transaction 与当前 target/manifest/shape 匹配时验证并复用已发布目标 OME-TIFF，并记录 `recovery_action=validated_existing_target_ome_tiff` / `reused_existing_target=true`；v0.72.30 在正常完整写出前按 raw pyramid byte estimate 加同等安全余量执行磁盘空间 preflight，空间不足时在 tile iterator 开始前失败并记录 failed transaction；v0.72.32 在正常完整 tile iterator 写出路径记录 `<target>.progress.json` 和 `progress_summary`，用于诊断已 yield 给 `tifffile` 的 tile 进度；但它仍要求完整 tile source manifest、high-to-low pyramid level order，且 `resume_capable=false`。磁盘空间 preflight 是保守预算 guard，不是精确 TIFF 大小预测；progress sidecar 是中断诊断，不是 TIFF 内部续写能力。
   - `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 可表述为 smoke 四层 direct tile source streaming 接入，且 direct tile source 物化 manifest 可复用已完成 streaming tile 并补齐 pending tile；不能表述为 production backend streaming，因为 tile source 仍由 deterministic smoke renderer 生成，且 writer 不支持中断后续写同一个 OME-TIFF 文件。
   - `run-generation --backend torch-diffusion-smoke --wsi-writer tile-streaming` 可表述为 PyTorch smoke sample preview 到磁盘 tile source writer 的接入；不能表述为 production backend streaming，因为 sample preview 仍是 smoke 级小型数组，且 writer 不支持中断后续写同一个 OME-TIFF 文件。
   - `run-generation --backend production-tile-stream --wsi-writer tile-streaming` 可表述为外部 production tile backend 执行合同：checkpoint 必须声明 `production_ready=true`、兼容 `production-tile-stream`，并提供 `external_tile_generator_v1` artifact；运行时逐 tile 写出 `production_tile_requests/*.request.json` 后调用外部命令，写出磁盘 RGB tile、level0 mask tile、可恢复 tile source manifest、memmap mask、OME-TIFF、metadata、QC、batch index 和 diagnostics。`{tile_request_path}` 是外部 backend 的可审计输入合同，不证明内置 production diffusion 模型已实现；`--retry-failed-tiles` 只允许在 immutable manifest / request path 校验通过后重试 failed tile source record，默认仍拒绝 failed manifest；该路径也不是同一 OME-TIFF 文件内部中断追加写入。中断恢复范围包括 OME 发布前的 tile source 物化阶段，以及 OME 发布阶段上次已完成临时 OME-TIFF 的验证发布。
   - v0.72.31 的 production tile backend execution evidence 只能表述为外部 backend 执行审计：新完成 tile record 会记录 request JSON、外部命令执行和 RGB/mask 输出文件证据，manifest / diagnostics 会汇总 evidence 覆盖；它不能被描述为内置 production diffusion backend、真实权重推理、真实训练 loop 或 OME-TIFF 文件内部续写。

10. 保持 P5 sampled policy 与 production prior 边界
   - `sampled_style_policy` / `sampled_texture_policy` 可以被 condition packet 显式消费并记录为可审计条件摘要。
   - smoke/torch generation 输出可以继续保留 sampled policy 的 selected style/token 摘要，作为审计链证据。
   - 该接入与输出保留不能被描述为 production style encoder、texture codebook、VQ-VAE、morphology token sampler、runtime sampler 自动调用或真实生成模型条件学习。
   - sampled policy source prior path 必须匹配当前 prior manifest 中的对应 artifact path；不允许用 silent fallback 混用来源不一致的 policy。
   - prior manifest 的 `production_readiness.production_ready=true` 必须由完整 component contract 支撑，且 layout/style/texture 组件都不能仍是 statistical/proxy backend；当前 builder 默认写入 `production_ready=false`，防止统计 prior 冒充 production prior。
   - production prior component contract 必须声明 `production_prior_component_v1`、生成流程所需 `condition_outputs` 和与 manifest artifact path/hash 匹配的 `training_evidence`；这只证明接口契约可审计，不证明 trainable prior 已实现。
   - fitted RGB-stat PCA style latent 可以作为 `style_latent` 条件对象的轻量前置产物；不能把它描述为深度 trainable style encoder、VAE latent 或 production style transfer。

11. 保持 P3 checkpoint inference contract 与 production 模型边界
   - `usable_for_inference=true` 必须由真实 checkpoint 文件、matching SHA-256 和显式 `inference_contract` 支撑，不能再由薄 JSON 布尔字段冒充。
   - `inference_contract.compatible_generation_backends` 必须显式声明可消费该 checkpoint 的 generation backend；generation plan 不能只凭 `usable_for_inference=true` 接受任意 checkpoint。
   - `inference_contract.model_architecture_contract` 必须声明模型族、架构名称、输入空间和输出空间，且模型族必须匹配当前 `latent_diffusion_unet` 契约；这只校验 manifest 接口声明，不证明权重结构真实可运行。
   - `inference_contract.condition_input_contract` 必须覆盖 mask、style seed、texture token、coord、structure anchor、source condition 和 previous scale，并匹配四层 cascade；generation plan 应保留该摘要，不能把缺少关键条件接口的 checkpoint 送入推理规划。
   - `inference_contract.production_ready=false` 的 smoke/test fixture 只能表述为契约就绪的非 production artifact；不能表述为 production latent diffusion / ControlNet / DiT backend。
   - skeleton checkpoint 和非 diffusion torch smoke checkpoint 默认继续保持 `usable_for_inference=false`。
   - PyTorch diffusion smoke checkpoint 可以声明 `usable_for_inference=true`，但只能在 `inference_contract.compatible_generation_backends=["torch-diffusion-smoke"]` 且 `production_ready=false` 的边界内进入统一 planning；这不等于真实 production inference backend。

12. 保持 P3 production training dataset contract 与真实训练边界
   - `init-training-run` 必须显式声明 `training_backend=latent_diffusion_unet` 和完整 `dataset_contract`，否则应尽早失败。
   - `dataset_contract` 的 sample_count、split 计数、cascade level 计数、conditioning 证据和 6 类 mask mapping 必须能从实际 training index JSONL 中核对，不能只信任手写汇总字段。
   - `dataset_contract.production_readiness_declared=true` 只表示训练数据契约字段已被声明和校验，不表示模型已训练、checkpoint 可推理或输出 production-ready。
   - skeleton checkpoint 可以记录 `training_backend`、`target_type` 和 `dataset_contract_summary`，但必须继续保持 `status=not_trained` 与 `usable_for_inference=false`。
   - 在真实 production training loop、真实 checkpoint artifact 和 production inference backend 完成前，不得把本轮 contract gate 描述为 production 模型训练能力。

13. 保持 P3 training objective contract 与真实 loss/训练边界
   - `init-training-run` 必须显式声明 `training_objective_contract`，否则应尽早失败。
   - `training_objective_contract` 只记录五类训练约束、loss weight、阶段目标映射和 QC 映射的静态契约；它不表示真实 diffusion loss、mask consistency loss、seam loss 或 style consistency loss 已实现。
   - skeleton checkpoint 可以记录 `training_objective_contract_summary`，但必须继续保持 `status=not_trained` 与 `usable_for_inference=false`。
   - 在真实 production training loop 完成前，不得把 v0.72.8 contract gate 描述为已实现 production loss 计算或模型训练。

14. 保持 P3 production training plan artifact 与真实训练边界
   - `training_plan.json` 只能表述为三阶段 production training plan artifact，记录阶段顺序、目标、条件输入、输出占位和 QC 映射。
   - `training_run.json` 与 skeleton checkpoint 可以引用 `training_plan_path`，但 checkpoint 必须继续保持 `status=not_trained` 与 `usable_for_inference=false`。
   - 在真实 production training loop、真实 checkpoint artifact 和 production inference backend 完成前，不得把 v0.72.20 描述为已训练 production latent diffusion / ControlNet / DiT 模型。

15. 保持 P4 mask-image tissue alignment QC proxy 与专家语义 QC 边界
   - `mask_image_tissue_alignment_proxy` 只能表述为基于生成图像组织区域 proxy 与 `mask > 0` 区域的一致性检查。
   - 该指标可以暴露粗粒度 mask/image 错位，并在明显错位时让 mask-region / overall QC fail。
   - 它不能被描述为病理语义分类器、专家级 segmentation 验证或真实 morphology consistency model。
   - 当图像没有可分离的明亮背景/组织候选时，metric 必须保留可解释 message，不能把不可判定场景伪装为强语义结论。

15. 保持 generation output diagnostics manifest 与 production writer 边界
   - `generation_output_diagnostics.json` 只能表述为集中诊断 manifest，用于汇总 artifact 路径、pyramid/write mode、writer 限制、tile execution/source 状态和 QC 摘要。
   - metadata、generation run summary 和函数返回值可以引用 diagnostics manifest，但 diagnostics manifest 不替代 `metadata.json`、`qc.json` 或 writer transaction manifest。
   - smoke-cascade 可以记录 `tile_manifest.json` 和 `tile_source_manifest.json` 的状态；torch-diffusion-smoke 没有 tile execution manifest 时必须显式 `applicable=false`，不能伪造 tile 完成状态。
   - `writer_summary.resume_capable=false` 与 transaction manifest path 必须保留，不能因为集中诊断 manifest 或 temporary publish recovery 存在而把当前 writer 描述为可在同一 OME-TIFF 文件内续写的 production writer。

## 禁止变更项

- 未经确认，不做与 P1 无关的实现重构、不改默认生成行为。
- 不把审计记录本身包装成新发布；只有实际功能补救才升级版本。
- 不删除现有 `build/validation/` 工件；它们是历史验证证据。
- 不把“现存工件仍可校验”表述成“本轮已重新执行真实 SVS 全链路”。
- 不把当前 v0.72.32 基线提交表述为已发布版本；tag、打包需另行执行并验证。
- 不把当前 PySide6 GUI flow 描述为后台任务系统；它支持同步本地 queued job 执行、刷新和输出摘要查看，但不包含后台 daemon、并发队列、运行中取消、跨机器调度或线程化 Qt 执行。
- 不把 v0.72.18 的 smoke direct tile source streaming resume 描述为完整 production gigapixel writer；当前 iterator writer 不组装完整 level array，smoke 接入也不再预先构造整张 blended canvas，并可恢复 direct tile source 物化 manifest，但仍由 deterministic smoke renderer 生成 tile source，且不支持中断后续写同一个 OME-TIFF 文件。
- 不把 v0.72.3 的 sampled policy condition packet 集成或 generation 输出摘要保留描述为 production style/texture model；它只记录显式传入的 sampled policy artifact 摘要，不自动调用 sampler 或改变 generation backend。
- 不把 v0.72.4 的 checkpoint inference artifact contract gate 描述为 production 生成模型；它只加固 manifest 入口契约，不训练或运行真实 production backend。
- 不把 v0.72.5 的 tile iterator streaming writer 原子发布事务描述为可恢复 production OME-TIFF writer；它只提供临时文件写入、发布前校验、原子替换和事务 manifest。v0.72.26 只补充完整临时 OME-TIFF 的验证发布恢复，仍不支持同一 OME-TIFF 文件内部 partial tile 续写。
- 不把 v0.72.7 的 production training dataset contract 与 training index JSONL 证据核对描述为 production latent diffusion / ControlNet / DiT 训练；它只校验训练数据与目标 backend 契约，并记录在 run manifest 和 skeleton checkpoint 中。
- 不把 v0.72.8 的 training objective/loss/QC mapping contract 描述为真实 production loss 计算或训练 loop；它只校验训练目标声明与 QC 映射，并记录在 run manifest 和 skeleton checkpoint 中。
- 不把 v0.72.10 的 checkpoint/backend compatibility contract、inference architecture/condition contract 描述为真实 production inference backend；它只声明并校验 checkpoint 可被哪些 generation backend 消费。
- 不把 v0.72.11 的 mask-image tissue alignment QC proxy 描述为专家级语义一致性验证；它只提供粗粒度组织区域对齐信号。
- 不把 v0.72.12 的 prior production readiness contract gate 描述为 production trainable prior；它只声明和校验 readiness 契约，不实现 trainable style encoder、texture codebook、VQ-VAE 或 morphology token sampler。
- 不把 v0.72.21 的 production prior component contract interface 描述为 production trainable prior；它只校验 contract version、condition outputs 和训练证据 artifact path/hash，不实现 trainable layout/mask generator、style encoder、texture codebook、VQ-VAE 或 morphology token sampler。
- 不把 v0.72.22 的 fitted style latent prior 描述为深度 production style encoder；它只基于 RGB mean/std 拟合 PCA-style latent，不实现 VAE style latent、style transfer 或真实 generation backend 条件学习。
- 不把 v0.72.23 的 fitted texture morphology latent/codebook contract 描述为 trainable texture codebook、VQ-VAE 或 production morphology token sampler；它只基于 embedding cluster centroid 生成可审计 token 和标准化 morphology latent，不实现真实 generation backend 条件学习。
- 不把 v0.72.24 的 `production-tile-stream` 描述为内置 production latent diffusion / ControlNet / DiT 推理模型、真实 production training loop 或 OME-TIFF 文件级可恢复 writer；它只是外部 tile generator 命令合同、磁盘 tile source 物化、memmap mask、streaming QC 和原子 OME 发布的执行闭环。
- 不把 v0.72.26 的 OME streaming started transaction temporary publish recovery 描述为完整 OME-TIFF 文件级续写；它只在上次 `started` transaction 留下完整、可读且 shape 匹配的临时 OME-TIFF 时验证并原子发布该临时文件，不支持在同一个 OME-TIFF 文件内部 append 或 partial tile 续写。
- 不把 v0.72.27 的 production tile request manifest contract 描述为内置 production latent diffusion / ControlNet / DiT 推理模型；它只为外部 tile backend 提供 per-tile request sidecar JSON、`{tile_request_path}` 命令占位符和 resume 不可变输入合同。
- 不把 v0.72.28 的 production failed tile retry/resume 描述为同一 OME-TIFF 文件内部续写或内置 production 推理模型；它只在 production tile source 物化阶段显式重试 failed tile record，并保留 retry 审计字段。
- 不把 v0.72.29 的 completed target OME validation reuse 描述为同一 OME-TIFF 文件内部续写；它只在已有 completed transaction 与当前 target/manifest/shape 匹配时验证并复用完整目标 OME-TIFF，不支持 append 或 partial tile 续写。
- 不把 v0.72.30 的 OME streaming disk-space preflight 描述为精确 TIFF 文件大小预测、同一 OME-TIFF 文件内部续写或内置 production 推理模型；它只在正常完整写出前用 raw pyramid byte estimate 加安全余量做保守磁盘空间检查，空间不足时提前失败并记录 transaction。
- 不把 v0.72.31 的 production tile backend execution evidence 描述为内置 production latent diffusion / ControlNet / DiT 推理模型、真实 production training loop 或 OME-TIFF 文件级可恢复 writer；它只记录外部 backend 逐 tile 执行时的 request、命令执行摘要和输出文件哈希证据。
- 不把 v0.72.32 的 OME streaming writer progress evidence 描述为同一 OME-TIFF 文件内部 partial tile 续写；它只记录正常完整写出路径中 tile iterator 已 yield 给 `tifffile` 的进度，并在失败时保留中断诊断。
- 不把 v0.72.13 的 PyTorch diffusion smoke checkpoint inference planning contract 描述为 production 生成模型或真实 production 推理 backend；它只让 smoke 训练产物以 `production_ready=false` 的契约进入 `torch-diffusion-smoke` planning。
- 不把 v0.72.14 的 generation output diagnostics manifest 描述为 production writer、可恢复 OME-TIFF 续写、真实 production 推理 backend 或专家级 QC；它只是集中输出完整性与 writer/QC 状态审计。
- 不把 v0.72.20 的 production training plan artifact 描述为真实 production training loop；它只把已校验的 dataset/objective/QC mapping 契约组织成可审计三阶段计划。
- 不把 v0.72.16 的 smoke direct tile source streaming resume 描述为 production diffusion backend 或可恢复 OME-TIFF writer；它只是降低 smoke tile-streaming writer 的 full-canvas 内存前置成本，并让 smoke direct tile source 物化过程可从 partial manifest 继续完成。
- 不把 v0.72.17 的 torch-diffusion-smoke tile-streaming writer 接入描述为 production diffusion backend 或可恢复 OME-TIFF writer；它只把 smoke sample preview 物化为磁盘 tile source，并复用现有受限 tiled iterator writer。
- 不把 v0.72.18 的 writer tile-grid seam QC proxy 描述为专家级 morphology seam detector、真实 stain/focus/seam production QC 或病理语义一致性模型；它只按 writer chunk/tile grid 的内部边界计算轻量 seam 相似度，缺少 grid 时保留中线 proxy 回退。
- 不把 v0.72.19 的 stain/focus QC proxy 描述为专家级 stain/focus 质量模型、真实 production QC 或病理语义一致性模型；它只记录 RGB 通道分离和局部边缘对比两个轻量信号。
- 不因为补救而扩展到当前系统边界外内容，例如 IHC/IF、临床分子标签、真人专家盲评、下游训练验证、权限/签名系统、数据库或远端协作审阅。

## 补救优先级决策

- 第一优先级：审计文件归位、文档诚实度、契约闭环。
- 第二优先级：真实可交互 PySide6 配置页与本地同步 GUI flow。
- 第三优先级：environment/真实 SVS 复跑验证。
- 第四优先级：production 级生成模型与 WSI 输出；P4 下一步应在已接入外部 production tile backend 和临时 OME 发布恢复的基础上，继续推进同一 OME-TIFF 文件内部 partial tile 续写或等价的完整文件级恢复能力，P3/P4 后续再补内置 production 模型本体。
- 第五优先级：大文件拆分与维护性收敛。
