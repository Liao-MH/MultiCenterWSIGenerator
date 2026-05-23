# DEMANDS

## v0.44.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的批量查看入口：在 `run-local-job`、`cancel-local-job` 和 `inspect-local-job` 之外，再提供一个可复现的 list 命令，直接列出 job_root 下的持久化 job 状态。

### 结构化需求

- 版本号升级为 `v0.44.0`。
- CLI 新增 `list-local-jobs <job_root>`。
- `list-local-jobs` 必须读取 job_root 下的持久化 job 记录，并以 JSON 数组输出，便于脚本和人工查看任务状态。
- `list-local-jobs` 对未知 job、非法 job id 或损坏记录必须显式报错并返回非零退出码，不得静默跳过坏记录。
- 新增/更新测试覆盖 list 成功路径和损坏记录失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 job 记录批量查看入口，不实现分页、过滤、后台 daemon、并发调度或状态订阅。
- `list-local-jobs` 只读 job_root 中的持久化记录，不会修改 job 状态。

## v0.43.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的查看入口：既然 `run-local-job` 和 `cancel-local-job` 已经可用，`he-wsi-gen` 也应提供可复现的 inspect 命令，把持久化 job 记录导出为 JSON 供排障和状态查看。

### 结构化需求

- 版本号升级为 `v0.43.0`。
- CLI 新增 `inspect-local-job <job_root> --job-id <id>`。
- `inspect-local-job` 必须复用 `JobRunner.load_job()` 读取已持久化记录；未知 job id、非法 job id 或损坏 JSON 必须显式报错并返回非零退出码。
- 成功时必须把完整 job record 以 JSON 形式写到 stdout，便于脚本和人工查看。
- 新增/更新测试覆盖 inspect 成功路径、未知 job 失败路径和损坏记录失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 job 记录查看入口，不实现 job 编辑、重放、批量列表、后台 daemon 或并发调度。
- `inspect-local-job` 只负责读取已存在的持久化记录，不会自动执行或修改 job 状态。

## v0.42.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地任务取消的 CLI 入口：既然 UI job runner 已支持 queued job 取消，`he-wsi-gen` 也应提供可复现命令来把已排队任务显式标记为 `cancelled`。

### 结构化需求

- 版本号升级为 `v0.42.0`。
- CLI 新增 `cancel-local-job <job_root> --job-id <id> [--message <message>]`。
- `cancel-local-job` 必须复用 `JobRunner.cancel_job()`，只允许取消 `queued` job；未知 job、非法 job id 或非 queued 状态必须显式报错并返回非零退出码。
- 取消成功时必须持久化 `job.json`、写空 `stdout.txt` / `stderr.txt`，并在 stdout 输出包含 `local job cancelled` 和记录路径的信息。
- 新增/更新测试覆盖 CLI 取消成功路径和非 queued job 的失败路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本常量和版本断言。

### 边界说明

- 本次版本只暴露 queued job 的显式取消入口，不实现运行中进程终止、后台 daemon、并发队列或跨机器调度。
- `run-local-job` 仍是同步执行命令；取消命令用于已经持久化但尚未运行的 queued job。

## v0.41.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐生成完成态审计：成功输出的 smoke generation 结果必须把 `tile_traversal_plan` 物化成完成态，而不是把已完成样本保留为 pending 计划。

### 结构化需求

- 版本号升级为 `v0.41.0`。
- 新增或更新 tile traversal completion helper，使 tile traversal plan 可转换为完成态，并能显式记录部分完成时的 `completed_tile_count`、`pending_tile_count`、`resume_index` 和 `next_tile_index`。
- `run_smoke_generation` 写出的 `metadata["generation"]["tile_traversal_plan"]` 和 `generation_run.json` 中的 plan 必须在成功输出时记录完成态，至少包含 `completed_tile_count = tile_count`、`pending_tile_count = 0`、`next_tile_index = null`、所有 `tiles.status = completed`。
- 同一份成功运行记录里的 `plan.stages` 也必须切换为 completed，避免生成运行摘要看起来仍停留在 planned 状态。
- QC 的 non-copy report 必须输出轻量 similarity proxy metrics，至少覆盖 thumbnail、tissue contour、mask layout 和 global embedding 四类指标；这些指标可以保持为 proxy，不要求做全量 patch nearest-neighbor 搜索。
- QC 还要给出 tile 级 seam score proxy 和 WSI 级 style consistency proxy，作为默认自动质控的一部分。
- smoke generation 必须真正按 `canvas_size_40x` 拼接 1/1 canvas，而不是只输出固定 512 方块。
- UI job runner 需要支持把 queued job 显式取消为 `cancelled`，并持久化终态记录。
- helper 必须支持部分完成状态，用于未来的中断/恢复审计；非法 completed count 或损坏的 traversal plan 必须显式报错。
- 新增/更新测试覆盖完成态 tile traversal plan、部分完成 helper，以及成功生成输出中的 completion state。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本断言和相关测试。

### 边界说明

- 本次版本只完善生成完成态与中断态的审计表达，不改变图像合成算法、QC 规则或采样逻辑。
- 本次版本不实现真正的磁盘级断点续写、partial write recovery 或额外的任务调度机制。

## v0.40.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进生成输出的可审计性：把 `tile_traversal_plan` 写入 smoke generation metadata，便于从单个产物直接追溯 traversal / resume / write-region 信息。

### 结构化需求

- 版本号升级为 `v0.40.0`。
- `run_smoke_generation` 产生的 metadata 必须在 `generation` 字段里记录 `tile_traversal_plan`，与 run summary 中已有的物化 plan 保持一致。
- `tile_traversal_plan` 的记录必须来自 `create_generation_plan` 的输出，不得静默重建或伪造。
- 新增/更新测试覆盖 `metadata["generation"]["tile_traversal_plan"]` 的存在、tile count 和 tile origin。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置、版本断言和相关测试 fixture。

### 边界说明

- 本次版本只提升 smoke 输出的审计完整度，不改变现有 smoke backend 的图像合成逻辑。
- 本次版本不引入新的生成模型、不改变 sampling 顺序，也不实现 production cascade sampler。

## v0.39.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 中 production cascade sampler 的前置执行能力：把 `tile traversal`、`resume index` 和 `overlap weighted blending` 从 generation plan 的字符串说明推进为可测试、可审计的基础设施。

### 结构化需求

- 版本号升级为 `v0.39.0`。
- 新增 generation tiling 基础模块，能够根据 40x canvas、512x512 tile 和 overlap 生成 row-major tile traversal plan。
- Tile traversal plan 必须记录 `resume_index`、tile 总数、已完成/待处理 tile 数、每个 tile 的 40x origin、模型 tile size、实际写入区域、stride、状态和 edge crop 策略。
- Traversal 需要显式校验 canvas、tile size、overlap 和 resume index；非法输入必须报错，不得静默回退。
- 新增 overlap weighted RGB tile blending helper，支持按 tile origin 把多个 RGB tile 写入 canvas，并对 overlap 区域执行权重平均。
- Blending 必须显式拒绝非 uint8 RGB tile、无效 tile origin、空 tile 输入和未覆盖完整 canvas 的输入。
- `create_generation_plan` 必须写入物化后的 `tile_traversal_plan`，同时保留既有 `tile_traversal`、`blending` 和 `write_mode` 字段，便于旧记录可读。
- 新增/更新测试覆盖 row-major traversal、resume 状态、edge crop write region、overlap weighted blending、未覆盖 canvas 错误，以及 generation plan 中的 traversal plan。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 sampler/reconstructor 需要的 tile traversal 与 blending 基础设施，并把 generation plan 从字符串记录推进为可审计对象。
- 本次版本不实现 production latent diffusion checkpoint、不实现真实 full-WSI tile batch inference、不实现异步 resume 执行、不实现磁盘级 chunk streaming。
- 默认 generation config 仍使用 512x512 smoke canvas；更大 canvas 的 traversal/blending 已可测试，但完整 production backend 后续继续接入。

## v0.38.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 的推理顺序要求：`torch-diffusion-smoke` generation backend 必须按 `1/32 -> 1/16 -> 1/4 -> 1/1` 执行级联采样，并保存每层中间状态。

### 结构化需求

