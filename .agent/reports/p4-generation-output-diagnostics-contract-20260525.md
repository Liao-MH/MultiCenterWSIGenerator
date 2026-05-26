# P4 Generation Output Diagnostics Contract Report

## Scope

- Version: `v0.72.14`
- Feature loop: P4 generation output diagnostics manifest contract.
- Goal: make each smoke / torch diffusion smoke generation run write one centralized `generation_output_diagnostics.json` that summarizes output artifact paths, pyramid/write mode, writer limits, tile execution/source status, and QC status.

## Implemented

- `run_smoke_generation()` now writes `generation_output_diagnostics.json` after metadata/QC archive publication and before `generation_run.json`.
- `run_torch_diffusion_smoke_generation()` writes the same diagnostics manifest and explicitly records non-applicable tile execution/source summaries.
- `metadata.json`, `generation_run.json`, and runner return values now reference `diagnostics_manifest_path`.
- Smoke diagnostics summarize `tile_manifest.json` and `tile_source_manifest.json` completed/pending/failed counts.
- Tile-streaming diagnostics record `write_mode=tile_iterator_streaming_write`, `atomic_publish`, `transaction_manifest_path`, and `resume_capable=false`.
- Added `validate_generation_output_diagnostics()` plus CLI schema kinds `generation-output-diagnostics` and `output-diagnostics`.
- Metadata schema now requires `output.diagnostics_manifest_path`; UI output summary preserves that path.

## Key Files

- `src/he_wsi_generator/generation/executor.py`
- `src/he_wsi_generator/schemas.py`
- `src/he_wsi_generator/cli.py`
- `src/he_wsi_generator/ui/controller.py`
- `tests/test_generation_runner.py`
- `tests/test_schemas.py`
- `tests/test_cli.py`
- `tests/test_torch_training.py`

## Validation

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_run_smoke_generation_writes_complete_output_object -v`
  - Passed: `Ran 1 test in 0.066s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_schemas.SchemaValidationTests.test_generation_output_diagnostics_accepts_required_contract tests.test_schemas.SchemaValidationTests.test_generation_output_diagnostics_rejects_invalid_status -v`
  - Passed: `Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_cli.CliValidationTests.test_cli_validates_generation_output_diagnostics_file -v`
  - Passed: `Ran 1 test in 0.049s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_generation_runner.GenerationRunnerTests.test_cli_runs_smoke_generation_with_tile_streaming_writer -v`
  - Passed: `Ran 1 test in 0.147s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_schemas tests.test_cli tests.test_generation_runner -v`
  - Passed: `Ran 40 tests in 1.706s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive tests.test_qc_review tests.test_ui_workflow tests.test_ui -v`
  - Passed: `Ran 80 tests in 0.559s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`
  - Passed: `Ran 26 tests in 19.133s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - Passed: `Ran 287 tests in 22.283s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - Passed: installed `multi-center-wsi-generator 0.72.14`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - Passed: `v0.72.14`
- Package metadata/constants check
  - Passed: `0.72.14`, `PROJECT_VERSION=v0.72.14`, `PACKAGE_VERSION=0.72.14`
- `git diff --check`
  - Passed with no output.

## Boundaries

- This does not implement production backend disk-level tile generation.
- This does not make OME-TIFF writes resumable after interruption.
- This does not replace `metadata.json`, `qc.json`, tile manifests, or writer transaction manifests; it summarizes and cross-links them for auditability.
