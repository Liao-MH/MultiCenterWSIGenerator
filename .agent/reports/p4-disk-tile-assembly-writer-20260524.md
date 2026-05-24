# Worker 最终报告：p4-disk-tile-assembly-writer-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p4-disk-tile-assembly-writer-20260524`
- Worker worktree：`.worktrees/p4-disk-tile-assembly-writer-20260524`
- Commit：`8ee5685`

## 摘要

新增 `write_pyramid_ome_tiff_from_tile_sources()`，先复用现有 `.npy` tile source contract 做发布前校验，再按 manifest 中的 level shape、tile origin 和 write region 把磁盘 tile 组装为 pyramid level arrays，最后复用现有 tifffile writer 写出 OME-TIFF。该实现会拒绝 pending/failed tile、缺口、overlap、越界、shape/dtype 不一致和未声明 level shape 的 manifest。报告继续明确 `production_streaming=false`，因为当前仍是内存组装后写出，不是真正逐 tile OME-TIFF streaming writer。

## 影响文件

- `src/he_wsi_generator/outputs/ome_tiff.py`：新增磁盘 tile source 组装写出接口和 coverage 校验 helper。
- `src/he_wsi_generator/outputs/__init__.py`：导出新接口。
- `tests/test_outputs_qc_archive.py`：新增正向组装写出测试和 gap/overlap/bounds/shape/pending 负向测试。

## 验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v` | `通过` | `Ran 25 tests in 0.082s OK` |
| `git diff --check` | `通过` | 无 whitespace error |

## 需求覆盖

- 从磁盘 `.npy` tile source manifest 组装 OME-TIFF：`完成` — `write_pyramid_ome_tiff_from_tile_sources()` 写出两层 OME-TIFF，并验证像素来源。
- coverage gap/overlap/越界显式失败：`完成` — 新增 `test_write_pyramid_ome_tiff_from_tile_sources_rejects_invalid_coverage`。
- shape/dtype/status 契约失败：`完成` — 复用现有 contract gate 并补 shape/pending 组装测试。
- 不宣称 production streaming：`完成` — 返回报告包含 `production_streaming=false`、`assembly_mode=in_memory_disk_tile_assembly` 和 `assembled_in_memory_before_tifffile_write` 限制。

## 风险与备注

- 该接口降低了调用方传完整 pyramid arrays 的要求，但仍会在写出前组装完整 level arrays 到内存中；不能用于声称 production gigapixel streaming writer 已完成。
- 当前只支持无 overlap 的 tile source assembly。带 overlap 的生成 tile 仍需在 generation 层先完成 blending 或另行定义 blending contract。

## 阻塞项

- 无。

## Orchestrator 后续动作

- 需要审查并合并。

## Diff 摘要

```text
 src/he_wsi_generator/outputs/__init__.py |  13 ++-
 src/he_wsi_generator/outputs/ome_tiff.py | 190 +++++++++++++++++++++++++++++++
 tests/test_outputs_qc_archive.py         | 180 ++++++++++++++++++++++++++++-
 3 files changed, 380 insertions(+), 3 deletions(-)
```
