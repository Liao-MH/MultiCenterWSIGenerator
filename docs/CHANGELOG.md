# CHANGELOG

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