- 版本号升级为 `v0.38.0`。
- `run_torch_diffusion_smoke_generation` 必须依次执行四个 cascade levels，而不是只采样 `1/1`。
- 每层采样必须写入独立目录和 `sample_manifest.json`，generation run summary 必须记录 `cascade_sample_manifests`。
- `1/32` 层必须使用默认 zero previous-scale condition；`1/16`、`1/4`、`1/1` 必须把上一层 `sample_preview.npy` 作为 `previous_scale_condition_path` 传入 sampler。
- Metadata 的 generation 字段必须记录 `cascade_sample_manifests`，便于追踪每个级联层级的采样输入输出。
- OME-TIFF pyramid 必须由四个 cascade sample preview 组装，而不是只从最终 preview resize 出所有层。
- Generation plan stage 必须记录每个层级已完成，以及 condition inputs 包含 previous-scale RGB proxy、mask、timestep、condition features 和 checkpoint。
- 新增/更新测试覆盖 generation run summary、metadata、四层 sample manifest 路径、previous-scale condition source/path 传递和 OME-TIFF 层级输出。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级四层级联采样链路，用于把文档要求的推理顺序和中间状态保存落到可审计文件。
- 本次版本不实现 production cascade sampler、不实现 tile traversal over full WSI、不实现 overlap weighted blending、不实现真实跨倍率 latent encoder 或 WSI consistency fine-tuning。
- 级联输出仍是 64x64 preview 级 smoke sample 后 resize 组装小型 pyramid，不得标记为 production inference。

## v0.37.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1 的“上一尺度图像 / latent”条件输入要求：让 PyTorch diffusion smoke denoiser 不再只依赖当前 latent、mask、timestep 和条件特征，而是接收可审计的上一尺度 RGB proxy 条件通道。

### 结构化需求

- 版本号升级为 `v0.37.0`。
- Diffusion checkpoint payload、checkpoint manifest 和 sampler manifest 必须记录 `cross_scale_condition_schema`。
- `cross_scale_condition_schema` 必须说明条件名称、通道数、注入方式、训练来源、采样来源、根层级行为和 smoke-only production 状态。
- `train_torch_diffusion_smoke_model` 必须为 denoiser 输入拼接上一尺度 RGB proxy 条件通道；对 `1/16`、`1/4`、`1/1` 从真实 RGB tile 构建 coarse-to-target proxy，对 `1/32` 使用显式 zero root condition。
- Cross-scale 条件通道必须参与 input channel 计算，并同步写入 `denoiser_architecture.input_channels`。
- `sample_torch_diffusion_smoke_model` 必须支持可选 `previous_scale_condition_path`，可从 `.npy` RGB preview 读取上一尺度条件；未提供时必须显式记录 zero/default source，不得静默假装已有上一尺度生成结果。
- CLI `sample-torch-diffusion-smoke` 必须新增 `--previous-scale-condition` 参数并传给 sampler。
- Sampling 必须校验 checkpoint manifest/payload 中的 `cross_scale_condition_schema`；缺失或不匹配时显式报错。
- 新增/更新测试覆盖训练 manifest/payload schema、input channel 增量、sampler manifest 默认 zero source、显式 previous-scale condition source、CLI 参数和缺失 schema 的错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级上一尺度 RGB proxy 条件通道，用于把 cross-scale condition 推进到真实张量输入与 checkpoint 契约。
- 本次版本不实现 production cascade sampler、不实现跨倍率 latent encoder、不实现 ControlNet、不实现 attention/cross-attention 或 WSI consistency fine-tuning。
- 未提供 previous-scale condition 时，sampler 必须记录 zero/default source，避免把单层 smoke sampling 伪装成真实多倍率级联推理。

## v0.36.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1 的 `latent_diffusion_unet` 主干要求：把 PyTorch diffusion smoke denoiser 从简单卷积堆栈升级为带 downsample、bottleneck、upsample 和 skip connection 的 smoke U-Net。

### 结构化需求

- 版本号升级为 `v0.36.0`。
- `_MaskConditionedLatentDenoiser` 必须实现 smoke U-Net 结构，至少包含 encoder、downsample、bottleneck、upsample、skip connection、decoder/output blocks。
- Diffusion checkpoint payload 和 checkpoint manifest 必须记录 `denoiser_architecture`，包括 architecture 名称、base channels、bottleneck channels、downsample stages、skip connection 语义、输入来源和 production 状态。
- `sample_torch_diffusion_smoke_model` 必须校验 checkpoint manifest/payload 中的 denoiser architecture；缺失或不匹配时显式报错。
- U-Net smoke denoiser 必须同时兼容 `rgb_downsample_proxy` latent 和 `trainable_vae_smoke` latent 的不同 output channel 数。
- 新增/更新测试覆盖 payload/manifest 架构记录、state_dict 中的 U-Net block key、VAE latent 路径兼容和缺失 denoiser architecture 的错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 smoke 级 U-Net denoiser，用于把模型结构从普通卷积堆栈推进到可审计 U-Net 主干。
- 本次版本不实现 production-scale U-Net/ControlNet、不实现 attention blocks、多尺度 cross-scale encoder、EMA、classifier-free guidance 或 WSI consistency fine-tuning。
- Checkpoint 仍必须标记为不可生产推理，避免把 smoke U-Net 伪装成完整 WSI latent diffusion generator。

## v0.35.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 v0.34.0 VAE smoke checkpoint 与 diffusion smoke 的连接：让 diffusion smoke trainer/sampler 可以选择使用 `trainable_vae_smoke` latent，而不是只能使用 `rgb_downsample_proxy`。

### 结构化需求

- 版本号升级为 `v0.35.0`。
- `train_torch_diffusion_smoke_model` 新增可选 `vae_checkpoint_manifest_path` 参数；提供时必须加载并校验 VAE smoke checkpoint。
- CLI `train-torch-diffusion-smoke` 新增可选 `--vae-checkpoint-manifest` 参数。
- 使用 VAE checkpoint 时，diffusion trainer 必须通过 VAE encoder 的 `mu` 构造 latent batch，记录 `latent_source=trainable_vae_smoke`。
- 使用 VAE latent 时，diffusion checkpoint payload/manifest 的 `latent_batch_shape`、`input_channels`、`output_channels` 必须反映 VAE latent channel 数。
- Diffusion checkpoint manifest 和 payload 必须记录 `vae_checkpoint_manifest_path`，便于审计 latent 来源。
- `sample_torch_diffusion_smoke_model` 遇到 `latent_source=trainable_vae_smoke` 时必须加载 VAE checkpoint，通过 VAE decoder 将 sampled latent 解码为 RGB preview，并在 `sample_manifest.json` 记录 latent sample shape。
- 旧的 `rgb_downsample_proxy` 路径必须保持可用；未提供 VAE checkpoint 时不得伪装为 VAE latent。
- 新增/更新测试覆盖 VAE latent diffusion 直接训练、采样解码、CLI 训练参数和 manifest 字段。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只把 smoke VAE encoder/decoder 接入 smoke diffusion 训练与采样路径，用于验证 VAE latent 工程闭环。
- 本次版本不实现 production VAE、不实现完整 U-Net/ControlNet、不实现 perceptual/adversarial VAE loss、不实现 VAE-diffusion 联合训练或 WSI consistency fine-tuning。
- VAE 和 diffusion checkpoint 仍必须标记为不可生产推理，不能伪装为完整 WSI latent diffusion generator。

## v0.34.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.1/7.2 的 VAE latent 缺口：新增 PyTorch VAE smoke trainer，使项目不再只有 RGB downsample proxy latent，而是具备可训练、可审计的 latent autoencoder 工程入口。

### 结构化需求

- 版本号升级为 `v0.34.0`。
- 新增 `train_torch_vae_smoke_model`，输入为 training-index JSONL、输出目录、batch size、split、cascade level、epochs、learning rate、random seed、device、latent channels、latent size 和 KL loss weight。
- 新增 CLI `train-torch-vae-smoke`，用于从 training-index 执行一次可审计的 PyTorch VAE smoke training。
- Trainer 必须通过 `load_training_batch(..., include_image=True)` 读取真实 RGB image tile，不得只消费 mask 或伪造图像。
- VAE smoke trainer 必须包含 encoder、reparameterization 和 decoder，并真实执行 reconstruction loss + KL loss 的反向传播。
- `model.pt` payload 与 `checkpoint_manifest.json` 必须记录 `latent_source=trainable_vae_smoke`、`target_type=vae_rgb_reconstruction`、latent channels、latent size、latent batch shape、loss histories、KL weight、checkpoint hash 和 batch summary。
- Trainer 必须写出 `latent_preview.npy` 与 `reconstruction_preview.npy`，用于审计 latent shape 和重建输出。
- Checkpoint manifest 必须明确 `usable_for_inference=false`，说明该 VAE 是 smoke 级 latent autoencoder，不是 production VAE。
- 新增/更新测试覆盖直接函数调用、checkpoint payload、manifest 字段、preview 文件形状和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只新增 trainable VAE smoke autoencoder 入口，目的是把 latent diffusion 路线从 RGB proxy 迈向可训练 latent。
- 本次版本不把 diffusion smoke trainer 切换到 VAE latent，不实现 production VAE、perceptual loss、adversarial loss、EMA、large-scale dataset streaming 或 WSI consistency fine-tuning。
- 后续仍需把 VAE encoder/decoder 接入 diffusion trainer/sampler，并替换当前 `rgb_downsample_proxy` latent。

