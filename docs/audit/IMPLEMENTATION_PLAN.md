# v0.72.32 审计补救实施计划

## 当前定位

当前仓库不是完整 production H&E WSI 生成器，而是一个可测试、可追踪的 core/CLI 工程骨架，并具备 smoke/proxy 级生成、QC、归档链路、可交互 PySide6 配置页、GUI 内同步 queued job 执行/状态刷新/输出摘要查看、checkpoint inference artifact contract gate、generation backend compatibility gate、inference architecture/condition contract gate、PyTorch diffusion smoke checkpoint inference planning contract、production training dataset contract、training index JSONL 证据核对、training objective/loss/QC mapping contract、production training plan artifact、可恢复 tile manifest contract、smoke resume execution、磁盘 `.npy` tile source contract 校验、磁盘 tile source 内存组装写出、受限 tiled iterator streaming writer、streaming writer pyramid level contract、tile iterator streaming writer 原子发布事务 manifest、OME streaming writer progress sidecar、OME streaming started transaction temporary publish recovery、completed target OME validation reuse、OME streaming disk-space preflight、production per-tile request manifest、production failed tile 显式 retry/resume、production tile backend execution evidence、`generation_output_diagnostics.json` 输出诊断 manifest、smoke 四层直接 tile source streaming 写出、direct tile source 物化 resume manifest、torch-diffusion-smoke tile-streaming writer 接入、`production-tile-stream` 外部 tile generator backend、writer tile-grid seam QC proxy、stain/focus QC proxy、mask-image tissue alignment QC proxy、tile blending 的 channel-wise 内存收敛、deterministic sampled style/texture policy artifact、fitted style latent prior、fitted texture morphology latent/codebook contract、prior production readiness contract gate、production prior component contract interface、condition packet 对 sampled style/texture policy 的可审计消费，以及 generation 输出对 sampled style/texture policy 摘要的保留。v0.72.32 当前补齐的是 OME streaming writer progress evidence：正常完整 tile iterator 写出路径会生成 `<target>.progress.json`，记录 planned/yielded/completed tile 数、当前 level/tile grid、last tile 和 failure reason，并把 `progress_summary` 写入 transaction/report/diagnostics。代码能力继承 v0.72.24 的 P4 production tile-stream 外部生产 tile backend 执行合同、v0.72.26 的 OME 发布阶段完整临时文件恢复、v0.72.27 的 per-tile request manifest、v0.72.28 的 failed tile 显式重试恢复、v0.72.29 的 completed target validation reuse、v0.72.30 的 OME streaming disk-space preflight 和 v0.72.31 的 production tile backend execution evidence。该能力补齐的是 GB 级写出中断诊断，不等于同一 OME-TIFF 文件内部 partial tile 续写、内置 production latent diffusion / ControlNet / DiT 模型、真实训练 loss 计算、真实 production 模型本体推理、深度 production style encoder、trainable texture codebook、VQ-VAE、production morphology token sampler 或专家级语义 QC。后续补救顺序应继续进入真实 production 模型训练/推理、生产级 prior，或把 P4 writer 从“tile source 阶段可恢复 + per-tile request/execution evidence + failed tile 显式 retry + 完整临时/目标 OME 文件级恢复 + 写入前磁盘空间 preflight + progress sidecar”推进到真正 OME-TIFF 内部 partial tile 续写或等价完整恢复能力。

## P0. 审计材料归位与证据闭环

- 目标：把审计材料集中到 `docs/audit/`，并让 README、需求记录和变更日志能指向新位置。
- 当前状态：本轮已执行迁移，后续只维护 `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md`。
- 完成标准：`docs/` 根目录不再保留上述三个审计文件；`README.md` 能直接找到审计入口。

## P0.5. v0.63.0 交付收口

