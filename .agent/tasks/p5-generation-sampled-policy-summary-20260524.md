# Worker 子任务：p5-generation-sampled-policy-summary-20260524

## 任务分配

- 任务 ID：`p5-generation-sampled-policy-summary-20260524`
- Orchestrator 会话：`2026-05-24-v0.72.0-p5`
- 目标分支：`worker/p5-generation-sampled-policy-summary-20260524`
- 目标 worktree：`.worktrees/p5-generation-sampled-policy-summary-20260524`
- 必须写入的报告：`.agent/reports/p5-generation-sampled-policy-summary-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

让已经进入 condition packet 的 `sampled_style_policy` / `sampled_texture_policy` 条件摘要继续保留到 smoke generation metadata、generation run summary，以及 torch diffusion smoke sample manifest / generation metadata 中。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`
- `.agent/reports/p5-generation-sampled-policy-summary-20260524.md`

禁止修改：

- `src/he_wsi_generator/priors/**`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/outputs/**`
- `src/he_wsi_generator/qc/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 不改变 condition feature vector 编码；`style_seed_value`、`texture_cluster_id` 等既有 summary 字段必须保持兼容。
- 不自动调用 policy sampler，不改变 smoke/torch generation backend 的图像生成行为。
- 不把 sampled policy 描述为 trainable style encoder、texture codebook、VQ-VAE token sampler、morphology token generator 或 production texture/style model。
- 对 sampled policy summary 缺失关键字段必须显式失败，不允许 silent fallback 到弱摘要。
- 如果实现需要修改禁止范围内的文件，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_generation_runner.py` 增加失败测试：
   - test helper 可以新增可选参数构造 `conditions.style_seed.source == "sampled_style_policy"` 和 `conditions.texture_token.source == "sampled_texture_policy"`；
   - `run_smoke_generation()` 输出的 metadata `generation.condition_summary.sampled_style_policy` / `sampled_texture_policy` 必须记录 sample id、artifact path、selected style/token 摘要；
   - `generation_run.json` 的 `condition_packet.summary` 必须保留同样摘要；
   - 删除 sampled style policy 的关键 `selected_style` 或 sampled texture policy 的关键 `representative_embedding_index` 时必须抛出 `GenerationExecutionError`。
4. 在 `tests/test_torch_training.py` 增加失败测试：
   - `_load_condition_packet()` 直接加载 sampled style/texture condition packet 时返回同样摘要；
   - `sample_torch_diffusion_smoke_model()` 写出的 sample manifest `condition_summary` 必须保留 sampled style/texture policy 摘要；
   - `run_torch_diffusion_smoke_generation()` 输出 metadata / generation run summary 也应保留这些摘要。
5. 确认红灯失败原因来自缺失 sampled policy summary 贯通，而不是测试本身错误。
6. 在 `src/he_wsi_generator/generation/executor.py` 中实现最小 summary helper：
   - `_condition_packet_summary()` 在 `style_seed.source == "sampled_style_policy"` 时调用新 helper，返回 `sampled_style_policy` 摘要；
   - 在 `texture_token.source == "sampled_texture_policy"` 时调用新 helper，返回 `sampled_texture_policy` 摘要；
   - helper 使用现有 `_require_non_empty_condition_str()`、`_require_condition_int()`、`_require_condition_list()` 等显式校验风格。
7. 在 `src/he_wsi_generator/models/torch_training.py` 中实现相同语义的 summary helper：
   - 字段名和结构与 executor 保持一致；
   - 不改 `_condition_feature_vector_from_summary()` 的输入语义。
8. 运行必须验证命令。
9. 按要求写最终报告。

## 建议摘要字段

`sampled_style_policy`：

```json
{
  "source": "sampled_style_policy",
  "artifact_path": "...",
  "sample_id": "...",
  "random_seed": 7,
  "selection_policy": "...",
  "selected_style": {
    "tile_index": 0,
    "sample_id": "...",
    "wsi_id": "...",
    "tile": {"x": 0, "y": 0},
    "mean_rgb": [120.0, 100.0, 140.0]
  },
  "rgb_statistics_reference": {},
  "limitations": ["statistical_policy_not_trainable_style_encoder"]
}
```

`sampled_texture_policy`：

```json
{
  "source": "sampled_texture_policy",
  "artifact_path": "...",
  "sample_id": "...",
  "random_seed": 7,
  "selection_policy": "...",
  "cluster_id": 1,
  "representative_embedding_index": 4,
  "prototype_index": 0,
  "sample_count": 2,
  "fraction": 0.5,
  "mean_embedding": [0.1, 0.2],
  "std_embedding": [0.01, 0.02],
  "limitations": ["statistical_policy_not_trainable_texture_codebook"]
}
```

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner tests.test_torch_training -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

写入 `.agent/reports/p5-generation-sampled-policy-summary-20260524.md`，必须包含：

- 修改摘要。
- 影响文件。
- 红灯/绿灯验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