## v0.33.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 6.3 与 7.1 的条件注入路径：让 PyTorch diffusion smoke denoiser 不再只记录 `generation_condition_packet`，而是把条件包中的 style、texture、coordinate、source 和 structure anchor 摘要编码为空间条件通道参与训练/采样。

### 结构化需求

- 版本号升级为 `v0.33.0`。
- PyTorch diffusion smoke checkpoint 必须记录 condition feature schema，包含 feature 名称、数量、来源和训练期默认策略。
- `train_torch_diffusion_smoke_model` 必须在 denoiser 输入中加入条件特征通道；训练期可从 training-index/tile 元数据构建确定性默认条件，不得伪造 production prior。
- `sample_torch_diffusion_smoke_model` 在提供 condition packet 时必须把同一份条件摘要编码为 feature vector，并作为 spatial condition channels 拼接到 denoiser 输入。
- `sample_manifest.json` 必须记录 `condition_feature_schema` 和 `condition_feature_vector`；没有 condition packet 时必须记录明确的 zero/default condition feature vector，而不是静默缺省。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 必须通过 sampler 使用相同的 condition feature vector，并让 sampler manifest、metadata、generation run summary 保持可审计一致。
- Checkpoint payload 与 checkpoint manifest 的 `input_channels` 必须包含 RGB latent、6 类 mask、timestep 和 condition feature channels。
- Sampling 必须校验 checkpoint 的 condition feature schema；缺失或不匹配时显式报错，避免用旧结构 checkpoint 静默采样。
- 新增/更新测试覆盖训练 manifest、checkpoint payload、sampler manifest、直接 generation 和 CLI generation 中的 condition feature schema/vector。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本是 smoke 级条件通道注入，用于把条件包推进到模型输入张量路径。
- 本次版本不实现 production VAE latent、不实现完整 U-Net/ControlNet、多尺度 source encoder、trainable style encoder、texture codebook 或 WSI consistency fine-tuning。
- Checkpoint 仍必须标记为 `usable_for_inference=false` / `usable_for_production=false`，不得把 smoke 条件注入伪装成生产级 WSI diffusion generator。

## v0.32.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 condition packet 从 smoke-cascade 记录链路扩展到 PyTorch diffusion smoke sampling/generation：让 `sample-torch-diffusion-smoke` 和 `run-generation --backend torch-diffusion-smoke` 可以显式消费并记录同一个 `generation_condition_packet`。

### 结构化需求

- 版本号升级为 `v0.32.0`。
- `sample_torch_diffusion_smoke_model` 新增可选 `condition_packet_path` 参数，并在 `sample_manifest.json` 中记录 `condition_packet_path` 与 `condition_summary`。
- `run_torch_diffusion_smoke_generation` 新增可选 `condition_packet_path` 参数，并将该参数传给 PyTorch smoke sampler。
- CLI `sample-torch-diffusion-smoke` 新增可选 `--condition-packet` 参数。
- CLI `run-generation --backend torch-diffusion-smoke` 必须复用已有 `--condition-packet` 参数，并传给 PyTorch diffusion smoke generation。
- PyTorch diffusion smoke sampling/generation 必须读取并校验 condition packet JSON：schema version、condition packet type、必要条件对象必须存在。
- 在 generation backend 中，condition packet 的 `prior_id` 必须与当前 prior manifest 的 `prior_id` 一致；不一致时显式报错。
- Metadata 的 `generation` 字段、`generation_run.json` 和 sampler 的 `sample_manifest.json` 必须记录 condition packet 路径与同一份条件摘要。
- 当未提供 condition packet 时，保持现有 PyTorch diffusion smoke 行为，不静默伪造条件包。
- 新增/更新测试覆盖 sampler 直接调用、generation 直接调用、CLI 行为、metadata/run summary/sample manifest 记录和 prior id mismatch 错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只让 PyTorch diffusion smoke 链路消费并记录 condition packet，用于把条件包推进到更接近真实采样的工程路径。
- 本次版本不改变 diffusion smoke 模型结构，不实现生产级 layout/style/texture 条件注入，也不把 smoke checkpoint 标记为 production inference 权重。
- 后续仍需实现真正消费 layout/style/texture/source 条件的 latent diffusion U-Net、VAE latent、采样器和多倍率一致性训练。

## v0.31.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 v0.30.0 条件包与生成执行链路的连接：让 `run-generation --backend smoke-cascade` 可以显式消费 `generation_condition_packet`，并把条件包路径与关键条件摘要写入 metadata 和 generation run summary。

### 结构化需求

- 版本号升级为 `v0.31.0`。
- `run_smoke_generation` 新增可选 `condition_packet_path` 参数。
- CLI `run-generation` 新增可选 `--condition-packet` 参数，传给 smoke backend。
- Smoke generation 必须读取并校验 condition packet JSON：schema version、condition packet type、prior id、必要条件对象和 prior manifest 关系必须一致。
- 条件包 prior id 与当前 prior manifest 的 `prior_id` 不一致时必须显式报错。
- Metadata 的 `generation` 字段必须记录 `condition_packet_path` 和 `condition_summary`，摘要至少包含 cascade level、tile origin、style seed value/source、texture cluster id、source condition enabled 和 structure anchor。
- `generation_run.json` 必须记录同样的 condition packet 路径和摘要，便于批量任务审计。
- 当未提供 condition packet 时，保持现有 smoke backend 行为，不静默伪造条件包。
- 新增/更新测试覆盖直接函数调用消费 condition packet、CLI `--condition-packet` 行为、metadata/run summary 记录和 prior id mismatch 错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只让 smoke generation 执行链路消费并记录已存在的 condition packet，用于打通条件包到生成记录的审计链路。
- 本次版本不实现 production latent diffusion 条件注入，不让 PyTorch diffusion smoke sampler 真实使用 layout/style/texture 条件，也不改变 smoke backend 的非生产性质。
- 后续仍需让 PyTorch/production backend 基于条件包执行真实条件采样，并逐步实现 VAE latent、U-Net sampler、多倍率一致性和 WSI consistency fine-tuning。

## v0.30.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 6.3 的 prior 与生成模型连接：把 `prior_manifest.json` 和 generation config 解析为可审计的 generation condition packet，使 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 不再只停留在 generation plan 的字符串列表中。

### 结构化需求

- 版本号升级为 `v0.30.0`。
- 新增 `build_generation_condition_packet`，输入为 generation config、prior manifest、输出路径、cascade level 和 40x tile 坐标。
- Builder 必须复用 `validate_generation_config` 和 `load_prior_manifest`，不得绕过既有 schema、artifact hash 和文件存在校验。
- Builder 必须读取四类 artifact JSON，并校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type` 和 `qc_reference_distribution` 的 `source`。
- 输出 JSON 必须包含 schema version、condition packet type、created time、prior id、prior manifest path、generation config summary 和完整条件对象。
- 条件对象必须显式包含 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor`。
- `style_seed=auto` 时必须采用可复现的 deterministic 解析规则并记录来源；整数 style seed 必须原样记录。
- `texture_token` 必须从 `texture_prior.texture_prototypes` 中按 random seed 做确定性选择，记录 cluster id、selection policy 和 representative embedding index。
- `coord` 必须记录 cascade level、40x tile origin、tile size 和 max magnification，并拒绝非法 cascade level 或负坐标。
- `source_condition` 必须明确记录是否启用；source-anchored generation 继续依赖 generation config 校验要求 `source_wsi_id`。
- CLI 新增 `build-condition-packet`，支持 generation config、`--prior-manifest`、`--output`、`--cascade-level`、`--tile-origin-x` 和 `--tile-origin-y`。
- 缺失 artifact、artifact 非 JSON、artifact 类型不匹配、缺失 texture prototypes、非法坐标、source-anchored 缺 source 等错误必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、condition packet 字段、auto style seed 解析、texture token 选择和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现可审计的条件包 JSON，用于把 prior artifact 与后续训练/生成接口连接起来。
- 本次版本不实现 production latent diffusion 条件注入、可采样 layout generator、style latent encoder、真实 texture sampler、source image encoder 或 WSI consistency fine-tuning。
- 后续仍需让 PyTorch/production 生成 backend 消费该条件包，并逐步替换当前 smoke/proxy 生成链路。

