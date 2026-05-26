# Repository Working Rules

本文件固化本仓库内 Codex 的常用工作规则。若用户在当前会话中给出更新或更具体的指令，以用户最新指令为准。

如有需要，`/home/muhengliao/LMH2025/Data/raw_data/Pancancer_Fanhong/Breast_cancer_N=137/291288_.svs` 可作为测试样本。


## 代码实现原则

1. 当前需求优先，避免为假设性的未来需求做过度设计。
2. 只处理与当前需求强相关、且高概率出现的边界和兼容场景。
3. 对明确非法、缺失或不符合任务要求的输入显式报错，不使用 silent fallback 掩盖问题。
4. 最小改动，除非明确需要，不做无关重构。
5. 在关键分支、函数定义、参数设计等地方写有价值和解释必要的注释。

## 禁止以 Smoke 级代码替代真实实现
1. smoke test 只是一种验证方式，不是功能实现方式。
2. 不得新增 smoke 级实现代码来替代真实业务实现。
4. 禁止将以下内容作为功能完成依据：
   - 只跑通 demo/sample 的入口脚本；
   - 只返回固定假数据的 mock 实现；
   - 只验证模块可导入的 smoke-only 流程；
   - 未连接真实数据契约的 placeholder pipeline；
   - 与最终业务路径无关的临时 CLI、脚本或测试夹具。
5. 如确实需要临时 scaffold、stub 或 mock 来降低开发风险，必须满足：
   - 明确标注为临时实现；
   - 说明为什么当前阶段需要；
   - 不得宣称功能已完成；
   - 在同一里程碑完成前替换为真实实现，或在最终回复中明确列为未完成项。
6. smoke test 应在真实功能实现完成后用于验证主流程健康状态，而不是倒逼新增 smoke-only 业务代码。
7. 最终判断功能是否完成，应以开发文档中不同module和stage对真实输入的处理结果为准，而不是以 smoke test 是否通过为准。

## 测试节奏规则
1. 本项目采用“开发文档中一个stage完成后集中验证”的测试节奏。
2. 开发过程中应优先完成每个stage对应的功能，不要在实现每个内部 helper、中间函数或临时分支时立即追加大量细碎测试。
3. 每完成一个开发文档中的stage后，再集中补充和运行测试，包括 smoke test。
4. 测试优先覆盖：
   - 核心成功路径；
   - 关键数据契约；
   - 高影响边界条件；
   - 高概率用户错误；
   - 已知回归问题。
5. 避免为以下内容设计冗余测试：
   - 低概率非法输入；
   - 内部 helper 的重复防御逻辑；
   - 完整错误文案逐字匹配；
   - 不影响业务契约的临时实现细节。
6. 只有在以下情况中，才应在stage完成前追加针对性测试或快速验证：
   - 不提前验证会显著增加后续定位成本。
8. 最终回复必须说明：
   - 本次完成的是哪个stage；
   - 执行了哪些测试；
   - 哪些测试暂未执行以及原因。

## 章节级代码追踪规则

在本项目开发过程中，除了完成代码实现、测试和常规文档更新外，还必须维护设计文档与开发文档中的“章节级代码追踪”。

重要时机要求：

1. 代码追踪块不要在开发过程中边做边更新，而应在本轮项目所有开发完成之后集中更新。
2. “开发完成”指本次代码实现、必要测试、README、CHANGELOG、需求文档等常规交付内容均已完成，并且已确认最终代码路径、类名、函数名、测试名和验证命令。

项目文档路径：
设计文档：
`/Users/lmh/Library/CloudStorage/OneDrive-WashingtonUniversityinSt.Louis/MultiCenterWSIGenerator/docs/plans/2026-05-18-he-wsi-generator-study-design.md`

开发文档：
`/Users/lmh/Library/CloudStorage/OneDrive-WashingtonUniversityinSt.Louis/MultiCenterWSIGenerator/docs/dev/2026-05-26-he-wsi-generator-module-stage-development-plan.md`

核心规则：

1. 本轮开发完成后，必须回到上述两个文档，找到与本次改动相关的最小级标题，并在该标题下补充或更新代码追踪块。
2. 如果一个功能对应多个小节，需要分别更新所有相关小节，不能只更新其中一个。
3. 每个最小级标题下都应有代码追踪块。即使尚未实现，也要明确写“未实现”；如果该小节不直接对应代码，则写“不适用”。禁止为了填充文档而伪造实现位置。
5. 代码追踪必须记录完整的项目内业务依赖。如果某个功能由多个文件、多个函数、同一文件的多个代码段共同实现，也要全部列出，并按职责分组。
6. “完整依赖”指实现该小节功能所需的项目内代码文件、配置、schema、测试、脚本等。不要机械列出 Python 标准库、typing、pathlib、普通工具 import 等无业务意义依赖。关键第三方依赖可以单独列为“外部关键依赖”。
7. 每个代码位置都必须附带职责说明。不能只堆文件路径或行号。
8. 主定位优先使用文件路径、类名、函数名、模块名、测试函数名。行号只作为辅助定位，因为代码迭代后行号可能漂移。
9. 如果代码位置发生变化，必须在开发完成后的追踪块更新阶段同步修正，避免文档指向过期实现。
10. 如果找不到合适小节，则在设计文档和开发文档最后添加一个“代码追踪附录”，并说明原因。
12. 验证命令必须是真实执行过；如果尚未执行，必须明确写“尚未执行”，不能伪造验证结果。

