# v0.62.0 审计补救实施计划

## 目标

在不改变既有研究边界的前提下，先补齐契约一致性和验证闭环，再处理可维护性问题；所有实现修复都需要用户确认后再开始。

## 当前基线

- 代码基线：`v0.62.0`
- 本轮范围：审计文档与补救计划
- 本轮不做：源码修复、版本号升级、功能扩展

## 优先级任务包

### P0. 契约闭环补齐

- 目标：
  - 把“文档里已定义的一等 artifact”补齐到统一验证入口。
  - 把会话级规则沉淀为仓库内可见规则文件。
- 建议修改：
  - 新增仓库内 `AGENTS.md` 或等效持久化规则文件。
  - 为 `qc_review` 补齐 `validate` CLI/schema kind。
- 影响范围：
  - `AGENTS.md`
  - `src/he_wsi_generator/schemas.py`
  - `src/he_wsi_generator/cli.py`
  - `tests/test_qc_review.py`
  - `tests/test_cli.py`
  - `README.md`
- 完成标准：
  - 新会话仅凭仓库文件即可读到规则。
  - `he-wsi-gen validate qc-review path/to/qc_review.json` 可用并有测试覆盖。

### P1. 输出摘要硬化

- 目标：
  - 让输出摘要遵循“显式失败”原则，而不是对坏 metadata 宽松容忍。
- 建议修改：
  - `collect_output_summary()` 先做 metadata schema 校验，再构造 summary。
  - 对 metadata / QC / review 的 `generated_id` 不一致给出统一报错。
- 影响范围：
  - `src/he_wsi_generator/ui/controller.py`
  - `src/he_wsi_generator/cli.py`
  - `tests/test_ui.py`
  - `README.md`
- 完成标准：
  - 非法 metadata 进入 `inspect-output-summary` 时返回非零退出码。
  - 新增针对 metadata 损坏、id 不一致的失败测试。

### P2. 环境化验证补齐

- 目标：
  - 把当前“历史上跑过”与“现在可复现”分开，补齐可重复验证步骤。
- 建议修改：
  - 准备独立 `conda` 环境说明或脚本，至少覆盖 `torch`、`ui`、`wsi` 可选依赖安装。
  - 在文档中固定真实 SVS 验证命令序列，必要时补一个只读验证脚本。
- 影响范围：
  - `README.md`
  - `docs/CHANGELOG.md`
  - 可选：`scripts/` 下验证脚本
- 完成标准：
  - 可在指定环境中复跑 PyTorch 路径测试。
  - 可重新执行真实 SVS 验证链路，而不是只依赖现存工件。

### P3. 维护性收敛

- 目标：
  - 降低后续补救和回归成本。
- 建议修改：
  - 先拆 `cli.py` 中与 `qc_review` / output summary / local job 无关的分支。
  - 再评估是否把 `torch_training.py` 按训练、采样、schema/manifest 辅助函数分拆。
- 影响范围：
  - `src/he_wsi_generator/cli.py`
  - `src/he_wsi_generator/models/torch_training.py`
  - 对应测试文件
- 完成标准：
  - 行为不变，测试不减。
  - 拆分以“降低风险”为前提，不做风格化重构。

## 建议执行顺序

1. P0 契约闭环补齐
2. P1 输出摘要硬化
3. P2 环境化验证补齐
4. P3 维护性收敛

## 暂停条件

- 用户未确认前，所有任务包保持未执行状态。
- 若用户只允许最小修复，优先做 P0 + P1，不进入 P3。
