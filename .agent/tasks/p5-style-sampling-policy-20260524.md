# Worker 子任务：p5-style-sampling-policy-20260524

## 任务分配

- 任务 ID：`p5-style-sampling-policy-20260524`
- Orchestrator 会话：`2026-05-24-v0.70.0-p5`
- 目标分支：`worker/p5-style-sampling-policy-20260524`
- 目标 worktree：`.worktrees/p5-style-sampling-policy-20260524`
- 必须写入的报告：`.agent/reports/p5-style-sampling-policy-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

在现有统计型 `style_prior` 基础上新增一个可复现、可审计的 style sampling policy artifact，明确记录 seed、选择策略、选中 tile style 和非 production 限制。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/priors/style.py`
- `tests/test_style_prior.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/priors/style.py`
- `tests/test_style_prior.py`
- `.agent/reports/p5-style-sampling-policy-20260524.md`

禁止修改：

- `src/he_wsi_generator/priors/texture.py`
- `src/he_wsi_generator/generation/**`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 不改变 `build_style_prior_from_training_index()` 的既有输出字段语义；只能增量添加 helper/API。
- 不引入 silent fallback；非法 seed、空 `tile_style_records`、缺失或非法 `mean_rgb` 必须显式抛出 `StylePriorBuildError`。
- 不把该能力描述为 trainable style encoder、VAE latent style model 或 production style transfer。
- 如果实现需要修改 CLI、condition packet、prior manifest 或 generation runtime，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_style_prior.py` 增加失败测试：期望新增的 `sample_style_policy_from_prior()` 能从 style prior JSON 产生 artifact；当前函数不存在应红灯失败。
4. 增加失败路径测试：非法 random seed、空 `tile_style_records`、缺失或非法 `mean_rgb` 必须抛出 `StylePriorBuildError`。
5. 在 `src/he_wsi_generator/priors/style.py` 中实现最小 helper：
   - API 建议为 `sample_style_policy_from_prior(style_prior_path, output_path, sample_id, random_seed)`；
   - 读取并校验 `prior_type == "style_prior"` 与 `schema_version == PROJECT_VERSION`；
   - 用 `random_seed % len(tile_style_records)` 选择 tile style；
   - 写出 JSON artifact，包含 `artifact_type=sampled_style_policy`、`sample_id`、`random_seed`、`selection_policy`、`selected_style`、`rgb_statistics_reference`、`source` 和 `limitations`。
6. 运行必须验证命令。
7. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_style_prior -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p5-style-sampling-policy-20260524.md`。报告必须包含：

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
