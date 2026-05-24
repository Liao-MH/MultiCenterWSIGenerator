# Worker 子任务：p4-smoke-multilevel-tile-source-20260524

## 任务分配

- 任务 ID：`p4-smoke-multilevel-tile-source-20260524`
- Orchestrator 会话：`2026-05-24-v0.69.0-p4`
- 目标分支：`worker/p4-smoke-multilevel-tile-source-20260524`
- 目标 worktree：`.worktrees/p4-smoke-multilevel-tile-source-20260524`
- 必须写入的报告：`.agent/reports/p4-smoke-multilevel-tile-source-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

让 `run-generation --backend smoke-cascade --wsi-writer tile-streaming` 写出完整四层 OME-TIFF pyramid，而不是当前只基于 level0 tile source manifest 写出单层 OME-TIFF。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_generation_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p4-smoke-multilevel-tile-source-20260524.md`

禁止修改：

- `src/he_wsi_generator/outputs/**`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- `tests/test_outputs_qc_archive.py`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 保留默认 `wsi_writer="array"` 的现有行为，包括当前 tile manifest、level0 tile source manifest 和 in-memory pyramid 写出路径。
- 新增的多层 tile source manifest 只用于显式 `wsi_writer="tile-streaming"`。
- 允许在 smoke cascade 已经构建的四层 numpy arrays 基础上按 TIFF tile grid 写出 `.npy` tile source；必须在报告中说明该路径仍不是 production backend streaming，因为 smoke cascade arrays 仍在内存中生成。
- 不要把该实现描述成 OME-TIFF 文件中断后可恢复写入。
- 如果实现需要修改输出层、CLI 或共享文档，停止并在报告中说明需要 orchestrator 批准。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_generation_runner.py` 增加失败测试，覆盖 `run_smoke_generation(..., wsi_writer="tile-streaming")` 或 CLI 显式 writer 生成四层 OME-TIFF，并检查 `generation_run.json` 中 `pyramid_report.level_count == 4`、`write_mode == "tile_iterator_streaming_write"`、`streaming_write_report.levels` 覆盖四层。
4. 保留并验证默认 array writer 测试仍期望四层 in-memory pyramid 和现有 tile manifest 行为。
5. 在 `src/he_wsi_generator/generation/executor.py` 中为显式 tile-streaming writer 生成完整四层 tile source manifest：每层按 `tile_size_40x` 对应的 TIFF tile shape 切分成 grid records，写出 `.npy` tile，记录 `level_index`、`tile_index`、相对路径、shape、dtype、status、`tile_origin_40x` 和 `write_region_40x`。
6. 将显式 tile-streaming writer 调用改为使用新的多层 tile source manifest；metadata / generation run summary 中继续记录实际 manifest path 和 `wsi_writer`。
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

使用 worker 报告模板写入 `.agent/reports/p4-smoke-multilevel-tile-source-20260524.md`。报告必须包含：

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
- 输出层 writer 无法消费多层 tile source manifest，且需要改 `src/he_wsi_generator/outputs/**`。
- 验证暴露了超出本任务范围的失败。
