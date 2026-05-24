# Worker 最终报告：p2-ui-job-command-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p2-ui-job-command`
- Worker worktree：`.worktrees/p2-ui-job-command`
- Commit：`00018e9`（本 worker 改动未提交）

## 摘要

新增非 Qt `ui.workflow` helper，把 UI form state 转换为 generation config、现有 `run-generation` CLI 命令和 local queued job record。实现只做数据转换、显式校验和 `JobRunner.create_job()` 调用，不引入 Qt 依赖，不修改 CLI / JobRunner 行为。新增单元测试覆盖成功路径、非法数值、缺失必填字段、重复 raw label、torch backend 缺 training index、queued job 不执行等场景。

## 影响文件

- `src/he_wsi_generator/ui/workflow.py`：新增 `UIWorkflowError`、generation config builder、run-generation 命令 builder、queued job builder 和表单校验。
- `src/he_wsi_generator/ui/__init__.py`：导出 workflow helper。
- `tests/test_ui_workflow.py`：新增 workflow helper 单元测试。

## 验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_ui_workflow tests.test_job_runner -v` | 通过 | `Ran 23 tests in 0.389s`，`OK` |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v` | 通过 | `Ran 2 tests in 0.000s`，`OK` |
| `git diff --check` | 通过 | 无输出，退出码 0 |

备注：验证前执行过 `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`，因为该 conda 环境的 editable install 原先指向主 worktree，导致本 worker 新增模块不可见；重新安装后导入路径指向当前 `.worktrees/p2-ui-job-command/src`。

## 需求覆盖

- 确认 branch / worktree：完成 — 当前路径为 `.worktrees/p2-ui-job-command`，分支为 `worker/p2-ui-job-command`。
- 新增非 Qt workflow helper：完成 — `workflow.py` 只依赖标准库、constants/schema 和 `JobRunner`。
- 从 `DEFAULT_GENERATION_CONFIG` 派生 P2 generation config：完成 — 只覆盖 random seed、anchor preset、structure anchor、style seed、source WSI id、sample steps、overlap、non-copy QC 开关。
- 构建现有 `run-generation` CLI 命令：完成 — 命令形如 `sys.executable -m he_wsi_generator.cli run-generation <config>`，包含 backend、prior manifest、checkpoint manifest、output root、generated id，支持可选 condition packet。
- torch backend training index 校验：完成 — `torch-diffusion-smoke` 缺少 `training_index_path` 时抛 `UIWorkflowError`。
- 创建 local queued job record：完成 — `create_run_generation_job()` 只调用 `JobRunner.create_job()`，不会同步执行 job。
- 错误路径测试：完成 — 覆盖非法数值、缺必填字段、重复 raw label、torch 缺 training index、排队前 generation 字段校验。

## 风险与备注

- helper 采用当前 P2 form key：`prior_manifest_path`、`checkpoint_manifest_path`、`output_root`、`generated_id` 等，并为少量路径字段提供当前 UI 可能使用的别名；后续 PySide 表单 worker 需要与这些 key 对齐。
- 本 worker 不写 generation config 文件，也不执行 generation；实际保存路径和点击运行行为由 PySide 层或 orchestrator 集成。
- 未修改版本号、README 或 docs，符合 worker 禁止范围；版本和共享文档需由 orchestrator 统一收口。

## 阻塞项

- 无。

## Orchestrator 后续动作

- 审查本 worker diff。
- 与 `p2-ui-form-20260524` 的 PySide6 表单改动集成，确认 form key 对齐。
- 统一处理版本号、README、`docs/DEMANDS.MD`、`docs/CHANGELOG.md` 和审计清单更新。

## Diff 摘要

```text
M  src/he_wsi_generator/ui/__init__.py
A  src/he_wsi_generator/ui/workflow.py
A  tests/test_ui_workflow.py

src/he_wsi_generator/ui/__init__.py | 10 insertions
src/he_wsi_generator/ui/workflow.py | 302 lines added
tests/test_ui_workflow.py | 158 lines added
```
