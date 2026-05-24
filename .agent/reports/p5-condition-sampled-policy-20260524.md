# Worker 最终报告：p5-condition-sampled-policy-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p5-condition-sampled-policy-20260524`
- Worker worktree：`.worktrees/p5-condition-sampled-policy-20260524`
- Commit：`53badad`（最终 worker 提交，包含本报告和 source path consistency 补充校验）。

## 摘要

新增 `build_generation_condition_packet()` 的可选 sampled style/texture policy 输入，并让 `build-condition-packet` CLI 支持 `--sampled-style-policy` 和 `--sampled-texture-policy`。condition packet 现在会在 `artifact_inputs` 和 `conditions.style_seed` / `conditions.texture_token` 中记录 policy artifact 的 sample id、seed、selection policy、selected style/token 摘要和非 production limitation。未提供 sampled policy 时，既有 style seed 和 texture prototype 选择逻辑保持不变。

## 影响文件

- `src/he_wsi_generator/generation/conditioning.py`：新增 sampled style/texture policy JSON 读取、校验、artifact input 记录和条件摘要覆盖。
- `src/he_wsi_generator/cli.py`：为 `build-condition-packet` 新增 `--sampled-style-policy` / `--sampled-texture-policy` 参数。
- `src/he_wsi_generator/cli_commands.py`：把 CLI 参数传入 condition packet builder。
- `tests/test_generation_conditioning.py`：新增 sampled policy API/CLI 正向用例和非法 artifact type、版本不匹配、缺失关键字段显式失败用例。

## 验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning -v` | 红灯符合预期 | 写生产代码前运行，`Ran 10 tests`，失败原因包括 `build_generation_condition_packet() got an unexpected keyword argument 'sampled_style_policy_path'`，CLI 子进程未写出 condition packet。 |
| `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'` | 通过 | 将 conda editable install 临时指向本 worker worktree，避免直接 API 测试仍导入主 worktree旧代码。 |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_conditioning -v` | 通过 | `Ran 10 tests in 0.088s OK`；审查后补充 source prior path consistency 校验再次复跑，`Ran 10 tests in 0.082s OK`。 |
| `git diff --check` | 通过 | 无 whitespace error 输出。 |

## 需求覆盖

- sampled style policy 接入 condition packet：`完成` — `artifact_inputs.sampled_style_policy` 与 `conditions.style_seed.source=sampled_style_policy` 记录 path、sample id、seed、selection policy、selected style 和 RGB reference。
- sampled texture policy 接入 condition packet：`完成` — `artifact_inputs.sampled_texture_policy` 与 `conditions.texture_token.source=sampled_texture_policy` 记录 path、sample id、seed、selection policy、cluster id、representative embedding index 和 embedding 摘要。
- CLI 接入：`完成` — `build-condition-packet` 支持 `--sampled-style-policy` / `--sampled-texture-policy`。
- 显式失败：`完成` — artifact type 错误、schema version 不匹配、sampled policy source prior path 不匹配、缺失 representative embedding index 均抛出 `GenerationConditionError`。

## 风险与备注

- 当前只是让 condition packet 审计消费 sampled policy artifact，不自动调用 sampler，也不改变 smoke/torch backend 的条件特征编码方式。
- sampled policy 仍是统计型 deterministic artifact，不是 production style encoder、texture codebook、VQ-VAE 或 morphology token generator。
- worker 验证期间将 conda editable install 指向本 worktree；orchestrator 合并后需要重新安装主 worktree。

## 阻塞项

- 无。

## Orchestrator 后续动作

- 审查 diff、合并 worker 分支，并统一同步版本号、README、`docs/audit/` 与 `docs/CHANGELOG.md`。

## Diff 摘要

```text
 src/he_wsi_generator/cli.py                     |   8 +
 src/he_wsi_generator/cli_commands.py            |   2 +
 src/he_wsi_generator/generation/conditioning.py | 203 +++++++++++++++++++++++-
 tests/test_generation_conditioning.py           | 194 ++++++++++++++++++++++
 4 files changed, 406 insertions(+), 1 deletion(-)
```