## v0.29.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 prior artifact 汇总能力：把已经可独立生成的 `layout_mask_prior`、`style_prior`、`texture_prior` 和 `qc_reference_distribution` JSON 组装为统一、可校验、可复现的 `prior_manifest.json`，减少后续 generation/training 入口对手工 manifest 编写的依赖。

### 结构化需求

- 版本号升级为 `v0.29.0`。
- 新增 `build_prior_manifest_from_artifacts`，输入为输出目录、prior id、dataset id、输入 manifest 路径、训练数据版本、WSI id 列表、随机种子和四类 prior artifact 路径。
- Builder 必须复用既有 `create_prior_artifact_entry`、`save_prior_manifest` 和 `load_prior_manifest`/校验契约，写出 `prior_manifest.json`。
- Builder 必须读取 artifact JSON，校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type` 与 artifact 类型一致，并校验 `qc_reference_distribution` 来源为 QC reference distribution。
- 输出 manifest 必须记录 schema version、prior id、created_at、random seed、input data、WSI ids、四类 artifact 的 path/kind/sha256/size_bytes/metadata。
- Artifact metadata 必须记录 artifact type、artifact schema version，以及能从源 JSON 中直接审计的关键摘要字段。
- CLI 新增 `build-prior-manifest`，支持 `--output-dir`、`--prior-id`、`--dataset-id`、`--input-manifest`、`--training-data-version`、可重复 `--wsi-id`、`--random-seed` 和四类 artifact 路径参数。
- 缺失 artifact、artifact 非 JSON、artifact 类型不匹配、缺失 WSI id、非法 random seed、重复 artifact 路径或 hash/size 不一致必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、manifest roundtrip 校验、artifact metadata 摘要和 artifact 类型不匹配错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现 prior artifact manifest 汇总与校验，不实现 layout/style/texture 的采样策略。
- 本次版本不把统计 prior 接入 production latent diffusion 条件注入，也不实现 trainable prior model、source-anchor layout mixing 或 tile-level texture sampler。
- 后续仍需把 `prior_manifest.json` 接入更完整的训练/生成工作流，并逐步实现可采样 layout、style seed sampler、texture condition selector 和 production inference backend。

## v0.28.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 `texture_prior` 落地：从 embedding cache 和 cluster report 中读取真实 patch embedding 与聚类标签，估计可追溯的 cluster-level texture prototype 统计，输出可作为 prior manifest `texture_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.28.0`。
- 新增 `build_texture_prior_from_embedding_cache`，输入为 embedding cache 目录、cache key、cluster report JSON、输出路径。
- Texture prior builder 必须通过 `load_embedding_cache` 读取真实 embedding array 和 metadata，不得静默构造假 embedding。
- Builder 必须校验 cluster report 的 `labels` 数量与 embedding row count 一致，`embedding_dim` 与 embedding metadata/array 一致，cluster count 与 labels 一致。
- 输出 JSON 必须包含 schema version、prior type、created time、source cache dir/cache key、embedding metadata、cluster report summary、embedding count、embedding dim、cluster count 和 texture prototype records。
- 每个 texture prototype record 必须记录 cluster id、sample count、fraction、mean embedding、embedding std 和 representative embedding index。
- 输出 JSON 必须记录 global embedding mean/std，用于后续 texture/morphology prior 条件和 non-copy/global similarity 报告复用。
- CLI 新增 `build-texture-prior`，支持 `--cache-dir`、`--cache-key`、`--cluster-report` 和 `--output`。
- 缺失 cache、cluster report 非 JSON、labels 数量不匹配、embedding dim 不匹配、非法 cluster count、非有限 embedding 等错误必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、prototype 统计、global embedding 统计、metadata 记录和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于 embedding/cluster 的统计型 `texture_prior` JSON，作为 texture/morphology prior 的可审计工程基础。
- 本次版本不实现 trainable texture codebook、VQ-VAE、morphology token sampler、区域特异纹理生成器或 production diffusion 条件注入。
- 后续仍需把该 texture prior 接入真实图像生成训练、mask 区域条件、tile-level texture conditioning 和 non-copy/global similarity QC。

## v0.27.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4 的 `layout_mask_prior` 落地：从 training-index 中真实读取 6 类 mask tile，估计可追溯的全局类别比例、tile 级 layout 分布和相邻类别计数，输出可作为 prior manifest `layout_mask_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.27.0`。
- 新增 `build_layout_mask_prior_from_training_index`，输入为 training-index JSONL、输出路径、batch size、split 和 cascade level。
- Layout/mask prior builder 必须通过 `load_training_batch(..., include_image=False)` 读取真实 mask tile，不得依赖图像 tile 或构造假 mask。
- 输出 JSON 必须包含 schema version、prior type、created time、source training-index、batch size、split、cascade level、sample ids、WSI ids、tile records、mask batch shape 和 mask class ids。
- 输出 JSON 必须记录项目 6 类名称、每类 pixel count、fraction、present flag、non-background tissue fraction 和 tile-level dominant class。
- 输出 JSON 必须记录 tile-level class fractions 和 source WSI id，用于审计 layout/mask prior 是否来自真实训练 mask tile。
- 输出 JSON 必须记录横向/纵向相邻类别 pair counts，作为后续 layout/mask prior 学习邻接关系的统计基础。
- CLI 新增 `build-layout-mask-prior`，支持 `--batch-size`、`--split`、`--cascade-level` 和 `--output`。
- 缺失 mask、非法 batch size、空匹配样本、未知 split/level、mask 维度非法或 label mapping 不完整等错误必须沿用 training batch loader 的显式错误路径，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、统计字段、tile-level layout records、adjacency counts、summary 不写入完整 mask batch，以及错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于真实 mask tile 的统计型 `layout_mask_prior` JSON，作为 de novo layout/mask prior 的可审计工程基础。
- 本次版本不实现可采样 layout generator、mask diffusion、VQ-VAE、空间生成模型、跨 WSI 结构扰动或 source-anchor layout mixing。
- 后续仍需把该 layout/mask prior 接入真实 layout 采样、生成条件构造和 production inference backend。

## v0.26.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M4/M5 之间的 `global_imaging_style_prior` 落地：从 training-index 中真实读取 RGB tile，估计可追溯的 slide/tile 级成像风格统计，并输出可作为 prior manifest `style_prior` artifact 使用的 JSON。

### 结构化需求

- 版本号升级为 `v0.26.0`。
- 新增 `build_style_prior_from_training_index`，输入为 training-index JSONL、输出路径、batch size、split 和 cascade level。
- Style prior builder 必须通过 `load_training_batch(..., include_image=True)` 读取真实 RGB image tile，不得只依赖 mask 或静默构造假图像。
- 输出 JSON 必须包含 schema version、prior type、created time、source training-index、batch size、split、cascade level、wsi ids、sample ids、tile records、image batch shape/dtype 和 RGB 统计。
- RGB 统计至少包含 per-channel mean、standard deviation、min、max，以及归一化到 `[0, 1]` 的 mean/std，供后续 generation style seed 与 QC 阈值复用。
- 输出 JSON 必须包含每个样本的 tile-level mean RGB 和 source WSI id，用于审计 global style prior 是否来自真实训练 tile。
- CLI 新增 `build-style-prior`，支持 `--batch-size`、`--split`、`--cascade-level` 和 `--output`。
- 缺失 WSI、无法读取 RGB tile、非法 batch size、空匹配样本、未知 split/level 等错误必须沿用 training batch loader 的显式错误路径，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、统计字段、tile-level style records、summary 不写入完整 image batch，以及错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现基于真实 RGB tile 的统计型 `style_prior` JSON，作为 `global_imaging_style_prior` 的可审计工程基础。
- 本次版本不实现 trainable style encoder、VAE style latent、stain normalization、style sampling policy、风格迁移模型或 production diffusion 条件注入。
- 后续仍需把该 style prior 接入真实 generation backend 的 style conditioning、同 WSI 风格一致性训练和更完整 QC reference 统计。

## v0.25.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进完整生成输出链路：在已有 PyTorch diffusion smoke sampler 基础上，新增 `torch-diffusion-smoke` generation backend，使 PyTorch sampler 输出能够进入 OME-TIFF、mask、metadata、QC 和 batch index 归档链路。

### 结构化需求

- 版本号升级为 `v0.25.0`。
- 新增 `run_torch_diffusion_smoke_generation`，输入为 generation config、prior manifest、diffusion smoke checkpoint manifest、training-index、输出目录、generated id 和 batch size。
- CLI `run-generation` 新增 backend 选择 `torch-diffusion-smoke`。
- `torch-diffusion-smoke` backend 必须要求 `--training-index`，用于提供 mask 条件；缺失时必须显式报错。
- Backend 必须调用 `sample_torch_diffusion_smoke_model`，复用 diffusion smoke checkpoint 和 generation config 中的 `sample_steps` / `random_seed`。
- Backend 必须从 sampler 输出的 `sample_preview.npy` 构造四层小型 pyramid：`1/1`、`1/4`、`1/16`、`1/32`。
- Backend 必须从 training-index batch 读取 mask，并写出与 `1/1` 输出尺寸一致的 `.npy` mask。
- Backend 必须复用现有 `write_pyramid_ome_tiff`、`write_mask_array`、`build_qc_report` 和 `archive_sample`，写出 OME-TIFF、mask、metadata、QC、batch index 和 generation run summary。
- Metadata 必须记录 `generation_backend=torch-diffusion-smoke`、checkpoint、prior、cascade、sample steps 和输出路径。
- QC non-copy report 必须记录该 backend 是 PyTorch diffusion smoke backend，不是 production WSI diffusion generator。
- Backend 不得把 diffusion smoke checkpoint 改成 `usable_for_inference=true`，不得伪装为 production inference。
- 新增/更新测试覆盖直接函数调用和 CLI 行为，验证 metadata、QC、batch index、sample manifest、OME-TIFF pyramid shape 和 backend 标记。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只把 PyTorch diffusion smoke sampler 接入完整输出归档链路，输出仍来自下采样 RGB proxy preview resize。
- 本次版本不实现真实 VAE decode、production sampler、multi-resolution cascade diffusion inference、tile stitching、gigapixel chunked OME-TIFF 或 WSI consistency fine-tuning。
- 后续仍需把真实模型主干、VAE latent、采样器和跨倍率条件接入 `run-generation` 的 production backend。

## v0.24.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进推理/采样链路：在已有 DDPM-style diffusion smoke trainer 基础上，新增一个可审计的 PyTorch diffusion smoke sampler，用于验证 checkpoint 加载、mask 条件输入、反向 DDPM-style 采样和 preview 输出链路。

### 结构化需求

- 版本号升级为 `v0.24.0`。
- 新增 `sample_torch_diffusion_smoke_model`，输入为 diffusion smoke checkpoint manifest、training-index JSONL、输出目录、batch size、split、cascade level、sample steps、random seed 和 device。
- 新增 CLI `sample-torch-diffusion-smoke`，用于从 diffusion smoke checkpoint 和 training-index mask 条件执行一次可审计 proxy latent sampling。
- Sampler 必须只接受 `training_backend=torch-smoke-mask-conditioned-latent-diffusion` 且 `target_type=diffusion_noise` 的 diffusion smoke checkpoint；其它 checkpoint 必须显式报错。
- Sampler 必须读取 checkpoint payload、恢复 denoiser `state_dict`、复用 manifest/payload 中的 `linear_ddpm` schedule 与 `rgb_downsample_proxy` latent shape。
- Sampler 必须通过 `load_training_batch(..., include_image=False)` 读取 mask 条件，不得要求 RGB target，也不得静默忽略 mask。
- 采样输入必须包含当前 latent、下采样 6 类 mask 条件和 timestep channel；采样过程必须执行反向 DDPM-style 更新。
- 输出必须包含 `sample_preview.npy` 和 `sample_manifest.json`。
- `sample_manifest.json` 必须记录 sampling backend、checkpoint manifest/path、checkpoint training backend、training-index、sample path、sample shape、dtype、sample steps、random seed、diffusion schedule、batch summary，并明确 `usable_for_production=false`。
- Sample manifest 的 batch summary 不得写入完整 `mask_batch` 数组。
- 非法 sample steps、sample steps 超过 diffusion timesteps、checkpoint 缺失/不匹配、state_dict 缺失、diffusion schedule 非法、缺失 mask 或 PyTorch/numpy 缺失时必须显式报错。
- 新增/更新测试覆盖直接函数调用、CLI 行为、preview `.npy` shape/dtype、sample manifest 字段、checkpoint backend 校验和 non-production 标记。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证 reverse DDPM-style mechanics 和 mask-conditioned sampling 工程链路，输出是下采样 RGB proxy latent preview。
- 本次版本不把 diffusion smoke checkpoint 改为 `usable_for_inference=true`，不接入 `run-generation`，不输出 OME-TIFF，不实现 production latent diffusion sampler 或 VAE decoder。
- 后续仍需实现可生产的模型主干、VAE latent、真实 sampler、multi-resolution cascade inference、tile stitching、OME-TIFF 写出和 QC/metadata 归档。

## v0.23.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 M5 中的 latent diffusion 训练目标：在已有 RGB training batch 与 PyTorch smoke training 基础上，新增一个真实执行 DDPM-style 加噪和噪声预测 loss 的 mask-conditioned latent diffusion smoke trainer。

### 结构化需求

- 版本号升级为 `v0.23.0`。
- 新增 `train_torch_diffusion_smoke_model`，输入为 training-index JSONL、输出目录、batch size、split、cascade level、epochs、learning rate、random seed、device、diffusion timesteps、beta schedule 和 latent size。
- 新增 CLI `train-torch-diffusion-smoke`，用于从 training-index 执行一次可审计的 PyTorch diffusion smoke training。
- Trainer 必须通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch，不得回退到只读 mask。
- 训练必须构造下采样 RGB proxy latent，记录 `latent_source=rgb_downsample_proxy`，避免伪装成 VAE latent。
- 训练必须实现线性 DDPM smoke schedule，记录 `scheduler=linear_ddpm`、`timesteps`、`beta_start`、`beta_end` 和 `latent_batch_shape`。
- 训练输入必须包含 noisy RGB proxy latent、下采样 6 类 mask 条件和 timestep channel；训练目标必须为加入的噪声，loss 名称为 `mse_noise_prediction`。
- Trainer 必须继续真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 checkpoint 写出。
- `model.pt` payload 必须记录 `target_type=diffusion_noise`、`input_channels=10`、`output_channels=3`、diffusion schedule、mask classes、cascade level、random seed 和 loss history。
- `checkpoint_manifest.json` 必须记录 target type、输入/输出通道、diffusion schedule、training parameters、image batch summary、loss summary、torch version、checkpoint hash，并保持 `usable_for_inference=false`。
- Manifest 的 batch summary 必须包含 `image_batch_shape` 和 `image_dtype`，不得写入完整 `image_batch` 或 `mask_batch` 数组。
- 非法 diffusion timesteps、latent size、beta schedule、缺失 WSI、图像不可读、tile 越界或 PyTorch 缺失时必须显式报错，不得静默回退。
- 新增/更新测试覆盖直接函数调用、CLI 行为、backend 名称、diffusion target、scheduler、latent shape、checkpoint payload、image batch summary 和 finite loss。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证真实 DDPM-style noise prediction 训练机制进入工程链路；latent 是下采样 RGB proxy，不是训练好的 VAE latent。
- 本次版本不实现完整 latent diffusion U-Net、VAE encoder/decoder、生产级噪声调度和采样器、多倍率 cross-scale condition、style latent、source anchor 条件、WSI 一致性微调或真实 inference backend。
- 本次 diffusion smoke checkpoint 仍不可用于 `run-generation` 的真实 diffusion inference；后续仍需实现 production dataset、模型主干、采样器、VAE latent 与生成执行 backend。

## v0.22.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 PyTorch 训练链路：把 `train-torch-smoke` 从只训练 mask autoencoder，升级为消费 RGB image tile 的 mask-conditioned RGB reconstruction smoke backend，使训练 loop 开始学习 mask 条件到 H&E 图像像素的映射。

### 结构化需求

- 版本号升级为 `v0.22.0`。
- `train_torch_smoke_model` 必须通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch。
- 训练输入必须为 6 类 mask one-hot tensor，训练目标必须为归一化到 `[0, 1]` 的 RGB image tile tensor。
- Smoke backend 名称升级为 `torch-smoke-mask-conditioned-rgb-reconstructor`，避免继续把产物描述为 mask autoencoder。
- Trainer 必须继续真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 checkpoint 写出；loss 使用明确的 RGB reconstruction MSE。
- `model.pt` payload 必须记录 `target_type=rgb_image`、`input_channels=6`、`output_channels=3`、`image_dtype`、mask classes、cascade level、random seed 和 loss history。
- `checkpoint_manifest.json` 必须记录 target type、输入/输出通道、loss 名称、image batch summary、torch version、training parameters、loss summary、checkpoint hash，并保持 `usable_for_inference=false`。
- Manifest 的 batch summary 必须包含 `image_batch_shape` 和 `image_dtype`，不得写入完整 `image_batch` 或 `mask_batch` 数组。
- CLI `train-torch-smoke` 继续使用原命令入口，但输出 manifest/backend 语义必须反映 RGB reconstruction smoke training。
- 缺失 WSI、图像不可读、tile 越界等 image batch 读取失败必须通过既有显式错误路径暴露，不得静默回退到只训练 mask。
- 新增/更新测试覆盖真实 fixture RGB slide 参与训练、backend 名称、target type、输入/输出通道、image batch summary、checkpoint payload 和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现最小可审计的 RGB reconstruction smoke training，用于验证图像目标进入 PyTorch 训练链路。
- 本次版本不实现完整 latent diffusion U-Net、VAE latent 编码、噪声调度、扩散去噪目标、多倍率条件注入、style latent、source anchor 训练、WSI 一致性微调或真实可推理生成权重。
- 本次 smoke checkpoint 仍不可用于 `run-generation` 的真实 diffusion inference；后续仍需实现 production dataset、latent diffusion loss、sampler 和推理 backend。

## v0.21.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实图像训练输入能力：在 training batch loader 中新增可选 RGB image tile 读取，使后续 PyTorch 图像生成训练不再只有 mask 条件输入。

### 结构化需求

- 版本号升级为 `v0.21.0`。
- `load_training_batch` 新增 `include_image` 参数；默认保持只读 mask，显式启用时读取 WSI/fixture 图像 tile。
- 图像 tile 读取必须使用 training-index 中的 `wsi_path`、tile 坐标和 source backend。
- 对 `fixture-image` backend，读取 PNG/TIFF 等小图并裁剪 RGB tile；对 `openslide` backend，使用 OpenSlide `read_region` 读取 level0 tile 并转为 RGB。
- Loader 输出新增 `image_batch`、`image_batch_shape` 和 `image_dtype`；summary 必须排除完整 `image_batch` 数组，只保留形状和 dtype。
- 缺失 WSI 文件、图像不可读、tile 超出图像范围、未知 backend 或 OpenSlide 缺依赖时必须显式报错。
- CLI `inspect-training-batch` 新增 `--include-image` 参数，用于训练前同时审计 mask 和 RGB tile 输入。
- 新增测试覆盖 fixture image tile 读取、summary 不写完整 image batch、缺失 WSI 报错和 CLI `--include-image` 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只读取训练输入 RGB tile，不实现真实 VAE latent 编码、归一化策略搜索、颜色增强、stain normalization 或 OpenSlide 多层降采样采样策略。
- 后续 PyTorch trainer 仍需把 image batch 接入真实图像重建/扩散损失；本次只让输入数据链路具备图像 tile。

## v0.20.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实 PyTorch 训练 backend：在既有 training-index batch loader 基础上，新增一个真实调用 PyTorch 的 smoke training backend，用于验证训练 loop、loss、optimizer、checkpoint 写出和 manifest 记录链路。

### 结构化需求

- 版本号升级为 `v0.20.0`。
- 新增 PyTorch smoke trainer，输入为 training-index JSONL、输出目录、batch size、epochs、learning rate、split 和 cascade level。
- Trainer 必须显式要求 PyTorch；未安装 torch 时必须清晰报错，不得静默回退到 numpy。
- Trainer 必须复用 `load_training_batch` 读取 batch，将 mask batch 转为 torch tensor，并执行真实 `torch.nn.Module`、loss、optimizer 和反向传播。
- Trainer 必须写出 `model.pt`、`training_log.jsonl` 和 `checkpoint_manifest.json`。
- Checkpoint manifest 必须包含 schema version、model family、status、usable_for_inference、model version、training backend、torch version、训练参数、loss summary、checkpoint path/hash 和明确边界说明。
- Smoke trainer 产物不得伪装成真实 latent diffusion 推理权重；`usable_for_inference` 必须为 `false`。
- 新增 CLI `train-torch-smoke`，用于从 training-index 执行一次可审计 PyTorch smoke training。
- 新增测试覆盖 PyTorch smoke trainer 产物、manifest 可校验、CLI 行为；在无 torch 环境中测试应跳过真实 torch 用例。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只验证真实 PyTorch 训练 loop、loss、optimizer 和 checkpoint 写出，不实现完整 latent diffusion U-Net、噪声调度、VAE latent、图像重建、WSI 一致性训练或真实可推理生成权重。
- 本次 smoke checkpoint 不可用于 `run-generation` 的真实推理；后续仍需实现 production PyTorch dataset、真实图像/latent 输入、扩散损失、采样器和 inference backend。

## v0.19.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实 PyTorch 训练 backend 的前置输入能力：新增 training-index batch loader，使后续训练 loop 可以从 JSONL 样本索引读取、校验、抽样并形成可审计 batch，而不是只停留在索引文件。

### 结构化需求

- 版本号升级为 `v0.19.0`。
- 新增 training batch loader，输入为 training-index JSONL 路径、batch size 和可选 split/cascade level。
- Loader 必须逐行解析 JSONL，显式拒绝空文件、非法 JSON、缺失字段、非法 batch size、未知 split、未知 cascade level、mask 文件缺失、mask 维度非法和 tile 超出 mask 范围。
- Loader 必须读取 `.npy` mask，按 training-index 中的 tile 坐标裁剪 batch mask，并将原始 mask 编号按 label mapping 转为项目 6 类 id。
- Loader 输出必须包含 schema version、batch size、sample ids、cascade levels、WSI ids、tile records、mask batch shape、mask class ids、conditioning 摘要和 source records。
- 新增 CLI `inspect-training-batch`，用于从 training-index 读取一个 batch 并输出 batch summary JSON，供训练前审计和后续 UI 调用。
- 新增测试覆盖 batch summary 写出、split/level 过滤、缺失 mask 报错和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现训练输入 batch loader 和审计 summary，不实现 PyTorch Dataset/DataLoader、GPU tensor 转换、latent diffusion 训练 loop、loss 计算或 checkpoint 权重更新。
- 由于当前环境未安装 PyTorch，本轮不得伪装真实 PyTorch backend 已完成；后续需在隔离环境中安装并验证 torch 后继续实现真实模型训练。

## v0.18.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 PySide6 本地控制台所需的长任务调度基础：新增可持久化本地 job runner，使 CLI/core 工作流能被排队、同步执行、记录 stdout/stderr、保存状态和结果，供 UI 后续调用。

### 结构化需求

- 版本号升级为 `v0.18.0`。
- 新增本地 job runner，支持创建 job、状态持久化、执行命令、记录 stdout/stderr、保存 return code 和时间戳。
- Job 状态必须使用既有 UI 状态集合：`queued`、`running`、`completed`、`failed`、`cancelled`。
- 空 job id、空命令、重复 job id、未知 job id 和非法状态必须显式报错。
- 执行成功时状态为 `completed`，命令返回非零或启动失败时状态为 `failed`，不得静默吞掉失败或留下 stale `running` 状态。
- 新增 CLI `run-local-job`，用于创建并同步执行一个本地命令 job，输出 job record 路径和最终状态。
- 新增测试覆盖成功 job、非零退出 job、命令启动失败、重复 job 拒绝和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只实现同步本地 job runner，不实现后台 daemon、进程取消、并发队列、跨机器调度或 PySide6 事件循环集成。
- 后续 UI 可通过该 job runner 触发已有 CLI/core 命令，但本次不实现完整图形界面按钮绑定。

## v0.17.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 `qc_reference_distribution` 的自动生成能力：从一组训练/参考 QC JSON 抽取数值 metrics，估计区间阈值并输出可作为 prior artifact 使用的 reference distribution JSON。

### 结构化需求

- 版本号升级为 `v0.17.0`。
- 新增 QC reference builder，输入为多个 QC report、metric 名称列表、输出 JSON 路径和最小样本数。
- Builder 必须复用现有 QC schema 校验，显式拒绝空输入、空 metric 列表、非法 min samples、缺失 metric 和样本数不足。
- 输出 JSON 必须包含 schema version、创建时间、来源、总样本数和 `metrics` 对象。
- 每个 metric 必须记录 `warning_min`、`warning_max`、`fail_min`、`fail_max`、`sample_count`、observed min/max 和 estimator 名称。
- 新增 CLI `build-qc-reference`，支持多个 QC JSON 输入、可重复 `--metric`、`--min-samples` 和 `--output`。
- 新增测试覆盖 reference distribution 写出、缺失 metric 报错和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本使用 observed min/max 与 range margin 的确定性估计器，不实现 IQR、稳健 z-score、分层组织/疾病阈值或自动异常样本剔除。
- 输入 QC report 的可信度仍由用户或训练数据准备流程保证；builder 不判断 QC report 是否来自真实训练集。
- 后续仍需把该 builder 接入完整 prior learning workflow，并从真实 WSI 训练集批量生成 QC metrics。

## v0.16.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进自动 QC 的训练分布自适应阈值能力：让 QC engine 使用 prior artifact 中的 `qc_reference_distribution` 对已计算指标进行 warning/fail 判定，而不是只使用固定规则。

### 结构化需求

- 版本号升级为 `v0.16.0`。
- QC engine 新增可选 `qc_reference_distribution` 输入，格式为 `{"metrics": {"metric_name": {"warning_min": number, "warning_max": number, "fail_min": number, "fail_max": number}}}`。
- 对支持的数值指标，QC 应优先使用 reference distribution 阈值：低于 `fail_min` 或高于 `fail_max` 为 `fail`，低于 `warning_min` 或高于 `warning_max` 为 `warning`，否则为 `pass`。
- 被 reference distribution 判定的 metric 必须记录 reference threshold 信息，便于用户解释 warning/fail 来源。
- reference distribution 格式非法、阈值非数值或边界顺序不合法时必须显式报错。
- `run-generation` 应从 prior manifest 的 `qc_reference_distribution` artifact 自动加载 JSON 并传入 QC engine。
- 新增测试覆盖 reference 阈值 warning/fail、非法阈值报错、端到端生成使用 prior reference。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本只支持 JSON reference distribution 和简单区间阈值，不实现 IQR、稳健 z-score 或分层组织/疾病阈值。
- 本次版本不做训练分布估计，只消费已经存在的 `qc_reference_distribution` artifact。
- 后续仍需实现从真实训练集统计生成 reference distribution 的 prior learner。

## v0.15.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进自动 QC 的真实指标能力：从只检查文件存在，扩展为读取生成 OME-TIFF 和 mask，输出 WSI/tile/mask-region 三级可解释指标，为后续真实生成样本筛选建立基础。

### 结构化需求

- 版本号升级为 `v0.15.0`。
- QC engine 必须读取 OME-TIFF pyramid 首层，记录可读性、实际 level count、RGB 均值和动态范围。
- QC engine 必须计算轻量 tile 质量指标，至少包含清晰度 proxy 和 tile proxy 样本数。
- QC engine 必须读取 `.npy` mask，记录 mask 可读性、出现类别数量、类别 id 列表、组织占比和 mask 与 WSI 首层尺寸是否一致。
- OME-TIFF 不可读、mask 不可读、mask 维度非法或 mask 与 WSI 尺寸不一致时，QC 必须显式 fail。
- 对低动态范围、空组织比例等非硬错误场景可给 warning，不静默通过。
- 新增测试覆盖真实 OME-TIFF/mask 指标写入和 mask-WSI 尺寸错位 fail。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本仍不实现训练分布自适应阈值，只提供确定性 smoke/规则指标。
- 本次版本不做真实病理质量判定，不替代专家评价或下游验证。
- 后续仍需接入 prior 中的 `qc_reference_distribution`，并补充颜色离群、seam、style consistency、mask 区域比例等训练分布阈值。

## v0.14.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进真实训练 backend 的前置能力：把输入 manifest、manifest audit 和 label mapping 转成四层 cascade training-index JSONL，使后续 PyTorch latent diffusion 训练 loop 有可审计的训练样本输入，而不是只引用一个未定义路径。

### 结构化需求

- 版本号升级为 `v0.14.0`。
- 新增 training index builder，输入为 input manifest、manifest audit、一个或多个 label mapping、输出 JSONL 路径。
- Training index builder 必须复用现有 schema 校验，拒绝非法 manifest、非法 label mapping、缺失 audit record、audit status 非 `ok`、缺失可训练 mask annotation、缺失匹配 label mapping、mask 文件不存在和无法切出完整 40x tile 的输入。
- 每条 JSONL 记录必须包含 dataset、WSI、split、cancer type、cascade level、40x tile 坐标、source metadata、mask annotation、6 类 label mapping 和 conditioning 约定。
- 对每个可训练 40x tile 写出 `1/32`、`1/16`、`1/4`、`1/1` 四层记录，保持与生成模型级联训练顺序一致。
- 新增 CLI `build-training-index`，支持 `--audit`、可重复 `--label-mapping` 和 `--output`。
- 新增测试覆盖 training index 写出、缺失 label mapping 拒绝和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本不执行真实 PyTorch 训练，也不产生可推理模型权重。
- Training index 仅建立可审计训练样本输入；后续仍需实现真实 dataset loader、latent diffusion U-Net、训练 loop、checkpoint 权重保存和真实推理 backend。
- 当前 tile 采样采用非重叠完整 512x512 40x tile；不处理 partial tile、组织区域过滤、hard negative 采样或 class-balanced sampler，以避免在无真实训练数据时过度设计。

## v0.13.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进完整核心系统中的“可运行生成任务”缺口：在现有 M1-M7 契约、prior、checkpoint、OME-TIFF、mask、metadata、QC 和 batch index 基础上，新增一个明确标记的端到端 smoke generation backend，用于验证生成任务可以产出完整 WSI 数据对象。

### 结构化需求

- 版本号升级为 `v0.13.0`。
- 新增 generation executor，接收 generation config、prior manifest、trained checkpoint manifest、output root 和 generated id。
- Executor 必须复用现有 generation plan 校验，拒绝未训练 checkpoint、缺失 prior artifact 或非法 generation config。
- 新增 `smoke-cascade` backend，按 `1/32 -> 1/16 -> 1/4 -> 1/1` 生成可审计的四层小型 cascade 输出，并写出 OME-TIFF pyramid。
- 生成输出必须包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`batch.jsonl` 和 generation run summary。
- Metadata 必须记录 backend 为 `smoke-cascade`，避免把 smoke backend 伪装为真实 PyTorch diffusion 生成。
- 新增 CLI `run-generation`，要求显式选择 `--backend smoke-cascade`，并写出完整生成样本目录。
- 新增测试覆盖端到端生成输出、未训练 checkpoint 拒绝和 CLI 生成行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject、默认配置和版本断言。

### 边界说明

- 本次版本不实现真实 PyTorch latent diffusion 训练或推理；`smoke-cascade` 只用于端到端工程链路验证。
- 本次版本不声称生成图像具有病理真实性，不替代真实模型 checkpoint。
- 后续仍需实现真实训练 backend、真实推理 backend、训练分布自适应 QC 指标和生产级 gigapixel 写出，才能满足完整 H&E WSI 生成器完成标准。

## v0.12.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M7：PySide6 本地单页控制台，为数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出查看建立 UI 配置与控制层。

### 结构化需求

- 版本号升级为 `v0.12.0`。
- 新增 UI 配置对象，覆盖数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出区域。
- 新增 UI job config 保存/读取能力，确保 UI 产生的配置可被 CLI/core 复现。
- 新增任务状态管理，支持 `queued`、`running`、`completed`、`failed`、`cancelled`，非法状态需显式报错。
- 新增输出摘要读取能力，从 metadata/QC JSON 中提取 generated id、QC 状态和核心输出路径。
- 新增 PySide6 单页控制台模块；若 PySide6 未安装，启动 UI 时必须明确报错。
- 新增 CLI `write-ui-config` 和 `launch-ui`。
- 新增测试覆盖 UI config roundtrip、任务状态转换、输出摘要、CLI config 写出和 PySide6 缺依赖错误。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不执行真实长任务调度、不在 UI 内训练模型或生成图像；UI 只负责配置、状态和输出查看控制层。
- Core 逻辑仍保留在 `he_wsi_generator` 包内，UI 不应绕过 CLI/core 直接实现业务处理。
- 当前环境未安装 PySide6 时，`launch-ui` 应失败并给出可操作错误，而不是静默跳过。

## v0.11.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M6：OME-TIFF 与 QC，建立小尺寸 pyramid 写出、QC JSON 和 batch JSONL 归档基础。

### 结构化需求

- 版本号升级为 `v0.11.0`。
- 新增 pyramid OME-TIFF smoke writer，使用 `tifffile` 写出多层 pyramid TIFF，并验证层级尺寸。
- 新增 mask 输出基础能力，支持写出 6 类 mask `.npy` 文件与 metadata。
- 新增 QC report builder，输出 WSI/tile/mask-region 三级状态、metrics 和轻量 non-copy report。
- 新增 per-WSI metadata writer，metadata 必须能通过既有 schema 校验。
- 新增 batch JSONL index writer，每行记录 generated sample 的 metadata、QC、WSI、mask 路径和状态。
- 新增 CLI `archive-sample`，用于把已有 WSI/mask/QC/metadata 归档到 batch JSONL。
- 新增测试覆盖 pyramid OME-TIFF smoke 写出与读取、QC JSON 校验、metadata 写出、batch JSONL 追加和 CLI 归档行为。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本只实现小尺寸 pyramid OME-TIFF smoke writer，不声称支持生产级 gigapixel chunked OME-TIFF。
- 本次版本不执行真实自动图像质量评估，只建立 QC JSON 结构、硬错误检查和可扩展 metrics 契约。
- 本次版本不实现 PySide6 UI，也不生成真实 diffusion tile。

## v0.10.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M5：训练与生成骨架，为后续真实 latent diffusion 训练和级联生成提供可审计入口。

### 结构化需求

- 版本号升级为 `v0.10.0`。
- 新增训练配置与训练 run manifest，记录 model family、prior manifest、training index、random seed、cascade levels、tile size、训练阶段和输出路径。
- 训练骨架必须要求 `latent_diffusion_unet`、四层 cascade、40x、512x512 tile，并校验 prior manifest 文件存在且有效。
- 新增 checkpoint manifest placeholder，明确状态为 `not_trained`，不得伪装成真实可用模型权重。
- 新增 cascade generation plan，基于 generation config、prior manifest 和 checkpoint manifest 输出四层生成顺序、tile traversal、resume index、overlap 和 write mode。
- generation plan 必须拒绝未训练 checkpoint、缺失 prior manifest、非法 cascade 或 source-anchored 配置缺 source。
- 新增 CLI `init-training-run` 和 `plan-generation`，分别生成训练 run manifest 和 generation plan JSON。
- 新增测试覆盖 training manifest、未训练 checkpoint、generation plan、非法 checkpoint 和 CLI 行为。
- 同步更新 README、CHANGELOG、VERSION、默认配置和版本断言。

### 边界说明

- 本次版本不执行真实 PyTorch 训练，不产生真实模型权重，不生成像素 tile。
- 本次 checkpoint manifest 只用于声明训练入口和状态，不得被视为可用于真实推理。
- 本次版本不实现 OME-TIFF 写出、自动 QC 执行、batch JSONL 归档或 PySide6 UI。

## v0.9.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M4：prior artifact，为 layout/style/texture/QC priors 建立统一 manifest、文件校验和可追溯基础。

### 结构化需求

- 版本号升级为 `v0.9.0`。
- 新增 `priors` 模块，支持 prior artifact manifest 的创建、保存、读取与校验。
- Prior manifest 必须记录 `prior_id`、版本、创建时间、训练输入、随机种子和 artifact 清单。
- Artifact 清单必须覆盖 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`，每项记录路径、kind、sha256、size_bytes 和 metadata。
- 校验 manifest 时必须显式拒绝缺失 artifact、缺失文件、hash 不匹配、非法 seed、非法 artifact type 和重复路径。
- 新增 CLI `validate-prior-manifest`，用于校验 prior manifest 与 artifact 文件完整性。
- 新增测试覆盖 prior manifest roundtrip、缺失必需 artifact、hash mismatch、重复路径和 CLI 校验。
- 同步更新 README、CHANGELOG、VERSION、默认配置和版本断言。

