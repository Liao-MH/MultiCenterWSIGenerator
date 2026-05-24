# Worker 子任务：p4-smoke-streaming-sequential-materialization-20260524

## 任务分配

- 任务 ID：`p4-smoke-streaming-sequential-materialization-20260524`
- Orchestrator 会话：`2026-05-24-v0.72.x-p4`
- 目标分支：`worker/p4-smoke-streaming-sequential-materialization-20260524`
- 目标 worktree：`.worktrees/p4-smoke-streaming-sequential-materialization-20260524`
- 必须写入的报告：`.agent/reports/p4-smoke-streaming-sequential-materialization-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

重构 `run_smoke_generation(..., wsi_writer="tile-streaming")` 的多层 tile source 材料化路径，使四层 smoke pyramid 的 `.npy` tile source 生成按 pyramid level 顺序逐层执行，不再一次性持有完整四层 `pyramid_levels` 容器，同时保持当前 smoke 输出、writer contract 和 CLI 行为不变。

## 必须先读取的上下文

- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p4-smoke-streaming-sequential-materialization-20260524.md`

禁止修改：

- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先检查现有实现，再做最小必要改动。
- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 不要改变默认 `array` writer 行为。
- 不要把当前实现夸大为 production backend 逐 tile 生成或可恢复 OME-TIFF 文件写入。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 检查 `run_smoke_generation()` 中 tile-streaming 分支的现有实现。
4. 用最小必要改动把 smoke 四层 tile source manifest 的构建改为按 pyramid level 顺序逐层执行，尽量避免一次性持有完整四层数组容器。
5. 保持 `tile_source_manifest.streaming.json`、`streaming_tiles/*.npy`、`generated.ome.tiff`、`metadata.json`、`qc.json` 和 `generation_run.json` 的现有契约。
6. 如有必要，补充或调整 `tests/test_generation_runner.py` 中与 tile-streaming 路径相关的测试，确保行为不变且可回归验证。
7. 运行必须的验证命令。
8. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-smoke-streaming-sequential-materialization-20260524.md`。报告必须包含：

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
