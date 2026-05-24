# Worker 最终报告：p4-streaming-writer-pyramid-contract-20260524

## 状态

- 结果：`完成`
- Worker 分支：`worker/p4-streaming-writer-pyramid-contract-20260524`
- Worker worktree：`.worktrees/p4-streaming-writer-pyramid-contract-20260524`
- Commit：`未提交，等待 orchestrator 审查与集成`

## 修改摘要

加固 `write_pyramid_ome_tiff_streaming_from_tile_sources()` 的 pyramid level 契约：streaming plan 现在按 manifest `levels` 的声明顺序形成 OME-TIFF pyramid，并要求该顺序必须是 high-to-low resolution。任一 streaming level 缺少 `shape`、重复 `level_index`，或后续 level 的 height/width 大于前一层，都会显式抛出 `OutputWriteError`，不会通过排序或 fallback 掩盖 manifest 问题。

`streaming_write_report` 现在明确记录 `pyramid_order=high_to_low_resolution`、`level_order` 和每层 `pyramid_position`。报告继续保留 `resume_capable=false` 与 `ome_tiff_file_resume_not_supported`，不把 writer 描述成可中断续写同一个 OME-TIFF 文件。

## 影响文件

- `src/he_wsi_generator/outputs/ome_tiff.py`：新增 streaming manifest level 顺序/shape 校验；streaming report 和 contract 增加 pyramid order 字段。
- `tests/test_outputs_qc_archive.py`：新增低到高 level 顺序失败测试、缺失 level shape 失败测试；扩展正向 streaming 写出报告断言。
- `.agent/reports/p4-streaming-writer-pyramid-contract-20260524.md`：记录本 worker 修改、验证和残余风险。

## 验证命令和结果

| 命令 | 结果 | 证据 |
|---|---|---|
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v` | 红灯符合预期 | 写生产代码前运行，`Ran 29 tests`，失败原因：缺少 `streaming_write_report.pyramid_order`、低到高 level order 未抛错、缺失 level shape 的错误消息未指向 shape。 |
| `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v` | 通过 | 实现后运行，`Ran 29 tests in 0.089s OK`。 |
| `git diff --check` | 通过 | 无 whitespace error 输出。 |

## 需求覆盖

- 非法 pyramid 顺序显式失败：`完成`，后续 level 的 height/width 大于前一层时抛出 `OutputWriteError`，错误消息包含 `pyramid level order`。
- 缺失 level shape 显式失败：`完成`，streaming manifest 任一 level 缺少 `shape` 会抛出 `OutputWriteError`。
- streaming report 顺序字段：`完成`，`streaming_write_report` 包含 `pyramid_order`、`level_order` 和每层 `pyramid_position`。
- 不可恢复写入限制：`完成`，报告继续保留 `resume_capable=false` 和 `ome_tiff_file_resume_not_supported`；当前 writer 不支持中断后续写同一个 OME-TIFF 文件。
- 禁止范围：`完成`，未修改 `generation/**`、CLI、配置、README、VERSION、pyproject 或 `docs/**`。

## 残余风险

- 当前改动只加固输出层 streaming writer 的 manifest 契约；production backend、多层 tile source 生成和可恢复 OME-TIFF 文件级续写仍不在本 worker 范围内。
- Streaming writer 仍要求完整 tile source manifest 先存在，再一次性写出目标 OME-TIFF；中断后需要重新发起写出，不支持续写同一个目标文件。

## 阻塞项或需要 orchestrator 决策的事项

- 无阻塞项。
- 共享文档、版本号、README 和审计清单按任务说明由 orchestrator 统一更新，本 worker 未修改。