- 目标：把当前已验证的 v0.63.0 工作区状态收敛为可追踪的提交/发布基线。
- 当前状态：v0.63.0 已提交到 `main` 作为后续 worker 基线；两个历史 worker worktree 仍存在，尚未打 tag 或形成发布包。
- 建议任务包：
  - 已完成：审查 `git diff --stat` 和 `git status --short`，确认所有 v0.63.0 改动都属于本轮范围。
  - 已完成：`.agent/logs/` 原始 JSONL 日志继续被忽略，任务和报告文件保留在 `.agent/tasks/`、`.agent/reports/`。
  - 删除或保留 `.worktrees/p1-qc-review-validate`、`.worktrees/p1-output-summary-contract` 前先确认不再需要继续审查。
  - 待完成：如需正式发布，补 tag 和发布包流程。
- 完成标准：`git status --short` 只剩预期未跟踪/忽略项或完全干净；v0.63.0 有明确 commit，tag/发布包状态被清楚记录。

## P1. 契约一致性与文档诚实度

- 目标：避免把 smoke/proxy 能力或 UI 骨架描述成完整项目成果。
- 当前状态：v0.63.0 已完成第一轮补救。
- 已完成：
  - README 的 M5/M7 和当前边界已明确标注 smoke/proxy、控制层与 production 完整成果的差异。
  - 新增仓库实体 `AGENTS.md`，让会话规则可持久追踪。
  - `he-wsi-gen validate qc-review <path>` 已接入现有 `validate_qc_review()`。
  - `collect_output_summary()` 已对 metadata 执行 schema 校验，并校验 metadata/QC/review 的 generated id 一致性。
- 影响范围：`README.md`、`AGENTS.md`、`src/he_wsi_generator/schemas.py`、`src/he_wsi_generator/cli.py`、`src/he_wsi_generator/ui/controller.py`、`tests/test_ui.py`、`tests/test_qc_review.py`。
- 完成标准：相关测试已覆盖坏 metadata、坏 qc_review、id 不一致和 validate CLI 路径。

## P2. 可交互 PySide6 自定义配置页与本地 GUI flow

- 目标：实现设计文档要求的本地单页控制台，让用户不手工编辑中间 JSON 也能完成配置。
- 当前状态：v0.72.32 已完成可交互配置页、非 Qt UI workflow helper、generation config 保存、queued local job record 创建、GUI 内同步执行 queued job、刷新 job 状态和 metadata/QC/可选 qc_review 输出摘要查看、首轮 CLI/torch smoke helper 维护性收敛，以及 P3 checkpoint inference artifact contract gate、generation backend compatibility gate、inference architecture/condition contract gate、production training dataset contract、training index JSONL 证据核对、training objective/loss/QC mapping contract、production training plan artifact、P4 可恢复 tile 状态、smoke resume execution、磁盘 tile source contract/assembly、受限 tile iterator streaming、streaming writer pyramid contract、tile iterator streaming writer 原子发布事务 manifest、OME streaming writer progress sidecar、OME streaming started transaction temporary publish recovery、completed target OME validation reuse、OME streaming disk-space preflight、production per-tile request manifest、production failed tile 显式 retry/resume、production tile backend execution evidence、generation output diagnostics manifest、smoke 四层 tile source streaming 接入和 tile-streaming 顺序物化、`production-tile-stream` 外部 tile generator backend、writer tile-grid seam QC proxy、stain/focus QC proxy、mask-image tissue alignment QC proxy、tile blending 的 channel-wise 内存收敛，以及 P5 deterministic sampled style/texture policy artifact、fitted style latent prior、prior production readiness contract gate、production prior component contract interface、CLI、condition packet 审计消费、generation 输出摘要保留和当前环境真实 SVS smoke/proxy 历史复跑验证；本轮在代码集中验证通过后同步 OME streaming writer progress evidence 相关设计/开发文档代码追踪块。
- 建议任务包：
  - 已完成：建立独立 conda UI 环境并验证 PySide6 offscreen。
  - 已完成：把 `pyside_app.py` 从只读字段展示升级为真实表单：路径选择、anchor preset、seed、sample steps、prior/checkpoint、输出目录、QC 设置。
  - 已完成：实现最小 label mapping 面板，非法 raw label、重复编号和空映射会阻塞。
  - 已完成：将 UI 表单保存为 JSON generation config，并通过 `JobRunner` 创建 queued local job record。
  - 已完成：给 PySide6 交互层补最小 GUI 单元/集成测试；无 GUI 环境下保留明确 skip。
  - 已完成：GUI 内执行 queued job、刷新 job 状态、展示 metadata/QC/qc_review 输出摘要。
  - 已完成：将 CLI 命令执行分发抽到 `src/he_wsi_generator/cli_commands.py`，保持入口和参数行为不变。
  - 已完成：将 `torch_training.py` 的纯 manifest/schema/validation helper 抽到 `src/he_wsi_generator/models/torch_training_contracts.py`，保持公开训练/采样函数不变。
