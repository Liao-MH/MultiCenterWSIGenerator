# CHANGELOG

## Audit Snapshot - 2026-05-24（v0.63.0 conda 环境验证）

### 用户需求

- 用户要求创建独立 conda 环境 `MultiCenterWSIGenerator`，安装全部项目依赖，包括 PyTorch。
- 用户要求基于该环境继续循环使用 `codex-worker-orchestration` 与 `project-remediation-audit`，完成 `docs/audit/` 中显示的未完成开发。

### 已做改动

- 创建 conda 环境 `MultiCenterWSIGenerator`，并通过 `pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'` 安装完整可选依赖集合。
- 确认该环境中的 Python、OpenSlide、PySide6、PyTorch/CUDA 和项目 CLI 可用。
- 在新环境中重新执行 PyTorch/UI 定向测试和全量单元测试，消除前一轮“当前环境缺少 torch/PySide6”的未验证项。
- 更新 `docs/DEMANDS.MD`、`docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/IMPLEMENTATION_PLAN.md`、`docs/audit/DECISIONS.md` 和 README 的环境化验证说明。
- 将 v0.63.0 工作区收口为 `main` 分支基线提交，便于后续 worker worktree 从正确版本启动；尚未 tag 或打包发布。
- 未修改 `src/`、`tests/`、`configs/` 运行时代码，未升级版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `mamba create -y -n MultiCenterWSIGenerator -c conda-forge python=3.11 pip openslide`
  - 结果：环境创建成功。
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e '.[embeddings,outputs,training,torch,ui,yaml,wsi]'`
  - 结果：完整可选依赖安装成功。
- `mamba run -n MultiCenterWSIGenerator python -c 'import torch, PySide6, openslide, yaml, tifffile, PIL, numpy'`
  - 结果：导入成功；Python `3.11.15`，PyTorch `2.12.0+cu130`，CUDA 可用，GPU 为 `NVIDIA GeForce RTX 5060 Ti`。
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - 结果：`v0.63.0`。
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training tests.test_ui -v`
  - 结果：通过，`Ran 39 tests ... OK`。
- `QT_QPA_PLATFORM=offscreen mamba run -n MultiCenterWSIGenerator python - <<'PY' ... create_main_window() ... PY`
  - 结果：窗口标题为 `MultiCenterWSIGenerator`，central widget 存在，widget count 为 `88`；该结果只证明当前 PySide6 依赖和窗口创建可用，不代表真实交互式配置页已完成。
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 191 tests in 19.932s OK`。
- `git status --short`
  - 结果：v0.63.0 基线提交后主工作区干净。
- `git log -1 --oneline`
  - 结果：最新提交信息包含版本号 `v0.63.0 contract remediation and env audit`。

## Audit Snapshot - 2026-05-24（v0.63.0 复审计）

### 用户需求

- 用户显式调用 `project-remediation-audit`，要求基于当前仓库状态进行补救审计。
- 本轮只做审计和审计工件维护，不开始新的实现修复。

### 已做改动

- 更新 `docs/DEMANDS.MD`，新增本轮 v0.63.0 复审计需求。
- 更新 `docs/audit/ACCEPTANCE_CHECKLIST.md`，补充当前工作区状态、未提交/未 tag 风险、worker worktree 遗留状态和本轮验证结果。
- 更新 `docs/audit/IMPLEMENTATION_PLAN.md`，新增 P0.5 交付收口任务包。
- 更新 `docs/audit/DECISIONS.md`，记录当前 v0.63.0 仍是未提交工作区状态，不能表述为已发布 release。
- 未修改 `src/`、`tests/`、`configs/` 运行时代码，未升级版本号。

### 影响文件

- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `git status --short`
  - 结果：当前 `v0.63.0` 仍是未提交工作区状态，包含版本、代码、测试、README、`.agent/` 和 `docs/audit/` 改动；旧根目录审计文件在 git 状态中显示为删除，新 `docs/audit/` 显示为未跟踪。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：通过，`Ran 191 tests ... OK (skipped=21)`；跳过项均为当前环境缺少 PyTorch 的 torch smoke 测试。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.63.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- `python -c` 导入依赖检查：
  - 结果：当前环境缺少 `torch` 与 `PySide6`，因此 PyTorch smoke 路径和真实 PySide6 GUI 启动仍未验证。

## v0.63.0 - 2026-05-24

### 用户需求

- 用户要求根据 `docs/audit/` 中的审计内容继续开发，并使用 `codex-worker-orchestration` 进行并行 worker 编排。
- 本轮选择 P1“契约一致性与文档诚实度”作为补救批次。

### 已做改动

- 版本号升级到 `v0.63.0`。
- 创建 worker 任务文件：
  - `.agent/tasks/p1-qc-review-validate-20260524.md`
  - `.agent/tasks/p1-output-summary-contract-20260524.md`
- 创建并派发两个 worker worktree：
  - `.worktrees/p1-qc-review-validate` / `worker/p1-qc-review-validate`
  - `.worktrees/p1-output-summary-contract` / `worker/p1-output-summary-contract`
- 回收 worker 报告：
  - `.agent/reports/p1-qc-review-validate-20260524.md`
  - `.agent/reports/p1-output-summary-contract-20260524.md`
- `he-wsi-gen validate` 新增 `qc-review` schema kind，并复用现有 `validate_qc_review()`；非法 `qc_review` artifact 会走 CLI 明确错误输出。
- `collect_output_summary()` 现在对 metadata 执行 schema 校验，并显式校验 metadata/QC/可选 `qc_review` 的 `generated_id` 一致性。
- 新增仓库实体 `AGENTS.md`，固化本仓库工作规则。
- 更新 README 的当前版本、schema kind 列表、输出摘要契约说明、M5/M7 里程碑边界和当前边界说明。
- 更新 `docs/audit/`，把已解决的 P1 项从“缺失/偏离”调整为“已完成”，并保留未完成项。

### 影响文件

- `AGENTS.md`
- `.agent/tasks/p1-qc-review-validate-20260524.md`
- `.agent/tasks/p1-output-summary-contract-20260524.md`
- `.agent/reports/p1-qc-review-validate-20260524.md`
- `.agent/reports/p1-output-summary-contract-20260524.md`
- `.gitignore`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/*.py`（版本字符串同步到 `v0.63.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- Worker `p1-qc-review-validate`：
  - RED：`PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_cli_accepts_qc_review_artifact tests.test_qc_review.QCReviewTests.test_validate_cli_rejects_invalid_qc_review_artifact_type -v` 初次失败于 `qc-review` 不是 CLI valid choice。
  - GREEN：`PYTHONPATH=src python -m unittest tests.test_cli tests.test_qc_review -v` 通过，`Ran 12 tests ... OK`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json` 通过。
  - `git diff --check` 通过。
- Worker `p1-output-summary-contract`：
  - RED：`PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_collect_output_summary_rejects_invalid_metadata_contract tests.test_ui.UITests.test_collect_output_summary_rejects_metadata_qc_generated_id_mismatch -v` 初次失败于未校验 metadata schema 和 generated id mismatch。
  - GREEN：`PYTHONPATH=src python -m unittest tests.test_ui -v` 通过，`Ran 17 tests ... OK`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json` 通过。
  - `git diff --check` 通过。
- Orchestrator 复核：
  - 已重新检查两个 worker 的 report、`git status --short` 和 diff，并在各自 worktree 重新运行关键验证。
  - `PYTHONPATH=src python -m unittest discover -s tests -v`
    - 结果：通过，`Ran 191 tests ... OK (skipped=21)`；跳过项均为当前环境缺少 PyTorch 的 torch smoke 测试。
  - `PYTHONPATH=src python -m he_wsi_generator.cli --version`
    - 结果：`v0.63.0`。
  - `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
    - 结果：`generation-config valid: configs/generation.default.json`。
  - `git diff --check`
    - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（One-time Parallel Developer 整合 Skill）

### 用户需求

- 用户认为“每循环一个问题”会降低并行效率，确认循环粒度应改为“一个补救主题或优先级批次”，批次内部并行派发多个 worker。
- 用户要求将 `codex-worker-orchestration` 和 `project-remediation-audit` 整合到一个 `one-time-parallel-developer` 大 skill 中。
- 用户要求同时确保 `codex-worker-orchestration` 和 `project-remediation-audit` 仍然可以被单独调用。

### 已做改动

- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/one-time-parallel-developer`。
- `one-time-parallel-developer` 定义完整闭环：`Audit -> Batch -> Task -> Worker -> Review -> Merge -> Re-audit -> Repeat/Stop`。
- `one-time-parallel-developer` 明确循环粒度为一个补救主题或优先级批次，每批建议 2-5 个可并行 worker。
- `one-time-parallel-developer` 明确了适合并行、不适合并行、每轮最小交付物和停止条件。
- 更新 `codex-worker-orchestration`，新增“独立调用与整合调用”说明，保留单独 worker 编排能力。
- 更新 `project-remediation-audit`，新增“独立调用与整合调用”说明，保留单独审计能力。
- 更新 README，记录三个相关个人 Codex skills 的职责边界。
- 更新 `docs/DEMANDS.MD`，记录本轮整合 skill 需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/one-time-parallel-developer/SKILL.md`
- `/home/muhengliao/.codex/skills/one-time-parallel-developer/agents/openai.yaml`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`

### 验证结果

- `find /home/muhengliao/.codex/skills/one-time-parallel-developer /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 2 -type f`
  - 结果：三个 skill 的 `SKILL.md` / `agents/openai.yaml` 均存在，`codex-worker-orchestration` 的 assets 模板仍存在。
- 手工 frontmatter 校验：
  - 结果：`one-time-parallel-developer`、`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `rg -n "one-time-parallel-developer|独立调用与整合调用|Audit -> Batch -> Task -> Worker -> Review -> Merge -> Re-audit -> Repeat/Stop" /home/muhengliao/.codex/skills/one-time-parallel-developer /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：整合 skill 包含完整闭环状态机；两个子 skill 均包含“独立调用与整合调用”说明，并指向 `one-time-parallel-developer`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（Worker 模板与 Skill 中文化）

### 用户需求

- 用户确认 worker final report 是每个子任务一份后，要求把两个 skill、子任务模板、子任务报告模板都改为中文。

### 已做改动

- 将 `.agent/templates/worker_task.md` 中文化。
- 将 `.agent/templates/worker_report.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/agents/openai.yaml` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md` 中文化。
- 将 `/home/muhengliao/.codex/skills/project-remediation-audit/agents/openai.yaml` 中文化。
- 更新 `docs/DEMANDS.MD`，记录本轮中文化需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `.agent/templates/worker_task.md`
- `.agent/templates/worker_report.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/agents/openai.yaml`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/agents/openai.yaml`

### 验证结果

- `rg -n "Assignment|Role|Goal|Required Context|Scope|Constraints|Final Report|Preconditions|Worker Contract|Workflow|Common Failure|Project Remediation|Overview|Use when" .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：无输出，未发现旧英文流程标题或关键短语残留。
- 手工 frontmatter 校验：
  - 结果：`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `find .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 3 -type f`
  - 结果：两个仓库模板、两个 skill 的 `SKILL.md` / `agents/openai.yaml`、并行开发 skill assets 中的两个模板均存在。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Workflow Snapshot - 2026-05-24（Codex worker 并行开发与审计 skill）

### 用户需求

- 用户要求生成 Codex worker 子任务文件模板和子报告模板。
- 用户要求把“主 Codex orchestrator + 独立 Codex exec worker + 任务文件 + 结果报告 + git worktree 隔离区”的并行开发流程固化为 skill。
- 用户要求把前面的项目补救审计流程固化为 skill。

### 已做改动

- 新增 `.agent/templates/worker_task.md`，定义 worker task file 的字段、角色、范围、验证命令和停止条件。
- 新增 `.agent/templates/worker_report.md`，定义 worker final report 的状态、变更、验证、风险和 orchestrator 后续动作格式。
- 更新 `.gitignore`，忽略 `.worktrees/` 和 `.agent/logs/`。
- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/codex-worker-orchestration`。
- 新增个人 Codex skill：`/home/muhengliao/.codex/skills/project-remediation-audit`。
- `codex-worker-orchestration` 同步保存 worker task/report 模板到 skill assets，便于跨项目复用。
- 更新 README 的协作模板入口。
- 更新 `docs/DEMANDS.MD`，记录本轮并行开发与审计 skill 固化需求。
- 未修改 `src/`、`tests/`、`configs/` 中的项目运行时代码，未升级项目版本号。

### 影响文件

- `.gitignore`
- `.agent/templates/worker_task.md`
- `.agent/templates/worker_report.md`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/SKILL.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_task_template.md`
- `/home/muhengliao/.codex/skills/codex-worker-orchestration/assets/worker_report_template.md`
- `/home/muhengliao/.codex/skills/project-remediation-audit/SKILL.md`

### 验证结果

- `codex exec --help`
  - 结果：可用，显示 `Run Codex non-interactively` 和 `-C, --cd <DIR>` / `-o, --output-last-message <FILE>` 等参数。
- `find .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit -maxdepth 3 -type f`
  - 结果：能找到两个仓库模板、两个 skill 的 `SKILL.md` / `agents/openai.yaml`，以及并行开发 skill assets 中的两个模板。
- 手工 frontmatter 校验：
  - 结果：`codex-worker-orchestration` 和 `project-remediation-audit` 均包含 `name`、`description`，skill name 符合 hyphen-case。
- `rg -n "TODO|\[TODO\]" .agent/templates /home/muhengliao/.codex/skills/codex-worker-orchestration /home/muhengliao/.codex/skills/project-remediation-audit`
  - 结果：无遗留 TODO。
- `git check-ignore -q .worktrees/probe` 和 `git check-ignore -q .agent/logs/probe.log`
  - 结果：均命中忽略规则。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.62.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- `python /home/muhengliao/.codex/skills/.system/skill-creator/scripts/quick_validate.py ...`
  - 结果：当前主环境缺少 PyYAML，失败于 `ModuleNotFoundError: No module named 'yaml'`；未在主环境安装依赖，后续可在隔离环境补跑。

## Audit Snapshot - 2026-05-24（审计文件迁移与项目进度）

### 用户需求

- 用户要求先把 `docs/ACCEPTANCE_CHECKLIST.md`、`docs/IMPLEMENTATION_PLAN.md`、`docs/DECISIONS.md` 移动到 `docs/audit/`。
- 用户要求读取现有设计说明、开发指南、README、`docs/` 目录和当前代码结构，总结当前项目开发进度，并明确距离完整项目成果还有多远。
- 用户要求把审计结果更新到 `docs/audit/` 的相关文件中。

### 已做改动

- 新建 `docs/audit/` 并迁移三个审计文件。
- 更新 `docs/audit/ACCEPTANCE_CHECKLIST.md`，按“已完成 / 缺失 / 偏离 / 未验证”重写当前项目进度审计，并明确当前仍是 core/CLI 骨架和 smoke/proxy 验证链，不是完整 production 生成器。
- 更新 `docs/audit/IMPLEMENTATION_PLAN.md`，把补救拆成审计归位、契约一致性、可交互 UI、production 模型、生产级 WSI 输出、环境化验证和维护性收敛任务包。
- 更新 `docs/audit/DECISIONS.md`，记录完整项目成果定义、关键设计决策和禁止变更项。
- 更新 `docs/DEMANDS.MD`，把本轮审计文件迁移与项目进度审计需求置顶记录。
- 更新 `README.md`，在核心文档列表中加入审计验收清单、补救计划和决策文件入口。
- 未修改 `src/`、`tests/`、`configs/` 中的实现逻辑，未升级版本号。

### 影响文件

- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

### 验证结果

- `find docs -maxdepth 2 -type f \( -path 'docs/audit/*' -o -name 'ACCEPTANCE_CHECKLIST.md' -o -name 'IMPLEMENTATION_PLAN.md' -o -name 'DECISIONS.md' \) -printf '%p\n' | sort`
  - 结果：仅返回 `docs/audit/ACCEPTANCE_CHECKLIST.md`、`docs/audit/DECISIONS.md`、`docs/audit/IMPLEMENTATION_PLAN.md`。
- `PYTHONPATH=src python -m he_wsi_generator.cli --version`
  - 结果：`v0.62.0`。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。

## Audit Snapshot - 2026-05-24（基于 v0.62.0）

### 用户需求

- 用户要求进入项目补救审计模式。
- 本轮先输出偏差审计，再给出最小补救计划；在确认前不开始修代码。

### 已做改动

- 未修改 `src/`、`tests/`、`configs/` 中的实现代码。
- 更新 `docs/DEMANDS.MD`，把本轮审计需求置顶记录。
- 新增 `docs/ACCEPTANCE_CHECKLIST.md`，把当前基线拆成“已完成 / 缺失 / 偏离 / 未验证”的可验收项。
- 新增 `docs/IMPLEMENTATION_PLAN.md`，整理补救任务包和优先级。
- 新增 `docs/DECISIONS.md`，冻结当前审计基线、关键设计决策和禁止变更项。
- 本轮审计额外确认：
  - 当前仓库内不存在实体 `AGENTS.md` 文件。
  - `qc_review` 具备内部校验函数，但尚未接入通用 `validate` CLI/schema kind。
  - `collect_output_summary()` 当前只校验 QC/review，不校验 metadata schema。
  - 当前环境缺少 `torch` 和 `PySide6`，所以 PyTorch 路径和真实 GUI 启动未在本轮复跑验证。

### 影响文件

- `docs/DEMANDS.MD`
- `docs/ACCEPTANCE_CHECKLIST.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DECISIONS.md`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_version -v`
  - 结果：2 个测试通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：187 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 `torch` 被跳过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate-prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-output-summary --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --qc-review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
  - 结果：返回 `qc_status=pass`、三级状态全 `pass`、`review_required=false`、`decision=accepted`。
