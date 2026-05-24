# Worker 子任务：p4-ome-tiff-streaming-contract-20260524

## 任务分配

- 任务 ID：`p4-ome-tiff-streaming-contract-20260524`
- Orchestrator 会话：`2026-05-24-v0.66.0-p4`
- 目标分支：`worker/p4-ome-tiff-streaming-contract-20260524`
- 目标 worktree：`.worktrees/p4-ome-tiff-streaming-contract-20260524`
- 必须写入的报告：`.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

在 `outputs/ome_tiff.py` 中新增磁盘 tile source / streaming contract 校验与报告能力，确保 incomplete tile source 不会被误判为可发布输出，并为后续真正 gigapixel streaming writer 留下明确契约。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`

禁止修改：

- `VERSION`
- `pyproject.toml`
- `src/he_wsi_generator/constants.py`
- `configs/generation.default.json`
- `README.md`
- `docs/CHANGELOG.md`
- `docs/audit/**`
- `docs/DEMANDS.MD`
- 除允许范围外的所有 `src/**` 和 `tests/**`

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。
- 不要把当前内存数组 writer 宣称为 production 级 gigapixel streaming writer；如只实现 contract/校验，报告和返回字段必须如实标注限制。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 编辑前先检查现有 `write_pyramid_ome_tiff()`、`_chunked_write_audit()` 和测试覆盖。
4. 用最小必要改动新增 helper，建议覆盖以下能力：
   - 校验磁盘 tile source manifest/records：tile index、level index、路径存在、shape、dtype、completed 状态和 expected count。
   - 对 pending/failed/missing/重复 tile 显式抛出 `OutputWriteError`。
   - 产出 contract report，明确 `production_streaming` 仍为 `False` 或 `partial_contract_only`，并列出可恢复 tile source 的覆盖情况。
   - 不要求本任务实现真正逐 tile 写入 OME-TIFF；若未实现，必须在报告和返回字段里保持诚实边界。
5. 增加或更新 `tests/test_outputs_qc_archive.py` 的定向测试。
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

使用 worker 报告模板写入 `.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`。报告必须包含：

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