- 决策点：是否让 `run-generation` 默认先弹配置页需要用户确认；默认建议保留 CLI 自动化，把 GUI 放在 `launch-ui`。
- 完成标准：安装 PySide6 后，用户能通过 UI 配置、保存 generation config、创建 smoke generation queued job、同步执行 queued job、刷新状态并查看输出摘要；CLI dispatch 与 torch helper 已完成行为保持拆分，后台 daemon、并发队列、运行中进程终止和线程化 Qt 执行不属于本阶段。

## P3. Production 级生成模型补齐

- 目标：从 smoke/proxy 生成升级到设计目标中的结构锚定多分辨率生成模型。
- 当前状态：v0.72.32 继承 checkpoint inference artifact contract gate：`usable_for_inference=true` 必须有 trained 状态、backend/target/checkpoint/hash 字段、真实 checkpoint 文件、matching SHA-256、显式 `inference_contract`、非空 `compatible_generation_backends`、`model_architecture_contract` 和 `condition_input_contract`；generation plan 会校验当前 backend 是否被 checkpoint 允许消费，并保留模型架构与条件输入契约摘要。`train_torch_diffusion_smoke_model()` 产物会写入 `usable_for_inference=true` 和 `inference_contract`，仅允许 `torch-diffusion-smoke` backend planning，并继续标记 `production_ready=false`。production training dataset contract 要求 `init-training-run` 必须声明 `training_backend=latent_diffusion_unet`，并校验 training index path、split 计数、四层 cascade 记录数、最小样本数、必需条件输入、6 类 mask schema 和 production readiness 标记；v0.72.7 进一步读取实际 training index JSONL，核对 record 数、split/level 计数、tile 坐标、conditioning 证据和 mask class mapping；v0.72.8 要求 `training_objective_contract` 声明五类训练约束、非负 loss weights、阶段目标映射和 QC 指标映射；v0.72.20 进一步写出 `training_plan.json`，记录 `prior_ready -> image_generator -> wsi_consistency` 三阶段计划、条件输入、输出占位和 QC 映射。v0.72.28 的 `--retry-failed-tiles` 只让外部 production tile backend 在 tile source 物化阶段显式重试 failed record；v0.72.29 的 completed target OME validation reuse 只减少已发布 OME 目标文件重复写出；v0.72.30 的 disk-space preflight 只在 OME streaming 正常写出前做资源预算 guard；v0.72.31 的 backend execution evidence 只记录外部 tile backend 执行证据；v0.72.32 的 writer progress evidence 只记录 OME streaming writer 已 yield tile 进度，不实现 production 模型本体、真实 loss 计算、真实训练 loop 或内置 production inference backend。
- 建议任务包：
  - 已完成：建立 checkpoint manifest 的真实 inference artifact contract gate。
  - 已完成：建立 checkpoint 与 generation backend 的 compatibility contract gate。
  - 已完成：建立 checkpoint 的模型架构与条件输入契约 gate，要求可推理 manifest 声明 `latent_diffusion_unet` 架构摘要和七类必需推理条件输入。
  - 已完成：将 PyTorch diffusion smoke checkpoint 接入统一 generation planning，限定 `torch-diffusion-smoke` backend 并保留 `production_ready=false`。
  - 已完成：定义 production training dataset contract、训练运行配置契约和实际 training index JSONL 证据核对。
  - 已完成：定义 training objective/loss/QC mapping contract gate，确保训练目标、阶段映射和自动 QC 指标映射在 skeleton run 中可审计。
  - 已完成：写出 production training plan artifact，记录三阶段训练计划、条件输入、阶段输出占位和 QC mapping，并由 run / checkpoint 引用。
  - 实现或接入 production latent diffusion / ControlNet / DiT 之一，保留 `structure_anchor`、mask、style、texture 和 source condition。
  - 实现真实 multi-scale cascade sampler，不再只输出 preview/proxy。
  - 增加小规模可重复训练 fixture，避免每次验证都依赖大型真实数据。