- `python - <<'PY' import torch ...`
  - 结果：`ModuleNotFoundError`。
- `python - <<'PY' import PySide6 ...`
  - 结果：`ModuleNotFoundError`。
- `python - <<'PY' import openslide ...`
  - 结果：可导入。

## v0.62.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 用户要求代码开发完成后使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 验证，并确保所有输出能正常交付。
- 本次版本需要把自动 QC 的 warning/fail 结果落盘为可追踪、可更新决策的 `qc_review` artifact，并让输出摘要能合并审阅状态。

### 已做改动

- 版本号升级到 `v0.62.0`。
- 新增 `src/he_wsi_generator/qc/review.py`，实现 `qc_review` artifact 的构建、读取、验证与决策更新。
- `build_qc_review()` 读取 `metadata.json` 与 `qc.json`，输出 `schema_version`、`artifact_type=qc_review`、`generated_id`、输入路径与 sha256、QC overall/level 状态、`review_required`、`decision=pending`、`created_at` 和待审阅 metric 列表。
- `review_required` 现在与 QC `overall_status` 强一致：`warning`/`fail` 为 `true`，`pass` 为 `false`。
- warning/fail metric 会保留 level、metric name、status、value、reference、message/reason（若存在）。
- `apply_qc_review_decision()` 仅接受 `accepted`、`rejected`、`needs_rerun`，只允许更新 `pending` 审阅单，并记录 `reviewer`、`note`、`reviewed_at`。
- CLI 新增 `create-qc-review` 与 `apply-qc-review-decision`，`inspect-output-summary` 新增可选 `--qc-review`。
- `collect_output_summary()` 现在可合并 `qc_review` 状态，输出 `review_required`、`decision`、`reviewer` 和 `review_item_count`。
- README 补充 `qc_review` 命令、输出摘要的 review 合并行为和本次边界说明。
- 需求记录 `docs/DEMANDS.MD` 顶部补充 v0.62.0 结构化需求。

### 影响文件

- `VERSION`
- `README.md`
- `docs/CHANGELOG.md`
- `docs/DEMANDS.MD`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/review.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_qc_review.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.62.0`）

### 验证结果

- TDD 红灯记录：
  - 新增 `tests/test_qc_review.py` 初次运行因 `he_wsi_generator.qc.review` 模块不存在而失败。
  - 新增 `collect_output_summary(..., qc_review_path=...)` 测试初次运行因函数签名不支持 `qc_review_path` 而失败。
  - 新增 `inspect-output-summary --qc-review` 测试初次运行因 CLI 参数未实现而失败。
  - 新增 `review_required` 强一致性测试初次运行因校验逻辑未实现而失败。
- `PYTHONPATH=src python -m unittest tests.test_qc_review -v`
  - 结果：8 个测试通过。
- `PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_collect_output_summary_includes_qc_review_status tests.test_ui.UITests.test_cli_inspects_output_summary_with_qc_review -v`
  - 结果：2 个测试通过。
- `PYTHONPATH=src python -m unittest tests.test_qc_review.QCReviewTests.test_validate_qc_review_rejects_mismatched_review_required -v`
  - 结果：初次失败，随后补齐 `review_required` 一致性校验并转绿。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：187 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.62.0 验证链路：
  - `validate manifest build/validation/v0.62.0-291288/input_manifest.json`
  - `validate qc build/validation/v0.62.0-291288/reference-qc/qc-reference-291288.json`
  - `build-wsi-tissue-overview build/validation/v0.62.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.62.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.62.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.62.0-291288/prior --prior-id prior-291288-v062 --dataset-id pancancer-fanhong-breast-291288-validation --input-manifest build/validation/v0.62.0-291288/input_manifest.json --training-data-version validation-v0.62.0 --wsi-id 291288 --random-seed 7 --layout-mask-prior build/validation/v0.62.0-291288/layout_mask_prior.json --style-prior build/validation/v0.62.0-291288/style_prior.json --texture-prior build/validation/v0.62.0-291288/texture_prior.json --qc-reference-distribution build/validation/v0.62.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.62.0-291288/layout_mask_prior.json --output-dir build/validation/v0.62.0-291288/sampled-layout --sample-id 291288-v062-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.62.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json --output build/validation/v0.62.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.62.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.62.0-291288/trained-checkpoint.json --output-root build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062 --generated-id gen-291288-smoke-sampled-mask-v062 --condition-packet build/validation/v0.62.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json`
  - `validate qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json`
  - `create-qc-review --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --output build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
  - `apply-qc-review-decision --review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json --decision accepted --reviewer "Dr. Chen" --note "Real SVS validation reviewed."`
  - `inspect-output-summary --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --qc-review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json`、`qc.json` 和 `qc_review.json` 均为 `schema_version=v0.62.0`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `qc_review.json` 返回 `artifact_type=qc_review`、`review_required=false`、`decision=accepted`、`reviewer=Dr. Chen`，`review_item_count=0`。
  - `generated_mask/mask.npy` shape 为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取，level count 为 4，首层 shape 为 `[512, 512, 3]`。
  - 输出目录 `build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`qc_review.json`、`generation_run.json` 和 `batch.jsonl`。

## v0.61.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 用户要求代码开发完成后使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 验证，并确保所有输出能正常交付。
- 本次版本在 v0.60.0 的分层 `qc_reference_distribution` artifact 基础上，推进运行时消费能力：生成/QC 链路需要能根据当前样本的可追踪上下文选择匹配 stratum 阈值，而不是永远只使用全局 `metrics`。

### 已做改动

- 版本号升级到 `v0.61.0`。
- `build_qc_report()` 新增可选 `qc_reference_context` 参数，并在启用 `qc_reference_distribution.stratification` 时按 context 构造 exact stratum key。
- 当 context 匹配 stratum 时，QC metric 使用该 stratum 的阈值，并在 `reference` 中记录 `selection=stratified`、`stratum_key`、`stratification_fields` 和 `group_values`。
- 当 context 缺失、不完整、非法或找不到 stratum 时，QC metric 显式回退全局阈值，并记录 `selection=global_fallback`、`fallback_reason` 和 `stratification_fields`。
- 未启用分层 reference 时，QC 仍消费全局 `metrics`，并记录 `selection=global`，保持既有全局阈值行为。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 从 condition packet summary 提取 `metadata.cancer_type`、`metadata.tissue_type`、`metadata.center_id`、`metadata.split` 作为 QC reference context。
- `build_generation_condition_packet()` 在 `conditions.layout.wsi_tissue_overview.records[*]` 中保留运行时 QC 分层需要的 manifest 摘要字段。
- `build-wsi-tissue-overview` 产物在输入 manifest 含 `center_id` 时保留该字段，便于后续按中心分层。
- 嵌套 stratum metrics 类型错误现在会报告实际 JSON 路径，避免误报成全局 `qc_reference_distribution.metrics`。
- README 同步说明运行时分层 QC exact-match 选择、global fallback 审计和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/priors/tissue.py`
- `src/he_wsi_generator/qc/engine.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_schemas.py`
- `tests/test_wsi_tissue_overview.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.61.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- TDD 红灯记录：
  - 新增 QC engine 分层 reference 测试最初因 `build_qc_report()` 不支持 `qc_reference_context` 而失败。
  - 新增 context 缺失 fallback 测试最初因 metric reference 未记录 `selection=global_fallback` 而失败。
  - 新增 smoke generation 分层 QC 测试最初因 condition packet summary 未传入 QC context 而失败。
  - 新增 condition packet manifest 摘要测试最初因 `conditions.layout.wsi_tissue_overview.records[*]` 未保留 manifest 字段而失败。
  - 新增 WSI tissue overview `center_id` 测试最初因 artifact 未保留输入 manifest 的 `center_id` 而失败。
  - 新增嵌套 stratum metrics 错误路径测试最初因报错仍指向全局 `qc_reference_distribution.metrics` 而失败。
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_generation_conditioning tests.test_wsi_tissue_overview tests.test_schemas tests.test_ui tests.test_version -v`
  - 结果：68 个测试通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：178 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
  - 结果：通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
  - 结果：`generation-config valid: configs/generation.default.json`。
- `git diff --check`
  - 结果：通过，无 whitespace error。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.61.0 验证链路：
  - `validate manifest build/validation/v0.61.0-291288/input_manifest.json`
  - `validate qc build/validation/v0.61.0-291288/reference-qc/qc-reference-291288.json`
  - `build-wsi-tissue-overview build/validation/v0.61.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.61.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.61.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.61.0-291288/prior ... --qc-reference-distribution build/validation/v0.61.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.61.0-291288/layout_mask_prior.json --output-dir build/validation/v0.61.0-291288/sampled-layout --sample-id 291288-v061-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.61.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json --output build/validation/v0.61.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.61.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.61.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.61.0-291288/trained-checkpoint.json --output-root build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v061 --condition-packet build/validation/v0.61.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.61.0`。
  - `wsi_tissue_overview.records[0].manifest` 保留 `cancer_type=breast_cancer`、`tissue_type=breast`、`center_id=fanhong`、`split=test`。
  - `condition_packet.conditions.layout.wsi_tissue_overview.records[0].manifest` 保留运行时 QC context 所需字段。
  - `qc_reference_distribution.stratification.enabled=true`，`fields=["metadata.cancer_type"]`，`stratum_count=1`，包含 `metadata.cancer_type=breast_cancer` stratum。
  - Prior manifest 的 `qc_reference_distribution` artifact metadata 记录 `stratification_fields=["metadata.cancer_type"]`、`stratum_count=1` 和 `metric_count=2`。
  - 输出目录 `build/validation/v0.61.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `qc.json` 中 `mean_red` 和 `mask_tissue_fraction` 均记录 `reference.selection=stratified`、`stratum_key=metadata.cancer_type=breast_cancer` 和 `group_values={"metadata.cancer_type":"breast_cancer"}`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`；最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取，包含 OME metadata，level count 为 4，首层 shape 为 `[512, 512, 3]`。
  - `generation_run.json.pyramid_report.chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - `batch.jsonl` 包含 1 条 generated sample 索引。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.60.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“按组织区域、疾病类型或中心分层统计/QC”的工程落地：`qc_reference_distribution` 需要支持显式分层阈值估计，在保留全局阈值兼容性的同时，为癌种、中心、组织类型等元数据分组写出独立 warning/fail 区间和审计记录。

### 已做改动

- 版本号升级到 `v0.60.0`。
- `build_qc_reference_distribution()` 新增可选 `stratify_by` 参数，接受一个或多个 dot-path 字段，例如 `metadata.cancer_type`、`metadata.center_id` 或 `metadata.tissue_type`。
- 未传 `stratify_by` 时，继续保留既有全局 `metrics`、`outlier_policy` 和 `outlier_audit` 行为兼容。
- 传入 `stratify_by` 时，输出 JSON 新增 `stratification` 和 `strata` 字段。
- 每个 stratum 独立使用同一 estimator、outlier policy 和 `min_samples` 规则估计 metric 阈值，并写出该分组的样本 id、group values 和 outlier audit。
- 分层字段缺失、为 `null`、为空字符串或值类型不适合做分组时，builder 会显式报错，不会静默归入 unknown bucket。
- CLI `build-qc-reference` 新增可重复参数 `--stratify-by <dot.path>`。
- Prior manifest 的 `qc_reference_distribution` artifact metadata 新增 `stratification_fields` 和 `stratum_count` 摘要。
- README 同步说明 `--stratify-by` 用法、输出字段、兼容关系和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_qc_reference.py`
- `tests/test_priors.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.60.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- TDD 红灯记录：
  - 新增分层 reference 测试最初因 `build_qc_reference_distribution()` 不支持 `stratify_by` 参数而失败。
  - CLI 测试最初因 `build-qc-reference` 不支持 `--stratify-by` 而未能写出输出文件。
  - Prior manifest 测试最初因 `qc_reference_distribution` artifact metadata 未记录 `stratification_fields` 而失败。
- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_priors tests.test_version -v`
  - 结果：23 个测试通过。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：174 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.60.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.60.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.60.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --stratify-by metadata.cancer_type --output build/validation/v0.60.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.60.0-291288/prior ... --qc-reference-distribution build/validation/v0.60.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.60.0-291288/layout_mask_prior.json --output-dir build/validation/v0.60.0-291288/sampled-layout --sample-id 291288-v060-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.60.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json --output build/validation/v0.60.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.60.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.60.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.60.0-291288/trained-checkpoint.json --output-root build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v060 --condition-packet build/validation/v0.60.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`prior_manifest.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.60.0`。
  - `qc_reference_distribution.stratification.enabled=true`，`fields=["metadata.cancer_type"]`，`stratum_count=1`。
  - `strata["metadata.cancer_type=breast_cancer"].metrics.mean_red.median=127.5`，分层 metric 使用 `robust_mad_z_score` estimator。
  - Prior manifest 的 `qc_reference_distribution` artifact metadata 记录 `stratification_fields=["metadata.cancer_type"]`、`stratum_count=1` 和 `metric_count=2`。
  - 输出目录 `build/validation/v0.60.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generated.ome.tiff` 可由 `tifffile` 读取并包含 OME metadata。
  - `generation_run.json.pyramid_report.chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`。

## v0.59.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持 robust z-score 风格的全局阈值估计，让颜色、清晰度、组织比例等数值 metric 能用 median/MAD 生成抗离群的 warning/fail 区间。

### 已做改动

- 版本号升级到 `v0.59.0`。
- `build_qc_reference_distribution()` 的 `estimator` 新增 `robust_mad_z_score`。
- `robust_mad_z_score` 基于排序后的参考 QC 数值计算 median、MAD 和 scaled MAD。
- `robust_mad_z_score` 输出 `median`、`mad`、`scaled_mad`、`warning_z_score`、`fail_z_score`、observed min/max、sample count 和 estimator 字段。
- Warning 区间使用 `median ± 3.0 * scaled_mad`，fail 区间使用 `median ± 6.0 * scaled_mad`。
- MAD 为 0 时使用有限非零 margin，避免阈值坍缩到单点。
- `robust_mad_z_score` 与既有 `outlier_policy` 兼容；显式启用 `robust_iqr_filter` 时会先过滤参考样本，再用保留样本估计 MAD/z-score 阈值。
- CLI `build-qc-reference --estimator` 新增 `robust_mad_z_score` 可选值。
- README 同步说明 MAD/z-score estimator 的用法、输出字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.59.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：12 个测试通过。
- TDD 红灯记录：
  - 新增 MAD/z-score estimator 测试最初因 `build_qc_reference_distribution()` 不支持 `robust_mad_z_score` estimator 而失败。
  - CLI 测试最初因 `build-qc-reference --estimator` 不支持 `robust_mad_z_score` 而未能写出输出文件。
- CLI 实测：
  - `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json ... <tmp>/qc-5.json --metric mean_red --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.59.0`，`outlier_policy=robust_iqr_filter`，`mean_red.estimator=robust_mad_z_score`，过滤后 `sample_count=4`、`observed_max=106.0`、`median=103.0`、`mad=2.0`、`scaled_mad=2.9652`、`warning_z_score=3.0`、`fail_z_score=6.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：172 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.59.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.59.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.59.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_mad_z_score --outlier-policy robust_iqr_filter --output build/validation/v0.59.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.59.0-291288/prior ... --qc-reference-distribution build/validation/v0.59.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.59.0-291288/layout_mask_prior.json --output-dir build/validation/v0.59.0-291288/sampled-layout --sample-id 291288-v059-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.59.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json --output build/validation/v0.59.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.59.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.59.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.59.0-291288/trained-checkpoint.json --output-root build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v059 --condition-packet build/validation/v0.59.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.59.0`。
  - `qc_reference_distribution.outlier_policy=robust_iqr_filter`，`metrics.mean_red.estimator=robust_mad_z_score`，单样本验证 reference 中 `mean_red.sample_count=1`、`median=127.5`、`mad=0.0`、`scaled_mad=12.75`、`warning_z_score=3.0`、`fail_z_score=6.0`。
  - `outlier_audit.metrics.mean_red` 记录原始 1 个样本、保留 1 个样本、排除 0 个样本。
  - 输出目录 `build/validation/v0.59.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.58.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本继续推进自动 QC 的训练分布自适应阈值能力：`qc_reference_distribution` 需要支持显式的参考 QC 异常值过滤策略，在生成阈值前排除少量明显离群参考样本，同时保留完整审计记录，避免静默丢弃数据。

### 已做改动

- 版本号升级到 `v0.58.0`。
- `build_qc_reference_distribution()` 新增 `outlier_policy` 参数，默认 `none`，保持既有行为兼容。
- 新增 `robust_iqr_filter` policy：对每个 metric 的参考 QC 数值计算 Q1、Q3 和 IQR，并使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 作为保留区间。
- `robust_iqr_filter` 会在阈值估计前按 metric 排除 fence 外的参考样本；过滤结果只影响当前 metric，不会删除或改写原始 QC 文件。
- 输出 JSON 新增 `outlier_policy` 和 `outlier_audit`，记录每个 metric 的原始样本数、保留样本数、排除样本数、filter fence 和被排除样本的 `generated_id`、metric name、value。
- 若过滤后样本数低于 `min_samples`，builder 会显式报错，不会回退到未过滤样本。
- 非法 `outlier_policy` 会通过 `QCReferenceBuildError` 显式报错。
- CLI `build-qc-reference` 新增 `--outlier-policy` 参数，支持 `none` 和 `robust_iqr_filter`。
- README 同步说明 reference outlier filtering 的用法、审计字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.58.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：10 个测试通过。
- TDD 红灯记录：
  - 新增 outlier policy 测试最初因 `build_qc_reference_distribution()` 不支持 `outlier_policy` 参数而失败。
  - CLI 测试最初因 `build-qc-reference` 不支持 `--outlier-policy` 而未能写出输出文件。
- CLI 实测：
  - `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json ... <tmp>/qc-5.json --metric mean_red --estimator robust_iqr --outlier-policy robust_iqr_filter --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.58.0`，`outlier_policy=robust_iqr_filter`，`mean_red.sample_count=4`，`mean_red.observed_max=106.0`，`outlier_audit` 记录原始 5 个样本、保留 4 个样本、排除 1 个样本，排除样本为 `gen-cli-005` 且数值为 `500.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：170 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.58.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.58.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.58.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_iqr --outlier-policy robust_iqr_filter --output build/validation/v0.58.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.58.0-291288/prior ... --qc-reference-distribution build/validation/v0.58.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.58.0-291288/layout_mask_prior.json --output-dir build/validation/v0.58.0-291288/sampled-layout --sample-id 291288-v058-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.58.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json --output build/validation/v0.58.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.58.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.58.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.58.0-291288/trained-checkpoint.json --output-root build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v058 --condition-packet build/validation/v0.58.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.58.0`。
  - `qc_reference_distribution.outlier_policy=robust_iqr_filter`，`metrics.mean_red.estimator=robust_iqr`，单样本验证 reference 中 `mean_red.sample_count=1`。
  - `outlier_audit.metrics.mean_red` 记录原始 1 个样本、保留 1 个样本、排除 0 个样本。
  - 输出目录 `build/validation/v0.58.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.57.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进研究设计中“训练分布自适应阈值”的稳健估计能力：`qc_reference_distribution` 需要支持 IQR-based robust threshold estimator，避免少量离群参考 QC 把 warning/fail 区间过度拉宽。

