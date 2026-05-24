# Worker 子任务：p1-output-summary-contract-20260524

## 任务分配

- 任务 ID：`p1-output-summary-contract-20260524`
- Orchestrator 会话：`2026-05-24-codex-worker-orchestration`
- 目标分支：`worker/p1-output-summary-contract`
- 目标 worktree：`.worktrees/p1-output-summary-contract`
- 必须写入的报告：`.agent/reports/p1-output-summary-contract-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## docs/audit 需求依据

- `docs/audit/ACCEPTANCE_CHECKLIST.md` 中 `AC-DEV-02`：输出摘要当前对 metadata 只 JSON 读取并宽松取字段，QC/review 校验更严格，契约偏离。
- `docs/audit/IMPLEMENTATION_PLAN.md` 中 `P1. 契约一致性与文档诚实度`：`collect_output_summary()` 需要对 metadata 执行 schema 校验，并校验 metadata/QC/review 的 generated id 一致性。
- 当前主 worktree 有未提交文档/审计迁移改动；本 worker 基于 `HEAD` 创建，任务文件已包含本任务所需审计摘录。不要修改 README、CHANGELOG、DEMANDS 或 audit 文档。

## 目标

收紧 `collect_output_summary()` 的 artifact 契约：metadata 必须通过项目 schema 校验，metadata 与 QC 的 `generated_id` 必须一致，传入 `qc_review` 时 review 的 `generated_id` 也必须与 metadata/QC 一致。

## 必须先读取的上下文

- `src/he_wsi_generator/ui/controller.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/review.py`
- `tests/test_ui.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/ui/controller.py`
- `tests/test_ui.py`
- `.agent/reports/p1-output-summary-contract-20260524.md`

禁止修改：

- `README.md`
- `VERSION`
- `pyproject.toml`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/review.py`
- `docs/**`
- `configs/**`
- 除上述允许范围外的源码和测试文件

## 约束

- 必须按 TDD：先新增失败测试并运行确认失败，再改实现。
- 不要升级版本号；版本与共享文档由 orchestrator 统一处理。
- 只收紧当前输出摘要契约，不扩展新 artifact 类型、不实现数据库、不做 UI 重构。
- metadata JSON fixture 应尽量使用项目现有 `validate_metadata()` 能接受的最小完整结构，而不是让 production code 继续兼容缺字段 metadata。
- 错误必须显式抛出；不要用 silent fallback 从 QC 补 metadata 字段。
- 如果需要扩大修改范围，停止并在报告中说明。

## 必须执行的工作

1. 确认当前分支为 `worker/p1-output-summary-contract`，当前目录为 `.worktrees/p1-output-summary-contract`。
2. 读取必须的上下文文件。
3. 在 `tests/test_ui.py` 中先写最小失败用例，覆盖 metadata/QC `generated_id` 不一致必须失败；如现有测试使用不完整 metadata，先通过测试 fixture/helper 表达完整 metadata contract。
4. 运行新增测试，确认失败原因是当前 `collect_output_summary()` 未校验 metadata/QC id 或 metadata schema。
5. 用最小改动让 `collect_output_summary()` 调用 `validate_metadata()`，并显式检查 metadata/QC/review `generated_id` 一致性。
6. 运行本任务验证命令。
7. 写入最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
PYTHONPATH=src python -m unittest tests.test_ui -v
PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p1-output-summary-contract-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- RED 阶段失败测试命令和失败原因。
- GREEN 阶段验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- 验证暴露了超出本任务范围的失败。
