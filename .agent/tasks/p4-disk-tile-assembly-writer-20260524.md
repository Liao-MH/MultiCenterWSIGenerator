# Worker 子任务：p4-disk-tile-assembly-writer-20260524

## 任务分配

- 任务 ID：`p4-disk-tile-assembly-writer-20260524`
- Orchestrator 会话：`2026-05-24-v0.67.0-p4`
- 目标分支：`worker/p4-disk-tile-assembly-writer-20260524`
- 目标 worktree：`.worktrees/p4-disk-tile-assembly-writer-20260524`
- 必须写入的报告：`.agent/reports/p4-disk-tile-assembly-writer-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

在 OME-TIFF 输出层新增从磁盘 `.npy` tile source manifest 组装 pyramid 并写出的接口，校验 tile coverage，不允许 incomplete、overlap、gap、越界或 shape/dtype 不一致的 tile source 被发布。

## 必须先读取的上下文

- `AGENTS.md`
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

禁止修改：

- `src/he_wsi_generator/generation/**`
- `src/he_wsi_generator/models/**`
- `src/he_wsi_generator/priors/**`
- `src/he_wsi_generator/ui/**`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `docs/**`
- `.agent/tasks/**`
- `.agent/reports/**`，但必须写入本任务指定报告
- `tests/*.py` 中除 `tests/test_outputs_qc_archive.py` 以外的文件

## 约束

- 保留与本任务无关的用户改动。
- 不要编辑允许范围之外的文件。
- 不要执行破坏性 git 操作。
- 不要静默忽略错误或验证失败。
- 如果需求互相冲突，停止并在报告中说明冲突。
- 如果实现需要扩大修改范围，停止并报告需要 orchestrator 批准的范围扩展。
- 遵循 TDD：先写最小失败测试并运行确认失败，再改实现。
- 不要把本接口描述为 production gigapixel streaming writer。若实现仍需组装内存数组，报告必须明确 `production_streaming=false` 和限制。

## 必须执行的工作

1. 确认当前分支和 worktree 路径。
2. 读取必须的上下文文件。
3. 在 `tests/test_outputs_qc_archive.py` 先增加失败测试，至少覆盖：
   - 新接口可从 `.npy` tile source manifest 组装两层或多层 OME-TIFF，并保留可审计报告；
   - coverage gap、overlap、越界 tile、shape mismatch、dtype mismatch 或 pending/failed tile 会抛出 `OutputWriteError`。
4. 在 `src/he_wsi_generator/outputs/ome_tiff.py` 新增明确接口，例如 `write_pyramid_ome_tiff_from_tile_sources(tile_source_manifest, output_path, ...)`。
5. 输入 manifest 必须复用或扩展已有 `validate_disk_tile_source_contract()` 契约；记录格式应支持：
   - `levels[].level_index`
   - `levels[].shape`
   - `levels[].expected_tile_count`
   - `tiles[].level_index`
   - `tiles[].tile_index`
   - `tiles[].path`
   - `tiles[].shape`
   - `tiles[].dtype`
   - `tiles[].status == "completed"`
   - `tiles[].tile_origin_40x` 或 `tiles[].tile_origin`
   - 可选 `tiles[].write_region_40x`
6. 组装逻辑只接受无 overlap、无 gap、无越界的 tile 写入区域；对 overlap 或未覆盖像素显式报错。
7. 写出仍可复用现有 `write_pyramid_ome_tiff()`，但返回报告必须新增或更新 `write_mode` / `streaming_contract` / `assembly_report`，明确这是 disk tile source assembly，不是 production streaming writer。
8. `src/he_wsi_generator/outputs/__init__.py` 导出新接口。
9. 运行必须的验证命令。
10. 按要求把最终报告写入指定路径。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p4-disk-tile-assembly-writer-20260524.md`。报告必须包含：

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
- 验证暴露了超出本任务范围的失败。