### 已做改动

- 版本号升级到 `v0.57.0`。
- `build_qc_reference_distribution()` 新增 `estimator` 参数，默认保持既有 `observed_min_max_with_range_margin`，以兼容旧调用。
- 新增 `robust_iqr` estimator，按排序值计算 Q1、median、Q3 和 IQR。
- `robust_iqr` 输出 `q1`、`median`、`q3`、`iqr`、observed min/max、sample count 和 estimator 字段。
- `robust_iqr` 使用 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` 生成 warning 区间，使用 `[Q1 - 3.0*IQR, Q3 + 3.0*IQR]` 生成 fail 区间。
- 零 IQR 时使用有限非零 margin，避免阈值坍缩到单点。
- 非法 estimator 会通过 `QCReferenceBuildError` 显式报错，不做静默回退。
- CLI `build-qc-reference` 新增 `--estimator` 参数，并限制为 `observed_min_max_with_range_margin` 或 `robust_iqr`。
- README 同步说明 robust IQR estimator 的用法、输出字段和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_qc_reference.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.57.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference tests.test_version -v`
  - 结果：7 个测试通过。
- `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference <tmp>/qc-1.json <tmp>/qc-2.json <tmp>/qc-3.json --metric mean_red --metric mask_tissue_fraction --estimator robust_iqr --output <tmp>/qc_reference_distribution.json`
  - 结果：输出 `schema_version=v0.57.0`，`mean_red.estimator=robust_iqr`，并记录 `q1=101.0`、`median=102.0`、`q3=103.0`、`iqr=2.0`。
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：167 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `git pull --ff-only origin main`
  - 结果：`Already up to date.`，远端 `origin/main` 与本地 `HEAD` 均为 `59557b19672f4b9806e600c9a1db271280795513`。
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.57.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.57.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `build-qc-reference build/validation/v0.57.0-291288/reference-qc/qc-reference-291288.json --metric mean_red --metric mask_tissue_fraction --min-samples 1 --estimator robust_iqr --output build/validation/v0.57.0-291288/qc_reference_distribution.json`
  - `build-prior-manifest --output-dir build/validation/v0.57.0-291288/prior ... --qc-reference-distribution build/validation/v0.57.0-291288/qc_reference_distribution.json --wsi-tissue-overview build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.57.0-291288/layout_mask_prior.json --output-dir build/validation/v0.57.0-291288/sampled-layout --sample-id 291288-v057-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.57.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json --output build/validation/v0.57.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.57.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.57.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.57.0-291288/trained-checkpoint.json --output-root build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v057 --condition-packet build/validation/v0.57.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.json`、`qc_reference_distribution.json`、`sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `schema_version=v0.57.0`。
  - `qc_reference_distribution.metrics.mean_red.estimator=robust_iqr`，并记录 robust quartile 字段；单样本验证 reference 中 `mean_red.q1=127.5`。
  - 输出目录 `build/validation/v0.57.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`，三级状态 `wsi/tile/mask_region` 均为 `pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`，`production_streaming=false`。
  - 验证目录大小约 `1.5M`，最终输出目录约 `1.2M`。

## v0.56.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进开发附录 7.4 和 README 中 `chunked_pyramid_write` 的输出侧前置能力：OME-TIFF writer 需要输出可审计的 chunked write plan / BigTIFF 决策记录，减少 generation plan 与实际 writer 报告之间的语义落差。

### 已做改动

- 版本号升级到 `v0.56.0`。
- `write_pyramid_ome_tiff()` 新增 `chunk_shape` 和 `bigtiff_threshold_bytes` 参数。
- OME-TIFF writer 的 `pyramid_report.write_mode` 现在记录为 `chunked_pyramid_write`。
- `pyramid_report.chunked_write_audit` 记录 writer backend、BigTIFF 决策、估算总字节数、chunk shape、每层 chunk grid / chunk count / edge chunk shape。
- 非法 `chunk_shape` 和非法 BigTIFF 阈值会显式报错。
- Audit 明确记录 `production_streaming=false` 和 `streaming_limitations`，避免把当前内存数组 writer 伪装成生产级 gigapixel streaming writer。
- Smoke generation 的 `generation_run.json.pyramid_report` 会保留同一份 chunked write audit，便于最终交付物审计。
- README 同步说明 OME-TIFF writer 的 chunked write audit 能力和当前边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.56.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_records_chunked_write_audit tests.test_outputs_qc_archive.OutputQCArchiveTests.test_write_pyramid_ome_tiff_rejects_invalid_chunk_shape tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
  - TDD 红灯：新增测试最初因 `write_pyramid_ome_tiff()` 不支持 `chunk_shape`、`pyramid_report.write_mode` 仍为 `small_pyramid_smoke_writer` 而失败；实现后同一命令通过。
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive tests.test_generation_runner tests.test_version tests.test_schemas -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：165 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.56.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.56.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `build-prior-manifest --output-dir build/validation/v0.56.0-291288/prior ... --wsi-tissue-overview build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.56.0-291288/layout_mask_prior.json --output-dir build/validation/v0.56.0-291288/sampled-layout --sample-id 291288-v056-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.56.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json --output build/validation/v0.56.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.56.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.56.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.56.0-291288/trained-checkpoint.json --output-root build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v056 --condition-packet build/validation/v0.56.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.56.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.schema_version=v0.56.0`，真实 thumbnail tissue fraction 保留为 `0.156499895`。
  - `sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `v0.56.0`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `generation_run.json.pyramid_report.write_mode=chunked_pyramid_write`，并包含 `chunked_write_audit`。
  - `chunked_write_audit.writer_backend=tifffile`、`production_streaming=false`、`bigtiff=false`、`estimated_total_bytes=839424`、`chunk_shape=[512, 512]`、level0 `chunk_grid=[1, 1]` 且 `chunk_count=1`。
  - `chunked_write_audit.streaming_limitations` 明确记录 `in_memory_array_writer`、`chunk_plan_is_audit_metadata_only` 和 `not_a_resume_capable_gigapixel_streaming_writer`。

## v0.55.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本为 v0.54.0 的 sampled layout mask 条件输出补齐 QC 审计，确认最终 generated mask 是否忠实保留 sampled mask 条件。

### 已做改动

- 版本号升级到 `v0.55.0`。
- `build_qc_report()` 新增可选 `sampled_layout_mask_summary` 参数。
- QC 的 `non_copy_report.metrics` 新增 `sampled_layout_mask_match_proxy`，读取 sampled layout `.npy` 与最终 generated mask 逐像素比较，记录 matched pixel fraction。
- sampled mask 与 generated mask 尺寸不一致但都是二维时，会用 nearest resize 对齐后计算匹配率。
- 缺失 sampled mask 文件、不可读 `.npy` 或非二维 mask 会显式报错。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition summary 包含 `sampled_layout_mask` 时，会把该摘要传给 QC builder。
- README 同步说明 sampled mask 条件现在有 QC match proxy 审计。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.55.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
  - 结果：163 个测试通过，21 个 PyTorch 相关测试因当前环境未安装 PyTorch 被跳过。
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 重新构建 v0.55.0 验证链路：
  - `build-wsi-tissue-overview build/validation/v0.55.0-291288/input_manifest.json --backend openslide --thumbnail-max-size 512 --output build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `build-prior-manifest --output-dir build/validation/v0.55.0-291288/prior ... --wsi-tissue-overview build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `validate-prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json`
  - `sample-layout-mask build/validation/v0.55.0-291288/layout_mask_prior.json --output-dir build/validation/v0.55.0-291288/sampled-layout --sample-id 291288-v055-sampled-layout --height 512 --width 512 --random-seed 7 --wsi-tissue-overview build/validation/v0.55.0-291288/wsi_tissue_overview.json`
  - `build-condition-packet configs/generation.default.json --prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json --output build/validation/v0.55.0-291288/condition_packet.json --cascade-level 1/1 --tile-origin-x 0 --tile-origin-y 0 --sampled-layout-mask build/validation/v0.55.0-291288/sampled-layout/sampled_layout_mask.json`
  - `run-generation configs/generation.default.json --backend smoke-cascade --prior-manifest build/validation/v0.55.0-291288/prior/prior_manifest.json --checkpoint-manifest build/validation/v0.55.0-291288/trained-checkpoint.json --output-root build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask --generated-id gen-291288-smoke-sampled-mask-v055 --condition-packet build/validation/v0.55.0-291288/condition_packet.json`
  - `validate metadata build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json`
  - `validate qc build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
  - `inspect-output-summary --metadata build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/metadata.json --qc build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/qc.json`
- 真实 SVS 验证结果：
  - `wsi_tissue_overview.schema_version=v0.55.0`，真实 thumbnail tissue fraction 保留为 `0.156499895`。
  - `sampled_layout_mask.json`、`condition_packet.json`、`generation_run.json`、`metadata.json` 与 `qc.json` 均为 `v0.55.0`。
  - 输出目录 `build/validation/v0.55.0-291288/generated/gen-291288-smoke-sampled-mask/` 包含 `generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`generation_run.json` 和 `batch.jsonl`。
  - `metadata.json` 与 `qc.json` 均通过当前 schema 校验，`inspect-output-summary` 返回 `qc_status=pass`。
  - `sampled_layout_mask_match_proxy.status=pass`，`value=1.0`，`matched_pixel_fraction=1.0`。
  - 最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，shape 均为 `[512, 512]`，类别 id 覆盖 `[0, 1, 2, 3, 4, 5]`。
  - `metadata.json` 和 `generation_run.json` 均记录 `sampled_layout_mask` 与 `wsi_tissue_overview` 条件摘要。

## v0.54.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 v0.53.0 的 `sampled_layout_mask` 从独立 artifact 接入 generation condition packet 和 smoke generation 输出，使统计型 sampled layout mask 能作为实际 mask 条件交付。

### 已做改动

- 版本号升级到 `v0.54.0`。
- `build_generation_condition_packet()` 新增可选 `sampled_layout_mask_path` 参数；CLI `build-condition-packet` 新增 `--sampled-layout-mask`。
- Condition packet 的 `artifact_inputs.sampled_layout_mask` 记录 sampled layout artifact path、kind、sample id、mask path 和 mask shape。
- Condition packet 的 `conditions.mask` 支持 `source=sampled_layout_mask`，记录 mask path、sample id、class counts/fractions 和 limitations。
- `run_smoke_generation()` 遇到 sampled layout mask 条件时读取 `.npy` mask，校验二维和 0-5 类 id，必要时 nearest resize 到输出 canvas，并写为最终 mask。
- `metadata.json` 与 `generation_run.json` 的 condition summary 记录 sampled layout mask 摘要，便于追踪最终输出 mask 来源。
- README 同步说明 sampled layout mask 现在可进入 condition packet 并驱动 smoke generation mask 输出。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.54.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning tests.test_generation_runner tests.test_layout_mask_sampler tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 对应验证 artifact 重建 v0.54 prior manifest，执行 `sample-layout-mask`、`build-condition-packet --sampled-layout-mask` 和 `run-generation --backend smoke-cascade --condition-packet`，确认最终 `generated_mask/mask.npy` 与 `sampled_layout_mask.npy` 完全一致，且 `metadata.json` / `generation_run.json` 均记录 `sampled_layout_mask` 摘要。

## v0.53.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本推进 Phase 1 layout/mask prior 的可执行能力：把统计型 `layout_mask_prior` 转成可复现的 sampled layout mask artifact，使低 anchor / fully de novo 路径有可交付的结构条件输入。

### 已做改动

- 版本号升级到 `v0.53.0`。
- 新增 `sample_layout_mask_from_prior()`，从 `layout_mask_prior.json` 读取 6 类比例和 tile layout records，输出 `.npy` sampled layout mask 与 `sampled_layout_mask.json` manifest。
- CLI 新增 `sample-layout-mask`，支持指定输出目录、sample id、mask height/width、random seed 和可选 `wsi_tissue_overview`。
- 可选 tissue overview 会把第一条 thumbnail tissue proxy 的 tissue fraction、bounding box 和 connected component count 记录到 manifest，并用 bounding box 限定 sampled mask 的非背景 footprint。
- 输出 manifest 记录 class counts/fractions、source prior path、可选 tissue overview path 和 limitations，明确该产物不是 mask diffusion 或语义分割模型。
- README 同步新增 sampled layout mask 用法和当前边界说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/sampler.py`
- `tests/test_layout_mask_sampler.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.53.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_layout_mask_sampler tests.test_layout_mask_prior tests.test_priors tests.test_generation_conditioning tests.test_generation_runner tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 既有验证 artifact 中的真实 `wsi_tissue_overview.json` 执行 `sample-layout-mask`，生成 `build/validation/v0.53.0-291288/sampled-layout/sampled_layout_mask.npy` 与 `sampled_layout_mask.json`，确认 `tissue_overview_reference.tissue_fraction=0.156499895`、mask shape 为 `[512, 512]` 且 6 类 class counts/fractions 可读取。

## v0.52.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把已进入 generation condition summary 的 `wsi_tissue_overview` 接入 QC 报告，形成生成 mask 组织比例与真实 WSI thumbnail tissue fraction 的轻量一致性审计。

### 已做改动

- 版本号升级到 `v0.52.0`。
- `build_qc_report()` 新增可选 `wsi_tissue_overview_summary` 参数；传入时会校验 summary 基础结构。
- QC 的 `non_copy_report.metrics` 新增 `wsi_tissue_fraction_reference_proxy`，记录生成 mask tissue fraction 与真实 thumbnail tissue fraction 的接近程度。
- `wsi_tissue_fraction_reference_proxy.reference.tissue_fraction` 保留 `wsi_tissue_overview` 源 artifact 的原始数值精度，真实 SVS 验证中确认 `0.156499895` 不再被舍入为 `0.1565`。
- `run_smoke_generation()` 和 `run_torch_diffusion_smoke_generation()` 在 condition packet summary 包含 `wsi_tissue_overview` 时，会把该摘要传入 QC builder。
- 缺失 `wsi_tissue_overview` 时保持既有 QC 路径兼容。
- 坏的 tissue overview summary 会显式报错，不会静默写入 QC。
- README 同步说明 tissue overview 进入 QC non-copy metrics 的审计边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_generation_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.52.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_records_wsi_tissue_fraction_reference_proxy tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_rejects_invalid_wsi_tissue_overview_summary tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_wsi_tissue_overview_qc_proxy -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`、组装 prior manifest、构建 condition packet，并运行 `run-generation --backend smoke-cascade --condition-packet`，确认真实 tissue overview 进入最终 QC 的 `wsi_tissue_fraction_reference_proxy`。

## v0.51.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 condition packet 中已记录的可选 `wsi_tissue_overview` 摘要继续写入 generation 交付物，使真实 WSI 低倍组织轮廓 proxy 能从 prior artifact 追踪到 `metadata.json` 和 `generation_run.json`。

### 已做改动

- 版本号升级到 `v0.51.0`。
- `run_smoke_generation()` 在 condition packet 包含 `conditions.layout.wsi_tissue_overview` 时，会把该摘要写入 `metadata["generation"]["condition_summary"]["wsi_tissue_overview"]`。
- `generation_run.json` 的 `condition_packet.summary` 会记录同一份 tissue overview 摘要，便于批量审计。
- PyTorch diffusion smoke 的 condition packet loader 同步保留该摘要，避免 smoke / torch 两条条件包摘要链路分叉。
- 缺失 `wsi_tissue_overview` 时保持既有 condition packet 兼容路径，不要求该字段。
- `tests/test_generation_runner.py` 新增 smoke generation metadata/run summary 的 tissue overview 摘要测试。
- `tests/test_torch_training.py` 新增不依赖 PyTorch 安装的 condition packet loader 摘要测试。
- README 同步说明 smoke generation 会把 tissue overview proxy 摘要保留到最终交付物。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_generation_runner.py`
- `tests/test_torch_training.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.51.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_wsi_tissue_overview_condition_summary tests.test_torch_training.TorchSmokeTrainingTests.test_torch_condition_packet_loader_records_wsi_tissue_overview_summary -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_records_condition_packet tests.test_generation_conditioning.GenerationConditioningTests.test_build_generation_condition_packet_records_wsi_tissue_overview_layout_summary tests.test_priors.PriorArtifactTests.test_build_prior_manifest_from_artifacts_records_optional_wsi_tissue_overview -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`、组装 prior manifest、构建 condition packet，并运行 `run-generation --backend smoke-cascade --condition-packet`，确认真实 tissue overview 摘要进入最终 `metadata.json` 和 `generation_run.json`。