设计文档追踪块格式：

``` 
Implementation Trace:
- 状态：已实现 / 部分实现 / 未实现 / 不适用
- 主实现：
  - path/to/file.py::ClassOrFunction，说明该位置如何落实本小节设计
- 完整依赖：
  - 入口与编排：
    - path/to/file.py::symbol，职责说明
  - 数据契约：
    - path/to/file.py::symbol，职责说明
  - 核心逻辑：
    - path/to/file.py::symbol，职责说明
  - 配置与默认值：
    - path/to/file.py::symbol，职责说明
  - 错误处理：
    - path/to/file.py::symbol，职责说明
  - 输出与持久化：
    - path/to/file.py::symbol，职责说明
  - 测试覆盖：
    - tests/path/test_file.py::test_name，验证内容说明
- 外部关键依赖：
  - package_name，使用原因
- 参考行号：
  - path/to/file.py 13-19，说明该段作用
- 更新时间：YYYY-MM-DD
```

开发文档追踪块格式：

```markdown
Implementation Trace:
- 状态：已实现 / 部分实现 / 未实现 / 不适用
- 主实现：
  - path/to/file.py::ClassOrFunction，核心职责说明
- 完整依赖：
  - 入口与编排：
    - path/to/file.py::symbol，负责启动、调度或连接该流程
  - 输入契约：
    - path/to/file.py::symbol，定义或校验输入结构
  - 输出契约：
    - path/to/file.py::symbol，定义或生成输出结构
  - 核心逻辑：
    - path/to/file.py::symbol，负责主要业务逻辑
  - 配置与默认值：
    - path/to/file.py::symbol，负责参数、默认值或配置解析
  - 错误处理：
    - path/to/file.py::symbol，负责非法输入、失败条件或异常暴露
  - 输出与持久化：
    - path/to/file.py::symbol，负责文件写入、结果保存或 artifact 生成
  - 测试覆盖：
    - tests/path/test_file.py::test_name，验证内容说明
  - 脚本与命令：
    - scripts/name.sh，负责构建、训练、验证或数据处理
- 调用链 / 实现流程：
  step_a -> step_b -> step_c
- 外部关键依赖：
  - package_name，使用原因
- 参考行号：
  - path/to/file.py 13-19，说明该段作用
- 验证命令：
  - pytest tests/path/test_file.py
  - 其他实际执行过的验证命令
- 更新时间：YYYY-MM-DD
```


## 环境执行规则

1. 当前开发与验证统一使用 conda 环境 `MultiCenterWSIGenerator`。
2. 运行项目命令时优先使用 `conda run -n MultiCenterWSIGenerator ...`，不要再用 `mamba run -n MultiCenterWSIGenerator ...` 生成新的验证记录。


## 仓库开发要求

1. 开发前维护 `docs/DEMANDS.MD`，把最新需求置顶记录。
2. 每次功能更新或迭代分配唯一语义化版本号，格式为 `v{major}.{minor}.{patch}`。
3. 版本号必须同步到 `VERSION`、`pyproject.toml`、代码常量、默认配置、测试断言和相关文档。
4. 每次改动同步更新 `README.md` 与 `docs/CHANGELOG.md`；日志按最新在前记录日期、用户需求、已做改动、影响文件和验证结果。
5. 优先使用 conda 或隔离环境安装开发依赖，不直接污染主环境。
6. 完成交付时确保 README 可让用户快速了解环境配置、使用方法、功能和当前边界。

## 并行开发要求
0. 如有可能，优先使用multiagent并行开发以提升开发效率
1. 如果不行，则使用codex exec命令派发worker
   a. 使用 `.agent/tasks/`、`.agent/reports/` 和 `.agent/logs/` 跟踪 worker 任务、报告和日志。
   b. worker 应使用独立 git worktree 与 `worker/<task-slug>` 分支。
   c. 只把文件范围不重叠、验证命令可独立运行的任务并行化。
   d. orchestrator 必须审查 worker report、`git status --short` 和 diff，并重新运行关键验证后再集成。
   e. README、DEMANDS、CHANGELOG、audit checklist 等共享文档优先由 orchestrator 统一整理。

## 输出要求

1. 完成任务后用中文以 `✅` 标识任务清单，明确已完成、部分完成或未完成项。
2. 不得伪造验证结果、隐藏失败或把历史工件说成本轮新验证。
3. 最终回复必须说明：
   - 改动了哪些代码文件；
   - 更新了哪些设计文档小节；
   - 更新了哪些开发文档小节；
   - 哪些追踪块是已实现、部分实现、未实现或不适用；
   - 本次完成的是哪个代码里程碑；
   - 执行了哪些验证命令；
   - 哪些测试暂未执行以及原因。
