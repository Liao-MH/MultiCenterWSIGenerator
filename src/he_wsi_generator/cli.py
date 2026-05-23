import argparse
import json
import sys
from pathlib import Path

from .constants import DEFAULT_GENERATION_CONFIG, PROJECT_VERSION
from .generation.conditioning import (
    GenerationConditionError,
    build_generation_condition_packet,
)
from .generation.executor import (
    GenerationExecutionError,
    run_smoke_generation,
    run_torch_diffusion_smoke_generation,
)
from .generation.planner import create_generation_plan
from .io.audit import audit_manifest, build_reader
from .metadata.archive import archive_sample
from .models.training import ModelRunError, create_training_run
from .models.training_batch import (
    TrainingBatchError,
    load_training_batch,
    write_training_batch_summary,
)
from .models.training_index import TrainingIndexError, build_training_index
from .models.torch_training import (
    TorchTrainingError,
    sample_torch_diffusion_smoke_model,
    train_torch_diffusion_smoke_model,
    train_torch_smoke_model,
    train_torch_vae_smoke_model,
)
from .priors.artifacts import (
    PriorArtifactError,
    build_prior_manifest_from_artifacts,
    load_prior_manifest,
)
from .priors.layout import LayoutMaskPriorBuildError, build_layout_mask_prior_from_training_index
from .priors.style import StylePriorBuildError, build_style_prior_from_training_index
from .priors.texture import TexturePriorBuildError, build_texture_prior_from_embedding_cache
from .qc.reference import QCReferenceBuildError, build_qc_reference_distribution
from .schemas import ValidationError, load_document, validate_file
from .ui.config import create_default_ui_config, load_ui_config, save_ui_config
from .ui.controller import collect_output_summary
from .ui.jobs import JobRunner, JobRunnerError
from .ui.pyside_app import UIUnavailableError, launch_ui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="he-wsi-gen",
        description="H&E WSI generator core utilities.",
    )
    parser.add_argument("--version", action="version", version=PROJECT_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a project JSON/YAML contract file.",
    )
    validate_parser.add_argument(
        "kind",
        choices=[
            "manifest",
            "input-manifest",
            "label-mapping",
            "generation-config",
            "metadata",
            "qc",
            "qc-report",
        ],
        help="Schema kind to validate.",
    )
    validate_parser.add_argument("path", help="Path to the JSON/YAML file.")

    init_parser = subparsers.add_parser(
        "init-generation-config",
        help="Write the documented default generation config.",
    )
    init_parser.add_argument("output", help="Destination JSON path.")

    audit_parser = subparsers.add_parser(
        "audit-manifest",
        help="Validate a manifest and read WSI metadata into an audit JSON.",
    )
    audit_parser.add_argument("manifest", help="Path to the input manifest JSON/YAML.")
    audit_parser.add_argument(
        "--backend",
        choices=["openslide", "fixture-image"],
        default="openslide",
        help="Slide reader backend. Use fixture-image only for smoke tests.",
    )
    audit_parser.add_argument(
        "--output",
        required=True,
        help="Path to write the manifest audit JSON.",
    )

    prior_parser = subparsers.add_parser(
        "validate-prior-manifest",
        help="Validate a prior manifest and referenced artifact files.",
    )
    prior_parser.add_argument("path", help="Path to prior_manifest.json.")

    prior_build_parser = subparsers.add_parser(
        "build-prior-manifest",
        help="Build prior_manifest.json from required prior artifact JSON files.",
    )
    prior_build_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where prior_manifest.json will be written.",
    )
    prior_build_parser.add_argument("--prior-id", required=True, help="Prior identifier.")
    prior_build_parser.add_argument("--dataset-id", required=True, help="Training dataset id.")
    prior_build_parser.add_argument(
        "--input-manifest",
        required=True,
        help="Path recorded as input_data.manifest_path.",
    )
    prior_build_parser.add_argument(
        "--training-data-version",
        required=True,
        help="Training data version recorded in the prior manifest.",
    )
    prior_build_parser.add_argument(
        "--wsi-id",
        action="append",
        required=True,
        help="WSI id used to build the prior. Repeat for multiple slides.",
    )
    prior_build_parser.add_argument("--random-seed", type=int, required=True, help="Random seed.")
    prior_build_parser.add_argument(
        "--layout-mask-prior",
        required=True,
        help="Path to layout_mask_prior JSON.",
    )
    prior_build_parser.add_argument("--style-prior", required=True, help="Path to style_prior JSON.")
    prior_build_parser.add_argument(
        "--texture-prior",
        required=True,
        help="Path to texture_prior JSON.",
    )
    prior_build_parser.add_argument(
        "--qc-reference-distribution",
        required=True,
        help="Path to qc_reference_distribution JSON.",
    )

    qc_ref_parser = subparsers.add_parser(
        "build-qc-reference",
        help="Build a qc_reference_distribution JSON from QC reports.",
    )
    qc_ref_parser.add_argument("qc_reports", nargs="+", help="Input QC report JSON/YAML files.")
    qc_ref_parser.add_argument(
        "--metric",
        action="append",
        required=True,
        help="Numeric metric name to include. Repeat for multiple metrics.",
    )
    qc_ref_parser.add_argument(
        "--min-samples",
        type=int,
        default=2,
        help="Minimum sample count required per metric.",
    )
    qc_ref_parser.add_argument("--output", required=True, help="Path to write reference JSON.")

    layout_prior_parser = subparsers.add_parser(
        "build-layout-mask-prior",
        help="Build a layout_mask_prior JSON from mask tiles in a training-index batch.",
    )
    layout_prior_parser.add_argument("training_index", help="Path to training-index JSONL.")
    layout_prior_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    layout_prior_parser.add_argument("--split", help="Optional split filter.")
    layout_prior_parser.add_argument(
        "--cascade-level",
        default="1/1",
        help="Cascade level filter.",
    )
    layout_prior_parser.add_argument(
        "--output",
        required=True,
        help="Path to write layout_mask_prior JSON.",
    )

    style_prior_parser = subparsers.add_parser(
        "build-style-prior",
        help="Build a style_prior JSON from RGB tiles in a training-index batch.",
    )
    style_prior_parser.add_argument("training_index", help="Path to training-index JSONL.")
    style_prior_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    style_prior_parser.add_argument("--split", help="Optional split filter.")
    style_prior_parser.add_argument(
        "--cascade-level",
        default="1/1",
        help="Cascade level filter.",
    )
    style_prior_parser.add_argument("--output", required=True, help="Path to write style_prior JSON.")

    texture_prior_parser = subparsers.add_parser(
        "build-texture-prior",
        help="Build a texture_prior JSON from embedding cache and cluster report.",
    )
    texture_prior_parser.add_argument("--cache-dir", required=True, help="Embedding cache directory.")
    texture_prior_parser.add_argument("--cache-key", required=True, help="Embedding cache key.")
    texture_prior_parser.add_argument(
        "--cluster-report",
        required=True,
        help="Path to cluster report JSON.",
    )
    texture_prior_parser.add_argument(
        "--output",
        required=True,
        help="Path to write texture_prior JSON.",
    )

    train_parser = subparsers.add_parser(
        "init-training-run",
        help="Validate a training config and initialize run manifests.",
    )
    train_parser.add_argument("config", help="Path to training config JSON/YAML.")

    index_parser = subparsers.add_parser(
        "build-training-index",
        help="Build a cascade training-index JSONL from manifest, audit, and label mappings.",
    )
    index_parser.add_argument("manifest", help="Path to input manifest JSON/YAML.")
    index_parser.add_argument("--audit", required=True, help="Path to manifest audit JSON/YAML.")
    index_parser.add_argument(
        "--label-mapping",
        action="append",
        required=True,
        help="Path to a label mapping JSON/YAML. Repeat for multiple annotations.",
    )
    index_parser.add_argument("--output", required=True, help="Path to write training-index JSONL.")

    batch_parser = subparsers.add_parser(
        "inspect-training-batch",
        help="Load a training-index batch and write an auditable summary JSON.",
    )
    batch_parser.add_argument("training_index", help="Path to training-index JSONL.")
    batch_parser.add_argument("--batch-size", type=int, required=True, help="Batch size to load.")
    batch_parser.add_argument("--split", help="Optional split filter.")
    batch_parser.add_argument("--cascade-level", help="Optional cascade level filter.")
    batch_parser.add_argument(
        "--include-image",
        action="store_true",
        help="Also read RGB image tiles into the audited batch summary.",
    )
    batch_parser.add_argument("--output", required=True, help="Path to write batch summary JSON.")

    torch_train_parser = subparsers.add_parser(
        "train-torch-smoke",
        help="Run a small real PyTorch smoke training loop from a training-index batch.",
    )
    torch_train_parser.add_argument("training_index", help="Path to training-index JSONL.")
    torch_train_parser.add_argument("--output-dir", required=True, help="Training output directory.")
    torch_train_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    torch_train_parser.add_argument("--split", help="Optional split filter.")
    torch_train_parser.add_argument("--cascade-level", default="1/1", help="Cascade level filter.")
    torch_train_parser.add_argument("--epochs", type=int, default=1, help="Training epochs.")
    torch_train_parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="Optimizer learning rate.",
    )
    torch_train_parser.add_argument("--random-seed", type=int, default=0, help="Torch random seed.")
    torch_train_parser.add_argument("--device", default="cpu", help="Torch device, defaults to cpu.")

    torch_vae_parser = subparsers.add_parser(
        "train-torch-vae-smoke",
        help="Run a small PyTorch VAE smoke training loop from RGB training-index tiles.",
    )
    torch_vae_parser.add_argument("training_index", help="Path to training-index JSONL.")
    torch_vae_parser.add_argument("--output-dir", required=True, help="Training output directory.")
    torch_vae_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    torch_vae_parser.add_argument("--split", help="Optional split filter.")
    torch_vae_parser.add_argument("--cascade-level", default="1/1", help="Cascade level filter.")
    torch_vae_parser.add_argument("--epochs", type=int, default=1, help="Training epochs.")
    torch_vae_parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="Optimizer learning rate.",
    )
    torch_vae_parser.add_argument("--random-seed", type=int, default=0, help="Torch random seed.")
    torch_vae_parser.add_argument("--device", default="cpu", help="Torch device, defaults to cpu.")
    torch_vae_parser.add_argument(
        "--latent-channels",
        type=int,
        default=4,
        help="Number of smoke VAE latent channels.",
    )
    torch_vae_parser.add_argument(
        "--latent-size",
        type=int,
        default=64,
        help="Square side length for smoke VAE latent maps.",
    )
    torch_vae_parser.add_argument(
        "--kl-weight",
        type=float,
        default=1e-4,
        help="Weight for the smoke VAE KL loss term.",
    )

    torch_diffusion_parser = subparsers.add_parser(
        "train-torch-diffusion-smoke",
        help="Run a small mask-conditioned DDPM-style PyTorch smoke training loop.",
    )
    torch_diffusion_parser.add_argument("training_index", help="Path to training-index JSONL.")
    torch_diffusion_parser.add_argument(
        "--output-dir",
        required=True,
        help="Training output directory.",
    )
    torch_diffusion_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    torch_diffusion_parser.add_argument("--split", help="Optional split filter.")
    torch_diffusion_parser.add_argument(
        "--cascade-level",
        default="1/1",
        help="Cascade level filter.",
    )
    torch_diffusion_parser.add_argument("--epochs", type=int, default=1, help="Training epochs.")
    torch_diffusion_parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-3,
        help="Optimizer learning rate.",
    )
    torch_diffusion_parser.add_argument(
        "--random-seed",
        type=int,
        default=0,
        help="Torch random seed.",
    )
    torch_diffusion_parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device, defaults to cpu.",
    )
    torch_diffusion_parser.add_argument(
        "--diffusion-timesteps",
        type=int,
        default=16,
        help="Number of DDPM timesteps for the smoke noise schedule.",
    )
    torch_diffusion_parser.add_argument(
        "--beta-start",
        type=float,
        default=1e-4,
        help="Start beta for the linear DDPM smoke schedule.",
    )
    torch_diffusion_parser.add_argument(
        "--beta-end",
        type=float,
        default=0.02,
        help="End beta for the linear DDPM smoke schedule.",
    )
    torch_diffusion_parser.add_argument(
        "--latent-size",
        type=int,
        default=64,
        help="Square side length for downsampled RGB proxy latents.",
    )
    torch_diffusion_parser.add_argument(
        "--vae-checkpoint-manifest",
        help="Optional VAE smoke checkpoint_manifest.json used to encode trainable VAE latents.",
    )

    torch_sample_parser = subparsers.add_parser(
        "sample-torch-diffusion-smoke",
        help="Sample a small proxy latent preview from a diffusion smoke checkpoint.",
    )
    torch_sample_parser.add_argument(
        "checkpoint_manifest",
        help="Path to a diffusion smoke checkpoint_manifest.json.",
    )
    torch_sample_parser.add_argument("training_index", help="Path to training-index JSONL.")
    torch_sample_parser.add_argument(
        "--output-dir",
        required=True,
        help="Sampling output directory.",
    )
    torch_sample_parser.add_argument("--batch-size", type=int, required=True, help="Batch size.")
    torch_sample_parser.add_argument("--split", help="Optional split filter.")
    torch_sample_parser.add_argument(
        "--cascade-level",
        default="1/1",
        help="Cascade level filter.",
    )
    torch_sample_parser.add_argument(
        "--sample-steps",
        type=int,
        default=8,
        help="Reverse DDPM smoke sample steps.",
    )
    torch_sample_parser.add_argument(
        "--random-seed",
        type=int,
        default=0,
        help="Torch random seed.",
    )
    torch_sample_parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device, defaults to cpu.",
    )
    torch_sample_parser.add_argument(
        "--condition-packet",
        help="Optional generation_condition_packet JSON recorded in the sample manifest.",
    )
    torch_sample_parser.add_argument(
        "--previous-scale-condition",
        help="Optional .npy RGB preview used as previous-scale cross-scale condition.",
    )

    plan_parser = subparsers.add_parser(
        "plan-generation",
        help="Create a cascade generation plan from config, prior, and checkpoint manifests.",
    )
    plan_parser.add_argument("generation_config", help="Path to generation config JSON/YAML.")
    plan_parser.add_argument("--prior-manifest", required=True, help="Path to prior_manifest.json.")
    plan_parser.add_argument(
        "--checkpoint-manifest",
        required=True,
        help="Path to checkpoint_manifest.json.",
    )
    plan_parser.add_argument("--output", required=True, help="Path to write generation plan JSON.")

    condition_parser = subparsers.add_parser(
        "build-condition-packet",
        help="Build a generation condition packet from config and prior artifacts.",
    )
    condition_parser.add_argument("generation_config", help="Path to generation config JSON/YAML.")
    condition_parser.add_argument("--prior-manifest", required=True, help="Path to prior_manifest.json.")
    condition_parser.add_argument("--output", required=True, help="Path to write condition packet JSON.")
    condition_parser.add_argument(
        "--cascade-level",
        default="1/1",
        help="Cascade level for this tile condition packet.",
    )
    condition_parser.add_argument(
        "--tile-origin-x",
        type=int,
        default=0,
        help="40x level0 tile origin x coordinate.",
    )
    condition_parser.add_argument(
        "--tile-origin-y",
        type=int,
        default=0,
        help="40x level0 tile origin y coordinate.",
    )

    run_parser = subparsers.add_parser(
        "run-generation",
        help="Run an explicit generation backend and archive a generated sample.",
    )
    run_parser.add_argument("generation_config", help="Path to generation config JSON/YAML.")
    run_parser.add_argument(
        "--backend",
        required=True,
        choices=["smoke-cascade", "torch-diffusion-smoke"],
        help="Generation backend. smoke backends validate plumbing, not production realism.",
    )
    run_parser.add_argument("--prior-manifest", required=True, help="Path to prior_manifest.json.")
    run_parser.add_argument(
        "--checkpoint-manifest",
        required=True,
        help="Path to trained checkpoint_manifest.json.",
    )
    run_parser.add_argument(
        "--training-index",
        help="Training-index JSONL required by torch-diffusion-smoke.",
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Backend batch size for torch-diffusion-smoke.",
    )
    run_parser.add_argument("--output-root", required=True, help="Generated sample output directory.")
    run_parser.add_argument("--generated-id", required=True, help="Generated sample id.")
    run_parser.add_argument(
        "--condition-packet",
        help="Optional generation_condition_packet JSON recorded by smoke generation backends.",
    )

    archive_parser = subparsers.add_parser(
        "archive-sample",
        help="Write metadata.json, qc.json, and append batch.jsonl for one generated sample.",
    )
    archive_parser.add_argument("output_root", help="Generated sample output directory.")
    archive_parser.add_argument("--metadata", required=True, help="Input metadata JSON/YAML.")
    archive_parser.add_argument("--qc", required=True, help="Input QC report JSON/YAML.")

    output_summary_parser = subparsers.add_parser(
        "inspect-output-summary",
        help="Inspect a metadata/QC output summary as JSON.",
    )
    output_summary_parser.add_argument("--metadata", required=True, help="Input metadata JSON.")
    output_summary_parser.add_argument("--qc", required=True, help="Input QC JSON.")

    ui_config_parser = subparsers.add_parser(
        "write-ui-config",
        help="Write the default single-page console UI config JSON.",
    )
    ui_config_parser.add_argument("output", help="Destination UI config JSON path.")

    launch_ui_parser = subparsers.add_parser(
        "launch-ui",
        help="Launch the optional PySide6 single-page desktop console.",
    )
    launch_ui_parser.add_argument("--config", help="Optional UI config JSON path.")

    job_parser = subparsers.add_parser(
        "run-local-job",
        help="Create and synchronously run a persisted local command job.",
    )
    job_parser.add_argument("job_root", help="Directory used to store local job records.")
    job_parser.add_argument("--job-id", required=True, help="Unique local job id.")
    job_parser.add_argument(
        "--cwd",
        help="Optional working directory for the command being run.",
    )

    cancel_job_parser = subparsers.add_parser(
        "cancel-local-job",
        help="Cancel a queued persisted local command job.",
    )
    cancel_job_parser.add_argument("job_root", help="Directory used to store local job records.")
    cancel_job_parser.add_argument("--job-id", required=True, help="Queued local job id to cancel.")
    cancel_job_parser.add_argument(
        "--message",
        default="job cancelled",
        help="Cancellation message persisted in the job record.",
    )

    inspect_job_parser = subparsers.add_parser(
        "inspect-local-job",
        help="Inspect a persisted local command job record as JSON.",
    )
    inspect_job_parser.add_argument("job_root", help="Directory used to store local job records.")
    inspect_job_parser.add_argument("--job-id", required=True, help="Local job id to inspect.")

    list_job_parser = subparsers.add_parser(
        "list-local-jobs",
        help="List persisted local command job records as JSON.",
    )
    list_job_parser.add_argument("job_root", help="Directory used to store local job records.")
    return parser


