# Worker 报告：p3-backend-compatibility-contract-20260525

## 结论

本轮未启动 multiagent，也未创建 worker worktree。主 orchestrator 直接推进 P3 checkpoint/backend compatibility contract gate，作为 v0.72.9 的保守契约增量。

## RED 证据

新增缺失 `compatible_generation_backends` 的失败测试后，旧实现没有拒绝缺少 backend compatibility 声明的可推理 checkpoint：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_rejects_checkpoint_without_compatible_generation_backend -v
```

旧实现结果：

```text
AssertionError: ModelRunError not raised
```

## 已做改动

- `src/he_wsi_generator/models/training.py`
  - `_validate_inference_checkpoint_contract()` 现在要求 `inference_contract.compatible_generation_backends` 为非空字符串列表。
  - 该校验只作用于 `usable_for_inference=true` checkpoint；skeleton / smoke training checkpoint 仍可保持 `usable_for_inference=false`。
- `src/he_wsi_generator/generation/planner.py`
  - 新增 `DEFAULT_GENERATION_BACKEND = "smoke-cascade"`。
  - `create_generation_plan()` 现在按当前 `generation_backend` 校验 checkpoint `compatible_generation_backends`，并把 `generation_backend` 与 `checkpoint_inference_contract` 摘要写入 generation plan。
- `tests/test_models_generation.py`
  - 新增缺失 `compatible_generation_backends` 的失败覆盖。
  - 新增 checkpoint 兼容列表不包含当前 generation backend 的失败覆盖。
  - 成功路径断言 generation plan 写入 `generation_backend` 和 checkpoint inference contract 摘要。
- `tests/test_generation_runner.py`
  - smoke generation runner 的可推理 checkpoint fixture 显式声明 `compatible_generation_backends=["smoke-cascade"]`。
- 版本、README、CHANGELOG、audit 文档、设计文档、开发附录和测试 fixture 同步到 `v0.72.9`。

## 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner -v`
  - 通过，`Ran 55 tests in 1.516s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 通过，`Ran 279 tests in 17.022s OK`
- `git diff --check`
  - 通过，无 whitespace error 输出
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 输出 `v0.72.9`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 通过，editable 安装升级到 `multi-center-wsi-generator 0.72.9`
- 包元数据检查：
  - `metadata.version('multi-center-wsi-generator') = 0.72.9`
  - `PROJECT_VERSION = v0.72.9`
  - `PACKAGE_VERSION = 0.72.9`

## 残余风险与边界

- 本任务只实现 checkpoint/backend compatibility JSON contract gate，不实现真实 production latent diffusion / ControlNet / DiT 推理 backend。
- `production_ready=false` 的 smoke/test checkpoint 只允许被 `smoke-cascade` 测试路径消费，不表示可用于 production generation。
- compatibility gate 防止 checkpoint 被错误 backend 消费，但不会证明 checkpoint 权重质量、模型结构兼容性或 OME-TIFF 输出达到 production 级。
