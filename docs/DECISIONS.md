# 审计决策与禁止变更项

## 当前审计基线

- 当前审计以 `v0.62.0` 为唯一基线。
- 本轮只更新审计文档，不修改实现代码，不升级版本号。

## 关键设计决策

1. 保持 smoke / proxy 边界显式可见
   - `smoke-cascade` 和 `torch-diffusion-smoke` 只能被描述为管线验证实现，不能在文档或代码里伪装成 production WSI generator。

2. 保持 6 类疾病无关 mask 体系不变
   - `background`、`tissue`、`target_pathology`、`supporting_tissue`、`necrosis_debris`、`artifact` 仍是当前统一语义契约。

3. 保持 metadata / QC / qc_review 分离
   - `metadata.json` 回答“如何生成”。
   - `qc.json` 回答“质量如何”。
   - `qc_review.json` 回答“人工是否接受”。

4. 保持显式失败优先
   - 对非法输入、缺失依赖、schema 不一致、artifact 不匹配，继续优先显式报错，不引入 silent fallback。

5. 保持 stratified QC 的 exact-match 选择策略
   - 当前只接受 exact-match stratum 命中。
   - 未命中时必须显式记录 `global_fallback` 与原因。

6. 保持可选依赖隔离
   - `torch`、`PySide6`、`openslide`、`PyYAML` 继续通过可选依赖或独立环境安装，不回写到基础依赖集合。

## 禁止变更项

- 未经确认，不修改 `src/`、`tests/`、`configs/` 实现逻辑。
- 未经确认，不把本轮审计记录包装成新的发布版本。
- 不删除现有 `build/validation/` 工件；它们是历史验证证据。
- 不把“现存工件仍可校验”表述成“本轮已重新执行真实 SVS 全链路”。
- 不因为补救而扩展到设计边界外内容，例如：
  - production latent diffusion / ControlNet
  - 图形化 QC review UI
  - 权限/签名系统
  - 数据库或远端协作审阅
  - 生产级 OME-TIFF 流式写入

## 补救优先级决策

- 第一优先级：契约一致性缺口
  - 仓库内 `AGENTS.md`
  - `qc_review` CLI 验证入口
- 第二优先级：输出摘要显式失败
- 第三优先级：环境化验证复跑
- 第四优先级：大文件拆分与维护性收敛
