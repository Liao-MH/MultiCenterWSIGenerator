# Worker 报告：p3-training-objective-contract-20260525

## 结论

本轮未启动 multiagent，也未创建 worker worktree。主 orchestrator 直接推进 P3 training objective/loss/QC mapping contract gate，作为 v0.72.8 的保守契约增量。

## RED 证据

新增缺失 `training_objective_contract` 的失败测试后，旧实现未拒绝缺失训练目标契约的 training config：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_rejects_missing_training_objective_contract -v
```

旧实现结果：

```text
AssertionError: ModelRunError not raised
```

## 已做改动

- `src/he_wsi_generator/models/training.py`
  - 新增 `TRAINING_OBJECTIVE_SCHEMA`、`REQUIRED_TRAINING_OBJECTIVES`、`REQUIRED_OBJECTIVES_BY_STAGE` 和 `REQUIRED_QC_MAPPING`。
  - `create_training_run()` 现在把通过校验的 `training_objective_contract` 写入 `training_run.json`。
  - `_validate_training_config()` 现在要求 `training_objective_contract` 通过 `_validate_training_objective_contract()`。
  - `_validate_training_objective_contract()` 要求五类训练约束、非负 loss weights、阶段目标映射和 QC 指标映射完整一致；缺失或不一致时显式抛出 `ModelRunError`。
  - skeleton checkpoint manifest 现在写入 `training_objective_contract_summary`，但继续保持 `status=not_trained` 与 `usable_for_inference=false`。
- `tests/test_models_generation.py`
  - 成功路径断言 run 和 checkpoint 写入训练目标契约摘要。
  - 新增缺失 training objective contract、缺失 loss weight、缺失阶段映射和 QC 映射不完整的失败覆盖。
- 版本、README、CHANGELOG、audit 文档、设计文档、开发附录和测试 fixture 同步到 `v0.72.8`。

## 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_rejects_missing_training_objective_contract -v`
  - 通过，`Ran 1 test in 0.001s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 通过，`Ran 30 tests in 0.100s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 通过，`Ran 277 tests in 21.053s OK`
- `git diff --check`
  - 通过，无 whitespace error 输出
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 输出 `v0.72.8`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 通过，editable 安装升级到 `multi-center-wsi-generator 0.72.8`
- 包元数据检查：
  - `metadata.version('multi-center-wsi-generator') = 0.72.8`
  - `PROJECT_VERSION = v0.72.8`
  - `PACKAGE_VERSION = 0.72.8`

## 残余风险与边界

- 本任务只实现 training objective/loss/QC mapping contract gate，不实现真实 production latent diffusion / ControlNet / DiT loss 计算或训练 loop。
- `training_objective_contract` 只表示训练目标与 QC 映射已声明并通过当前静态校验，不表示模型已训练、checkpoint 可推理或输出 production-ready。
- skeleton checkpoint 仍不可用于推理；production inference backend、真实 production checkpoint 和 production cascade sampler 仍未完成。