def _build_local_job_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="he-wsi-gen run-local-job",
        description="Create and synchronously run a persisted local command job.",
    )
    parser.add_argument("job_root", help="Directory used to store local job records.")
    parser.add_argument("--job-id", required=True, help="Unique local job id.")
    parser.add_argument(
        "--cwd",
        help="Optional working directory for the command being run.",
    )
    return parser


def _run_local_job_cli(argv: list[str]) -> int:
    local_parser = _build_local_job_parser()
    if "-h" in argv or "--help" in argv:
        local_parser.parse_args(argv)
        return 0
    if "--" not in argv:
        local_parser.error("run-local-job requires a command after --")
    separator_index = argv.index("--")
    args = local_parser.parse_args(argv[:separator_index])
    command = argv[separator_index + 1 :]
    try:
        runner = JobRunner(args.job_root)
        record = runner.create_job(args.job_id, command, cwd=args.cwd)
        record = runner.run_job(record["job_id"])
    except JobRunnerError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    message = f"local job {record['status']}: {record['record_path']}"
    if record["status"] == "completed":
        print(message)
        return 0
    print(message, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] == "run-local-job":
        return _run_local_job_cli(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        try:
            validate_file(args.kind, args.path)
        except ValidationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{args.kind} valid: {args.path}")
        return 0

    if args.command == "init-generation-config":
        output = Path(args.output)
        if output.exists():
            print(f"{output} already exists", file=sys.stderr)
            return 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(DEFAULT_GENERATION_CONFIG, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"generation-config written: {output}")
        return 0

    if args.command == "audit-manifest":
        try:
            manifest = validate_file("manifest", args.manifest)
            audit = audit_manifest(manifest, reader=build_reader(args.backend))
        except (ValidationError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(f"manifest audit written: {output}")
        return 0

    if args.command == "validate-prior-manifest":
        try:
            load_prior_manifest(args.path, verify_files=True)
        except PriorArtifactError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"prior manifest valid: {args.path}")
        return 0

    if args.command == "build-prior-manifest":
        try:
            manifest = build_prior_manifest_from_artifacts(
                output_dir=args.output_dir,
                prior_id=args.prior_id,
                dataset_id=args.dataset_id,
                input_manifest_path=args.input_manifest,
                training_data_version=args.training_data_version,
                wsi_ids=args.wsi_id,
                random_seed=args.random_seed,
                layout_mask_prior_path=args.layout_mask_prior,
                style_prior_path=args.style_prior,
                texture_prior_path=args.texture_prior,
                qc_reference_distribution_path=args.qc_reference_distribution,
            )
        except PriorArtifactError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            "prior manifest written: "
            f"{Path(args.output_dir) / 'prior_manifest.json'} "
            f"({len(manifest['artifacts'])} artifacts)"
        )
        return 0

    if args.command == "build-qc-reference":
        try:
            reports = [load_document(path) for path in args.qc_reports]
            reference = build_qc_reference_distribution(
                reports,
                output_path=args.output,
                metric_names=args.metric,
                min_samples=args.min_samples,
            )
        except (ValidationError, QCReferenceBuildError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"qc reference distribution written: {args.output} "
            f"({reference['sample_count']} reports)"
        )
        return 0

    if args.command == "build-layout-mask-prior":
        try:
            prior = build_layout_mask_prior_from_training_index(
                args.training_index,
                output_path=args.output,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
            )
        except LayoutMaskPriorBuildError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"layout/mask prior written: {args.output} ({prior['sample_count']} samples)")
        return 0

    if args.command == "build-style-prior":
        try:
            style_prior = build_style_prior_from_training_index(
                args.training_index,
                output_path=args.output,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
            )
        except StylePriorBuildError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"style prior written: {args.output} ({style_prior['sample_count']} samples)")
        return 0

    if args.command == "build-texture-prior":
        try:
            prior = build_texture_prior_from_embedding_cache(
                cache_dir=args.cache_dir,
                cache_key=args.cache_key,
                cluster_report_path=args.cluster_report,
                output_path=args.output,
            )
        except TexturePriorBuildError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"texture prior written: {args.output} ({prior['cluster_count']} clusters)")
        return 0

    if args.command == "init-training-run":
        try:
            config = load_document(args.config)
            run = create_training_run(config)
        except (ValidationError, ModelRunError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"training run initialized: {run['output_dir']}")
        return 0

    if args.command == "build-training-index":
        try:
            manifest = load_document(args.manifest)
            audit = load_document(args.audit)
            mappings = [load_document(path) for path in args.label_mapping]
            summary = build_training_index(manifest, audit, mappings, args.output)
        except (ValidationError, TrainingIndexError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"training index written: {summary['output_path']} ({summary['sample_count']} samples)")
        return 0

    if args.command == "inspect-training-batch":
        try:
            batch = load_training_batch(
                args.training_index,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
                include_image=args.include_image,
            )
            summary = write_training_batch_summary(batch, args.output)
        except TrainingBatchError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"training batch summary written: {args.output} ({summary['batch_size']} samples)")
        return 0

    if args.command == "train-torch-smoke":
        try:
            run = train_torch_smoke_model(
                training_index_path=args.training_index,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
                epochs=args.epochs,
                learning_rate=args.learning_rate,
                random_seed=args.random_seed,
                device=args.device,
            )
        except TorchTrainingError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"torch smoke training completed: {run['checkpoint_manifest_path']}")
        return 0

    if args.command == "train-torch-vae-smoke":
        try:
            run = train_torch_vae_smoke_model(
                training_index_path=args.training_index,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
                epochs=args.epochs,
                learning_rate=args.learning_rate,
                random_seed=args.random_seed,
                device=args.device,
                latent_channels=args.latent_channels,
                latent_size=args.latent_size,
                kl_weight=args.kl_weight,
            )
        except TorchTrainingError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"torch VAE smoke training completed: {run['checkpoint_manifest_path']}")
        return 0

    if args.command == "train-torch-diffusion-smoke":
        try:
            run = train_torch_diffusion_smoke_model(
                training_index_path=args.training_index,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
                epochs=args.epochs,
                learning_rate=args.learning_rate,
                random_seed=args.random_seed,
                device=args.device,
                diffusion_timesteps=args.diffusion_timesteps,
                beta_start=args.beta_start,
                beta_end=args.beta_end,
                latent_size=args.latent_size,
                vae_checkpoint_manifest_path=args.vae_checkpoint_manifest,
            )
        except TorchTrainingError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"torch diffusion smoke training completed: {run['checkpoint_manifest_path']}")
        return 0

    if args.command == "sample-torch-diffusion-smoke":
        try:
            sample = sample_torch_diffusion_smoke_model(
                checkpoint_manifest_path=args.checkpoint_manifest,
                training_index_path=args.training_index,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                split=args.split,
                cascade_level=args.cascade_level,
                sample_steps=args.sample_steps,
                random_seed=args.random_seed,
                device=args.device,
                condition_packet_path=args.condition_packet,
                previous_scale_condition_path=args.previous_scale_condition,
            )
        except TorchTrainingError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"torch diffusion smoke sample completed: {sample['sample_manifest_path']}")
        return 0

    if args.command == "plan-generation":
        try:
            config = load_document(args.generation_config)
            plan = create_generation_plan(
                config,
                prior_manifest_path=args.prior_manifest,
                checkpoint_manifest_path=args.checkpoint_manifest,
            )
        except (ValidationError, ModelRunError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(f"generation plan written: {output}")
        return 0

    if args.command == "build-condition-packet":
        try:
            config = load_document(args.generation_config)
            packet = build_generation_condition_packet(
                config,
                prior_manifest_path=args.prior_manifest,
                output_path=args.output,
                cascade_level=args.cascade_level,
                tile_origin_40x=(args.tile_origin_x, args.tile_origin_y),
            )
        except (ValidationError, GenerationConditionError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"condition packet written: {args.output} "
            f"({packet['conditions']['coord']['cascade_level']})"
        )
        return 0

    if args.command == "run-generation":
        try:
            config = load_document(args.generation_config)
            if args.backend == "smoke-cascade":
                run = run_smoke_generation(
                    config,
                    prior_manifest_path=args.prior_manifest,
                    checkpoint_manifest_path=args.checkpoint_manifest,
                    output_root=args.output_root,
                    generated_id=args.generated_id,
                    condition_packet_path=args.condition_packet,
                )
            elif args.backend == "torch-diffusion-smoke":
                if not args.training_index:
                    raise GenerationExecutionError(
                        "--training-index is required for torch-diffusion-smoke"
                    )
                run = run_torch_diffusion_smoke_generation(
                    config,
                    prior_manifest_path=args.prior_manifest,
                    checkpoint_manifest_path=args.checkpoint_manifest,
                    training_index_path=args.training_index,
                    output_root=args.output_root,
                    generated_id=args.generated_id,
                    batch_size=args.batch_size,
                    condition_packet_path=args.condition_packet,
                )
            else:
                raise GenerationExecutionError(f"unsupported generation backend: {args.backend}")
        except (ValidationError, GenerationExecutionError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"generation run completed: {run['generation_run_path']}")
        return 0

    if args.command == "archive-sample":
        try:
            metadata = load_document(args.metadata)
            qc = load_document(args.qc)
            archive = archive_sample(args.output_root, metadata, qc)
        except (ValidationError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"sample archived: {archive['batch_index_path']}")
        return 0

    if args.command == "inspect-output-summary":
        try:
            summary = collect_output_summary(args.metadata, args.qc)
        except (ValidationError, ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "write-ui-config":
        try:
            save_ui_config(create_default_ui_config(), args.output)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"ui config written: {args.output}")
        return 0

    if args.command == "launch-ui":
        try:
            config = load_ui_config(args.config) if args.config else create_default_ui_config()
            return launch_ui(config)
        except (UIUnavailableError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.command == "cancel-local-job":
        try:
            record = JobRunner(args.job_root).cancel_job(args.job_id, message=args.message)
        except JobRunnerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"local job cancelled: {record['record_path']}")
        return 0

    if args.command == "inspect-local-job":
        try:
            record = JobRunner(args.job_root).load_job(args.job_id)
        except JobRunnerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(record, indent=2))
        return 0

    if args.command == "list-local-jobs":
        try:
            records = JobRunner(args.job_root).list_jobs()
        except JobRunnerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(records, indent=2))
        return 0

    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