## v0.50.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 prior manifest 中可选的 `wsi_tissue_overview` 继续接入 generation condition packet，使真实 WSI 低倍组织轮廓 proxy 能进入生成条件审计链路。

### 已做改动

- 版本号升级到 `v0.50.0`。
- `build_generation_condition_packet()` 在 prior manifest 包含 `wsi_tissue_overview` 时，会读取并校验该 artifact。
- `conditions.layout.wsi_tissue_overview` 现在记录 artifact path、record count、source backend、thumbnail max size，以及每张 WSI 的 tissue fraction、bounding box 和 connected component count。
- `artifact_inputs` 继续记录可选 `wsi_tissue_overview` 的 path/hash/size，便于从 condition packet 追踪源 artifact。
- 缺失 `wsi_tissue_overview` 时保持旧路径兼容，不要求该 artifact。
- `tests/test_generation_conditioning.py` 新增带 tissue overview 的 condition packet 测试和坏 artifact 失败路径测试。
- README 同步更新 condition packet 对 tissue overview 的审计说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `tests/test_generation_conditioning.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.50.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`，通过 `build-prior-manifest --wsi-tissue-overview` 组装 prior manifest，再用 `build-condition-packet` 确认真实 tissue overview 摘要进入 `conditions.layout`。

## v0.49.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本把 `v0.48.0` 新增的 `wsi_tissue_overview` 接入 prior manifest，使真实 WSI 低倍组织轮廓 artifact 能被统一 manifest 追踪、校验和复现。

### 已做改动

- 版本号升级到 `v0.49.0`。
- `build_prior_manifest_from_artifacts()` 新增可选 `wsi_tissue_overview_path` 参数；传入时会校验并写入 `artifacts.wsi_tissue_overview`。
- `build-prior-manifest` CLI 新增可选 `--wsi-tissue-overview <path>`。
- `validate_prior_manifest()` 继续要求四类核心 prior artifact，同时允许可选 `wsi_tissue_overview` 并继续拒绝其它未知 artifact type。
- `wsi_tissue_overview` artifact 校验 `artifact_type=wsi_tissue_overview`，manifest metadata 记录 artifact schema version、record count、source backend 和 thumbnail max size。
- `tests/test_priors.py` 新增可选 tissue overview manifest 组装测试，并更新 CLI 构建测试覆盖 `--wsi-tissue-overview`。
- README 同步更新 prior manifest 构建说明和可选 tissue overview 追踪边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/priors/__init__.py`
- `tests/test_priors.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.49.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_priors -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 生成 `wsi_tissue_overview.json`，再通过 `build-prior-manifest --wsi-tissue-overview` 确认真实 artifact 可被 prior manifest 追踪。

## v0.48.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐真实 WSI 低倍组织概览 artifact：从输入 manifest 读取真实 WSI thumbnail，输出可审计的 tissue contour proxy，为 layout/mask prior、QC 和后续 de novo layout 采样建立 WSI-level 组织轮廓基础。

### 已做改动

