# Worker 子任务：p4-streaming-publish-transaction-20260525

## 任务分配

- 任务 ID：`p4-streaming-publish-transaction-20260525`
- Orchestrator 会话：`2026-05-25-p4-streaming-publish-transaction`
- 目标分支：`worker/p4-streaming-publish-transaction-20260525`
- 目标 worktree：`.worktrees/p4-streaming-publish-transaction-20260525`
- 必须写入的报告：`.agent/reports/p4-streaming-publish-transaction-20260525.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

为 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 增加可审计的写入事务 manifest 和原子发布流程，防止 tile-streaming writer 失败时半成品被误认为完整输出，同时保持 `resume_capable=false` 的真实边界。

## 必须先读取的上下文

- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `.agent/reports/p4-streaming-publish-transaction-20260525.md`

禁止修改：

- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/`
- `docs/`
- 其他 `src/`、`tests/` 文件

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 不要把本任务描述为 production 可恢复 OME-TIFF writer；本轮只实现原子发布和事务审计。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 先写一个 RED 测试，证明旧 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 缺少 transaction manifest / atomic publish 证据。
4. 用最小必要改动实现：
   - 先写临时 OME-TIFF 文件；
   - 成功校验 OME/pyramid 后用原子替换发布到目标路径；
   - 写出 transaction manifest，包含 `schema_version`、`manifest_type`、writer 类型、目标路径、临时路径、tile source manifest、状态、开始/结束时间、失败原因、`atomic_publish`、`resume_capable`；
   - 成功 report 和 streaming contract 里记录 transaction manifest path、`atomic_publish=true`、`resume_capable=false`；
   - 失败时 transaction manifest 记录 `failed` 和错误原因，并且不要覆盖既有目标文件。
5. 保持既有 writer 输入/输出兼容，不新增 CLI 参数，不改变 generation executor。
6. 运行必须的验证命令。
7. 按要求把最终报告写入指定路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-streaming-publish-transaction-20260525.md`。报告必须包含：

- 修改摘要。
- RED 测试命令与失败结果摘要。
- GREEN 验证命令和结果。
- 影响文件。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