- 完成标准：production 模型 checkpoint 可被标记为 `usable_for_inference=true`，并能用真实推理 backend 生成完整交付物；当前 smoke/test fixture 的 `production_ready=false` 不满足 production 完成标准。

## P4. 生产级 WSI 输出、恢复和 QC 验证

- 目标：补齐 gigapixel 级交付可靠性。
- 当前状态：v0.72.32 继承并扩展 P4 contract/执行级补救：`build_resumable_tile_manifest()` / `update_resumable_tile_manifest()` / `validate_resumable_tile_manifest()` / `require_complete_tile_manifest()` 可记录和校验 tile 执行状态；`run-generation --backend smoke-cascade --resume-tile-manifest` 可从 partial manifest 继续 pending tile 并拒绝 failed/gapped/missing completed tile；`write_pyramid_ome_tiff(..., tile_source_manifest=...)` 可在写出前校验磁盘 `.npy` tile source manifest；`write_pyramid_ome_tiff_from_tile_sources()` 可从磁盘 tile source manifest 内存组装 pyramid 并写出；`write_pyramid_ome_tiff_streaming_from_tile_sources()` 可按 TIFF tile grid 从磁盘逐 tile iterator 写出且不组装完整 level array，并通过同目录临时 OME-TIFF、发布前 OME/pyramid shape 校验、原子替换、`<target>.progress.json` 和 `<target>.transaction.json` 事务 manifest 降低半成品污染风险；v0.72.26 支持从上次 `started` transaction 中验证并发布完整临时 OME-TIFF，completed transaction 记录 `recovery_action=published_existing_temporary_ome_tiff`，报告记录 `recovered_from_temporary=true`；v0.72.29 支持在既有 `completed` transaction 与当前 target/manifest/shape 匹配时验证并复用已发布目标 OME-TIFF，completed transaction 记录 `recovery_action=validated_existing_target_ome_tiff`，报告和 diagnostics 记录 `reused_existing_target=true`；v0.72.30 在正常完整写出前执行磁盘空间 preflight，按 raw pyramid byte estimate 加同等安全余量检查目标文件系统，空间不足时在 tile iterator 开始前显式失败并写出 failed transaction，正常写出时 transaction/report/diagnostics 记录 `disk_space_preflight`；v0.72.32 在正常完整写出路径记录 planned/yielded/completed tile 数、当前 level/tile grid、last tile、failure reason 和 `progress_semantics`，并把 `progress_summary` 写入 transaction/report/diagnostics；streaming writer 继续校验 pyramid level order，且 `resume_capable=false` 保留；`run-generation --backend smoke-cascade --wsi-writer tile-streaming` 现在直接按 pyramid level 和 TIFF tile grid 写出四层 smoke tile source manifest，物化过程维护可恢复 manifest并能复用已完成 streaming tile，再写出四层 OME-TIFF；`run-generation --backend torch-diffusion-smoke --wsi-writer tile-streaming` 会将四层 sample preview 物化为磁盘 tile source，再写出四层 OME-TIFF；`run-generation --backend production-tile-stream --wsi-writer tile-streaming` 会校验 production-ready checkpoint 和 `external_tile_generator_v1` artifact，按四层 pyramid tile grid 逐 tile 写出 `production_tile_requests/*.request.json` 后调用外部 backend，写出磁盘 RGB tile、level0 mask tile、request/backend execution/output evidence、可恢复 `production_tile_source_manifest.json`、memmap mask、OME-TIFF、metadata、QC、batch index 和 diagnostics；默认拒绝 failed tile manifest，显式 `--retry-failed-tiles` 时可在 immutable manifest 和 `tile_request_path` 校验后重试 failed record；`run_smoke_generation()` / `run_torch_diffusion_smoke_generation()` / `run_production_tile_stream_generation()` 会写出 `generation_output_diagnostics.json`，集中汇总 artifact、writer、tile execution/source、backend execution summary、progress summary 和 QC 状态；`build_qc_report()` 会记录 `writer tile-grid seam QC proxy`、`stain/focus QC proxy` 和 `mask_image_tissue_alignment_proxy`，用于暴露 writer 内部 tile 边界突变、近单色/无局部边缘对比输出，以及 mask 与图像组织区域粗粒度错位。本轮已在代码集中验证通过后同步 OME streaming writer progress evidence 相关设计/开发文档代码追踪块；该状态实现了外部 production backend 的磁盘级逐 tile 生成合同、per-tile request 输入合同、backend execution evidence、failed tile 显式重试恢复、OME 发布阶段完整临时文件恢复、已发布目标 OME 文件级验证复用、写入前磁盘空间预算 guard 和 writer 中断进度诊断，但仍不是同一 OME-TIFF 文件内部中断追加写入，也不是内置 production diffusion 模型、精确 TIFF 大小预测或专家级语义 QC。
- 建议任务包：
  - 已完成：实现可恢复 tile manifest/state contract。
  - 已完成：实现磁盘 `.npy` tile source contract gate 和 streaming limitation report。
  - 已完成：将 smoke generation run manifest 的 completed/pending tile 信息接入恢复执行。
  - 已完成：实现磁盘 tile source manifest 的内存组装写出接口，并明确 production streaming 限制。
  - 已完成：实现受限的磁盘 tile source tiled iterator streaming writer，并显式接入 smoke-cascade writer 选择。
  - 已完成：为 streaming writer 加固 high-to-low pyramid level contract，并让 smoke-cascade 显式 `tile-streaming` 路径写出四层 OME-TIFF。
  - 已完成：为 tile iterator streaming writer 增加临时文件写入、发布前校验、原子发布和事务 manifest，失败时保留既有目标。
  - 已完成：为 tile iterator streaming writer 增加 started transaction 完整临时 OME-TIFF 验证发布恢复，避免发布阶段崩溃后重复 tile iterator 写出。
  - 已完成：为 tile iterator streaming writer 增加 completed transaction 已发布目标 OME-TIFF 验证复用，避免重复运行时无意义重写已校验通过的目标 OME-TIFF。
  - 已完成：为 tile iterator streaming writer 增加写入前磁盘空间 preflight，空间不足时在 tile iterator 开始前失败并记录 failed transaction，正常写出时把 `disk_space_preflight` 写入 transaction/report/diagnostics。
  - 已完成：为 tile iterator streaming writer 增加 progress sidecar，记录 planned/yielded/completed tile 数、当前 level/tile grid 和失败原因，并将 `progress_summary` 写入 transaction/report/diagnostics。
  - 已完成：为 generation 输出增加集中 diagnostics manifest，记录输出完整性、writer 限制、tile 状态和 QC 摘要，并接入 schema/CLI validator。
  - 已完成：为 QC report 增加 mask-image tissue alignment proxy，让 mask 与图像组织区域明显错位时触发 mask-region / overall fail。
  - 已完成：让 QC `seam_score_proxy` 优先使用 writer chunk/tile grid 的内部边界，避免只检查图像中线而漏掉非中线 tile seam。
  - 已完成：为 QC report 增加 `stain_color_separation_proxy` 和 `focus_edge_density_proxy`，让近单色 RGB 通道和几乎无局部边缘对比的输出触发 fail。
  - 已完成：让 smoke-cascade 的显式 `tile-streaming` writer 直接生成四层磁盘 tile source，避免为 tiled iterator writer 预先构造整张 blended canvas。
  - 已完成：让 smoke direct tile source 物化 manifest 记录 completed/pending/failed 计数，并在重跑时复用 completed tile、补齐 pending tile。
  - 已完成：让 `torch-diffusion-smoke` 显式 `tile-streaming` writer 将四层 sample preview 物化为磁盘 tile source，并复用 tiled iterator writer 写出 OME-TIFF。
  - 已完成：接入 `production-tile-stream` 外部 production backend 磁盘级逐 tile 生成，支持 production-ready checkpoint gate、tile source 阶段恢复、memmap mask 和 streaming QC。
  - 已完成：为 `production-tile-stream` 增加 per-tile request manifest，外部 backend 可通过 `{tile_request_path}` 读取完整 tile 请求；resume 校验把 request path 纳入不可变合同。
  - 已完成：为 `production-tile-stream` 增加 failed tile 显式 retry/resume；默认拒绝 failed manifest，显式 retry 时记录 previous status/error、retry count 和 attempt count。
  - 已完成：为 `production-tile-stream` 增加 backend execution evidence；新完成 tile 记录 request JSON、外部命令执行摘要和 RGB/mask 输出文件哈希，manifest 与 diagnostics 汇总 evidence 覆盖。
  - 待完成：支持同一 OME-TIFF 文件内部中断追加写入；当前 writer 只能在 tile source 阶段恢复、在上次已生成完整临时 OME-TIFF 时验证并发布该临时文件，或验证复用既有 completed transaction 的完整目标 OME-TIFF。
  - 扩展 QC 到更真实的 stain、focus、seam、专家级 mask-image semantic consistency 和 non-copy 审计。
  - 保留当前自动 QC 的 pass/warning/fail 和 reference distribution 审计链。
