# P5 Prior Production Readiness Contract - 2026-05-25

## Summary

- Version: `v0.72.12`
- Feature loop: P5 prior manifest production readiness contract gate.
- Scope: `src/he_wsi_generator/priors/artifacts.py` and `tests/test_priors.py`.
- Multiagent: not used.

## Implemented

- `build_prior_manifest_from_artifacts()` now writes `production_readiness` into generated prior manifests.
- The default readiness contract explicitly marks statistical layout/style/texture priors as `production_ready=false`.
- `validate_prior_manifest()` validates the readiness contract shape and rejects `production_ready=true` manifests when:
  - component contracts are missing;
  - layout/style/texture components are not explicitly production-ready;
  - a component still declares a statistical/proxy backend or non-production limitations.

## Boundary

- This is a manifest contract gate only.
- It does not implement a trainable layout generator, style encoder, texture codebook, VQ-VAE, morphology token sampler, or production generation backend.

## Verification

- RED evidence:
  - New production readiness assertion failed on old code with `KeyError: 'production_readiness'`.
  - New production-ready missing component contract test failed on old code with `AssertionError: PriorArtifactError not raised`.
- Focused RED/GREEN:
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_priors.PriorArtifactTests.test_build_prior_manifest_from_artifacts_writes_valid_manifest tests.test_priors.PriorArtifactTests.test_prior_manifest_rejects_production_ready_without_component_contracts -v`
  - Result after implementation: `Ran 2 tests in 0.001s OK`
- Focused module:
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_priors -v`
  - Result: `Ran 10 tests in 0.235s OK`
- Version:
  - `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_version -v`
  - Result: `Ran 2 tests in 0.000s OK`
- Full suite:
  - `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - Result: `Ran 283 tests in 22.987s OK`
- Editable install:
  - `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - Result: built editable wheel `multi_center_wsi_generator-0.72.12-0.editable-py3-none-any.whl` and installed `multi-center-wsi-generator-0.72.12`
- CLI version:
  - `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - Result: `v0.72.12`
- Package metadata/constants:
  - `mamba run -n MultiCenterWSIGenerator python - <<'PY' ... metadata/constants ... PY`
  - Result: package metadata `0.72.12`, `PROJECT_VERSION=v0.72.12`, `PACKAGE_VERSION=0.72.12`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with no output

## Deferred Verification

- Real SVS full-chain rerun was not performed in this loop; current real-SVS evidence remains the historical v0.72.1 smoke/proxy validation artifact.
- Design/development document trace blocks are intentionally deferred until the whole project is complete, per the latest user instruction.