### 边界说明

- 本次版本不实现真实 layout/style/texture/QC prior 学习算法，只建立 artifact 契约和审计校验。
- 本次版本不实现 latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。
- Prior manifest 的文件完整性校验不得静默跳过；如 artifact 文件缺失或 checksum 不一致，必须报错。

## v0.8.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M3：patch embedding 与伪 mask 基础能力，为后续 prior artifact 和聚类伪 mask 工作流提供接口与缓存。

### 结构化需求

- 版本号升级为 `v0.8.0`。
- 新增 `PatchEmbedder` 接口和 embedding result 数据结构。
- 新增 checkpoint-backed embedder：缺少 checkpoint、checkpoint JSON 损坏、embedding 维度非法或输出非有限值时必须显式报错。
- 新增 fixture/smoke embedder，用于小型测试数据，不得伪装成正式 pathology foundation model。
- 新增 embedding cache，支持保存和读取 embedding array 与 metadata，metadata 至少记录 model_id、checkpoint_hash、embedding_dim 和 patch_count。
- 新增轻量 clustering report，支持对 embedding array 生成 cluster labels、cluster counts 和 inertia；空 embedding 或非法 cluster 数需显式报错。
- 新增测试覆盖缺 checkpoint、合法 checkpoint embedding metadata、cache roundtrip、cluster report 和错误路径。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不绑定任何第三方 pathology foundation model，不下载模型权重，不实现真实伪 mask UI。
- fixture/smoke embedder 只用于开发测试；正式 prior 学习仍需要用户提供 checkpoint。
- 本次版本不实现 prior artifact、latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。