- 完成标准：中断后可恢复生成；不完整输出不能被标为 pass；writer 本体能在不持有完整 gigapixel canvas 的情况下逐 tile 写入，并支持同一 OME-TIFF 文件内部 partial tile 续写或等价完整文件级恢复。

## P4.5. 生产级 prior 与采样策略

- 目标：补齐 production 级 layout/style/texture prior 与采样策略。
- 当前状态：v0.72.32 继承 deterministic sampled style/texture policy artifact，让 `build-condition-packet` 可选读取 `sampled_style_policy` / `sampled_texture_policy`，校验 source prior path 与关键 selected 字段后写入 `artifact_inputs` 和 `conditions.style_seed` / `conditions.texture_token`，并在 smoke/torch generation 输出摘要中继续保留 selected style/token 摘要；`build-style-prior` 现在会拟合 `fitted_rgb_stats_pca_v1`，在 `style_prior.json` 中写出 encoder 摘要和 tile-level `style_latent`，`sample-style-policy` 会输出 selected `style_latent` 与 encoder reference；`build-texture-prior` 现在会写出 `fitted_embedding_cluster_codebook_v1`、prototype `texture_token` 和 `morphology_latent`，`sample-texture-policy`、condition packet、smoke summary 和 torch smoke summary 会保留 selected `morphology_latent` 与 codebook reference；prior manifest `production_readiness` contract gate 默认标记统计型 layout/style/texture prior 为非 production-ready，并拒绝缺 component contract 或 statistical/proxy backend 却声明 `production_ready=true` 的 manifest；当 manifest 声明 `production_ready=true` 时，layout/style/texture component 还必须声明 `production_prior_component_v1`、所需 `condition_outputs` 和与 manifest artifact path/hash 匹配的 `training_evidence`。该能力仍不是 production trainable layout/mask generator、深度 style encoder、trainable texture codebook、VQ-VAE 或 production morphology token sampler。
- 建议任务包：
  - 已完成：从统计型 style prior 生成 `sampled_style_policy` artifact 和 CLI。
  - 已完成：为 style prior 增加 fitted RGB-stat PCA style latent encoder，并让 sampled style policy 携带 selected `style_latent`。
  - 已完成：从统计型 texture prior 生成 `sampled_texture_policy` artifact 和 CLI。
  - 已完成：为 texture prior 增加 fitted embedding-cluster codebook、prototype `texture_token` 和 `morphology_latent`，并让 sampled texture policy / condition packet / generation summary 保留 selected `morphology_latent`。
  - 已完成：让 condition packet 显式消费 sampled style/texture policy artifact，记录可审计 style/texture 条件摘要。
  - 已完成：让 smoke/torch generation 输出继续保留 sampled style/texture policy 的 selected style/token 摘要。
  - 已完成：为 prior manifest 增加 production readiness contract gate，防止统计型 prior 被误标记为 production-ready。
  - 待完成：实现 production 级深度 trainable style encoder / stain-style latent，并接入真实 generation backend。
  - 待完成：实现 production 级 texture codebook / morphology token sampler，并接入真实 generation backend。
