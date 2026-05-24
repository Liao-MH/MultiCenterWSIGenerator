# p3-checkpoint-inference-contract-20260525 Worker Report

## 修改摘要

- 在 `src/he_wsi_generator/models/training.py` 中加固 checkpoint manifest 的 inference 可用性契约。
- `usable_for_inference=true` 现在必须满足：
  - `status == "trained"`；
  - `training_backend`、`target_type`、`checkpoint_path`、`checkpoint_sha256` 为非空字符串；
  - `checkpoint_path` 指向存在的文件；
  - `checkpoint_sha256` 与 checkpoint 文件实际 SHA-256 一致；
  - `inference_contract` 为 JSON object，且显式声明 `backend_type`、`artifact_role`、`production_ready`、`limitations`；
  - `production_ready` 不做默认推断，必须由 manifest 显式声明。
- `usable_for_inference=false` 的 skeleton / smoke manifest 继续只走原有基础 schema 校验，不要求 inference contract 字段。
- 更新 `tests/test_models_generation.py` 和 `tests/test_generation_runner.py` 的可推理 checkpoint fixture，写入最小真实 checkpoint 文件、matching SHA-256 和显式非 production inference contract。
- Orchestrator 审查时剔除了 worker worktree 中仅为隔离环境导入而添加的 `sys.path` workaround；主线实现依赖 editable install 和正常包导入路径验证。

## 影响文件

- `src/he_wsi_generator/models/training.py`
- `tests/test_models_generation.py`
- `tests/test_generation_runner.py`
- `.agent/reports/p3-checkpoint-inference-contract-20260525.md`

## RED 测试命令与失败结果摘要

命令：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v
```

失败结果摘要：

- 新增 `test_generation_plan_rejects_thin_inference_checkpoint_manifest` 后，测试失败。
- 失败信息为 `AssertionError: ModelRunError not raised`。
- 该失败证明旧实现允许 `status=trained` 且 `usable_for_inference=true` 但缺少 checkpoint 文件、hash 和 inference contract 的薄 manifest 进入 generation plan。

## GREEN 验证命令与结果

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation -v
```

结果：worker worktree 通过，`Ran 7 tests ... OK`；主线集成后通过，`Ran 12 tests in 0.143s OK`。

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v
```

结果：worker worktree 通过，`Ran 23 tests ... OK`；主线集成后通过，`Ran 23 tests in 1.578s OK`。

```bash
git diff --check
```

结果：worker worktree 和主线集成都通过，无 whitespace/error 输出。

## Orchestrator 审查结论

- 接受核心契约加固实现和 fixture 更新。
- 拒绝把 worker 隔离环境使用的 `sys.path` 导入 workaround 合入主线，避免测试文件承担环境修补逻辑。
- 主线验证以 `MultiCenterWSIGenerator` conda 环境中的 editable install、定向测试、全量单元测试、CLI 版本和包元数据为准。
- 主线最终验证通过：`tests.test_version` 为 `Ran 2 tests in 0.000s OK`，全量 `unittest discover` 为 `Ran 257 tests in 16.210s OK`，editable install 升级到 `multi-center-wsi-generator 0.72.4`，CLI 返回 `v0.72.4`，包元数据/常量为 `0.72.4`、`v0.72.4`、`0.72.4`。

## 残余风险

- 本任务只加固 manifest 入口契约，不实现 production latent diffusion / ControlNet / DiT 模型本体。
- 测试 fixture 的 `production_ready=false` 只表示 contract-ready 的非 production backend；没有把 smoke checkpoint 标记为 production 可推理。
- 当前校验确认 checkpoint 文件存在并匹配 SHA-256，但不解析具体 checkpoint payload 的 production 语义；payload 级语义应由后续 production backend contract 继续定义。

## 阻塞项或需要 Orchestrator 决策的事项

- 无阻塞项。
- 未请求扩大修改范围；未修改 planner/executor 或 torch training 行为。
