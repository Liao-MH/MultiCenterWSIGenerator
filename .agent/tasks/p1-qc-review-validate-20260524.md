# Worker 子任务：p1-qc-review-validate-20260524

## 任务分配

- 任务 ID：`p1-qc-review-validate-20260524`
- Orchestrator 会话：`2026-05-24-codex-worker-orchestration`
- 目标分支：`worker/p1-qc-review-validate`
- 目标 worktree：`.worktrees/p1-qc-review-validate`
- 必须写入的报告：`.agent/reports/p1-qc-review-validate-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## docs/audit 需求依据

- `docs/audit/ACCEPTANCE_CHECKLIST.md` 中 `AC-MISS-07`：`qc_review` 接入通用 `validate` CLI/schema kind 当前缺失。
- `docs/audit/IMPLEMENTATION_PLAN.md` 中 `P1. 契约一致性与文档诚实度`：为 `qc_review` 增加 `he-wsi-gen validate qc-review <path>` 入口。
- 当前主 worktree 有未提交文档/审计迁移改动；本 worker 基于 `HEAD` 创建，任务文件已包含本任务所需审计摘录。不要修改 README、CHANGELOG、DEMANDS 或 audit 文档。

## 目标

为通用 schema validator 和 CLI `validate` 命令新增 `qc-review` 验证入口，复用现有 `src/he_wsi_generator/qc/review.py::validate_qc_review`，并保持非法 review artifact 显式报错。

## 必须先读取的上下文

- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/qc/review.py`
- `tests/test_cli.py`
- `tests/test_qc_review.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_cli.py`
- `tests/test_qc_review.py`
- `.agent/reports/p1-qc-review-validate-20260524.md`

禁止修改：

- `README.md`
- `VERSION`
- `pyproject.toml`
- `src/he_wsi_generator/constants.py`
- `docs/**`
- `configs/**`
- 除上述允许范围外的源码和测试文件

## 约束

- 必须按 TDD：先新增一个失败测试并运行确认失败，再改实现。
- 不要升级版本号；版本与共享文档由 orchestrator 统一处理。
- 避免在 `schemas.py` 顶层导入 `qc.review` 造成循环导入；如果需要接入 `validate_qc_review`，优先在 `validate_file()` 的 `qc-review` 分支内局部导入。
- 支持 `qc-review` 作为 CLI/schema kind；如果支持 `qc_review` 别名，必须保持未知 kind 继续显式失败。
- 不要静默吞掉 `QCReviewError` / `ValidationError`；CLI 失败需要走既有错误输出路径。
- 如果需要扩大修改范围，停止并在报告中说明。

## 必须执行的工作

1. 确认当前分支为 `worker/p1-qc-review-validate`，当前目录为 `.worktrees/p1-qc-review-validate`。
2. 读取必须的上下文文件。
3. 在 `tests/test_cli.py` 或 `tests/test_qc_review.py` 中先写最小失败用例，验证 `he-wsi-gen validate qc-review <path>` 可接受有效 `qc_review`，并且破坏 `artifact_type` 等字段时会失败。
4. 运行新增测试，确认失败原因是当前缺少 `qc-review` schema kind 或 CLI kind。
5. 用最小改动接入 `validate_qc_review`。
6. 运行本任务验证命令。
7. 写入最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
PYTHONPATH=src python -m unittest tests.test_cli tests.test_qc_review -v
PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p1-qc-review-validate-20260524.md`。报告必须包含：

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
