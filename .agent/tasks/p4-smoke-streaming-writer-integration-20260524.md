# Worker 子任务：p4-smoke-streaming-writer-integration-20260524

## 任务分配

- 任务 ID：`p4-smoke-streaming-writer-integration-20260524`
- Orchestrator 会话：`2026-05-24-v0.68.0-p4`
- 目标分支：`worker/p4-smoke-streaming-writer-integration-20260524`
- 目标 worktree：`.worktrees/p4-smoke-streaming-writer-integration-20260524`
- 必须写入的报告：`.agent/reports/p4-smoke-streaming-writer-integration-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

让 `run-generation --backend smoke-cascade` 通过显式参数选择 tile source streaming writer，默认行为保持现有内存数组写出路径。

## 必须先读取的上下文

- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p4-smoke-streaming-writer-integration-20260524.md`

禁止修改：

- `src/he_wsi_generator/outputs/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- `tests/test_outputs_qc_archive.py`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 默认 smoke-cascade 写出路径必须保持当前行为。
- 新参数必须显式 opt-in，建议命名为 `--wsi-writer tile-streaming` 或等价枚举。
- 如果输出层新函数尚未存在，可在本 worker 中用局部导入/接口假定写测试；合并时由 orchestrator 处理依赖顺序。
- 不要把 `torch-diffusion-smoke` 接入该参数；若参数对 torch backend 不支持，必须显式失败。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_generation_runner.py` 增加失败测试，覆盖 smoke-cascade 显式选择 tile streaming writer 后 generation summary / metadata 记录 `write_mode=tile_iterator_streaming_write`。
4. 保留默认 `run_smoke_generation()` 行为仍走既有 `write_pyramid_ome_tiff()` 路径。
5. 为 CLI 增加显式 writer 选择参数，并传递到 `run_smoke_generation()`。
6. 对 `torch-diffusion-smoke` 使用该参数时显式报错。
7. 运行必须验证命令。
8. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-smoke-streaming-writer-integration-20260524.md`。报告必须包含：

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
- 需要更改输出层实现；该范围由另一个 worker 负责。
- 验证暴露了超出本任务范围的失败。
