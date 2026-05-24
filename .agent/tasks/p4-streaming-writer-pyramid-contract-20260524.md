# Worker 子任务：p4-streaming-writer-pyramid-contract-20260524

## 任务分配

- 任务 ID：`p4-streaming-writer-pyramid-contract-20260524`
- Orchestrator 会话：`2026-05-24-v0.69.0-p4`
- 目标分支：`worker/p4-streaming-writer-pyramid-contract-20260524`
- 目标 worktree：`.worktrees/p4-streaming-writer-pyramid-contract-20260524`
- 必须写入的报告：`.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

加固 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 的 pyramid level 契约，确保 streaming tile source manifest 按 high-to-low 分辨率顺序写出，并在报告中明确 pyramid order 与不可恢复写入限制。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `tests/test_outputs_qc_archive.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`

禁止修改：

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
- 不改变 `write_pyramid_ome_tiff()` 和 `write_pyramid_ome_tiff_from_tile_sources()` 的既有行为。
- 不引入 silent fallback；非法 level 顺序、缺失 shape 或后续 level 大于前一层时必须显式抛出 `OutputWriteError`。
- 不把 writer 描述成可中断续写同一个 OME-TIFF 文件；报告中必须继续保留 `resume_capable=false` 和 `ome_tiff_file_resume_not_supported`。
- 如果实现需要修改 generation 或 CLI，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_outputs_qc_archive.py` 增加失败测试：构造 `levels` 中 level0 小于 level1 或 level 顺序低到高的 tile source manifest，调用 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 时应抛出 `OutputWriteError`，错误消息能指向 pyramid level order。
4. 增加或更新正向测试，检查 `streaming_write_report` 包含明确的 `pyramid_order` / `level_order` 信息，并且 `resume_capable=false` 与 `ome_tiff_file_resume_not_supported` 仍存在。
5. 在 `src/he_wsi_generator/outputs/ome_tiff.py` 中加固 streaming plan 构建逻辑：按 manifest level 顺序或 level_index 顺序形成 pyramid，并验证后续 level 的 height/width 不大于前一层。
6. 运行必须验证命令。
7. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`。报告必须包含：

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
- 需要修改 generation/CLI 才能完成。
- 验证暴露了超出本任务范围的失败。