- 版本号升级到 `v0.48.0`。
- 新增 `src/he_wsi_generator/priors/tissue.py`，提供 `build_wsi_tissue_overview_from_manifest()`，可从 OpenSlide 或 fixture reader 读取 WSI metadata / thumbnail 并写出 `wsi_tissue_overview` JSON。
- CLI 新增 `build-wsi-tissue-overview`，支持指定 reader backend、thumbnail max size 和输出路径。
- `wsi_tissue_overview` artifact 记录 slide metadata、manifest 摘要、thumbnail RGB 统计、tissue/background pixel count、tissue fraction、bounding box 和 connected component count，并明确其不是语义分割 mask。
- 新增 `tests/test_wsi_tissue_overview.py`，覆盖函数成功路径、空白 thumbnail 显式失败和 CLI 成功路径。
- README 同步新增 WSI tissue overview 用法和边界说明。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/tissue.py`
- `tests/test_wsi_tissue_overview.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.48.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_wsi_tissue_overview -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- 使用 `/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 执行 `build-wsi-tissue-overview --backend openslide`，确认可写出真实 `wsi_tissue_overview.json`。

## v0.47.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐 UI 配置的 YAML 支持，让 `write-ui-config` / `launch-ui` 相关配置能按路径后缀读写 JSON/YAML，并在缺少 PyYAML 时显式报错。

### 已做改动

- 版本号升级到 `v0.47.0`。
- `src/he_wsi_generator/ui/config.py` 按路径后缀支持 JSON/YAML 读写；`.yaml` / `.yml` 路径在缺少 PyYAML 时会显式报错。
- `tests/test_ui.py` 新增 YAML roundtrip 与缺依赖失败路径测试。
- README 同步更新 UI 配置格式说明和 YAML 使用示例。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/config.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.47.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_ui tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `python -m compileall src tests`
- `git diff --check`

## v0.46.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐输出摘要的 CLI 入口：UI controller 已有 `collect_output_summary()`，但命令行还没有一个可复现方式把 metadata + QC 汇总成稳定 JSON。

### 已做改动

- 版本号升级到 `v0.46.0`。
- CLI 新增 `inspect-output-summary --metadata <metadata.json> --qc <qc.json>`。
- `inspect-output-summary` 复用 `collect_output_summary()`，把 metadata + QC 汇总成 JSON 输出；坏输入会返回非零退出码并输出明确错误。
- 新增 CLI output summary 成功路径和坏 QC 失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_ui.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.46.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_ui.UITests.test_cli_inspects_output_summary tests.test_ui.UITests.test_cli_rejects_invalid_output_summary_qc -v`
- `PYTHONPATH=src python -m unittest tests.test_ui tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（137 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.45.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 执行命令的工作目录透传：`JobRunner.create_job()` 已支持 `cwd`，但 `run-local-job` 还没有暴露这个能力。

### 已做改动

- 版本号升级到 `v0.45.0`。
- `run-local-job` CLI 新增可选 `--cwd <path>`，并透传给 `JobRunner.create_job()`。
- 使用 `--cwd` 时，job record 现在会持久化 `cwd`，且命令在指定目录执行。
- 新增 `run-local-job --cwd` 成功路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.45.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_runs_local_job_with_cwd -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（135 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.44.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的批量查看入口：在 `run-local-job`、`cancel-local-job` 和 `inspect-local-job` 之外，再提供一个可复现的 list 命令，直接列出 job_root 下的持久化 job 状态。

### 已做改动

- 版本号升级到 `v0.44.0`。
- CLI 新增 `list-local-jobs <job_root>`。
- `list-local-jobs` 复用 `JobRunner.list_jobs()` 读取持久化 job record，并以 JSON 数组输出；坏记录不会被静默跳过。
- 新增 CLI list 成功路径和损坏记录失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/jobs.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.44.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_lists_local_jobs tests.test_job_runner.JobRunnerTests.test_cli_rejects_listing_corrupt_local_job_record -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（134 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.43.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地 job 的查看入口：在 `run-local-job` 和 `cancel-local-job` 之外，再提供一个可复现的 inspect 命令，把持久化 job 记录导出为 JSON，便于排障和状态查看。

### 已做改动

- 版本号升级到 `v0.43.0`。
- CLI 新增 `inspect-local-job <job_root> --job-id <id>`。
- `inspect-local-job` 复用 `JobRunner.load_job()` 读取持久化 job record；未知 job、非法 job id 或损坏 JSON 会返回非零退出码并输出明确错误。
- 成功时把完整 job record 以 JSON 输出到 stdout，便于脚本和人工查看。
- 新增 CLI inspect 成功路径、未知 job 失败路径和损坏记录失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.43.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_inspects_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_inspecting_unknown_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_inspecting_corrupt_local_job_record -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（132 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.42.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐本地任务取消的 CLI 入口，使已排队 job 可以通过可复现命令显式持久化为 `cancelled`。

### 已做改动

- 版本号升级到 `v0.42.0`。
- CLI 新增 `cancel-local-job <job_root> --job-id <id> [--message <message>]`。
- `cancel-local-job` 复用 `JobRunner.cancel_job()`，仅允许取消 queued job；非 queued job、未知 job 或非法 job id 会返回非零退出码并输出明确错误。
- 取消成功时写出 `job.json`、空 `stdout.txt` / `stderr.txt`，并在 stdout 输出 `local job cancelled` 和记录路径。
- 新增 CLI 取消成功路径和非 queued job 失败路径测试。
- 同步更新 README、VERSION、pyproject、默认配置、版本常量和版本断言。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `tests/test_job_runner.py`
- `tests/*.py`（版本字符串与断言同步到 `v0.42.0`）
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner.JobRunnerTests.test_cli_cancels_queued_local_job tests.test_job_runner.JobRunnerTests.test_cli_rejects_cancelling_non_queued_local_job -v`
- `PYTHONPATH=src python -m unittest tests.test_job_runner tests.test_version tests.test_cli -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（129 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`

## v0.41.0 - 2026-05-23

### 用户需求

- 用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。
- 本次版本补齐生成完成态审计：成功输出的 smoke generation 结果必须把 `tile_traversal_plan` 物化成完成态，避免把已完成样本保留为 pending 计划。

### 已做改动

- 版本号升级到 `v0.41.0`。
- 新增 `complete_tile_traversal_plan`，支持把 traversal plan 转换为完成态，并保留对部分完成状态的显式记录。
- `run_smoke_generation` 在写出 metadata 和 generation run summary 前，将 tile traversal plan 切换为完成态，成功样本现在能直接看到 `completed_tile_count`、`pending_tile_count`、`resume_index`、`next_tile_index` 和每个 tile 的完成状态。
- `run_smoke_generation` 同步把 `plan.stages` 切换为 completed，确保 generation run summary 反映真实执行态，而不是保留 planned 阶段状态。
- 新增针对 partial completion helper 的单元测试，并更新 smoke generation 端到端测试断言完成态字段。
- `build_qc_report` 现在会为 non-copy report 额外写入 thumbnail / tissue contour / mask layout / global embedding 四类 similarity proxy metrics，保留轻量审计但不做全量近邻检索。
- `build_qc_report` 还会写入 tile 级 seam score proxy 和 WSI 级 style consistency proxy，并把 tile 级 metrics 纳入 overall status。
- `run_smoke_generation` 现在会按 `canvas_size_40x` 真正拼接 1/1 canvas，再输出 pyramid 和 mask，而不是固定写死 512 方块。
- `JobRunner` 新增 `cancel_job`，可把 queued job 显式转成 `cancelled` 并持久化终态记录。
- 同步更新 README、VERSION、pyproject、默认配置和版本断言。

### 影响文件

- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/generation/executor.py`
- `tests/test_generation_tiling.py`
- `tests/test_generation_runner.py`
- `src/he_wsi_generator/constants.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `tests/*.py`（版本字符串与断言同步到 `v0.41.0`）

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_models_generation -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`（127 tests passed, 21 skipped）
- `python -m compileall src tests`
- `git diff --check`

## v0.40.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进生成输出的可审计性：把 `tile_traversal_plan` 写入 smoke generation metadata，便于从单个产物直接追溯 traversal / resume / write-region 信息。

### 已做改动

- 版本号升级到 `v0.40.0`。
- `run_smoke_generation` 在 metadata 的 `generation` 字段中写入 `tile_traversal_plan`，与 run summary 中的物化 plan 保持一致。
- `tile_traversal_plan` 直接复用 `create_generation_plan` 的输出，不在 metadata 层重建。
- 新增/更新 `tests/test_generation_runner.py`，覆盖 metadata 里的 `tile_traversal_plan`、tile count 和 tile origin。
- 更新 README 当前能力描述，说明 smoke metadata 现在也记录物化 traversal plan。
- 更新 `docs/DEMANDS.MD`，记录 v0.40.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_generation_tiling.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling -v`
- `PYTHONPATH=src python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_config_rejects_invalid_canvas_size -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_generation_runner tests.test_models_generation tests.test_schemas tests.test_version -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.39.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.4 中 production cascade sampler 的前置执行能力：把 `tile traversal`、`resume index` 和 `overlap weighted blending` 从 generation plan 的字符串说明推进为可测试、可审计的基础设施。

### 已做改动

- 版本号升级到 `v0.39.0`。
- 新增 `src/he_wsi_generator/generation/tiling.py`，提供 `create_tile_traversal_plan` 和 `blend_rgb_tiles`。
- `create_tile_traversal_plan` 按 40x canvas、模型 tile size 和 overlap 生成 row-major traversal plan，记录 resume index、tile 总数、已完成/待处理 tile 数、下一待处理 tile、tile origin、write region、stride、状态和 edge crop 策略。
- Traversal 对 canvas、tile size、overlap 和 resume index 做显式校验，非法输入通过 `GenerationTilingError` 报错。
- `blend_rgb_tiles` 支持按 tile origin 把多个 uint8 RGB tile 写入 canvas，并对 overlap 区域执行权重平均；非 RGB、非 uint8、非法 origin、空 tile 列表和未覆盖完整 canvas 会显式报错。
- `create_generation_plan` 新增 `tile_traversal_plan` 字段，同时保留既有 `tile_traversal`、`blending` 和 `write_mode` 字段。
- `validate_generation_config` 支持并校验可选 `canvas_size_40x`；默认生成配置写入 `[512, 512]`。
- 新增 `tests/test_generation_tiling.py`，覆盖 traversal/resume/edge crop、overlap weighted blending 和未覆盖 canvas 错误路径。
- 更新 `tests/test_models_generation.py` 和 `tests/test_schemas.py`，覆盖 generation plan 物化 traversal plan 与 `canvas_size_40x` 校验。
- README 更新 v0.39.0 当前能力、tiling/blending 基础设施和非 production 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.39.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/generation/tiling.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_generation_tiling.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_models_generation.ModelGenerationSkeletonTests.test_generation_plan_accepts_trained_checkpoint_manifest -v`
- `PYTHONPATH=src python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_config_rejects_invalid_canvas_size -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_tiling tests.test_models_generation tests.test_schemas tests.test_version -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.38\.0|version = "0\.38\.0"|PROJECT_VERSION = "v0\.38\.0"|PACKAGE_VERSION = "0\.38\.0"' VERSION README.md pyproject.toml configs src tests`

## v0.38.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.4 的推理顺序要求：`torch-diffusion-smoke` generation backend 必须按 `1/32 -> 1/16 -> 1/4 -> 1/1` 执行级联采样，并保存每层中间状态。

### 已做改动

- 版本号升级到 `v0.38.0`。
- `run_torch_diffusion_smoke_generation` 从单次 `1/1` sampling 改为四层 cascade sampling。
- 每个 cascade level 写入独立 sample 目录和 `sample_manifest.json`。
- `1/32` 使用默认 zero previous-scale condition；`1/16`、`1/4`、`1/1` 将上一层 `sample_preview.npy` 作为 `previous_scale_condition_path` 传给 sampler。
- `generation_run.json` 和 metadata generation 字段新增 `cascade_sample_manifests`，记录每层 level、sample manifest、sample preview、cross-scale condition source 和 previous-scale path。
- OME-TIFF pyramid 由四层 cascade sample preview 分别 resize 组装，不再只从最终 `1/1` preview 派生所有层。
- Torch diffusion smoke plan stage 的 condition inputs 新增 `previous_scale_rgb_proxy` 和 `condition_feature_channels`，并记录四层状态为 completed。
- 新增/更新 `tests/test_torch_training.py`，覆盖 cascade sample manifests、metadata/run summary 记录、previous-scale path 链式传递、condition packet 在四层 sampler 中复用和 OME-TIFF 层级输出。
- README 更新四层级联 smoke generation 行为和当前非 production 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.38.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.37\.0|version = "0\.37\.0"|PROJECT_VERSION = "v0\.37\.0"|PACKAGE_VERSION = "0\.37\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.38\.0|version = "0\.38\.0"|cascade_sample_manifests|torch_diffusion_cascade_samples|previous_scale_rgb_proxy' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.37.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1 的“上一尺度图像 / latent”条件输入要求：让 PyTorch diffusion smoke denoiser 接收可审计的上一尺度 RGB proxy 条件通道。

### 已做改动

- 版本号升级到 `v0.37.0`。
- Diffusion smoke checkpoint payload、checkpoint manifest 和 sampler manifest 新增 `cross_scale_condition_schema`。
- `train_torch_diffusion_smoke_model` 在 denoiser 输入中拼接 3 个上一尺度 RGB proxy 条件通道。
- 训练期 cross-scale condition 从真实 RGB tile 构建：非根层级先降采样到上一 cascade proxy 尺度，再上采样到 latent grid；`1/32` 根层级使用显式 zero previous-scale condition。
- Denoiser input channels 与 `denoiser_architecture.input_channels` 同步包含 current latent、previous-scale RGB proxy、6 类 mask、timestep 和 7 个 condition feature channels。
- `sample_torch_diffusion_smoke_model` 新增可选 `previous_scale_condition_path`，支持读取 `.npy` RGB preview 作为 previous-scale condition；未提供时显式记录 `cross_scale_condition_source=default_zero_previous_scale`。
- CLI `sample-torch-diffusion-smoke` 新增 `--previous-scale-condition` 参数。
- Sampling 校验 checkpoint manifest/payload 中的 `cross_scale_condition_schema`，缺失或不匹配时显式报错。
- 新增/更新 `tests/test_torch_training.py`，覆盖训练 manifest/payload schema、input channel 增量、VAE latent 兼容、sampler 默认 zero source、显式 previous-scale source、CLI 参数和缺失 schema 错误路径。
- README 更新 cross-scale condition 用法、`--previous-scale-condition` 参数和 smoke-only 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.37.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_writes_proxy_preview tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_previous_scale_condition tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_rejects_missing_cross_scale_condition_schema tests.test_torch_training.TorchSmokeTrainingTests.test_cli_samples_torch_diffusion_smoke_model -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.36\.0|version = "0\.36\.0"|PROJECT_VERSION = "v0\.36\.0"|PACKAGE_VERSION = "0\.36\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.37\.0|version = "0\.37\.0"|cross_scale_condition_schema|previous_scale_condition|--previous-scale-condition|previous_scale_rgb_proxy' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.36.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1 的 `latent_diffusion_unet` 主干要求：把 PyTorch diffusion smoke denoiser 从简单卷积堆栈升级为带 downsample、bottleneck、upsample 和 skip connection 的 smoke U-Net。

### 已做改动

- 版本号升级到 `v0.36.0`。
- `_MaskConditionedLatentDenoiser` 从普通卷积堆栈升级为 smoke latent U-Net，包含 `encoder_block`、`downsample`、`bottleneck`、`upsample`、`decoder_block` 和 `output_block`。
- Smoke latent U-Net 采用 32 个 base channels、64 个 bottleneck channels、1 个 downsample stage，并通过 encoder/decoder concat skip connection 保留空间条件信息。
- Diffusion checkpoint payload 与 checkpoint manifest 新增 `denoiser_architecture`，记录 architecture 名称、base/bottleneck channels、downsample stages、skip connection 语义、input source、input/output channels、支持的 latent sources 和 smoke-only production 状态。
- `sample_torch_diffusion_smoke_model` 采样前校验 checkpoint manifest 与 payload 的 `denoiser_architecture`，缺失、不匹配或旧结构 checkpoint 会显式报错。
- Sampler manifest 新增 `denoiser_architecture`，便于审计当前 sample 使用的 denoiser 结构。
- 保持 `rgb_downsample_proxy` 和 `trainable_vae_smoke` 两条 latent 路径可用，U-Net output channels 按 latent channel 数配置。
- 新增/更新 `tests/test_torch_training.py`，覆盖架构记录、state_dict 中 U-Net block key、VAE latent output channel 兼容，以及 manifest/payload 缺失 `denoiser_architecture` 的错误路径。
- README 更新 PyTorch diffusion smoke U-Net 行为、checkpoint 架构契约和当前 smoke-only 边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.36.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_rejects_missing_denoiser_architecture -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.35\.0|version = "0\.35\.0"|PROJECT_VERSION = "v0\.35\.0"|PACKAGE_VERSION = "0\.35\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.36\.0|version = "0\.36\.0"|denoiser_architecture|smoke_latent_unet|encoder_decoder_concat|smoke latent U-Net' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.35.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 v0.34.0 VAE smoke checkpoint 与 diffusion smoke 的连接：让 diffusion smoke trainer/sampler 可以选择使用 `trainable_vae_smoke` latent，而不是只能使用 `rgb_downsample_proxy`。

### 已做改动

- 版本号升级到 `v0.35.0`。
- `train_torch_diffusion_smoke_model` 新增可选 `vae_checkpoint_manifest_path` 参数。
- CLI `train-torch-diffusion-smoke` 新增 `--vae-checkpoint-manifest` 参数。
- 使用 VAE checkpoint 时，diffusion trainer 会加载并校验 VAE smoke checkpoint，通过 VAE encoder 的 `mu` 构造 latent batch。
- Diffusion checkpoint payload/manifest 在 VAE latent 路径下记录 `latent_source=trainable_vae_smoke`、`vae_checkpoint_manifest_path`、VAE checkpoint hash、latent channel 数、latent batch shape、input channels 和 output channels。
- Denoiser 输出通道从固定 3 改为按 latent channel 数配置，兼容 RGB proxy latent 和 VAE latent。
- `sample_torch_diffusion_smoke_model` 遇到 `latent_source=trainable_vae_smoke` 时加载 VAE checkpoint，通过 VAE decoder 将 sampled latent 解码成 RGB preview。
- `sample_manifest.json` 新增 `latent_sample_shape`，并在 VAE latent 路径下记录 VAE checkpoint 路径与 hash。
- 旧的 `rgb_downsample_proxy` diffusion smoke 训练/采样路径保持可用；未提供 VAE checkpoint 时不伪装为 VAE latent。
- 新增/更新 `tests/test_torch_training.py`，覆盖 VAE latent diffusion 直接训练、采样解码、CLI 训练参数和 manifest 字段。
- README 更新 VAE latent diffusion smoke 用法，并明确当前仍是 smoke 级 VAE/diffusion 闭环，不是 production WSI latent diffusion generator。
- 更新 `docs/DEMANDS.MD`，记录 v0.35.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_uses_vae_latent_checkpoint -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_decodes_vae_latent_preview tests.test_torch_training.TorchSmokeTrainingTests.test_cli_trains_torch_diffusion_smoke_model_with_vae_latent -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.34\.0|version = "0\.34\.0"|PROJECT_VERSION = "v0\.34\.0"|PACKAGE_VERSION = "0\.34\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.35\.0|version = "0\.35\.0"|--vae-checkpoint-manifest|vae_checkpoint_manifest_path|trainable_vae_smoke|latent_sample_shape|vae_checkpoint_sha256' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.34.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 7.1/7.2 的 VAE latent 缺口：新增 PyTorch VAE smoke trainer，使项目不再只有 RGB downsample proxy latent，而是具备可训练、可审计的 latent autoencoder 工程入口。

### 已做改动

- 版本号升级到 `v0.34.0`。
- 新增 `train_torch_vae_smoke_model`，从 training-index 读取真实 RGB image tile，训练小型 PyTorch VAE smoke autoencoder。
- VAE smoke trainer 包含 encoder、reparameterization 和 decoder，并真实执行 reconstruction loss + KL loss 的反向传播。
- 新增 CLI `train-torch-vae-smoke <training-index.jsonl> --output-dir <dir> --batch-size <n>`，支持 split、cascade level、epochs、learning rate、random seed、device、latent channels、latent size 和 KL weight。
- `model.pt` payload 记录 `target_type=vae_rgb_reconstruction`、`latent_source=trainable_vae_smoke`、latent channels、latent size、latent batch shape、loss histories 和 KL weight。
- `checkpoint_manifest.json` 记录 checkpoint hash、training log、latent/reconstruction preview、batch summary、loss summary 和 `usable_for_inference=false`。
- Trainer 写出 `latent_preview.npy` 与 `reconstruction_preview.npy`，用于审计 latent shape 和 smoke 重建输出。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用、checkpoint payload、manifest 字段、preview 文件形状和 CLI 行为。
- README 更新 VAE smoke training 用法，并明确当前 VAE 只验证 trainable latent autoencoder 路径，尚未接入 diffusion trainer/sampler，也不是 production WSI VAE。
- 更新 `docs/DEMANDS.MD`，记录 v0.34.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_vae_smoke_model_writes_latent_autoencoder_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_cli_trains_torch_vae_smoke_model -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.33\.0|version = "0\.33\.0"|PROJECT_VERSION = "v0\.33\.0"|PACKAGE_VERSION = "0\.33\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.34\.0|version = "0\.34\.0"|train-torch-vae-smoke|train_torch_vae_smoke_model|trainable_vae_smoke|vae_rgb_reconstruction|latent_preview|reconstruction_preview' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.33.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 6.3 与 7.1 的条件注入路径：让 PyTorch diffusion smoke denoiser 不再只记录 `generation_condition_packet`，而是把条件包中的 style、texture、coordinate、source 和 structure anchor 摘要编码为空间条件通道参与训练/采样。

### 已做改动

- 版本号升级到 `v0.33.0`。
- 新增 PyTorch diffusion smoke condition feature schema，固定记录 7 个条件特征：style seed、texture cluster、tile origin x/y、cascade level、source enabled 和 structure anchor。
- `train_torch_diffusion_smoke_model` 的 denoiser 输入从 RGB proxy latent + mask + timestep 扩展为 RGB proxy latent + mask + timestep + condition feature channels。
- 训练期 condition feature 使用 training-index tile 坐标/cascade 和零值 style/texture/source/anchor 默认策略，避免伪造 production prior。
- Checkpoint payload 和 checkpoint manifest 记录 `condition_feature_schema`，`input_channels` 同步包含 7 个 condition feature channels。
- `sample_torch_diffusion_smoke_model` 在提供 condition packet 时把条件摘要编码为 `condition_feature_vector`，并作为 constant spatial condition channels 拼接到 denoiser 输入。
- 未提供 condition packet 时，sampler 显式记录 `condition_feature_source=default_zero` 和全零 `condition_feature_vector`。
- `sample_manifest.json` 新增 `condition_feature_schema`、`condition_feature_source` 和 `condition_feature_vector`。
- Sampling 校验 checkpoint manifest/payload 的 condition feature schema，缺失或不匹配时显式报错。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 通过 sampler 使用同一份 condition feature vector，并继续保持 sampler manifest、metadata 和 generation run summary 可审计。
- 新增/更新 `tests/test_torch_training.py`，覆盖训练 manifest、checkpoint payload、sampler manifest 和 generation 中的 condition feature schema/vector。
- README 更新 PyTorch diffusion smoke condition feature channel 行为，并明确当前仍不是 production VAE latent、完整 U-Net/ControlNet 或多倍率真实条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.33.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_writes_proxy_preview tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.32\.0|version = "0\.32\.0"|PROJECT_VERSION = "v0\.32\.0"|PACKAGE_VERSION = "0\.32\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.33\.0|version = "0\.33\.0"|condition_feature_schema|condition_feature_vector|condition_feature_source|CONDITION_FEATURES|condition feature channels' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.32.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本把 v0.30.0/v0.31.0 的 `generation_condition_packet` 记录链路从 `smoke-cascade` 扩展到 PyTorch diffusion smoke sampling/generation：`sample-torch-diffusion-smoke` 和 `run-generation --backend torch-diffusion-smoke` 可以显式消费、校验并记录同一份条件包。

### 已做改动

- 版本号升级到 `v0.32.0`。
- `sample_torch_diffusion_smoke_model` 新增可选 `condition_packet_path` 和 `expected_prior_id` 参数。
- PyTorch diffusion smoke sampler 新增 condition packet 读取与校验：检查 schema version、condition packet type、必要条件对象，并在需要时检查 `prior_id`。
- `sample_manifest.json` 新增 `condition_packet_path` 和 `condition_summary`，记录 cascade level、tile origin、style seed、texture cluster、source condition 和 structure anchor 摘要。
- CLI `sample-torch-diffusion-smoke` 新增 `--condition-packet` 参数。
- `run_torch_diffusion_smoke_generation` 新增可选 `condition_packet_path` 参数，并传给 PyTorch smoke sampler。
- `run-generation --backend torch-diffusion-smoke --condition-packet` 会要求条件包 `prior_id` 与当前 prior manifest 一致；不一致时显式报错。
- PyTorch diffusion smoke generation 的 metadata、`generation_run.json` 和 sampler `sample_manifest.json` 记录同一份 condition packet 路径与摘要。
- 未提供 condition packet 时保持既有 PyTorch diffusion smoke 行为，不伪造条件包。
- 新增/更新 `tests/test_torch_training.py`，覆盖 sampler 直接调用、sampler CLI、generation 直接调用、generation CLI、metadata/run summary/sample manifest 记录和 prior id mismatch 错误路径。
- README 更新 PyTorch diffusion smoke sampling/generation 的 `--condition-packet` 用法，并明确当前只是审计记录，不是 production layout/style/texture 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.32.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/models/torch_training.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_sample_torch_diffusion_smoke_model_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_cli_samples_torch_diffusion_smoke_model_with_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_records_condition_packet tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_rejects_condition_prior_mismatch -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.31\.0|version = "0\.31\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.32\.0|version = "0\.32\.0"|sample-torch-diffusion-smoke|condition_packet_path|condition_summary|--condition-packet' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.31.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 v0.30.0 条件包与生成执行链路的连接：让 `run-generation --backend smoke-cascade` 可以显式消费 `generation_condition_packet`，并把条件包路径与关键条件摘要写入 metadata 和 generation run summary。

### 已做改动

- 版本号升级到 `v0.31.0`。
- `run_smoke_generation` 新增可选 `condition_packet_path` 参数。
- CLI `run-generation` 新增可选 `--condition-packet` 参数，传给 `smoke-cascade` backend。
- Smoke generation 新增 condition packet 读取与校验：检查 schema version、condition packet type、prior id 和必要条件对象。
- 条件包 `prior_id` 与当前 prior manifest 的 `prior_id` 不一致时显式报错。
- Metadata 的 `generation` 字段新增 `condition_packet_path` 和 `condition_summary`，记录 cascade level、tile origin、style seed、texture cluster、source condition 和 structure anchor 摘要。
- `generation_run.json` 新增 condition packet 路径和同一份摘要，便于批量审计。
- 未提供 condition packet 时保持既有 smoke backend 行为，不静默伪造条件包。
- 新增/更新 `tests/test_generation_runner.py`，覆盖直接函数调用、CLI `--condition-packet`、metadata/run summary 记录和 prior id mismatch 错误路径。
- README 更新 smoke generation 记录 condition packet 的用法，并说明当前仍不是 production diffusion 条件采样。
- 更新 `docs/DEMANDS.MD`，记录 v0.31.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.30\.0|version = "0\.30\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.31\.0|version = "0\.31\.0"|--condition-packet|condition_packet_path|condition_summary|generation_condition_packet' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.30.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 6.3 的 prior 与生成模型连接：把 `prior_manifest.json` 和 generation config 解析为可审计的 generation condition packet，使 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition` 和 `structure_anchor` 成为明确 JSON 条件对象。

### 已做改动

- 版本号升级到 `v0.30.0`。
- 新增 `build_generation_condition_packet`，从 generation config、prior manifest、cascade level 和 40x tile 坐标构建条件包 JSON。
- 新增 `GenerationConditionError`，将 artifact 缺失、artifact 非 JSON、artifact 类型不匹配、缺失 texture prototypes、非法 cascade level 或负坐标等错误显式暴露。
- Builder 复用 `validate_generation_config` 和 `load_prior_manifest`，继续执行 schema、artifact 文件、hash 与 size 校验。
- Builder 读取四类 artifact JSON，校验 `layout_mask_prior` / `style_prior` / `texture_prior` 的 `prior_type`，以及 `qc_reference_distribution.source`。
- Condition packet 显式记录 `layout`、`mask`、`style_seed`、`texture_token`、`coord`、`source_condition`、`structure_anchor` 和 QC reference 摘要。
- `style_seed=auto` 时采用 deterministic `random_seed` 解析并记录来源；整数 style seed 原样记录。
- `texture_token` 从 `texture_prior.texture_prototypes` 按 random seed 确定性选择，记录 cluster id、selection policy 和 representative embedding index。
- 新增 CLI `build-condition-packet <generation-config> --prior-manifest <prior_manifest.json> --output <condition_packet.json> --cascade-level <level> --tile-origin-x <x> --tile-origin-y <y>`。
- 新增 `tests/test_generation_conditioning.py`，覆盖直接函数调用、CLI 行为、condition packet 字段、auto style seed 解析、texture token 选择、source condition 和错误路径。
- README 更新 `build-condition-packet` 用法，并说明当前输出是可审计条件包契约，不是 production diffusion 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.30.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/conditioning.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_conditioning.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_conditioning -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.29\.0|version = "0\.29\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.30\.0|version = "0\.30\.0"|build-condition-packet|build_generation_condition_packet|GenerationConditionError|generation_condition_packet|texture_token' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.29.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 prior artifact 汇总能力：把已可独立生成的 `layout_mask_prior`、`style_prior`、`texture_prior` 和 `qc_reference_distribution` JSON 组装为统一、可校验、可复现的 `prior_manifest.json`，减少后续训练/生成入口对手工 manifest 编写的依赖。

### 已做改动

- 版本号升级到 `v0.29.0`。
- 新增 `build_prior_manifest_from_artifacts`，从四类 prior artifact JSON 构建并写出 `prior_manifest.json`。
- Builder 复用既有 `create_prior_artifact_entry`、`save_prior_manifest` 和 `load_prior_manifest` 校验契约，继续记录 artifact path、kind、sha256、size_bytes 和 metadata。
- Builder 读取 artifact JSON 并校验 `layout_mask_prior`、`style_prior`、`texture_prior` 的 `prior_type`，校验 `qc_reference_distribution` 的 `source` 和 `metrics`。
- Artifact metadata 新增 artifact type、artifact schema version、sample/embedding/cluster 等可直接审计的摘要字段。
- 新增 CLI `build-prior-manifest`，支持输出目录、prior id、dataset id、input manifest、training data version、可重复 WSI id、random seed 和四类 artifact 路径参数。
- 新增/更新 `tests/test_priors.py`，覆盖直接函数调用、CLI 行为、manifest roundtrip 校验、artifact metadata 摘要和 artifact 类型不匹配错误路径。
- README 更新 `build-prior-manifest` 用法，并说明当前只做 prior manifest 汇总，不实现 prior 采样策略或 production diffusion 条件注入。
- 更新 `docs/DEMANDS.MD`，记录 v0.29.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_priors -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg -n 'v0\.28\.0|version = "0\.28\.0"' VERSION README.md pyproject.toml configs src tests`
- `rg -n 'v0\.29\.0|version = "0\.29\.0"|build-prior-manifest|build_prior_manifest_from_artifacts|prior_manifest.json|qc_reference_distribution' VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.28.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `texture_prior` 的工程基础：从 embedding cache 和 cluster report 中读取真实 patch embedding 与聚类标签，构建可审计的统计型 texture prior JSON，供 prior manifest、texture/morphology 条件和后续 non-copy/global similarity QC 复用。

### 已做改动

- 版本号升级到 `v0.28.0`。
- 新增 `build_texture_prior_from_embedding_cache`，从 embedding cache 与 cluster report 构建 `texture_prior.json`。
- 新增 `TexturePriorBuildError`，将缺失 cache、cluster report 非 JSON、labels 数量不匹配、embedding dim 不匹配、cluster counts 不一致和非有限 embedding 等错误显式暴露。
- 新增 CLI `build-texture-prior --cache-dir <dir> --cache-key <key> --cluster-report <cluster-report.json> --output <texture_prior.json>`。
- Texture prior JSON 记录 schema version、prior type、embedding cache 来源、embedding metadata、cluster report summary、embedding count、embedding dim 和 cluster count。
- Texture prior JSON 记录 global embedding mean/std，以及每个 cluster 的 sample count、fraction、mean embedding、embedding std 和 representative embedding index。
- 新增 `tests/test_texture_prior.py`，覆盖直接函数调用、CLI 行为、prototype 统计、global embedding 统计、metadata 记录和 label count mismatch 错误路径。
- README 更新 `build-texture-prior` 用法，并说明当前产物是统计型 texture prior，不是 trainable texture codebook、VQ-VAE 或 morphology token sampler。
- 更新 `docs/DEMANDS.MD`，记录 v0.28.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/layout.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/priors/texture.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_texture_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_texture_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.27.0|version = \"0.27.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.28.0|version = \"0.28.0\"|build-texture-prior|build_texture_prior_from_embedding_cache|TexturePriorBuildError|texture_prior|texture_prototypes" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.27.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `layout_mask_prior` 的工程基础：从 training-index 中真实读取 6 类 mask tile，构建可审计的统计型 layout/mask prior JSON，供 prior manifest、de novo layout 采样和后续 generation conditioning 复用。

### 已做改动

- 版本号升级到 `v0.27.0`。
- 新增 `build_layout_mask_prior_from_training_index`，从 training-index batch 读取真实 mask tile 并写出 `layout_mask_prior.json`。
- 新增 `LayoutMaskPriorBuildError`，将缺失 mask、非法 batch size、未知 split/level、mask 维度非法和 label mapping 不完整等 training batch 错误显式暴露。
- 新增 CLI `build-layout-mask-prior <training-index.jsonl> --batch-size <n> --output <layout_mask_prior.json>`，支持 `--split` 和 `--cascade-level`。
- Layout/mask prior JSON 记录 schema version、prior type、training-index 来源、batch size、split、cascade level、sample ids、WSI ids、tile records、mask batch shape、mask class ids 和 batch summary。
- Layout/mask prior JSON 记录 6 类名称、每类 pixel count、fraction、present flag、non-background fraction 和 tile-level dominant class。
- Layout/mask prior JSON 记录每个 tile 的 class fractions、source WSI id，并统计横向/纵向相邻类别 pair counts。
- 输出不写入完整 `mask_batch`，避免把训练 mask 数组直接塞进 prior JSON。
- 新增 `tests/test_layout_mask_prior.py`，覆盖直接函数调用、CLI 行为、统计字段、tile-level layout records、adjacency counts 和缺失 mask 错误路径。
- README 更新 `build-layout-mask-prior` 用法，并说明当前产物是统计型 layout/mask prior，不是可采样 layout generator、mask diffusion 或 source-anchor layout mixing 模型。
- 更新 `docs/DEMANDS.MD`，记录 v0.27.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/layout.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_layout_mask_prior.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_layout_mask_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.26.0|version = \"0.26.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.27.0|version = \"0.27.0\"|build-layout-mask-prior|build_layout_mask_prior_from_training_index|LayoutMaskPriorBuildError|layout_mask_prior|adjacency_counts" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.26.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `global_imaging_style_prior` 的工程基础：从 training-index 中真实读取 RGB tile，构建可审计的统计型 `style_prior` JSON，供 prior manifest 和后续 generation style conditioning 复用。

### 已做改动

- 版本号升级到 `v0.26.0`。
- 新增 `build_style_prior_from_training_index`，从 training-index batch 读取真实 RGB image tile 并写出 `style_prior.json`。
- 新增 `StylePriorBuildError`，将缺失 WSI、非法 batch size、未知 split/level、无法读取 RGB tile 等 training batch 错误显式暴露。
- 新增 CLI `build-style-prior <training-index.jsonl> --batch-size <n> --output <style_prior.json>`，支持 `--split` 和 `--cascade-level`。
- Style prior JSON 记录 schema version、prior type、training-index 来源、batch size、split、cascade level、sample ids、WSI ids、tile records、image batch shape/dtype 和 batch summary。
- Style prior JSON 记录 RGB mean/std/min/max、归一化 mean/std，以及每个 tile 的 mean RGB 和 source WSI id。
- 输出不写入完整 `image_batch`，避免把训练图像数组直接塞进 prior JSON。
- 新增 `tests/test_style_prior.py`，覆盖直接函数调用、CLI 行为、统计字段、tile-level style records 和缺失 WSI 错误路径。
- README 更新 `build-style-prior` 用法，并说明当前产物是统计型 style prior，不是 trainable style encoder、VAE style latent 或风格迁移模型。
- 更新 `docs/DEMANDS.MD`，记录 v0.26.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/style.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_style_prior.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_style_prior -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.25.0|version = \"0.25.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.26.0|version = \"0.26.0\"|build-style-prior|build_style_prior_from_training_index|StylePriorBuildError|style_prior|mean_rgb_normalized" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.25.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进完整生成输出链路：在已有 PyTorch diffusion smoke sampler 基础上，新增 `torch-diffusion-smoke` generation backend，使 PyTorch sampler 输出能够进入 OME-TIFF、mask、metadata、QC 和 batch index 归档链路。

### 已做改动

- 版本号升级到 `v0.25.0`。
- 新增 `run_torch_diffusion_smoke_generation`，用于从 generation config、prior manifest、diffusion smoke checkpoint 和 training-index 生成完整 smoke sample 对象。
- CLI `run-generation` 新增 backend 选择 `torch-diffusion-smoke`。
- `run-generation` 新增 `--training-index` 和 `--batch-size` 参数，`torch-diffusion-smoke` backend 缺少 `--training-index` 时显式报错。
- Backend 调用 `sample_torch_diffusion_smoke_model`，复用 generation config 中的 `sample_steps` 和 `random_seed`。
- Backend 读取 sampler 的 `sample_preview.npy`，用 nearest resize 构造 `1/1`、`1/4`、`1/16`、`1/32` 四层小型 pyramid。
- Backend 从 training-index batch 读取 mask，写出与 `1/1` 输出对齐的 `.npy` mask。
- Backend 复用现有 `write_pyramid_ome_tiff`、`write_mask_array`、`build_qc_report` 和 `archive_sample` 写出 OME-TIFF、mask、metadata、QC、batch index 和 generation run summary。
- Metadata 记录 `generation_backend=torch-diffusion-smoke`，generation run summary 记录 sample manifest 路径。
- QC non-copy report 记录该 backend 是 PyTorch diffusion smoke backend，不是 production WSI diffusion generator。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用和 CLI 行为，验证 metadata、QC、batch index、sample manifest、OME-TIFF pyramid shape 和 backend 标记。
- README 更新 `torch-diffusion-smoke` generation 用法和当前仍未实现 production inference、VAE decode、tile stitching、gigapixel chunked OME-TIFF 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.25.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend torch-diffusion-smoke --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/torch-diffusion-run/checkpoint_manifest.json" --training-index "$tmpdir/training-index.jsonl" --output-root "$tmpdir/generated/gen-torch-smoke" --generated-id gen-torch-smoke --batch-size 1`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg -n '[ \t]+$' README.md VERSION pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`
- `rg "v0.24.0|version = \"0.24.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.25.0|version = \"0.25.0\"|torch-diffusion-smoke|run_torch_diffusion_smoke_generation|sample_manifest_path|training-index" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.24.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进推理/采样链路：在已有 DDPM-style diffusion smoke trainer 基础上，新增一个可审计的 PyTorch diffusion smoke sampler，用于验证 checkpoint 加载、mask 条件输入、反向 DDPM-style 采样和 preview 输出链路。

### 已做改动

- 版本号升级到 `v0.24.0`。
- 新增 `sample_torch_diffusion_smoke_model`，支持从 diffusion smoke checkpoint manifest 和 training-index mask 条件执行 proxy latent smoke sampling。
- 新增 CLI `sample-torch-diffusion-smoke <checkpoint_manifest.json> <training-index.jsonl> --output-dir <dir> --batch-size <n>`。
- Sampler 校验 checkpoint manifest 必须为 `torch-smoke-mask-conditioned-latent-diffusion` 且 `target_type=diffusion_noise`。
- Sampler 读取 checkpoint payload，恢复 `_MaskConditionedLatentDenoiser` 的 `state_dict`，复用 `linear_ddpm` schedule 和 `rgb_downsample_proxy` latent shape。
- Sampler 通过 `load_training_batch(..., include_image=False)` 读取 mask 条件，并构造下采样 6 类 mask 条件和 timestep channel。
- Sampler 执行反向 DDPM-style smoke update，输出 `sample_preview.npy` 和 `sample_manifest.json`。
- `sample_manifest.json` 记录 sampling backend、checkpoint 来源、sample path、shape、dtype、sample steps、random seed、diffusion schedule、batch summary，并明确 `usable_for_production=false`。
- 新增 checkpoint manifest/payload/schedule 校验，缺失 checkpoint、非 diffusion smoke checkpoint、非法 sample steps、sample steps 超过 diffusion timesteps 或 schedule 不合法时显式报错。
- 新增/更新 `tests/test_torch_training.py`，覆盖直接函数调用、CLI 行为、preview `.npy` shape/dtype、sample manifest 字段和 non-production 标记。
- README 更新 diffusion smoke sampling 用法和当前仍未实现 production sampler、VAE decoder、`run-generation` 接入、OME-TIFF 输出的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.24.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli sample-torch-diffusion-smoke "$tmpdir/torch-diffusion-run/checkpoint_manifest.json" "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-diffusion-sample" --batch-size 2 --split train --cascade-level 1/1 --sample-steps 4`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.23.0|version = \"0.23.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.24.0|version = \"0.24.0\"|sample-torch-diffusion-smoke|sample_torch_diffusion_smoke_model|torch-smoke-mask-conditioned-latent-diffusion-sampler|sample_preview|usable_for_production" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.23.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 M5 中的 latent diffusion 训练目标：在已有 RGB training batch 与 PyTorch smoke training 基础上，新增一个真实执行 DDPM-style 加噪和噪声预测 loss 的 mask-conditioned latent diffusion smoke trainer。

### 已做改动

- 版本号升级到 `v0.23.0`。
- 新增 `train_torch_diffusion_smoke_model`，用于从 training-index 执行 PyTorch diffusion smoke training。
- 新增 CLI `train-torch-diffusion-smoke`，支持 `--diffusion-timesteps`、`--beta-start`、`--beta-end` 和 `--latent-size`。
- Trainer 继续通过 `load_training_batch(..., include_image=True)` 读取 mask batch 与 RGB image batch。
- 新增下采样 RGB proxy latent 构造，manifest 中记录 `latent_source=rgb_downsample_proxy`，避免伪装成 VAE latent。
- 新增线性 DDPM smoke schedule，记录 `scheduler=linear_ddpm`、`timesteps`、`beta_start`、`beta_end` 和 `latent_batch_shape`。
- 训练输入包含 noisy latent、下采样 6 类 mask 条件和 timestep channel，训练目标为加入的噪声，loss 名称为 `mse_noise_prediction`。
- 新增极小 mask-conditioned latent denoiser，真实执行 `torch.nn.Module`、loss、AdamW optimizer、反向传播和 `.pt` checkpoint 写出。
- `model.pt` payload 和 `checkpoint_manifest.json` 新增 `target_type=diffusion_noise`、`input_channels=10`、`output_channels=3`、diffusion schedule 与 image batch summary。
- Checkpoint manifest 继续明确 `usable_for_inference=false`，说明它不是 VAE latent diffusion generator。
- PyTorch 缺失错误信息泛化为 torch training commands，覆盖两个 PyTorch 训练命令。
- `tests/test_torch_training.py` 新增直接函数和 CLI 覆盖，断言 backend、diffusion target、scheduler、latent shape、checkpoint payload、image batch summary 和 finite loss。
- README 更新 PyTorch diffusion smoke training 用法和当前仍未实现 production latent diffusion U-Net、VAE latent、采样器、多倍率条件注入、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.23.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-diffusion-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-diffusion-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01 --diffusion-timesteps 8 --latent-size 64`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.22.0|version = \"0.22.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.23.0|version = \"0.23.0\"|train-torch-diffusion-smoke|torch-smoke-mask-conditioned-latent-diffusion|diffusion_noise|linear_ddpm|mse_noise_prediction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.22.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 PyTorch 训练链路：把 `train-torch-smoke` 从只训练 mask autoencoder，升级为消费 RGB image tile 的 mask-conditioned RGB reconstruction smoke backend，使训练 loop 开始学习 mask 条件到 H&E 图像像素的映射。

### 已做改动

- 版本号升级到 `v0.22.0`。
- `train_torch_smoke_model` 改为调用 `load_training_batch(..., include_image=True)`，训练前同时读取 mask batch 与 RGB image batch。
- PyTorch smoke backend 名称升级为 `torch-smoke-mask-conditioned-rgb-reconstructor`。
- 训练输入从 mask one-hot tensor 构造，训练目标从 RGB image tile 转为 `[0, 1]` 浮点 tensor。
- 模型从 mask autoencoder 改为极小的 mask-conditioned RGB reconstructor，输出 3 通道 sigmoid RGB，并使用 `mse_rgb_reconstruction` loss。
- `model.pt` payload 新增 `target_type=rgb_image`、`input_channels=6`、`output_channels=3` 和 `image_dtype`。
- `checkpoint_manifest.json` 新增 target type、输入/输出通道、loss 名称和 image batch summary，并继续明确 `usable_for_inference=false`。
- `tests/test_torch_training.py` 改为生成真实 fixture RGB slide，覆盖 backend 名称、RGB target、image batch summary、checkpoint payload 和 CLI 行为。
- 去除测试夹具中 Pillow 已弃用的 `mode` 参数，避免新版本 Pillow 输出 deprecation warning。
- README 更新 PyTorch smoke training 当前语义和仍未实现 latent diffusion、VAE latent、生产级图像重建/扩散损失、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.22.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-rgb-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `python - <<'PY' ...` 扫描 README、VERSION、pyproject、configs、src、tests、DEMANDS 和 CHANGELOG 的文本文件尾随空白
- `rg "v0.21.0|version = \"0.21.0\"" VERSION README.md pyproject.toml configs src tests`
- `rg "v0.22.0|version = \"0.22.0\"|torch-smoke-mask-conditioned-rgb-reconstructor|target_type|image_batch_shape|mse_rgb_reconstruction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.21.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实图像训练输入能力：在 training batch loader 中新增可选 RGB image tile 读取，使后续 PyTorch 图像生成训练不再只有 mask 条件输入。

### 已做改动

- 版本号升级到 `v0.21.0`。
- `load_training_batch` 新增 `include_image` 参数，默认保持只读 mask，显式启用时读取 RGB image tile。
- Training batch loader 使用 training-index 中的 `wsi_path`、tile 坐标和 source backend 读取图像 tile。
- 对 `fixture-image` backend，使用 Pillow 读取 PNG/TIFF 等小图并裁剪 RGB tile。
- 对 `openslide` backend，使用 OpenSlide `read_region` 读取 level0 tile 并转为 RGB。
- Loader 输出新增 `image_batch`、`image_batch_shape` 和 `image_dtype`。
- `training_batch_summary` 会排除完整 `mask_batch` 和 `image_batch` 数组，只保留 shape、dtype 和审计字段。
- 缺失 WSI 文件、图像不可读、tile 超出图像范围、未知 backend 或 OpenSlide 缺依赖时显式报错。
- CLI `inspect-training-batch` 新增 `--include-image`，用于训练前同时审计 mask 和 RGB tile 输入。
- `pyproject.toml` 中 `training` 和 `torch` 可选依赖补充 `Pillow>=9.0`。
- 新增/更新 `tests/test_training_batch.py`，覆盖 fixture image tile 读取、summary 不写完整 image batch、缺失 WSI 报错和 CLI `--include-image` 行为。
- 更新 README，说明 RGB/mask training batch loader 用法和当前仍未实现 VAE latent、图像重建损失、stain normalization、OpenSlide 多层采样策略的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.21.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/training_batch.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_batch -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-training-batch "$tmpdir/training-index.jsonl" --batch-size 2 --split train --cascade-level 1/1 --include-image --output "$tmpdir/batch-summary.json"`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.21.0|version = \"0.21.0\"|include-image|image_batch_shape|image_dtype|RGB/mask training batch" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.20.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实 PyTorch 训练 backend：在既有 training-index batch loader 基础上，新增一个真实调用 PyTorch 的 smoke training backend，用于验证训练 loop、loss、optimizer、checkpoint 写出和 manifest 记录链路。

### 已做改动

- 版本号升级到 `v0.20.0`。
- 新增 `he_wsi_generator.models.torch_training` 模块，提供 `train_torch_smoke_model` 和 `TorchTrainingError`。
- 新增 `torch-smoke-mask-autoencoder` backend，真实执行 `torch.nn.Module`、cross entropy loss、AdamW optimizer、反向传播和权重更新。
- Trainer 复用 `load_training_batch` 读取 training-index batch，并将 `.npy` mask batch 转成 torch tensor 和 one-hot 输入。
- Trainer 写出 `model.pt`、`training_log.jsonl`、`training_run.json` 和 `checkpoint_manifest.json`。
- Checkpoint manifest 记录 `training_backend`、`torch_version`、training parameters、loss summary、batch summary、checkpoint path 和 sha256。
- Smoke checkpoint 明确 `status=trained` 且 `usable_for_inference=false`，避免伪装成真实 latent diffusion 推理权重。
- PyTorch 未安装时，trainer 会显式报错，不静默回退到 numpy。
- CLI 新增 `he-wsi-gen train-torch-smoke <training-index.jsonl> --output-dir <dir> --batch-size <n>`，支持 `--split`、`--cascade-level`、`--epochs`、`--learning-rate`、`--random-seed` 和 `--device`。
- `pyproject.toml` 新增可选依赖组 `torch = ["numpy>=1.24", "torch>=2.5"]`。
- 新增 `tests/test_torch_training.py`，覆盖 PyTorch smoke trainer 产物、manifest 校验和 CLI 行为；无 torch 环境中真实 torch 用例会跳过。
- 更新 README，说明 PyTorch smoke training 用法和仍未实现 diffusion U-Net、噪声调度、VAE latent、图像重建、WSI 一致性训练及真实 inference backend 的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.20.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/torch_training.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_torch_training.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `conda run -n qupath-pytorch env PYTHONPATH=src python -m unittest tests.test_torch_training -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `conda run -n qupath-pytorch env PYTHONPATH=src python -m he_wsi_generator.cli train-torch-smoke "$tmpdir/training-index.jsonl" --output-dir "$tmpdir/torch-smoke-run" --batch-size 2 --split train --cascade-level 1/1 --epochs 1 --learning-rate 0.01`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.20.0|version = \"0.20.0\"|train-torch-smoke|TorchTrainingError|train_torch_smoke_model|torch-smoke-mask-autoencoder" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.19.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实 PyTorch 训练 backend 的前置输入能力：新增 training-index batch loader，使后续训练 loop 可以从 JSONL 样本索引读取、校验、抽样并形成可审计 batch，而不是只停留在索引文件。

### 已做改动

- 版本号升级到 `v0.19.0`。
- 新增 `he_wsi_generator.models.training_batch` 模块，提供 `load_training_batch`、`training_batch_summary`、`write_training_batch_summary` 和 `TrainingBatchError`。
- Batch loader 支持从 training-index JSONL 读取样本，并按可选 `split` 和 `cascade_level` 过滤。
- Loader 读取 `.npy` mask，按 training-index tile 坐标裁剪 batch mask，并按 label mapping 转成项目 6 类 id。
- Loader 输出包含 schema version、batch size、sample ids、cascade levels、WSI ids、tile records、mask batch shape、mask class ids、conditioning 和 source records。
- 对空 training-index、非法 JSON、缺失字段、非法 batch size、未知 split、未知 cascade level、缺失 mask、非法 mask 维度、非整数 mask id 和 tile 越界显式报错。
- 新增 CLI `he-wsi-gen inspect-training-batch <training-index.jsonl> --batch-size <n> --output <summary.json>`，支持 `--split` 和 `--cascade-level`。
- `pyproject.toml` 新增可选依赖组 `training = ["numpy>=1.24"]`。
- 新增 `tests/test_training_batch.py`，覆盖 batch 读取和 class id 映射、缺失 mask 报错和 CLI summary 写出。
- 更新 README，说明训练 batch loader 用法和当前仍未实现 PyTorch Dataset/DataLoader、GPU tensor、loss 和 checkpoint 权重更新的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.19.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training_batch.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_batch.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_batch -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-training-batch "$tmpdir/training-index.jsonl" --batch-size 2 --split train --cascade-level 1/1 --output "$tmpdir/batch-summary.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.19.0|version = \"0.19.0\"|inspect-training-batch|TrainingBatchError|load_training_batch|training batch" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.18.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 PySide6 本地控制台所需的长任务调度基础：新增可持久化本地 job runner，使 CLI/core 工作流能被创建为 job、同步执行、记录 stdout/stderr、保存状态和结果，供 UI 后续调用。

### 已做改动

- 版本号升级到 `v0.18.0`。
- 新增 `he_wsi_generator.ui.jobs` 模块，提供 `JobRunner` 和 `JobRunnerError`。
- `JobRunner` 支持创建本地 job 目录，持久化 `job.json`、`stdout.txt` 和 `stderr.txt`。
- Job record 记录 `queued`、`running`、`completed`、`failed`、`cancelled` 状态集合中的状态，以及 command、cwd、created/updated/started/finished 时间戳、return code 和消息。
- 空 job id、包含路径分隔符的 job id、空命令、重复 job id、未知 job id、非法状态和损坏 JSON record 会显式报错。
- 命令返回非零时 job 状态落盘为 `failed`；命令启动失败时也会写入 stderr 并落盘为 `failed`，避免遗留 stale `running` 状态。
- CLI 新增 `he-wsi-gen run-local-job <job_root> --job-id <id> -- <command...>`，用于创建并同步执行一个本地 job。
- `run-local-job` 成功时输出 job record 路径并返回 0；job 失败或参数非法时返回非零退出码。
- 新增 `tests/test_job_runner.py`，覆盖成功 job、非零退出 job、命令启动失败、重复 job 拒绝和 CLI 行为。
- 更新 README，说明本地 job runner 用法和当前不支持 daemon、并发队列、取消执行、跨机器调度或 PySide6 事件循环绑定。
- 更新 `docs/DEMANDS.MD`，记录 v0.18.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/ui/__init__.py`
- `src/he_wsi_generator/ui/jobs.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_job_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_job_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-local-job "$tmpdir/jobs" --job-id job-smoke -- python -c "print('job smoke')"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.18.0|version = \"0.18.0\"|run-local-job|JobRunner|JobRunnerError|local job" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.17.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进 `qc_reference_distribution` 的自动生成能力：从一组训练/参考 QC JSON 抽取数值 metrics，估计区间阈值并输出可作为 prior artifact 使用的 reference distribution JSON。

### 已做改动

- 版本号升级到 `v0.17.0`。
- 新增 `he_wsi_generator.qc.reference` 模块。
- 新增 `build_qc_reference_distribution`，输入为多个 QC report、metric 名称列表、输出 JSON 路径和最小样本数。
- Builder 复用现有 QC schema 校验，显式拒绝空输入、空 metric 列表、非法 min samples、缺失 metric 和样本数不足。
- 输出 JSON 包含 schema version、创建时间、来源、总样本数和 `metrics` 对象。
- 每个 metric 记录 `warning_min`、`warning_max`、`fail_min`、`fail_max`、`sample_count`、observed min/max 和 estimator 名称。
- 当前估计器使用 observed min/max 作为 warning 边界，并按 observed range 扩展 fail 边界，保持结果直接可解释。
- CLI 新增 `he-wsi-gen build-qc-reference <qc...> --metric <name> --output <qc_reference_distribution.json>`，支持重复 `--metric` 和 `--min-samples`。
- 新增 `tests/test_qc_reference.py`，覆盖 reference distribution 写出、缺失 metric 报错和 CLI 行为。
- 更新 README，说明 `build-qc-reference` 用法和估计器边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.17.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/reference.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_qc_reference.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_qc_reference -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli build-qc-reference "$tmpdir/qc-1.json" "$tmpdir/qc-2.json" "$tmpdir/qc-3.json" --metric mean_red --metric mask_tissue_fraction --output "$tmpdir/qc_reference_distribution.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.17.0|version = \"0.17.0\"|build-qc-reference|build_qc_reference_distribution|QCReferenceBuildError|observed_min_max_with_range_margin" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.16.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进自动 QC 的训练分布自适应阈值能力：让 QC engine 使用 prior artifact 中的 `qc_reference_distribution` 对已计算指标进行 warning/fail 判定，而不是只使用固定规则。

### 已做改动

- 版本号升级到 `v0.16.0`。
- `build_qc_report` 新增可选 `qc_reference_distribution` 参数。
- 新增 `QCReferenceError`，用于显式报告 reference distribution 格式非法、阈值非数值或边界顺序不合法。
- 支持 JSON reference distribution 格式：`{"metrics": {"metric_name": {"warning_min": number, "warning_max": number, "fail_min": number, "fail_max": number}}}`。
- 对数值 QC metric 应用 reference 阈值：超出 fail 区间为 `fail`，超出 warning 区间为 `warning`，否则为 `pass`。
- 被 reference 阈值判定的 metric 会记录 `reference` 字段，包含 warning/fail 边界和 `source=qc_reference_distribution`。
- `run-generation` 自动从 prior manifest 的 `qc_reference_distribution` artifact 读取 JSON，并传入 QC engine。
- 新增测试覆盖 reference 阈值 warning/fail、非法阈值报错，以及端到端 smoke generation 使用 prior reference。
- 更新 README，说明当前支持消费 reference distribution，但尚不自动估计训练分布阈值。
- 更新 `docs/DEMANDS.MD`，记录 v0.16.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.16.0|version = \"0.16.0\"|qc_reference_distribution|QCReferenceError|reference distribution|warning_min" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.15.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进自动 QC 的真实指标能力：从只检查文件存在，扩展为读取生成 OME-TIFF 和 mask，输出 WSI/tile/mask-region 三级可解释指标，为后续真实生成样本筛选建立基础。

### 已做改动

- 版本号升级到 `v0.15.0`。
- 增强 `he_wsi_generator.qc.engine.build_qc_report`。
- QC engine 读取 OME-TIFF pyramid 首层，记录 `wsi_readable`、实际 level count、RGB 均值和 `rgb_dynamic_range`。
- QC engine 新增 tile 级轻量指标：`sharpness_laplacian_proxy` 和 `tile_proxy_sample_count`。
- QC engine 读取 `.npy` mask，记录 `mask_readable`、`mask_classes_present`、`mask_unique_class_ids`、`mask_shape_matches_wsi` 和 `mask_tissue_fraction`。
- OME-TIFF 不可读、mask 不可读、mask 维度非法或 mask 与 WSI 首层尺寸不一致时，QC 显式 fail。
- 低动态范围、空组织比例等非硬错误场景返回 warning，避免静默通过。
- 新增 QC 单元测试，覆盖真实 OME-TIFF/mask 指标写入和 mask-WSI 尺寸错位 fail。
- 更新 README，说明当前 QC 指标能力和训练分布自适应阈值未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.15.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.15.0|version = \"0.15.0\"|sharpness_laplacian_proxy|mask_shape_matches_wsi|rgb_dynamic_range|mask_tissue_fraction" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.14.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进真实训练 backend 的前置能力：把输入 manifest、manifest audit 和 label mapping 转成四层 cascade training-index JSONL，使后续 PyTorch latent diffusion 训练 loop 有可审计的训练样本输入。

### 已做改动

- 版本号升级到 `v0.14.0`。
- 新增 `he_wsi_generator.models.training_index` 模块。
- 新增 `build_training_index`，输入为 input manifest、manifest audit、一个或多个 label mapping、输出 JSONL 路径。
- Training index builder 复用现有 manifest 和 label mapping schema 校验。
- Builder 显式拒绝缺失 audit record、audit status 非 `ok`、缺失 mapped/validated mask annotation、缺失匹配 label mapping、mask 文件不存在和无法切出完整 40x tile 的输入。
- 每条 JSONL 记录包含 dataset、WSI、split、cancer type、cascade level、40x tile 坐标、source metadata、mask annotation、6 类 label mapping 和 conditioning 约定。
- 对每个完整 512x512 40x tile 写出 `1/32`、`1/16`、`1/4`、`1/1` 四层记录，保持与生成模型级联训练顺序一致。
- CLI 新增 `he-wsi-gen build-training-index <manifest> --audit <audit.json> --label-mapping <mapping.json> --output <training-index.jsonl>`，并支持重复传入 `--label-mapping`。
- 新增 `tests/test_training_index.py`，覆盖 training index 写出、缺失 label mapping 拒绝和 CLI 行为。
- 更新 README，说明 training index 用法和真实 PyTorch 训练尚未实现的边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.14.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training_index.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_training_index.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_training_index -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli build-training-index "$tmpdir/manifest.json" --audit "$tmpdir/audit.json" --label-mapping "$tmpdir/label-mapping.json" --output "$tmpdir/training-index.jsonl"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.14.0|version = \"0.14.0\"|build-training-index|build_training_index|TrainingIndexError|training-index" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.13.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进完整核心系统中的“可运行生成任务”缺口：在既有 schema、prior、checkpoint、OME-TIFF、mask、metadata、QC 和 batch index 基础上，新增明确标记的端到端 smoke generation backend，用于验证生成任务可以产出完整 WSI 数据对象。

### 已做改动

- 版本号升级到 `v0.13.0`。
- 新增 `he_wsi_generator.generation.executor` 模块。
- 新增 `run_smoke_generation`，接收 generation config、prior manifest、trained checkpoint manifest、output root 和 generated id。
- Executor 复用 `create_generation_plan` 校验，显式拒绝未训练 checkpoint、缺失 prior artifact 或非法 generation config。
- 新增 `smoke-cascade` backend，按 `1/32 -> 1/16 -> 1/4 -> 1/1` 构造可审计四层 cascade smoke 输出，并以 `1/1 -> 1/4 -> 1/16 -> 1/32` 顺序写出 OME-TIFF pyramid。
- 生成输出新增完整样本目录：`generated.ome.tiff`、`generated_mask/mask.npy`、`metadata.json`、`qc.json`、`batch.jsonl` 和 `generation_run.json`。
- Metadata 记录 `generation_backend=smoke-cascade`、prior/checkpoint 路径、prior id、cascade、seed、anchor、采样步数和 overlap，避免把 smoke backend 伪装为真实 diffusion 输出。
- CLI 新增 `he-wsi-gen run-generation <generation-config> --backend smoke-cascade --prior-manifest <prior_manifest.json> --checkpoint-manifest <checkpoint_manifest.json> --output-root <dir> --generated-id <id>`。
- 新增 `tests/test_generation_runner.py`，覆盖端到端输出、未训练 checkpoint 拒绝和 CLI 生成行为。
- 更新 README，说明端到端 smoke generation 用法和真实 diffusion 未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 v0.13.0 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_generation_runner.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest tests.test_generation_runner -v`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli run-generation "$tmpdir/generation-config.json" --backend smoke-cascade --prior-manifest "$tmpdir/prior_manifest.json" --checkpoint-manifest "$tmpdir/trained-checkpoint.json" --output-root "$tmpdir/generated/gen-cli" --generated-id gen-cli`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.13.0|version = \"0.13.0\"|run-generation|smoke-cascade|run_smoke_generation|GenerationExecutionError" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.12.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M7：PySide6 本地单页控制台，为数据输入、label mapping、prior/model、生成参数、任务状态和 QC/输出查看建立可复现的 UI 配置与控制层。

### 已做改动

- 版本号升级到 `v0.12.0`。
- 新增 `he_wsi_generator.ui` 模块。
- 新增 UI config 创建、保存、读取和校验能力，覆盖 `data_input`、`label_mapping`、`prior_model`、`generation_parameters`、`task_status` 和 `qc_output` 六个单页控制台区域。
- 新增 job state store，支持 `queued`、`running`、`completed`、`failed`、`cancelled`，并对空 job id 或非法状态显式报错。
- 新增 output summary 读取能力，从 metadata/QC JSON 提取 `generated_id`、总体 QC 状态、三级 QC 状态和核心输出路径。
- 新增可选 PySide6 单页控制台入口；若未安装 PySide6，`launch-ui` 明确报错并提示安装 `.[ui]`。
- CLI 新增 `he-wsi-gen write-ui-config <output>`，用于写出默认 UI 配置 JSON。
- CLI 新增 `he-wsi-gen launch-ui --config <ui-config.json>`，用于启动可选 PySide6 本地控制台。
- `pyproject.toml` 新增可选依赖组 `ui`，包含 `PySide6>=6.7`。
- 新增 M7 单元测试，覆盖 UI config roundtrip、任务状态、输出摘要、CLI config 写出和 PySide6 缺依赖错误。
- 更新 README，说明 M1-M7 当前能力、UI CLI 用法、可选依赖和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M7 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/__init__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/ui/__init__.py`
- `src/he_wsi_generator/ui/config.py`
- `src/he_wsi_generator/ui/controller.py`
- `src/he_wsi_generator/ui/pyside_app.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_ui.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_ui -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli write-ui-config "$tmpdir/ui-config.json"`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.12.0|version = \"0.12.0\"|write-ui-config|launch-ui|create_default_ui_config|JobStateStore|UIUnavailableError" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.11.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M6：OME-TIFF 与 QC，建立小尺寸 pyramid 写出、QC JSON 和 batch JSONL 归档基础。

### 已做改动

- 版本号升级到 `v0.11.0`。
- 新增 `he_wsi_generator.outputs` 模块。
- 新增小尺寸 pyramid OME-TIFF smoke writer，使用 `tifffile` 写出多层 pyramid TIFF 并验证层级尺寸。
- 新增 6 类 mask `.npy` 输出和 mask metadata 写出。
- 新增 `he_wsi_generator.qc` 模块，构建 WSI/tile/mask-region 三级 QC JSON 和轻量 non-copy report。
- 新增 `he_wsi_generator.metadata` 模块，支持 per-WSI metadata 写出、batch JSONL 追加和单样本归档。
- CLI 新增 `he-wsi-gen archive-sample <output-root> --metadata <metadata.json> --qc <qc.json>`。
- `pyproject.toml` 新增可选依赖组 `outputs`，包含 `numpy` 和 `tifffile`。
- 新增 M6 单元测试，覆盖 pyramid OME-TIFF smoke 写出与读取、QC JSON 校验、metadata 写出、batch JSONL 追加和 CLI 归档行为。
- 更新 README，说明 M6 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M6 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/metadata/__init__.py`
- `src/he_wsi_generator/metadata/archive.py`
- `src/he_wsi_generator/outputs/__init__.py`
- `src/he_wsi_generator/outputs/masks.py`
- `src/he_wsi_generator/outputs/ome_tiff.py`
- `src/he_wsi_generator/qc/__init__.py`
- `src/he_wsi_generator/qc/engine.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_outputs_qc_archive.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_outputs_qc_archive -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.11.0|version = \"0.11.0\"|archive-sample|write_pyramid_ome_tiff|build_qc_report|archive_sample" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.10.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M5：训练与生成骨架，为后续真实 latent diffusion 训练和级联生成提供可审计入口。

### 已做改动

- 版本号升级到 `v0.10.0`。
- 新增 `he_wsi_generator.models` 模块，提供训练 run 初始化和 checkpoint manifest 读取/校验。
- 新增训练 run manifest，记录 model family、prior manifest、training index、random seed、cascade levels、tile size、训练阶段和输出路径。
- 新增 checkpoint manifest placeholder，明确状态为 `not_trained` 且 `usable_for_inference=false`，避免伪装成真实模型权重。
- 新增 `he_wsi_generator.generation` 模块，提供四层 cascade generation plan。
- Generation plan 记录 `1/32 -> 1/16 -> 1/4 -> 1/1` 生成顺序、tile traversal、resume index、overlap、blending 和 write mode。
- Generation plan 拒绝未训练 checkpoint、缺失 prior manifest、非法 cascade 或 source-anchored 配置缺 source。
- CLI 新增 `he-wsi-gen init-training-run <training-config>`。
- CLI 新增 `he-wsi-gen plan-generation <generation-config> --prior-manifest <prior_manifest.json> --checkpoint-manifest <checkpoint_manifest.json> --output <generation-plan.json>`。
- 新增 M5 单元测试，覆盖 training manifest、未训练 checkpoint、generation plan、非法 checkpoint 和 CLI 行为。
- 更新 README，说明 M5 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M5 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/generation/__init__.py`
- `src/he_wsi_generator/generation/planner.py`
- `src/he_wsi_generator/models/__init__.py`
- `src/he_wsi_generator/models/training.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_models_generation.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m unittest tests.test_models_generation -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.10.0|version = \"0.10.0\"|init-training-run|plan-generation|create_training_run|create_generation_plan" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.9.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M4：prior artifact，为 layout/style/texture/QC priors 建立统一 manifest、文件校验和可追溯基础。

### 已做改动

- 版本号升级到 `v0.9.0`。
- 新增 `he_wsi_generator.priors` 模块。
- 新增 prior artifact manifest 创建、保存、读取与校验能力。
- Prior manifest 记录 `prior_id`、版本、创建时间、训练输入、随机种子和 artifact 清单。
- Artifact 清单要求覆盖 `layout_mask_prior`、`style_prior`、`texture_prior`、`qc_reference_distribution`。
- 每个 artifact 记录路径、kind、sha256、size_bytes 和 metadata。
- 校验 manifest 时显式拒绝缺失 artifact、缺失文件、hash 不匹配、非法 seed、非法 artifact type 和重复路径。
- CLI 新增 `he-wsi-gen validate-prior-manifest <prior_manifest.json>`。
- 新增 M4 单元测试，覆盖 manifest roundtrip、缺失必需 artifact、hash mismatch、重复路径和 CLI 校验。
- 更新 README，说明 M4 能力、CLI 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M4 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/priors/__init__.py`
- `src/he_wsi_generator/priors/artifacts.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_priors.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.9.0|version = \"0.9.0\"|validate-prior-manifest|PriorArtifactError|create_prior_artifact_entry|validate_prior_manifest" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.8.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M3：patch embedding 与伪 mask 基础能力，为后续 prior artifact 和聚类伪 mask 工作流提供接口、缓存和 cluster report。

### 已做改动

- 版本号升级到 `v0.8.0`。
- 新增 `he_wsi_generator.embeddings` 模块。
- 新增 `CheckpointPatchEmbedder`，要求用户提供 JSON checkpoint；缺 checkpoint、checkpoint 损坏、embedding 维度非法或输出非有限值时显式报错。
- 新增 `FixturePatchEmbedder`，仅用于 smoke test，并在 metadata 中标记 `embedding_confidence=low`。
- 新增 `EmbeddingResult` 数据结构，统一返回 embedding array 与 metadata。
- 新增 embedding cache，支持保存/读取 `.npy` embedding array 和 JSON metadata。
- 新增轻量 `cluster_embeddings`，输出 labels、cluster counts、inertia、embedding count 和 embedding dim。
- `pyproject.toml` 新增可选依赖组 `embeddings`。
- 新增 M3 单元测试，覆盖缺 checkpoint、合法 checkpoint embedding metadata、cache roundtrip、cluster report 和错误路径。
- 更新 README，说明 M3 能力、可选依赖和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M3 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/embeddings/__init__.py`
- `src/he_wsi_generator/embeddings/cache.py`
- `src/he_wsi_generator/embeddings/cluster.py`
- `src/he_wsi_generator/embeddings/embedder.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_embeddings.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.8.0|version = \"0.8.0\"|CheckpointPatchEmbedder|FixturePatchEmbedder|cluster_embeddings|save_embedding_cache" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.7.0 - 2026-05-23

### 用户需求

用户要求继续根据 `docs/` 中的项目设计和开发指南完成本项目开发。本次版本推进开发附录 M2：WSI 与 mask I/O，建立真实输入审计、thumbnail smoke、mask label mapping 和坐标对齐基础。

### 已做改动

- 版本号升级到 `v0.7.0`。
- 新增 `he_wsi_generator.io` 模块，包含 `OpenSlideReader`、`FixtureImageSlideReader`、`SlideMetadata` 和 `WSIReadError`。
- 新增 manifest audit 能力，支持读取 manifest 后输出每张 WSI 的路径、尺寸、level、MPP、倍率、backend、状态和错误信息。
- CLI 新增 `he-wsi-gen audit-manifest <manifest> --backend <openslide|fixture-image> --output <audit.json>`。
- 新增 `he_wsi_generator.annotations` 模块，支持 PNG/TIFF/numpy mask label 读取、6 类 label mapping 应用和未映射编号显式报错。
- 新增 mask alignment 校验，基于 `transform_to_level0` 的 scale/offset 判断 mask 是否落在 WSI level0 范围内。
- `pyproject.toml` 新增可选依赖组 `wsi`，包含 `numpy`、`Pillow` 和 `openslide-python`。
- 新增 M2 单元测试，覆盖 WSI metadata、thumbnail、manifest audit、mask 编号读取、mapping 应用和坐标对齐错误。
- 更新 README，说明 M2 能力、可选依赖、CLI audit 用法和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录 M2 开发需求和边界。

### 影响文件

- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/annotations/__init__.py`
- `src/he_wsi_generator/annotations/alignment.py`
- `src/he_wsi_generator/annotations/masks.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/io/__init__.py`
- `src/he_wsi_generator/io/audit.py`
- `src/he_wsi_generator/io/readers.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_annotations.py`
- `tests/test_cli.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `tests/test_wsi_io.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli audit-manifest "$tmpdir/manifest.json" --backend fixture-image --output "$tmpdir/audit.json"`（临时 fixture image manifest）
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.7.0|version = \"0.7.0\"|audit-manifest|FixtureImageSlideReader|OpenSlideReader|validate_mask_alignment" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.6.0 - 2026-05-23

### 用户需求

用户要求根据 `docs/` 中的项目设计和开发指南完成本项目开发。当前版本从开发附录 M1 开始，先实现数据契约与 schema 校验，为后续 WSI I/O、mask 映射、prior、训练生成、QC 和 PySide6 UI 提供可测试基础。

### 已做改动

- 版本号升级到 `v0.6.0`。
- 新增 Python package `he_wsi_generator`。
- 新增 `pyproject.toml`，声明 package metadata、CLI 入口和可选 YAML 依赖。
- 新增 CLI：`he-wsi-gen validate <kind> <path>` 与 `he-wsi-gen init-generation-config <output>`。
- 新增 schema validator，覆盖 input manifest、label mapping、generation config、metadata 和 QC report。
- 新增默认生成配置 `configs/generation.default.json`，默认值与开发附录保持一致。
- 新增单元测试，覆盖 schema 成功路径、显式错误路径、CLI 返回码和版本一致性。
- 更新 README，说明当前 M1 能力、安装方式、CLI 用法、开发路线和未实现边界。
- 更新 `docs/DEMANDS.MD`，记录本轮代码实现需求和边界。

### 影响文件

- `.gitignore`
- `VERSION`
- `README.md`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/__init__.py`
- `src/he_wsi_generator/__main__.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/constants.py`
- `src/he_wsi_generator/schemas.py`
- `tests/test_cli.py`
- `tests/test_schemas.py`
- `tests/test_version.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `python -m compileall src tests`
- `git diff --check`
- `rg "v0.6.0|version = \"0.6.0\"|he_wsi_generator|generation.default.json|he-wsi-gen" VERSION README.md pyproject.toml configs src tests docs/DEMANDS.MD docs/CHANGELOG.md`

## v0.5.1 - 2026-05-23

### 用户需求

用户要求将本地文件夹重命名为 `MultiCenterWSIGenerator`，并将当前仓库内容同步到 GitHub 仓库 `Liao-MH/MultiCenterWSIGenerator`。

### 已做改动

- 版本号升级到 `v0.5.1`。
- README 项目标题更新为 `MultiCenterWSIGenerator`，并新增 GitHub 仓库链接。
- 新增 `.gitignore`，忽略 `.DS_Store` 和常见 Python 缓存目录。
- 记录远端同步要求、空仓库检查结果和鉴权边界。

### 影响文件

- `.gitignore`
- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`

### 验证结果

- `git ls-remote https://github.com/Liao-MH/MultiCenterWSIGenerator.git`
- `ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com`
- `rg "v0.5.1|MultiCenterWSIGenerator|Liao-MH/MultiCenterWSIGenerator" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md`
- `git status --short`
- `git push -u origin main`

## v0.5.0 - 2026-05-23

### 用户需求

用户要求保存第一版开发指南，将现有 H&E WSI 生成器 proposal 转换为可开发规格，并记录已经确认的工程默认值、数据契约、模块边界、模型路线、QC、UI 和测试验收要求。

### 已做改动

- 版本号升级到 `v0.5.0`。
- 新增 `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`，作为第一版开发附录。
- 开发附录明确 v1 工程默认：Python core/CLI + PySide6，OpenSlide+tifffile，PyTorch latent diffusion U-Net，可插拔 PatchEmbedder。
- 开发附录补充输入 manifest、annotation record、label mapping、generation config、输出文件、模块契约、prior artifact、模型训练、推理重建、QC、UI、测试验收和 v1 不做内容。
- 更新 `README.md`，新增开发附录入口并把项目状态更新为研究设计 + 开发规格阶段。
- 更新 `docs/DEMANDS.MD`，新增 `v0.5.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.5.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

### 验证结果

- `test -s docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `rg "v0.5.0|OpenSlide|tifffile|PySide6|latent diffusion U-Net|PatchEmbedder|structure_anchor" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `rg "^## |^### " docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- `python3 - <<'PY' ...`（检查版本一致性、开发附录链接和核心章节）
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`

## v0.4.0 - 2026-05-21

### 用户需求

用户希望把 conditional priors learning 的数理逻辑、产物类型和约束机制写入 proposal，明确这些 prior 如何通过条件输入、loss、guidance 和 QC 落到实际生成模型中。

### 已做改动

- 版本号升级到 `v0.4.0`。
- 在 `docs/plans/2026-05-18-he-wsi-generator-study-design.md` 新增 `Conditional Priors 的产物与约束机制` 小节，补充联合分布、prior 产物类型、条件注入方式和扩散目标。
- 补充 conditional priors 与 `structure_anchor` 的数学关系，明确 `alpha` 不是像素插值，而是条件强度和 loss 权重的连续调节。
- 在三阶段训练协议中补充说明：layout、mask、style seed 和 `structure_anchor` 都是 conditional priors 的实例化结果，而不是临时拼接特征。
- 更新 `README.md` 的当前版本和更新重点。
- 更新 `docs/DEMANDS.MD`，新增 `v0.4.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.4.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.4.0|2026-05-21" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（检查版本字段、conditional priors 小节和 metadata 示例）

## v0.3.0 - 2026-05-18

### 用户需求

用户希望现有 proposal 文档更完整地覆盖前期讨论达成的所有细节共识，并加强因果分析、设计取舍说明、训练协议、自动 QC、metadata、LLM 边界和系统完成标准。

### 已做改动

- 版本号升级到 `v0.3.0`。
- 扩写 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，新增细节共识总表，系统整理全部关键决策。
- 补充因果假设、反事实边界和被放弃路线，解释为什么当前主线选择结构锚定多分辨率条件扩散，而不是普通增强、CycleGAN、GAN、纯随机生成、先高倍后拼接或文本 prompt 入模。
- 扩写总体架构，补充数据流和因果依赖，明确 thumbnail、mask、patch embedding、style prior、source relation 和 QC reference distribution 的作用。
- 扩写 mask 体系，补充无标注场景、聚类伪 mask、用户映射流程和可信度层级。
- 扩写 `structure_anchor`，补充训练与推理语义、不同 anchor 区间的因果解释。
- 扩写生成模型部分，补充 backbone 选择原则、四层 pyramid 责任分工、训练样本构造、训练约束与 QC 映射。
- 扩写本地桌面单页控制台、高级参数、LLM 角色、metadata 双层 manifest、自动 QC 判定逻辑和非复制报告解释规则。
- 新增核心系统完成标准，明确完整 H&E WSI 生成器必须具备的输出和审计能力。
- 更新 `README.md`，增加 `v0.3.0` 更新重点。
- 更新 `docs/DEMANDS.MD`，新增 `v0.3.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.3.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.3.0|2026-05-18" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（metadata / structure / format checks）

## v0.2.0 - 2026-05-18

### 用户需求

用户要求根据 `research-design-ladder` 技能，将前期已确认的 H&E WSI 数据生成器方案写入正式研究设计文档，并同步更新项目版本、README、需求记录和开发日志。

### 已做改动

- 版本号升级到 `v0.2.0`。
- 新增 `docs/plans/2026-05-18-he-wsi-generator-study-design.md`，按完整 proposal / study design 结构写入 H&E WSI 数据生成器研究设计。
- 新研究设计文档明确当前系统边界：只做 H&E WSI 生成器，不把下游训练/测试作为当前成败标准。
- 新研究设计文档纳入结构锚定多分辨率条件扩散框架、`structure_anchor`、`global_imaging_style_prior`、疾病无关 6 类 mask、40x 四层级联生成、自动 QC、metadata/schema、本地桌面单页控制台、风险矩阵和最终逻辑链。
- 更新 `README.md`，将项目入口、当前定位、核心输出、关键技术路线和边界说明同步到 `v0.2.0`。
- 更新 `docs/DEMANDS.MD`，新增 `v0.2.0` 结构化需求并置顶。
- 更新 `VERSION` 为 `v0.2.0`。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-18-he-wsi-generator-study-design.md`

### 验证结果

- `rg "v0.2.0|2026-05-18" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `test -s docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`
- `python3 - <<'PY' ...`（metadata / structure / format checks）
- `ls -l VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-18-he-wsi-generator-study-design.md`

## v0.1.0 - 2026-05-16

### 用户需求

用户希望设计一个面向 H&E 染色 WSI 数据的多中心数据生成器，用于缓解真实多中心数据收集困难，并要求按 `research-design-ladder` 方法生成完整研究设计。

### 已做改动

- 初始化项目文档版本 `v0.1.0`。
- 新增研究设计文档，系统整理研究定位、核心问题、生成器架构、数据协议、验证方案、风险矩阵、执行顺序、交付版本和候选标题。
- 新增需求记录文件，结构化保存本次用户需求与设计边界。
- 新增 README，说明项目目标、当前状态、核心文档和后续实现阶段的环境原则。
- 新增 VERSION 文件，记录当前文档设计版本。

### 影响文件

- `VERSION`
- `README.md`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`

### 验证结果

- `find . -maxdepth 3 -type f | sort`
- `grep -R "v0.1.0" VERSION README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`
- `wc -l README.md docs/DEMANDS.MD docs/CHANGELOG.md docs/plans/2026-05-16-he-wsi-multicenter-data-generator-study-design.md`
