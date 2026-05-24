# 审计验收清单（v0.62.0 基线）

## 说明

- 目标：把当前仓库是否满足 `v0.62.0` 已声明能力，以及补救前还缺什么，整理成可核验清单。
- 状态说明：`已完成`、`缺失`、`偏离`、`未验证`。

| ID | 验收项 | 证据 | 当前状态 | 备注 |
|---|---|---|---|---|
| AC-01 | 版本号在 README、`VERSION`、`pyproject.toml`、常量和版本测试中同步为 `v0.62.0` | `README.md`、`VERSION`、`pyproject.toml`、`src/he_wsi_generator/constants.py`、`tests/test_version.py`；命令：`PYTHONPATH=src python -m unittest tests.test_version -v` | 已完成 | 本轮实测通过 |
| AC-02 | 仓库保留设计说明、开发附录、需求与变更日志 | `docs/plans/2026-05-18-he-wsi-generator-study-design.md`、`docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`、`docs/DEMANDS.MD`、`docs/CHANGELOG.md` | 已完成 | 设计与开发说明齐全 |
| AC-03 | Core package / CLI / UI 控制层结构与开发附录建议的目录边界一致 | `src/he_wsi_generator/{io,annotations,embeddings,priors,models,generation,qc,metadata,ui}` | 已完成 | 模块分层存在 |
| AC-04 | `qc_review` artifact 构建、决策更新和输出摘要合并已实现 | `src/he_wsi_generator/qc/review.py`、`src/he_wsi_generator/ui/controller.py`、`src/he_wsi_generator/cli.py`、`tests/test_qc_review.py`、`tests/test_ui.py` | 已完成 | 本轮单测通过 |
| AC-05 | 统计 prior、condition packet、smoke generation、QC、chunked write audit 主链路可在当前环境通过单测验证 | `tests/test_priors.py`、`tests/test_generation_conditioning.py`、`tests/test_generation_runner.py`、`tests/test_outputs_qc_archive.py`；命令：`PYTHONPATH=src python -m unittest discover -s tests -v` | 已完成 | 当前环境 187 通过 |
| AC-06 | 仓库中保留了 `v0.62.0` 真实 SVS 验证工件，并且 metadata / QC / prior manifest 目前仍可校验 | `build/validation/v0.62.0-291288/...`；命令：`validate metadata`、`validate qc`、`validate-prior-manifest`、`inspect-output-summary --qc-review` | 已完成 | 本轮只校验现存工件，未重跑生成 |
| AC-07 | `AGENTS.md` 规则在仓库内可直接落地复用 | 仓库内 `rg --files -g 'AGENTS.md' .` 结果为空 | 缺失 | 当前仅会话注入，仓库本身没有实体文件 |
| AC-08 | `qc_review` 作为一等契约可通过通用 `validate` CLI 入口校验 | `src/he_wsi_generator/schemas.py::validate_file()`；`src/he_wsi_generator/cli.py` `validate` 子命令 choices | 缺失 | 内部有 `validate_qc_review()`，但没有 CLI/schema kind 暴露 |
| AC-09 | 输出摘要严格校验 metadata 契约，遇到坏 metadata 显式失败 | `src/he_wsi_generator/ui/controller.py::collect_output_summary()` | 偏离 | 当前只校验 QC/review，metadata 仅 `json.loads()` 后宽松读取 |
| AC-10 | CLI 和 PyTorch 训练/采样实现保持清晰模块边界，便于后续补救和回归 | `src/he_wsi_generator/cli.py` 1156 行、`src/he_wsi_generator/models/torch_training.py` 1912 行 | 偏离 | 功能可用，但维护面偏大 |
| AC-11 | 当前环境已验证 PyTorch smoke 训练/采样/生成路径 | `tests/test_torch_training.py`；命令：`python - <<'PY' import torch ...` 返回 `ModuleNotFoundError` | 未验证 | 21 个相关测试本轮被跳过 |
| AC-12 | 当前环境已验证 PySide6 图形 UI 可启动 | `python - <<'PY' import PySide6 ...` 返回 `ModuleNotFoundError` | 未验证 | 仅配置/控制层被验证，未验证真实 GUI 启动 |
| AC-13 | 本轮重新执行了真实 SVS 全链路生成并复核输出 | 原始 SVS 文件存在，但本轮未执行 `run-generation` 重建链路 | 未验证 | 只验证了现存 `build/validation` 工件 |

## 本轮实际验证命令

- `PYTHONPATH=src python -m unittest tests.test_version -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate generation-config configs/generation.default.json`
- `PYTHONPATH=src python -m unittest discover -s tests -v`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli validate-prior-manifest build/validation/v0.62.0-291288/prior/prior_manifest.json`
- `PYTHONPATH=src python -m he_wsi_generator.cli inspect-output-summary --metadata build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/metadata.json --qc build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc.json --qc-review build/validation/v0.62.0-291288/generated/gen-291288-smoke-sampled-mask-v062/qc_review.json`
