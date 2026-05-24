# Worker 子任务：p3-checkpoint-inference-contract-20260525

## 任务分配

- 任务 ID：`p3-checkpoint-inference-contract-20260525`
- Orchestrator 会话：`2026-05-25`
- 目标分支：`worker/p3-checkpoint-inference-contract-20260525`
- 目标 worktree：`.worktrees/p3-checkpoint-inference-contract-20260525`
- 必须写入的报告：`.agent/reports/p3-checkpoint-inference-contract-20260525.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

加固 checkpoint manifest 的 inference 可用性契约：`usable_for_inference=true` 不能再只靠薄 JSON 布尔字段通过，必须具备可审计的 checkpoint 文件、hash 和 inference contract 字段；`usable_for_inference=false` 的 smoke/skeleton manifest 继续可加载但不能用于 generation plan。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/DEMANDS.MD`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p3-checkpoint-inference-contract-20260525.md`

禁止修改：

- `docs/`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`
- `.agent/tasks/`
- 其他未列入允许范围的文件

## 约束

- 必须先写 RED 测试并运行，证明薄 checkpoint manifest 被拒绝；再实现最小代码使测试通过。
- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。
- 不要把 smoke / torch smoke checkpoint 标记为 production 可推理；本任务只加固可推理 checkpoint 的契约，不实现 production 模型本体。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 编辑前先检查现有实现。
4. 在 `tests/test_models_generation.py` 中新增或调整最小 RED 测试，验证只有 `usable_for_inference=true` 的薄 checkpoint manifest 会失败。
5. 在 `src/he_wsi_generator/models/training.py` 中实现最小契约加固：
   - `status` 必须为 `trained` 时才允许 `usable_for_inference=true`；
   - `usable_for_inference=true` 时必须校验非空 `training_backend`、`target_type`、`checkpoint_path`、`checkpoint_sha256` 和 `inference_contract`；
   - `checkpoint_path` 必须存在且为文件；
   - `checkpoint_sha256` 必须与文件实际 SHA-256 一致；
   - `inference_contract` 必须为 JSON object，且至少明确 `backend_type`、`artifact_role`、`production_ready`、`limitations`；
   - `production_ready` 当前不得静默默认，必须由 manifest 显式声明；本任务允许 fixture 使用 `false` 以表示 contract-ready 但非 production backend。
6. 更新 `tests/test_models_generation.py` / `tests/test_generation_runner.py` 中的可推理 checkpoint fixture，使它们包含最小真实 checkpoint 文件与 matching SHA-256。
7. 运行必须的验证命令。
8. 按要求把最终报告写入指定路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

写入 `.agent/reports/p3-checkpoint-inference-contract-20260525.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- RED 测试命令、失败结果摘要。
- GREEN 验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