- 完成标准：style/texture prior 不再只是统计 artifact，能被 production inference backend 以可解释、可复现的方式消费。

## P5. 环境化复跑验证

- 目标：区分“历史上有工件”和“当前环境可复现”。
- 当前状态：已创建 conda 环境 `MultiCenterWSIGenerator`，安装完整可选依赖并通过 PyTorch/UI/P4/P5 定向测试、PySide6 offscreen 表单 smoke；mamba 与 conda 环境列表指向同一个 prefix，因此不删除该环境目录，后续验证统一使用 `conda run -n MultiCenterWSIGenerator ...`。v0.72.32 本轮围绕 OME streaming writer progress evidence、outputs/generation/schema/CLI/version 闭环做集中验证：`conda run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_schemas tests.test_cli tests.test_version -v` 通过，`Ran 84 tests in 3.295s OK`；收束审计补充执行 `conda run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v` 通过，`Ran 300 tests in 28.868s OK`；CLI 版本输出 `v0.72.32`；`outputs/ome_tiff.py` / `generation/executor.py` / `schemas.py` py_compile 通过，无输出；默认 generation config CLI 校验输出 `generation-config valid: configs/generation.default.json`；`git diff --check` 通过，无输出。真实 SVS smoke/proxy 复跑已在历史 v0.72.1 轮次完成，本轮不重复执行真实 SVS 全链路。
- 建议任务包：
  - 已完成：准备独立 conda/pip 环境说明，覆盖 `torch`、`ui`、`wsi`、`outputs`、`yaml`。
  - 已完成：复跑完整单元测试、PyTorch smoke 路径和 PySide6 当前窗口创建 smoke。
  - 待完成：如需当前版本再次验收真实数据，复跑真实 SVS 链路，并记录输入数据、输出目录、metadata/QC/batch index 证据。
  - 把每条命令和输出摘要记录到 `docs/audit/ACCEPTANCE_CHECKLIST.md` 与 `docs/CHANGELOG.md`。
