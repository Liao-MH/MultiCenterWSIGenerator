# Worker 子任务：p6-torch-training-helpers-20260524

## 任务分配

- 任务 ID：`p6-torch-training-helpers-20260524`
- Orchestrator 会话：`2026-05-24-v0.65.1-p6-maintainability`
- 目标分支：`worker/p6-torch-training-helpers`
- 目标 worktree：`.worktrees/p6-torch-training-helpers`
- 必须写入的报告：`.agent/reports/p6-torch-training-helpers-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

对 `src/he_wsi_generator/models/torch_training.py` 做行为保持的维护性收敛：把 manifest/schema/validation 辅助逻辑拆到模型内部 helper 模块，降低单文件后续修改风险，同时保持所有公开训练/采样函数的签名、返回结构和错误文案不变。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/DEMANDS.MD`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_torch_training.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`（如需要新增）
- `tests/test_torch_training.py`
- `.agent/reports/p6-torch-training-helpers-20260524.md`

禁止修改：

- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `docs/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `src/he_wsi_generator/constants.py`
- `tests/test_version.py`
- 任何未列入允许范围的文件

## 约束

- 这是 patch 版本的行为保持重构，不允许改变 public API：
  - `train_torch_smoke_model`
  - `train_torch_vae_smoke_model`
  - `train_torch_diffusion_smoke_model`
  - `sample_torch_diffusion_smoke_model`
- 不改变 checkpoint manifest 字段、sample manifest 字段、错误消息和测试 fixture 输出。
- 不实现 production 模型能力，不扩大训练算法。
- 不触碰 CLI 文件，避免和另一个 worker 冲突。
- 如果需要扩大修改范围，停止并报告。

## 必须执行的工作

1. 确认当前分支是 `worker/p6-torch-training-helpers`，当前路径是 `.worktrees/p6-torch-training-helpers`。
2. 读取上下文文件，定位适合迁出的 helper 群组。
3. 先运行基线验证命令，确认本 worktree 起点测试通过；如失败，停止并报告。
4. 选择最小拆分方式：
   - 推荐新增 `src/he_wsi_generator/models/torch_training_contracts.py`；
   - 优先迁出纯 helper：checkpoint manifest builder、diffusion/vae manifest validator、condition/cross-scale schema helper、denoiser architecture helper；
   - 保留实际训练 loop 和采样 loop 在 `torch_training.py`，避免一次性大搬迁。
5. 如现有测试不足以证明行为保持，可补一个小测试验证 manifest 字段仍存在且值不变。
6. 运行必须验证命令。
7. 写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p6-torch-training-helpers-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 行为保持边界。
- 验证命令和结果。
- 残余风险。
- 是否需要 orchestrator 决策。

## 停止条件

- 当前 worktree 或分支不符合预期。
- 基线验证失败。
- 需要修改禁止范围内的文件。
- 发现必须改变 torch training 行为才能继续。
