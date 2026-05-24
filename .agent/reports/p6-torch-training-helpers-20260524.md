# Worker 最终报告：p6-torch-training-helpers-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p6-torch-training-helpers`
- Worker worktree：`.worktrees/p6-torch-training-helpers`
- Commit：`未提交`

## 修改摘要

- 新增 `src/he_wsi_generator/models/torch_training_contracts.py`，迁出 PyTorch smoke training 相关的 backend 常量、checkpoint manifest builder、VAE/diffusion checkpoint manifest 和 payload validator、diffusion schedule validator、condition/cross-scale schema helper、denoiser architecture helper。
- 保留 `src/he_wsi_generator/models/torch_training.py` 中的公开训练/采样函数、训练 loop、采样 loop、tensor channel 构造和模型类，只通过导入的内部 helper 复用原有 manifest/schema/validation 逻辑。
- 在 `tests/test_torch_training.py` 新增合约 helper 字段保持测试，固定 condition schema、cross-scale schema 和 denoiser architecture 的关键字段和值。
- 在 `tests/test_torch_training.py` 开头插入当前 worktree 的 `src` 到 `sys.path`，避免本 conda 环境的 editable 安装继续指向主 worktree，确保该测试命令验证当前 worker worktree 的源码。

## 影响文件

- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/torch_training_contracts.py`
- `tests/test_torch_training.py`
- `.agent/reports/p6-torch-training-helpers-20260524.md`

## 行为保持边界

- 未改变 `train_torch_smoke_model`、`train_torch_vae_smoke_model`、`train_torch_diffusion_smoke_model`、`sample_torch_diffusion_smoke_model` 的函数签名。
- 未改变 checkpoint manifest、sample manifest 的字段结构、schema 字段值、training backend 字符串、denoiser architecture 字段或错误文案。
- 未实现 production 模型能力，未扩大训练/采样算法。
- 未修改 CLI、版本文件、README、`docs/**`、配置或其他禁止范围文件。
- `TorchTrainingError` 仍可从 `he_wsi_generator.models.torch_training` 导入；错误消息沿用原字符串。

## 验证命令和结果

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v` | 通过 | 基线阶段：`Ran 22 tests ... OK` |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_torch_training_contract_helpers_preserve_schema_fields -v` | 先失败后通过 | RED：`ImportError: cannot import name 'torch_training_contracts'`；GREEN：`Ran 1 test ... OK` |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v` | 通过 | 修改后：`Ran 23 tests ... OK` |
| `git diff --check` | 通过 | 无输出，退出码 0 |

## 残余风险

- 本 worker 只迁出 manifest/schema/validation 纯 helper；condition packet loader、tensor condition channel 构造、训练/采样 loop 和模型类仍留在 `torch_training.py`，避免一次性扩大重构风险。
- 当前 conda 环境原本的 editable 安装指向主 worktree；测试文件已显式优先使用当前 worktree `src`，但 orchestrator 若在其他环境回收，仍建议确认 `python -c 'import he_wsi_generator; print(he_wsi_generator.__file__)'` 指向预期源码。

## 是否需要 orchestrator 决策

- 不需要。当前改动在允许范围内，未触发停止条件。

## Diff 摘要

```text
src/he_wsi_generator/models/torch_training.py           | helper 逻辑迁出，公开训练/采样流程保留
src/he_wsi_generator/models/torch_training_contracts.py | 新增内部 contracts/helper 模块
tests/test_torch_training.py                            | 新增 helper 合约字段测试，并确保测试导入当前 worktree src
.agent/reports/p6-torch-training-helpers-20260524.md    | 本 worker 报告
```
