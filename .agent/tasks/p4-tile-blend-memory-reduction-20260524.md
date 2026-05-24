# Worker 子任务：p4-tile-blend-memory-reduction-20260524

## 任务分配

- 任务 ID：`p4-tile-blend-memory-reduction-20260524`
- Orchestrator 会话：`2026-05-24`
- 目标分支：`worker/p4-tile-blend-memory-reduction-20260524`
- 目标 worktree：`.worktrees/p4-tile-blend-memory-reduction-20260524`
- 必须写入的报告：`.agent/reports/p4-tile-blend-memory-reduction-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

在不改变现有 tile blending 语义和测试结果的前提下，降低 `src/he_wsi_generator/generation/tiling.py` 中 `blend_rgb_tiles()` 的中间内存占用，并保持现有 smoke generation / tile traversal / resumable manifest 行为不变。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/DEMANDS.MD`
- `src/he_wsi_generator/generation/tiling.py`
- `tests/test_generation_tiling.py`
- `tests/test_generation_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/generation/tiling.py`
- `tests/test_generation_tiling.py`
- `.agent/reports/p4-tile-blend-memory-reduction-20260524.md`

禁止修改：

- 其他源码文件
- `docs/`
- `README.md`
- 版本号文件
- `.agent/tasks/` 之外的任务文件

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 编辑前先检查现有实现。
4. 用最小必要改动完成目标。
5. 仅在任务明确要求时更新直接相关的文档或测试。
6. 运行必须的验证命令。
7. 按要求把最终报告写入指定路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_streaming_materializes_pyramid_levels_sequentially -v
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-tile-blend-memory-reduction-20260524.md`。报告必须包含：

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
