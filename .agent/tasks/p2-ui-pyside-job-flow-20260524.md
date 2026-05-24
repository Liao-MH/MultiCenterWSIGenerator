# Worker 子任务：p2-ui-pyside-job-flow-20260524

## 任务分配

- 任务 ID：`p2-ui-pyside-job-flow-20260524`
- Orchestrator 会话：`2026-05-24-v0.65.0-p2-gui-flow`
- 目标分支：`worker/p2-ui-pyside-job-flow`
- 目标 worktree：`.worktrees/p2-ui-pyside-job-flow`
- 必须写入的报告：`.agent/reports/p2-ui-pyside-job-flow-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

把 PySide6 单页配置页升级为可执行/刷新/查看输出的本地 GUI flow：在现有保存配置和创建 queued job 基础上，新增执行 queued job、刷新 job 状态、展示 metadata/QC/qc_review 摘要的控件与测试。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/jobs.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_ui.py`
- `tests/test_ui_workflow.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/ui/pyside_app.py`
- `tests/test_ui.py`
- `.agent/reports/p2-ui-pyside-job-flow-20260524.md`

禁止修改：

- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/jobs.py`
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
- 只把核心业务逻辑委托给 `ui.workflow` / `ui.jobs`，不要把 subprocess 或 artifact schema 校验逻辑写进 Qt 事件处理器。
- 按当前仓库风格保持简单直接，不新增复杂线程/异步系统。本轮允许同步执行 queued job，UI 状态应明确显示运行结果。
- 如果所需 workflow helper 不存在，可在测试中用 `unittest.mock.patch` 描述期望调用形状；不要修改禁止范围内的 helper 文件。

## 必须执行的工作

1. 确认当前分支是 `worker/p2-ui-pyside-job-flow`，当前路径是 `.worktrees/p2-ui-pyside-job-flow`。
2. 先写或扩展失败测试，覆盖至少这些行为：
   - 主窗口暴露 `run_job_button`、`refresh_job_button`、`load_output_summary_button`。
   - 点击执行按钮会调用 workflow helper，并把状态标签更新为 completed/failed。
   - 点击刷新按钮会展示当前 job status/message/record path。
   - 点击输出摘要按钮会展示 generated id、QC status、WSI/mask/metadata/QC 路径和可选 review decision。
   - helper 抛错时状态标签以 `Error:` 开头，且不静默吞错。
3. 运行定向测试，确认新增测试在实现前失败，记录失败摘要到报告。
4. 最小改动实现 UI：
   - 新增按钮对象名建议：`run_job_button`、`refresh_job_button`、`load_output_summary_button`。
   - 新增摘要展示控件对象名建议：`job_status_label`、`output_summary_label`。
   - 使用 `self._form_state()` 作为 helper 输入，保持 v0.64.0 创建任务路径规则。
5. 不要改变 `launch-ui` 入口，不要让 `run-generation` 默认弹 GUI。
6. 运行必须的验证命令。
7. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p2-ui-pyside-job-flow-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- 新增控件对象名。
- 对 helper API 形状的假设。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
