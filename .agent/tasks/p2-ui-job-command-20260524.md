# Worker 子任务：p2-ui-job-command-20260524

## 任务分配

- 任务 ID：`p2-ui-job-command-20260524`
- Orchestrator 会话：`2026-05-24-p2-ui`
- 目标分支：`worker/p2-ui-job-command`
- 目标 worktree：`.worktrees/p2-ui-job-command`
- 必须写入的报告：`.agent/reports/p2-ui-job-command-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

新增非 Qt workflow helper，把 UI form state 转换为 generation config、`he_wsi_generator.cli run-generation` 命令和 local job record，让 PySide6 层保持薄封装。

## 必须先读取的上下文

- `AGENTS.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/DEMANDS.MD`
- `README.md`
- `src/he_wsi_generator/ui/config.py`
- `src/he_wsi_generator/ui/jobs.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_ui.py`
- `tests/test_job_runner.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/ui/workflow.py`
- `src/he_wsi_generator/ui/__init__.py`
- `tests/test_ui_workflow.py`

禁止修改：

- `src/he_wsi_generator/ui/pyside_app.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/config.py`
- `src/he_wsi_generator/ui/jobs.py`
- `src/he_wsi_generator/ui/controller.py`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `README.md`
- `docs/**`
- 除 `tests/test_ui_workflow.py` 外的 `tests/**`

## 约束

- helper 只做数据转换、显式校验和 JobRunner 调用，不引入 Qt 依赖。
- 只支持当前 P2 必需字段，不为未来 GUI 大功能做过度泛化。
- 对非法输入、缺失必填字段、重复 raw label、非法数值范围和 torch backend 缺少 training index 必须显式抛错。
- 不要修改 CLI 参数或 JobRunner 行为；命令必须复用现有 `run-generation` CLI。
- 使用当前版本常量，不要在 worker 中升级版本号。

## 必须执行的工作

1. 确认当前分支为 `worker/p2-ui-job-command`，当前 worktree 为 `.worktrees/p2-ui-job-command`。
2. 新增 `src/he_wsi_generator/ui/workflow.py`，建议提供：
   - `UIWorkflowError(ValueError)`；
   - `build_generation_config_from_form(form_state: dict) -> dict`；
   - `build_run_generation_command(form_state: dict, generation_config_path: str | Path) -> list[str]`；
   - `create_run_generation_job(form_state: dict, job_root: str | Path, generation_config_path: str | Path, cwd: str | Path | None = None) -> dict`。
3. `build_generation_config_from_form()` 从 `DEFAULT_GENERATION_CONFIG` 派生配置，只覆盖 P2 表单字段：random seed、anchor preset、structure anchor、style seed、source WSI id、sample steps、overlap、non-copy QC 开关。
4. `build_run_generation_command()` 生成等价于现有 CLI 的命令：
   - `sys.executable -m he_wsi_generator.cli run-generation <generation_config_path>`;
   - 必须包含 backend、prior manifest、checkpoint manifest、output root、generated id；
   - 可选 condition packet；
   - backend 为 `torch-diffusion-smoke` 时必须包含 training index，否则报错。
5. `create_run_generation_job()` 只创建 queued job record，不同步执行 job。
6. 新增 `tests/test_ui_workflow.py` 覆盖成功路径和错误路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow tests.test_job_runner -v
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p2-ui-job-command-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是 `.worktrees/p2-ui-job-command`。
- 当前分支不是 `worker/p2-ui-job-command`。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
