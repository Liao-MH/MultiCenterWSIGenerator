# Worker 子任务：p5-condition-sampled-policy-20260524

## 任务分配

- 任务 ID：`p5-condition-sampled-policy-20260524`
- Orchestrator 会话：`2026-05-24-v0.71.0-p5`
- 目标分支：`worker/p5-condition-sampled-policy-20260524`
- 目标 worktree：`.worktrees/p5-condition-sampled-policy-20260524`
- 必须写入的报告：`.agent/reports/p5-condition-sampled-policy-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

让 `build-condition-packet` 可选读取 v0.70.0 的 `sampled_style_policy` / `sampled_texture_policy` artifact，并将其写入 condition packet 的可审计条件摘要。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_conditioning.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_conditioning.py`
- `.agent/reports/p5-condition-sampled-policy-20260524.md`

禁止修改：

- `src/he_wsi_generator/priors/**`
- `src/he_wsi_generator/models/**`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/outputs/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 不改变未提供 sampled policy 时的既有 condition packet 输出语义。
- 不引入 silent fallback；非法 artifact type、版本不匹配、缺失关键字段必须显式抛出 `GenerationConditionError` 或 CLI 返回非零。
- 不把 sampled policy 描述为 trainable style encoder、texture codebook、VQ-VAE token sampler、morphology token generator 或 production texture/style model。
- 不接入 generation runtime 自动调用 policy sampler；本任务只处理 condition packet 的显式输入记录。
- 如果实现需要修改禁止范围内的文件，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_generation_conditioning.py` 增加失败测试：
   - 直接调用 `build_generation_condition_packet(..., sampled_style_policy_path=..., sampled_texture_policy_path=...)` 时，输出记录 `artifact_inputs.sampled_style_policy`、`artifact_inputs.sampled_texture_policy`、`conditions.style_seed.source == "sampled_style_policy"`、`conditions.texture_token.source == "sampled_texture_policy"` 和 selected style/token 摘要；
   - CLI 通过 `--sampled-style-policy` 与 `--sampled-texture-policy` 写出同等 condition packet；
   - 非法 sampled policy artifact type 或缺失关键 selected field 显式失败。
4. 确认红灯失败原因来自缺失参数或缺失行为，而不是测试本身错误。
5. 在 `src/he_wsi_generator/generation/conditioning.py` 中实现最小可审计接入：
   - `build_generation_condition_packet()` 新增可选 `sampled_style_policy_path` / `sampled_texture_policy_path`；
   - 读取并校验 sampled policy JSON；
   - 有 sampled style policy 时覆盖 `conditions.style_seed` 的 source 和摘要；
   - 有 sampled texture policy 时覆盖 `conditions.texture_token` 的 source 和摘要；
   - `artifact_inputs` 记录两个 sampled policy artifact 的 path/kind/metadata；
   - 保留 limitations 中的非 production 边界。
6. 在 `src/he_wsi_generator/cli.py` / `src/he_wsi_generator/cli_commands.py` 中接入可选 CLI 参数。
7. 运行必须验证命令。
8. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p5-condition-sampled-policy-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
