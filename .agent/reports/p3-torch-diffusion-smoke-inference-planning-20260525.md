# P3 Torch Diffusion Smoke Inference Planning Contract

## Summary

- Version: `v0.72.13`
- Date: 2026-05-25
- Status: completed and verified
- Worker mode: not used; implemented directly in the main session because the remaining work was a single serial feature loop with overlapping docs.

## Feature Loop

`AC-MISS-04` / P3 conservative model contract increment:

- `train_torch_diffusion_smoke_model()` now emits a PyTorch diffusion smoke checkpoint manifest that can be consumed by unified generation planning.
- The manifest is `usable_for_inference=true` only inside a smoke-only contract:
  - `compatible_generation_backends=["torch-diffusion-smoke"]`
  - `production_ready=false`
  - model architecture contract for `smoke_latent_unet`
  - condition input contract for mask, style seed, texture token, coord, structure anchor, source condition, and previous scale
- `create_generation_plan(..., generation_backend="torch-diffusion-smoke")` accepts that checkpoint and preserves the inference contract summary.
- The same checkpoint is rejected for `generation_backend="smoke-cascade"`.

## Code Changes

- `src/he_wsi_generator/models/torch_training_contracts.py`
  - `diffusion_checkpoint_manifest()` writes `usable_for_inference=true` and an `inference_contract`.
  - `_diffusion_smoke_inference_contract()` defines the smoke-only non-production planning contract.
- `src/he_wsi_generator/generation/planner.py`
  - `create_generation_plan()` accepts a `generation_backend` argument, checks backend compatibility, and records `checkpoint_inference_contract`.
- `src/he_wsi_generator/generation/executor.py`
  - `run_torch_diffusion_smoke_generation()` carries checkpoint inference contract into the run summary plan.
- `tests/test_torch_training.py`
  - Added coverage for torch diffusion smoke checkpoint planning compatibility and run summary contract persistence.

## Documentation

- Updated:
  - `README.md`
  - `docs/DEMANDS.MD`
  - `docs/CHANGELOG.md`
  - `docs/audit/ACCEPTANCE_CHECKLIST.md`
  - `docs/audit/IMPLEMENTATION_PLAN.md`
  - `docs/audit/DECISIONS.md`
- Not updated:
  - `docs/plans/2026-05-18-he-wsi-generator-study-design.md`
  - `docs/dev/2026-05-23-he-wsi-generator-development-appendix.md`
- Reason: user requested design/dev code trace blocks be updated only after the whole project is complete.

## Verification

- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training.TorchSmokeTrainingTests.test_run_torch_diffusion_smoke_generation_writes_archived_sample tests.test_torch_training.TorchSmokeTrainingTests.test_torch_diffusion_smoke_checkpoint_can_plan_torch_generation_backend_only tests.test_torch_training.TorchSmokeTrainingTests.test_train_torch_diffusion_smoke_model_writes_noise_prediction_manifest -v`
  - Passed: `Ran 3 tests in 2.084s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_torch_training -v`
  - Passed: `Ran 26 tests in 11.825s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest tests.test_models_generation tests.test_generation_runner tests.test_version -v`
  - Passed: `Ran 59 tests in 1.485s OK`
- `mamba run -n MultiCenterWSIGenerator python -m unittest discover -s tests -v`
  - Passed: `Ran 284 tests in 14.265s OK`
- `mamba run -n MultiCenterWSIGenerator python -m pip install -e .`
  - Passed: installed `multi-center-wsi-generator 0.72.13`
- `mamba run -n MultiCenterWSIGenerator he-wsi-gen --version`
  - Passed: `v0.72.13`
- Metadata/constants check:
  - Passed: package metadata `0.72.13`, `PROJECT_VERSION=v0.72.13`, `PACKAGE_VERSION=0.72.13`
- `git diff --check`
  - Passed with no output.

## Boundaries

- This does not implement production latent diffusion / ControlNet / DiT.
- This does not implement a production training loop, production inference backend, production checkpoint, or gigapixel production writer.
- This only makes PyTorch diffusion smoke checkpoints usable by the unified planning gate under a smoke-only, non-production contract.