## v0.7.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 M2：WSI 与 mask I/O，为后续 patch embedding、prior 学习、训练生成和 QC 建立真实输入基础。

### 结构化需求

- 版本号升级为 `v0.7.0`。
- 新增 WSI metadata 读取抽象，生产路径使用 OpenSlide；缺少文件、OpenSlide 不可读取、MPP 缺失等情况必须显式报错。
- 新增 fixture image reader，用于小型 PNG/TIFF smoke test，不得伪装成生产 WSI 后端。
- 新增 manifest audit 能力：校验 manifest 后逐条读取 WSI 元数据，输出可审计记录，包括路径、尺寸、level、MPP、倍率和 backend。
- 新增 thumbnail 读取/生成基础能力，至少支持在 fixture reader 中输出指定尺寸 thumbnail，用于后续 UI 与 QC。
- 新增 mask label 读取与 label mapping 应用能力，支持 PNG/numpy 小型 mask，并拒绝未映射编号。
- 新增 mask 坐标对齐校验，基于 `transform_to_level0` 的 scale/offset 判断 mask 是否落在 WSI level0 范围内。
- 新增 CLI `audit-manifest`，用于根据 manifest 生成数据审计 JSON。
- 新增单元测试覆盖 WSI metadata、thumbnail、manifest audit、mask 编号读取、mapping 应用和坐标对齐错误。
- 同步更新 README、CHANGELOG、VERSION、pyproject 和版本断言。