- 完成标准：当前机器可从干净环境复现主要验证结果。

## P6. 维护性收敛

- 目标：降低后续补救风险，不做风格化大重构。
- 当前状态：v0.65.1 已完成首轮维护性收敛；v0.72.32 保持统计 prior 的 deterministic policy helper、condition packet 审计消费和 generation 输出摘要保留，并继承 checkpoint inference artifact contract、production training dataset contract、training index JSONL 证据核对、training objective/loss/QC mapping contract、production training plan artifact、production prior component contract interface、fitted style latent prior、fitted texture morphology latent/codebook contract、output diagnostics manifest、外部 production tile backend 执行合同、OME streaming started transaction temporary publish recovery、completed target OME validation reuse、OME streaming disk-space preflight、OME streaming writer progress sidecar、production per-tile request manifest、production failed tile 显式 retry/resume 和 production tile backend execution evidence；本轮同步文档追踪块与审计基线，但仍未实现内置 production prior/model 本体、真实 production 模型推理或专家级语义 QC。
- 建议任务包：
  - 优先拆分 `src/he_wsi_generator/cli.py` 的命令注册和命令执行分支。
  - 再拆分 `src/he_wsi_generator/models/torch_training.py` 中训练、采样、manifest/schema 辅助逻辑。
  - 每次拆分都保持行为不变，并先跑相关测试。
- 完成标准：测试不减少，功能边界更清楚，后续 production 模型和 UI 迭代不再堆入单个大文件。
