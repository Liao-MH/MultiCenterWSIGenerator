# Worker 最终报告：p4-ome-tiff-streaming-contract-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p4-ome-tiff-streaming-contract-20260524`
- Worker worktree：`.worktrees/p4-ome-tiff-streaming-contract-20260524`
- Commit：`a295a23（未提交改动）`

## 摘要

本任务在 `outputs/ome_tiff.py` 新增了磁盘 `.npy` tile source manifest contract 校验，并把该 contract 接入 `write_pyramid_ome_tiff()` 的写出前检查与返回报告。实现会校验 expected count、level/tile index、tile path、shape、dtype 和 completed 状态，对 pending、failed、missing、duplicate、缺文件、shape/dtype 不一致均显式抛出 `OutputWriteError`。返回字段明确标注 `production_streaming=False`、`partial_contract_only=True`，不把现有 tifffile 内存数组 writer 宣称为 production gigapixel streaming writer。

## 影响文件

- `src/he_wsi_generator/outputs/ome_tiff.py`：新增 `tile_source_manifest` 参数、`validate_disk_tile_source_contract()` helper、contract report 和失败校验逻辑。
- `tests/test_outputs_qc_archive.py`：新增磁盘 tile source contract 的正向/负向测试，并让该定向测试模块优先导入当前 worker worktree 的 `src/`。
- `.agent/reports/p4-ome-tiff-streaming-contract-20260524.md`：记录本 worker 修改、验证、风险和后续动作。

## 验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v` | `通过` | `Ran 23 tests in 0.081s`，`OK` |
| `git diff --check` | `通过` | 命令退出码 0，无 whitespace error 输出 |

## 需求覆盖

- 确认 worktree 路径和 worker 分支：`完成` — `pwd` 与 `git branch --show-current` 均匹配任务要求。
- 读取指定上下文：`完成` — 已读取 `AGENTS.md`、`docs/DEMANDS.MD` 顶部相关需求、审计清单、实施计划、`ome_tiff.py` 和 `tests/test_outputs_qc_archive.py`。
- 编辑前检查现有 writer/audit/tests：`完成` — 确认原实现为 in-memory tifffile pyramid writer，`_chunked_write_audit()` 仅记录 chunk plan audit，原测试只覆盖 smoke、chunk audit 和非法 chunk shape。
- 校验磁盘 tile source manifest/records：`完成` — 覆盖 expected count、level index、tile index、路径存在、`.npy` shape/dtype、completed 状态。
- pending/failed/missing/duplicate 显式失败：`完成` — 新增测试覆盖并由 `OutputWriteError` 抛出。
- contract report 诚实标注限制：`完成` — 返回 `streaming_contract.contract_status=partial_contract_only`、`production_streaming=False`、`partial_contract_only=True` 和 per-level coverage。
- 不实现真正逐 tile OME-TIFF streaming writer：`完成` — 实现只做发布前 contract gate，现有 OME-TIFF 写出仍使用内存数组 writer，并在 report limitations 中说明。

## 风险与备注

- 当前 contract 只支持 `.npy` tile array 文件，以便可靠校验磁盘 shape/dtype；PNG/TIFF tile source 需要后续真实 streaming writer 设计时扩展。
- 当前返回的是 tile source 覆盖报告，不执行 tile-by-tile 写入，也不验证 tile 坐标拼接、overlap blending 或写入后的 OME-TIFF 像素级一致性。
- `tests/test_outputs_qc_archive.py` 现在会优先插入当前 worktree 的 `src/`，避免共享 conda 环境 editable install 指向主工作区时误测旧代码。

## 阻塞项

- 无。

## Orchestrator 后续动作

- 审查并合并本 worker diff。
- 由 orchestrator 统一更新禁止 worker 修改的版本号、README、`docs/CHANGELOG.md`、`docs/DEMANDS.MD` 和 `docs/audit/**`。
- 后续若推进真正 production streaming writer，需要确定非 `.npy` tile format、tile geometry/coordinate schema 和 OME-TIFF incremental write backend。

## Diff 摘要

```text
src/he_wsi_generator/outputs/ome_tiff.py | 303 +++++++++++++++++++++++++++++++
tests/test_outputs_qc_archive.py         | 169 ++++++++++++++++-
2 files changed, 469 insertions(+), 3 deletions(-)

Untracked report file:
.agent/reports/p4-ome-tiff-streaming-contract-20260524.md
```
