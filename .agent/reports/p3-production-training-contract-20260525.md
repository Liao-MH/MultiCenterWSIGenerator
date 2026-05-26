# Worker 报告：p3-production-training-contract-20260525

## 结论

worker 已派发到 `.worktrees/p3-production-training-contract-20260525`，但长时间停滞在上下文读取阶段，未生成实现 diff，也未写出最终报告。orchestrator 审查日志和 worktree 状态后接管实现、验证、文档同步和复审计。

当前报告已在 v0.72.7 追加本轮 P3 training index evidence contract：在 v0.72.6 production training dataset contract gate 基础上，`init-training-run` 现在读取并核对实际 `training_index_path` JSONL，避免只靠手写 `dataset_contract` 汇总字段通过训练数据覆盖检查。

## Worker 审查

- 任务文件：`.agent/tasks/p3-production-training-contract-20260525.md`
- worker worktree：`.worktrees/p3-production-training-contract-20260525`
- worker branch：`worker/p3-production-training-contract-20260525`
- 日志：`.agent/logs/p3-production-training-contract-20260525.jsonl`
- 审查结论：worker 日志末尾停在读取版本测试附近；`git -C .worktrees/p3-production-training-contract-20260525 status --short` 与 diff 审查未发现可集成实现。

## RED 证据

新增缺失 dataset contract 的失败测试后，旧实现未拒绝不完整 training config：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation.ModelGenerationSkeletonTests.test_create_training_run_rejects_missing_dataset_contract -v
```

旧实现结果：

```text
AssertionError: ModelRunError not raised
```

v0.72.7 追加 actual training index mismatch RED evidence：新增 `test_create_training_run_rejects_dataset_contract_sample_count_mismatch_with_index` 后，旧实现不会读取实际 training index JSONL，结果为：

```text
AssertionError: ModelRunError not raised
```

## 已做改动

- `src/he_wsi_generator/models/training.py`
  - 新增 `PRODUCTION_TRAINING_BACKEND`、`PRODUCTION_TARGET_TYPE` 和必需 dataset condition inputs。
  - `create_training_run()` 现在把通过校验的 `training_backend` 与 `dataset_contract` 写入 training run manifest。
  - skeleton checkpoint manifest 记录 `training_backend`、`target_type` 和 `dataset_contract_summary`，但继续保持 `status=not_trained` 与 `usable_for_inference=false`。
  - `_validate_training_config()` 要求 `training_backend=latent_diffusion_unet`，并调用 `_validate_dataset_contract()`。
  - `_validate_dataset_contract()` 显式校验 training index path、production readiness、最小样本数、样本数、train split、四层 cascade 记录数、必需条件输入和 6 类 `integer_index` mask schema。
  - v0.72.7 进一步读取实际 `training_index_path` JSONL，要求文件存在、非空、逐行 JSON object，record `schema_version` 匹配当前项目版本，并核对实际 record 数、split 计数、cascade level 计数、tile 坐标、conditioning 证据和 mask class mapping。
- `src/he_wsi_generator/models/training_index.py`
  - `build_training_index()` 生成的 record 现在写入 `conditioning.texture_token_source`，使项目自身 training index 输出满足 v0.72.7 evidence gate。
- `tests/test_models_generation.py`
  - 成功路径断言 run/checkpoint 写入 training backend 与 dataset contract summary。
  - 新增缺失 dataset contract、缺 cascade level、样本数不足、mask schema mismatch、unsupported backend、training index mismatch、readiness 缺失、缺必需条件输入和缺 train split 的失败覆盖。
  - v0.72.7 新增 actual training index mismatch 覆盖：sample_count mismatch、split mismatch、conditioning evidence 缺失和 mask mapping mismatch。
- `tests/test_training_index.py`
  - 新增断言，验证 `build_training_index()` 输出包含 `texture_token_source`。
- 版本、README、CHANGELOG、audit 文档和测试 fixture 同步到 `v0.72.7`。

## 验证结果

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v`
  - 通过，`Ran 26 tests in 0.210s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_training_index -v`
  - 通过，`Ran 3 tests in 0.042s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - 通过，`Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 通过，`Ran 273 tests in 20.181s OK`
- `git diff --check`
  - 通过，无 whitespace error
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - 通过，editable 安装升级到 `multi-center-wsi-generator 0.72.7`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 返回 `v0.72.7`
- 包元数据 / 常量检查
  - 返回 `0.72.7`、`v0.72.7`、`0.72.7`

## 残余风险与边界

- 本任务只实现 production training dataset contract 与 training index JSONL 证据核对 gate，不实现真实 production latent diffusion / ControlNet / DiT 训练 loop。
- `dataset_contract.production_readiness_declared=true` 只表示训练数据契约字段已声明并通过当前静态校验，不表示模型已训练或 checkpoint 可推理。
- skeleton checkpoint 仍不可用于推理；production inference backend、真实 production checkpoint 和 production cascade sampler 仍未完成。
- production prior、style encoder、texture codebook、VQ-VAE、production OME-TIFF writer 和可恢复 OME-TIFF 逐 tile 写入仍是后续缺口。
