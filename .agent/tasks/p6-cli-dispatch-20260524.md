# Worker 子任务：p6-cli-dispatch-20260524

## 任务分配

- 任务 ID：`p6-cli-dispatch-20260524`
- Orchestrator 会话：`2026-05-24-v0.65.1-p6-maintainability`
- 目标分支：`worker/p6-cli-dispatch`
- 目标 worktree：`.worktrees/p6-cli-dispatch`
- 必须写入的报告：`.agent/reports/p6-cli-dispatch-20260524.md`
- 派发时状态：`assigned`

## 角色定位

你是一个隔离运行的 Codex worker。只能在指定 git worktree 内执行本任务。除本任务文件和仓库文件外，不要假设自己能访问 orchestrator 的对话上下文。

## 目标

对 `src/he_wsi_generator/cli.py` 做行为保持的维护性收敛：把 `main()` 中的长命令执行分支拆到清晰的 helper/模块，降低单文件后续修改风险，同时保持 `he_wsi_generator.cli:main`、所有 CLI 命令、参数、输出和返回码不变。

## 必须先读取的上下文

- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`
- `docs/DEMANDS.MD`
- `src/he_wsi_generator/cli.py`
- `tests/test_cli.py`
- `tests/test_job_runner.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`

## 修改范围

允许修改：

- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/cli_commands.py`（如需要新增）
- `tests/test_cli.py`
- `tests/test_job_runner.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `.agent/reports/p6-cli-dispatch-20260524.md`

禁止修改：

- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/models/**`
- `docs/**`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/**`
- `src/he_wsi_generator/constants.py`
- `tests/test_version.py`
- 任何未列入允许范围的文件

## 约束

- 这是 patch 版本的行为保持重构，不允许新增、删除或重命名 CLI 命令。
- 不改变 CLI 参数名、choices、默认值、stdout/stderr 文案和返回码，除非现有测试明确要求。
- 保留 `he_wsi_generator.cli:main` 为 console script 入口。
- 不做 unrelated style cleanup，不触碰 torch training 大文件。
- 如果需要扩大修改范围，停止并报告。

## 必须执行的工作

1. 确认当前分支是 `worker/p6-cli-dispatch`，当前路径是 `.worktrees/p6-cli-dispatch`。
2. 读取上下文文件，记录当前 `cli.py` 命令分支结构。
3. 先运行基线验证命令，确认本 worktree 起点测试通过；如失败，停止并报告。
4. 选择最小拆分方式：
   - 推荐新增 `src/he_wsi_generator/cli_commands.py`，把 `main()` 中的命令执行分支迁出为 `run_command(args) -> int` 或等价 helper；
   - `build_parser()` 可留在 `cli.py`，避免一次性大改 parser 构建；
   - `_run_local_job_cli()` 的特殊 `--` 解析保持不变。
5. 如现有测试不足以证明入口不变，可补一个小测试验证 `cli_module.main(["validate", "generation-config", ...])` 仍走同样输出。
6. 运行必须验证命令。
7. 写最终报告。

## 验证命令

在指定 worktree 根目录运行：

```bash
mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_cli tests.test_job_runner tests.test_qc_review tests.test_ui -v
mamba run -n MultiCenterWSIGenerator he-wsi-gen --version
mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json
git diff --check
```

如果某条命令无法运行，必须在报告中记录确切原因。

## 最终报告要求

使用 worker 报告模板写入 `.agent/reports/p6-cli-dispatch-20260524.md`。报告必须包含：

- 修改摘要。
- 影响文件。
- 行为保持边界。
- 验证命令和结果。
- 残余风险。
- 是否需要 orchestrator 决策。

## 停止条件

- 当前 worktree 或分支不符合预期。
- 基线验证失败。
- 需要修改禁止范围内的文件。
- 发现必须改变 CLI 行为才能继续。