### 边界说明

- 本次版本不实现 patch embedding、聚类伪 mask、prior artifact、latent diffusion 训练、级联生成、OME-TIFF 写出或 PySide6 UI。
- fixture image reader 只服务于 smoke test 和小型开发样例；真实 WSI 仍应走 OpenSlide 后端。
- 若 PNG/numpy mask 需要可选依赖而环境缺失，必须显式报错，不做静默替代。

## v0.6.0 - 2026-05-23

### 用户需求

- 用户要求根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 当前开发应从 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md` 的里程碑顺序推进，保持完整 H&E WSI 生成器作为最终目标。
- 本次版本先落地 M1：数据契约与 schema 校验，为后续 WSI I/O、mask 映射、prior、训练生成、QC 和 PySide6 UI 提供可测试基础。

### 结构化需求

- 版本号升级为 `v0.6.0`。
- 创建 Python core package，包名采用开发附录建议的 `he_wsi_generator`。
- 创建 CLI 入口 `he-wsi-gen`，至少支持对 manifest、label mapping、generation config、metadata 和 QC JSON 进行校验。
- 建立项目配置文件，支持本地以源码路径运行测试，不在主环境中安装额外运行依赖。
- 实现严格 schema 校验：缺少必填字段、非法 mask 类别、非法 `structure_anchor`、非法 cascade/tile/magnification、缺失 source 追踪和不完整 QC 输出都需要显式报错。
- 提供默认 generation config 示例，默认值需与开发附录一致：`latent_diffusion_unet`、`40x`、`512 x 512`、`["1/32", "1/16", "1/4", "1/1"]`、`sample_steps=50`、`overlap_px_40x=64`、`non_copy_patch_nearest_neighbor_search=false`。
- 添加单元测试覆盖 schema validator 和 CLI 校验行为。
- 同步更新 README、CHANGELOG、VERSION 和测试中的版本断言。

### 边界说明

- 本次版本不实现真实 WSI 读取、OME-TIFF 写出、patch embedding、prior 学习、latent diffusion 训练、级联生成或 PySide6 桌面 UI。
- 对 YAML 配置的支持若缺少解析依赖，必须显式报错，不允许把 YAML 静默当作 JSON 或忽略。
- 当前 M1 产物应作为后续 M2-M7 的基础，不应宣称完整 H&E WSI 生成器已经完成。

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
