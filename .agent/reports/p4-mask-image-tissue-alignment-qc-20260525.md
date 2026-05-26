# P4 Mask-Image Tissue Alignment QC Report - 2026-05-25

## Scope

- Version: `v0.72.11`
- Feature loop: P4 / Phase 6 automatic QC proxy for mask-image tissue alignment.
- User constraint: do not update design/development code trace blocks until the whole project is complete.
- Multiagent: not used.

## Implementation

- Added `mask_image_tissue_alignment_proxy` to `build_qc_report()` mask-region metrics.
- The proxy estimates tissue/background from the generated WSI level-0 image and compares it with `mask > 0`.
- A clear mismatch fails `levels.mask_region.status` and `overall_status`.
- Low-confidence image tissue proxy cases keep an explanatory metric message and are not described as expert semantic QC.

## Files

- `src/he_wsi_generator/qc/engine.py`
- `tests/test_outputs_qc_archive.py`
- `README.md`
- `VERSION`
- `pyproject.toml`
- `configs/generation.default.json`
- `src/he_wsi_generator/constants.py`
- `tests/*.py`
- `docs/DEMANDS.MD`
- `docs/CHANGELOG.md`
- `docs/audit/ACCEPTANCE_CHECKLIST.md`
- `docs/audit/IMPLEMENTATION_PLAN.md`
- `docs/audit/DECISIONS.md`

## Verification

- RED evidence: `test_build_qc_report_flags_mask_image_tissue_alignment_mismatch` failed on the old implementation with `KeyError: 'mask_image_tissue_alignment_proxy'`.
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive.OutputQCArchiveTests.test_build_qc_report_flags_mask_image_tissue_alignment_mismatch -v`
  - `Ran 1 test in 0.007s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_outputs_qc_archive -v`
  - `Ran 32 tests in 0.096s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - `Ran 2 tests in 0.000s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - `Ran 282 tests in 20.835s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - Installed `multi-center-wsi-generator 0.72.11`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - `v0.72.11`
- Package metadata/constants check:
  - metadata: `0.72.11`
  - `PROJECT_VERSION=v0.72.11`
  - `PACKAGE_VERSION=0.72.11`
- `git diff --check`
  - Passed with no output.

## Remaining Boundaries

- Not a pathology semantic classifier.
- Not expert-level segmentation validation.
- Not a production inference backend or production training loop.
- Real SVS full-chain rerun was not executed in this loop; existing evidence remains historical v0.72.1.
