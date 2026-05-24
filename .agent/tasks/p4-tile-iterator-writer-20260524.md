# Worker 子任务：p4-tile-iterator-writer-20260524

## 任务分配

- 任务 ID：`p4-tile-iterator-writer-20260524`
- Orchestrator 会话：`2026-05-24-v0.68.0-p4`
- 目标分支：`worker/p4-tile-iterator-writer-20260524`
- 目标 worktree：`.worktrees/p4-tile-iterator-writer-20260524`
- 必须写入的报告：`.agent/reports/p4-tile-iterator-writer-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

在输出层新增受限但真实的磁盘 tile source OME-TIFF tiled iterator writer：不先组装整幅 level array，而是按 TIFF tile 顺序从磁盘 `.npy` tile 加载并写出 OME-TIFF pyramid。

## 必须先读取的上下文

- `docs/DEMANDS.MD`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `tests/test_outputs_qc_archive.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `tests/test_outputs_qc_archive.py`
- `.agent/reports/p4-tile-iterator-writer-20260524.md`

禁止修改：

- `src/he_wsi_generator/generation/**`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `docs/**`
- 其他 `.agent/tasks/**` 或 `.agent/reports/**`

## 约束

- 先写失败测试，再写生产代码；报告中记录红灯命令和失败原因。
- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 不把当前实现夸大为中断后可恢复写同一个 OME-TIFF 文件。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_outputs_qc_archive.py` 增加失败测试，覆盖 tiled iterator writer 写出、报告字段和非法 tile grid/coverage 失败。
4. 在 `src/he_wsi_generator/outputs/ome_tiff.py` 新增公开函数，建议命名为 `write_pyramid_ome_tiff_streaming_from_tile_sources()`。
5. 新 writer 必须复用现有 `.npy` tile source contract，并额外校验每层 `shape`、`tile_origin_40x` / `write_region_40x`、无 overlap、无 gap、无越界、tile grid 与 `chunk_shape` 对齐；只接受 `uint8` 2D/RGB/RGBA tile。
6. 写出时使用 `tifffile.TiffWriter.write(data=<iterator>, shape=..., dtype=..., tile=..., subifds=...)`；不要分配完整 level array。
7. 返回报告必须包含 `write_mode=tile_iterator_streaming_write`、`production_streaming=true`、`resume_capable=false`、tile grid/coverage 信息和 limitation。
8. 在 `src/he_wsi_generator/outputs/__init__.py` 导出新函数。
9. 运行必须验证命令。
10. 按要求写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-tile-iterator-writer-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 验证命令和结果。
- 残余风险。
- 阻塞项或需要 orchestrator 决策的事项。

## 停止条件

遇到以下情况时停止，不要继续实现：

- 当前 worktree 不是预期路径。
- 当前分支不是预期 worker 分支。
- 必须读取的上下文文件不存在。
- 任务需要修改禁止范围内的文件。
- `tifffile` 当前版本无法用 iterator + tile 写出多层 OME-TIFF。
- 验证暴露了超出本任务范围的失败。
