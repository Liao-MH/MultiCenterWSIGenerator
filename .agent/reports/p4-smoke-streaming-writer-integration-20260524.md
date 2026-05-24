# Worker 最终报告：p4-smoke-streaming-writer-integration-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p4-smoke-streaming-writer-integration-20260524`
- Worker worktree：`.worktrees/p4-smoke-streaming-writer-integration-20260524`
- Commit：`未提交`

## 摘要

`run-generation --backend smoke-cascade` 新增显式 `--wsi-writer` 选择，默认 `array` 保持原有 in-memory pyramid 写出路径，`tile-streaming` 使用输出层 `write_pyramid_ome_tiff_streaming_from_tile_sources()`。torch diffusion smoke backend 对 `--wsi-writer tile-streaming` 显式失败。smoke tile source manifest 的 level0 `levels[]` 现在记录 shape，以满足 streaming writer 的覆盖校验。

## 影响文件

- `src/he_wsi_generator/generation/executor.py`：新增 `wsi_writer` 参数、writer 选择分支、metadata 中的 writer 记录和 tile source level shape。
- `src/he_wsi_generator/cli.py`：新增 `run-generation --wsi-writer {array,tile-streaming}`。
- `src/he_wsi_generator/cli_commands.py`：传递 writer 参数，并拒绝 torch backend 使用 tile streaming writer。
- `tests/test_generation_runner.py`：覆盖 smoke CLI tile streaming writer 和 torch 拒绝路径，更新 tile source manifest shape 断言。

## 验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer tests.test_generation_runner.GenerationRunnerTests.test_cli_rejects_tile_streaming_writer_for_torch_diffusion_smoke -v` | 通过 | 初始红灯为 CLI 尚未支持参数；实现后 `Ran 2 tests in 0.175s OK` |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner -v` | 通过 | `Ran 20 tests in 1.284s OK` |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_tiling tests.test_generation_runner -v` | 通过 | `Ran 31 tests in 1.309s OK` |
| `git diff --check` | 通过 | 无 whitespace error 输出 |

## 需求覆盖

- smoke-cascade 显式接入 tile streaming writer：`完成` — CLI `--wsi-writer tile-streaming` 生成 run summary，`pyramid_report.write_mode=tile_iterator_streaming_write`。
- 默认行为保持：`完成` — 既有 smoke generation 测试仍断言默认 `chunked_pyramid_write` 并通过。
- torch backend 拒绝：`完成` — `torch-diffusion-smoke` 搭配 `--wsi-writer tile-streaming` 返回错误。
- metadata / summary 记录：`完成` — metadata `generation.wsi_writer` 和 run summary `pyramid_report` 记录 writer 选择及 streaming 报告。

## 风险与备注

- 当前 smoke tile source manifest 仍只覆盖 level0；`tile-streaming` 路径生成单层 OME-TIFF，而默认 array writer 仍生成四层 pyramid。该限制需要 orchestrator 在复审计中保留，后续如需完整多层 streaming，应让 generation 生成每个 cascade level 的 tile source manifest。
- `tile-streaming` 不支持 torch backend，也不支持中断后续写同一个 OME-TIFF 文件。

## 阻塞项

- 无。

## Orchestrator 后续动作

- 需要审查、合并，并统一同步 v0.68.0 版本、README、CHANGELOG 和 `docs/audit/`。

## Diff 摘要

```text
 src/he_wsi_generator/cli.py                 |  9 +++
 src/he_wsi_generator/cli_commands.py        |  5 ++
 src/he_wsi_generator/generation/executor.py | 51 +++++++++++----
 tests/test_generation_runner.py             | 98 ++++++++++++++++++++++++++++-
 4 files changed, 150 insertions(+), 13 deletions(-)
```
