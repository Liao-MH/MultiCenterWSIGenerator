# 审计决策与禁止变更项

## 当前审计基线

- 原始审计基线为 `v0.62.0`；本轮补救开发版本为 `v0.63.0`。
- v0.63.0 允许修改 P1 契约闭环相关的 `src/`、`tests/`、配置、README 和审计文档。
- 审计文件统一维护在 `docs/audit/`，不再放在 `docs/` 根目录。
- 本轮按仓库版本规则升级版本号，因为新增了向后兼容的 CLI/schema 校验入口并收紧输出摘要契约。
- 截至本次复审计，v0.63.0 已提交为 `main` 分支基线，但不是已 tag 或打包发布的 release；不能表述为已经 tag 或发布。
- 本轮已创建 conda 环境 `MultiCenterWSIGenerator` 并验证 PyTorch、CUDA、PySide6 依赖和全量单元测试；该结论只覆盖当前机器环境，不替代真实 SVS 全链路和完整 production 验收。

## 完整项目成果定义

完整项目成果以研究设计文档为准，至少包括：

- 本地桌面单页控制台，支持 WSI/mask 导入、编号映射、模型训练/加载、生成参数、任务状态和输出查看。
- 结构锚定的多分辨率 mask-conditioned latent diffusion / ControlNet / DiT 级生成模型。
- 40x 四层级联生成：`1/32 -> 1/16 -> 1/4 -> 1/1`。
- OME-TIFF pyramid WSI、6 类 mask、metadata JSON、QC JSON 和 batch JSONL index。
- 自动 QC、非复制审计、可追踪 seed/model/prior/source/config。

当前 `v0.63.0` 不能被表述为完整项目成果，只能表述为可审计工程骨架和 smoke/proxy 级验证链。

## 关键设计决策

1. 保持 core/CLI 优先
   - UI 只负责配置、调度和展示，不把核心业务逻辑藏在界面事件里。

2. 保持 CLI 自动化入口
   - 未经用户确认，不让 `run-generation` 默认弹出 GUI，以免破坏脚本化和批处理使用。
   - 图形配置页优先通过 `launch-ui` 落地。

3. 保持 smoke / proxy 边界显式可见
   - `smoke-cascade`、`torch-diffusion-smoke`、统计 prior、preview sampling 不能被描述为 production WSI generator。

4. 保持 6 类疾病无关 mask 体系
   - `background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact` 是当前统一语义契约。

5. 保持 metadata / QC / qc_review 分离
   - `metadata.json` 回答“如何生成”。
   - `qc.json` 回答“质量如何”。
   - `qc_review.json` 回答“人工是否接受”。

6. 保持显式失败优先
   - 对非法输入、缺失依赖、schema 不一致、artifact 不匹配，继续显式报错，不引入 silent fallback。

7. 保持可选依赖隔离
   - `torch`、`PySide6`、`openslide`、`PyYAML` 继续通过可选依赖或独立环境安装，不回写到基础依赖集合。
   - 当前验证环境命名为 `MultiCenterWSIGenerator`，安装完整 extras 后用于后续审计和 worker 复验。

## 禁止变更项

- 未经确认，不做与 P1 无关的实现重构、不改默认生成行为。
- 不把审计记录本身包装成新发布；只有实际功能补救才升级版本。
- 不删除现有 `build/validation/` 工件；它们是历史验证证据。
- 不把“现存工件仍可校验”表述成“本轮已重新执行真实 SVS 全链路”。
- 不把 main 上的 v0.63.0 基线提交直接表述为已发布版本；tag、打包需另行执行并验证。
- 不把 UI 骨架窗口描述为完整图形化自定义配置页。
- 不因为补救而扩展到当前系统边界外内容，例如 IHC/IF、临床分子标签、真人专家盲评、下游训练验证、权限/签名系统、数据库或远端协作审阅。

## 补救优先级决策

- 第一优先级：审计文件归位、文档诚实度、契约闭环。
- 第二优先级：真实可交互 PySide6 配置页。
- 第三优先级：环境化验证复跑。
- 第四优先级：production 级生成模型与 WSI 输出。
- 第五优先级：大文件拆分与维护性收敛。
