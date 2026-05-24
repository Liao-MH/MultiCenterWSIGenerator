# Worker 子任务：p2-ui-job-flow-helper-20260524

## 任务分配

- 任务 ID：`p2-ui-job-flow-helper-20260524`
- Orchestrator 会话：`2026-05-24-v0.65.0-p2-gui-flow`
- 目标分支：`worker/p2-ui-job-flow-helper`
- 目标 worktree：`.worktrees/p2-ui-job-flow-helper`
- 必须写入的报告：`.agent/reports/p2-ui-job-flow-helper-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

补齐 GUI 可调用的非 Qt job workflow helper：能够从表单状态定位 queued job，执行 queued job，刷新 job 状态，并在 job 完成后基于 output root/generated id 读取 `metadata.json`、`qc.json` 和可选 `qc_review.json` 输出摘要。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/jobs.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_ui_workflow.py`
- `tests/test_job_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/jobs.py`
- `tests/test_ui_workflow.py`
- `tests/test_job_runner.py`
- `.agent/reports/p2-ui-job-flow-helper-20260524.md`

禁止修改：

- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/cli.py`
- `docs/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `src/he_wsi_generator/constants.py`
- `tests/test_version.py`
- 任何未列入允许范围的源码或测试文件

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 对非法表单、未知 job、未完成 job、缺失/非法 metadata 或 QC artifact 必须显式抛出 `UIWorkflowError` 或 `JobRunnerError`，不得返回空摘要。
- helper 必须保持 CLI-first：不要让 `run-generation` 默认打开 GUI，不要新增 GUI 入口。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支是 `worker/p2-ui-job-flow-helper`，当前路径是 `.worktrees/p2-ui-job-flow-helper`。
2. 先写或扩展失败测试，覆盖至少这些行为：
   - `run_queued_generation_job(...)` 能执行已有 queued job 并返回 completed/failed record。
   - `load_generation_job_status(...)` 能读取 job record。
   - `collect_generation_job_output_summary(...)` 在 completed job 下读取 `<output_root>/metadata.json`、`<output_root>/qc.json` 和可选 `<output_root>/qc_review.json`，并返回 `collect_output_summary()` 的结果。
   - job 未完成或输出 artifact 缺失时显式失败。
3. 运行定向测试，确认新增测试在实现前失败，记录失败摘要到报告。
4. 用最小必要改动实现 helper。建议 API 名称：
   - `load_generation_job_status(form_state: dict) -> dict`
   - `run_queued_generation_job(form_state: dict) -> dict`
   - `collect_generation_job_output_summary(form_state: dict, include_qc_review: bool = True) -> dict`
   允许按现有代码微调签名，但必须让 PySide UI 可以直接用表单状态调用。
5. helper 内 job root 规则应与 v0.64.0 创建任务保持一致：`<output_root>/ui_jobs/<generated_id>/job.json`。
6. 输出摘要路径规则应直接、可解释：
   - metadata: `<output_root>/metadata.json`
   - QC: `<output_root>/qc.json`
   - qc_review: `<output_root>/qc_review.json`，不存在时可不包含 review；若传入路径存在但非法，应显式失败。
7. 运行必须的验证命令。
8. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow tests.test_job_runner -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p2-ui-job-flow-helper-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- 新增 API 名称与错误边界。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
