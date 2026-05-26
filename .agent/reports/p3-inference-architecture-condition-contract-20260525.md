# Worker 报告：p3-inference-architecture-condition-contract-20260525

## 结论

本轮未启动 multiagent，也未创建 worker worktree。主 orchestrator 直接推进 P3 inference architecture/condition contract gate，作为 v0.72.10 的保守契约增量。

## RED 证据

新增缺失 `model_architecture_contract` 的失败测试后，旧实现没有拒绝缺少模型架构契约的可推理 checkpoint：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_without_model_architecture_contract -v
```

旧实现结果：

```text
AssertionError: ModelRunError not raised
```

## 已做改动

- `src/he_wsi_generator/models/training.py`
  - 新增 `REQUIRED_INFERENCE_CONDITION_INPUTS`。
  - `_validate_inference_checkpoint_contract()` 现在要求 `inference_contract.model_architecture_contract` 和 `inference_contract.condition_input_contract`。
  - `model_architecture_contract` 必须声明 model family、architecture name、input space 和 output space，且 model family 必须匹配项目模型族。
  - `condition_input_contract` 必须覆盖 mask、style seed、texture token、coord、structure anchor、source condition 和 previous scale，并要求 cascade levels 与项目四层级联一致。
- `src/he_wsi_generator/generation/planner.py`
  - generation plan 的每层 `condition_inputs` 现在显式包含 `source_condition` 和 `previous_scale`。
  - `checkpoint_inference_contract` 摘要现在保留 model architecture contract 和 condition input contract。
- `tests/test_models_generation.py`
  - 新增缺失 `model_architecture_contract` 的失败覆盖。
  - 新增缺失必需 condition input 的失败覆盖。
  - 成功路径断言 generation plan 保留架构/条件契约摘要，并且 stage condition inputs 包含 `previous_scale`。
- `tests/test_generation_runner.py`
  - smoke generation runner 的可推理 checkpoint fixture 显式声明模型架构契约和条件输入契约。
- 版本、README、CHANGELOG、audit 文档和测试 fixture 同步到 `v0.72.10`。按用户最新要求，设计文档和开发附录的代码追踪块等整个项目开发完成后再统一补充，本轮不更新。

## 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_without_model_architecture_contract -v`
  - RED：旧实现失败，`AssertionError: ModelRunError not raised`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_without_model_architecture_contract tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_missing_required_condition_input tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_accepts_trained_checkpoint_manifest -v`
  - 通过，`Ran 3 tests in 0.002s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner -v`
  - 通过，`Ran 57 tests in 1.446s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 通过，`Ran 281 tests in 20.749s OK`
- `git diff --check`
  - 通过，无输出
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 通过，editable wheel `multi_center_wsi_generator-0.72.10-0.editable-py3-none-any.whl` 构建并安装
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 输出 `v0.72.10`
- `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - 输出包元数据 `0.72.10`、`PROJECT_VERSION=v0.72.10`、`PACKAGE_VERSION=0.72.10`

## 残余风险与边界

- 本任务只实现 inference architecture/condition JSON contract gate，不实现真实 production latent diffusion / ControlNet / DiT 推理 backend。
- `production_ready=false` 的 smoke/test checkpoint 只声明可审计的 fixture 架构和条件输入，不表示可用于 production generation。
- 该 gate 只能证明 checkpoint manifest 声明了 backend、模型架构和条件输入契约；不会证明 checkpoint 权重质量、模型结构真实可运行性或 OME-TIFF 输出达到 production 级。
