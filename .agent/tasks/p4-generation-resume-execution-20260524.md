# Worker 子任务：p4-generation-resume-execution-20260524

## 任务分配

- 任务 ID：`p4-generation-resume-execution-20260524`
- Orchestrator 会话：`2026-05-24-v0.67.0-p4`
- 目标分支：`worker/p4-generation-resume-execution-20260524`
- 目标 worktree：`.worktrees/p4-generation-resume-execution-20260524`
- 必须写入的报告：`.agent/reports/p4-generation-resume-execution-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

把 `run_smoke_generation()` 接入可恢复 tile manifest：首次运行写出 tile `.npy` 与 completed manifest；恢复运行可从已有 partial manifest 继续 pending tile；failed/gapped/missing/incomplete manifest 必须显式失败。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_runner.py`
- `tests/test_generation_tiling.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `tests/test_generation_runner.py`

禁止修改：

- `src/he_wsi_generator/outputs/**`
- `src/he_wsi_generator/priors/**`
- `src/he_wsi_generator/models/**`
- `src/he_wsi_generator/ui/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `docs/**`
- `.agent/tasks/**`
- `.agent/reports/**`，但必须写入本任务指定报告
- `tests/*.py` 中除 `tests/test_generation_runner.py` 以外的文件

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。
- 遵循 TDD：先写最小失败测试并运行确认失败，再改实现。
- 不要把本批次描述为 production gigapixel streaming writer；这是恢复执行和 tile manifest 闭环。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_generation_runner.py` 先增加失败测试，至少覆盖：
   - 首次 `run_smoke_generation()` 写出 `tile_manifest.json` 和磁盘 tile source manifest，并在 metadata / run summary 中记录路径；
   - `run_smoke_generation(..., resume_tile_manifest_path=...)` 可从 partial manifest 继续 pending tile；
   - failed/gapped/missing completed tile 文件会抛出 `GenerationExecutionError`。
4. 在 `run_smoke_generation()` 中新增最小必要参数，例如 `resume_tile_manifest_path: str | Path | None = None`，保持现有调用兼容。
5. 首次运行时从 generation plan 构建 resumable tile manifest，按 row-major 生成 tile `.npy`，更新 completed 状态，并写出 manifest。
6. 恢复运行时读取并验证已有 manifest，拒绝 failed、row-major gap、schema/version 不匹配和缺失 completed tile 文件；只生成 pending tile。
7. 最终调用 `require_complete_tile_manifest()`，未完成时不得继续写出 OME-TIFF / metadata / QC。
8. 生成一个现有 `write_pyramid_ome_tiff(..., tile_source_manifest=...)` 可校验的 tile source manifest，并把路径同步到 plan、metadata 或 run summary 中；可保留当前 in-memory pyramid writer。
9. CLI `run-generation --backend smoke-cascade` 增加可选 `--resume-tile-manifest`；`torch-diffusion-smoke` 收到该参数时必须显式失败或不接受。
10. 运行必须的验证命令。
11. 按要求把最终报告写入指定路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-generation-resume-execution-20260524.md`。报告必须包含：

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
