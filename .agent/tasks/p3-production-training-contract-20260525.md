# Worker 子任务：p3-production-training-contract-20260525

## 任务分配

- 任务 ID：`p3-production-training-contract-20260525`
- Orchestrator 会话：`2026-05-25`
- 目标分支：`worker/p3-production-training-contract-20260525`
- 目标 worktree：`.worktrees/p3-production-training-contract-20260525`
- 必须写入的报告：`.agent/reports/p3-production-training-contract-20260525.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

为 P3 `init-training-run` 增加 production training dataset contract 校验与 manifest 记录；这是训练数据/目标 backend 契约补丁，不实现真实 production 训练 loop，也不把 skeleton/smoke checkpoint 标为可推理。

## 必须先读取的上下文

- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- `src/he_wsi_generator/constants.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- `.agent/reports/p3-production-training-contract-20260525.md`

禁止修改：

- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `docs/CHANGELOG.md`
- `docs/audit/*`
- `docs/DEMANDS.MD`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`
- `src/he_wsi_generator/generation/*`
- `src/he_wsi_generator/outputs/*`
- 任何 `build/validation/` 或 `.worktrees/` 证据清理

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。
- 保持当前边界：本任务只做 production training dataset contract，不实现真实 production latent diffusion / ControlNet / DiT，不写 production-ready checkpoint。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_models_generation.py` 中新增 RED 测试，证明旧实现不会拒绝缺失 `dataset_contract` 的 training config。
4. 在 `src/he_wsi_generator/models/training.py` 中加固 training config：
   - 要求 `training_backend == "latent_diffusion_unet"`；
   - 要求 `dataset_contract` 为 JSON object；
   - `dataset_contract.training_index_path` 必须与顶层 `training_index_path` 完全一致；
   - `dataset_contract.production_readiness_declared` 必须为 `true`；
   - `dataset_contract.minimum_sample_count` 必须是正整数；
   - `dataset_contract.sample_count` 必须是正整数且不小于 `minimum_sample_count`；
   - `dataset_contract.records_by_split` 必须包含至少 `train` 且其数量为正整数；
   - `dataset_contract.records_by_level` 必须覆盖 `["1/32", "1/16", "1/4", "1/1"]` 且每层数量为正整数；
   - `dataset_contract.required_condition_inputs` 必须至少包含 `mask`, `style`, `texture`, `coord`, `source_condition`, `structure_anchor`；
   - `dataset_contract.mask_class_schema.classes` 必须等于项目 6 类 mask classes；
   - `dataset_contract.mask_class_schema.label_encoding` 必须为 `integer_index`。
5. `create_training_run()` 写出的 `training_run.json` 必须包含通过校验的 `training_backend` 和 `dataset_contract`。
6. skeleton checkpoint manifest 必须包含 `training_backend`、`target_type` 和 `dataset_contract_summary`，但继续保持 `status=not_trained`、`usable_for_inference=false`。
7. 失败必须抛出 `ModelRunError`，错误信息要指向具体字段，不允许 silent fallback。
8. 按要求把最终报告写入 `.agent/reports/p3-production-training-contract-20260525.md`。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p3-production-training-contract-20260525.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- RED 测试的旧实现失败证据。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
