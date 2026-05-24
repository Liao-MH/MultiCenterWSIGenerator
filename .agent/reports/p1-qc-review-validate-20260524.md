# Worker Report: p1-qc-review-validate-20260524

## 修改摘要

- 为通用 `validate` CLI 增加 `qc-review` schema kind。
- 在 `src/he_wsi_generator/schemas.py::validate_file()` 中为 `qc-review` 局部导入并复用 `validate_qc_review()`，避免在模块顶层导入 `qc.review` 造成循环导入风险。
- 在 CLI `validate` 分支中将 `QCReviewError` 纳入既有 stderr + exit 1 错误输出路径，非法 qc_review artifact 不会以 traceback 形式泄漏。
- 新增 CLI 回归测试，覆盖有效 `qc_review` artifact 可通过 `he-wsi-gen validate qc-review <path>`，以及篡改 `artifact_type` 时显式失败。

## 影响文件

- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_qc_review.py`
- `.agent/reports/p1-qc-review-validate-20260524.md`

## RED 阶段

命令：

```bash
PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_cli_accepts_qc_review_artifact tests.test_qc_review.QCReviewTests.test_validate_cli_rejects_invalid_qc_review_artifact_type -v
```

结果：失败，符合预期。

失败原因：

- `test_validate_cli_accepts_qc_review_artifact` 返回码为 `2`，stderr 显示 `argument kind: invalid choice: 'qc-review'`。
- `test_validate_cli_rejects_invalid_qc_review_artifact_type` 未能看到 `artifact_type` 错误，因为 CLI parser 在进入 schema validator 前拒绝了 `qc-review` kind。

## GREEN 阶段

新增测试回跑：

```bash
PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_cli_accepts_qc_review_artifact tests.test_qc_review.QCReviewTests.test_validate_cli_rejects_invalid_qc_review_artifact_type -v
```

结果：通过，`Ran 2 tests ... OK`。

任务指定验证命令：

```bash
PYTHONPATH=src python -m unittest tests.test_cli tests.test_qc_review -v
```

结果：通过，`Ran 12 tests ... OK`。

```bash
PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json
```

结果：通过，输出 `generation-config valid: configs/generation.default.json`。

```bash
git diff --check
```

结果：通过，无输出。

## 残余风险

- 本任务仅按要求支持 `qc-review`，未增加 `qc_review` 下划线别名；未知 kind 仍由 argparse 或 `validate_file()` 显式失败。
- `qc-review` 的具体字段契约继续由现有 `validate_qc_review()` 维护，本次未扩展 review artifact schema。

## 阻塞项或需 Orchestrator 决策事项

- 无阻塞项。
- 未修改 README、CHANGELOG、DEMANDS、audit 文档、版本文件或配置文件；版本与共享文档仍由 orchestrator 统一处理。
