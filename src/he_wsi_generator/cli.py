import argparse
import sys

from .cli_commands import run_command
from .constants import PROJECT_VERSION
from .ui.jobs import JobRunner, JobRunnerError


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
            "qc-review",
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
    prior_build_parser.add_argument(
        "--wsi-tissue-overview",
        help="Optional path to wsi_tissue_overview JSON.",
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
    qc_ref_parser.add_argument(
        "--estimator",
        choices=[
            "observed_min_max_with_range_margin",
            "robust_iqr",
            "robust_mad_z_score",
        ],
        default="observed_min_max_with_range_margin",
        help="Threshold estimator used for warning/fail bounds.",
    )
    qc_ref_parser.add_argument(
        "--outlier-policy",
        choices=["none", "robust_iqr_filter"],
        default="none",
        help="Optional reference QC outlier policy applied before threshold estimation.",
    )
    qc_ref_parser.add_argument(
        "--stratify-by",
        action="append",
        help="Optional QC report dot-path used for stratified thresholds. Repeat for multiple fields.",
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

    style_policy_parser = subparsers.add_parser(
        "sample-style-policy",
        help="Sample a reproducible style policy artifact from a style_prior JSON.",
    )
    style_policy_parser.add_argument("style_prior", help="Path to style_prior JSON.")
    style_policy_parser.add_argument("--output", required=True, help="Path to write sampled_style_policy JSON.")
    style_policy_parser.add_argument("--sample-id", required=True, help="Sample identifier.")
    style_policy_parser.add_argument("--random-seed", type=int, required=True, help="Random seed.")

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

    texture_policy_parser = subparsers.add_parser(
        "sample-texture-policy",
        help="Sample a reproducible texture policy artifact from a texture_prior JSON.",
    )
    texture_policy_parser.add_argument("texture_prior", help="Path to texture_prior JSON.")
    texture_policy_parser.add_argument(
        "--output",
        required=True,
        help="Path to write sampled_texture_policy JSON.",
    )
    texture_policy_parser.add_argument("--sample-id", required=True, help="Sample identifier.")
    texture_policy_parser.add_argument("--random-seed", type=int, required=True, help="Random seed.")

    tissue_overview_parser = subparsers.add_parser(
        "build-wsi-tissue-overview",
        help="Build a WSI thumbnail tissue overview JSON from an input manifest.",
    )
    tissue_overview_parser.add_argument("manifest", help="Path to input manifest JSON/YAML.")
    tissue_overview_parser.add_argument(
        "--backend",
        choices=["openslide", "fixture-image"],
        default="openslide",
        help="Slide reader backend. Use fixture-image only for smoke tests.",
    )
    tissue_overview_parser.add_argument(
        "--thumbnail-max-size",
        type=int,
        default=1024,
        help="Maximum thumbnail side length used for tissue proxy metrics.",
    )
    tissue_overview_parser.add_argument(
        "--output",
        required=True,
        help="Path to write wsi_tissue_overview JSON.",
    )

    layout_sample_parser = subparsers.add_parser(
        "sample-layout-mask",
        help="Sample a reproducible layout mask artifact from a layout_mask_prior JSON.",
    )
    layout_sample_parser.add_argument("layout_mask_prior", help="Path to layout_mask_prior JSON.")
    layout_sample_parser.add_argument("--output-dir", required=True, help="Output directory.")
    layout_sample_parser.add_argument("--sample-id", required=True, help="Sample identifier.")
    layout_sample_parser.add_argument("--height", type=int, required=True, help="Output mask height.")
    layout_sample_parser.add_argument("--width", type=int, required=True, help="Output mask width.")
    layout_sample_parser.add_argument("--random-seed", type=int, required=True, help="Random seed.")
    layout_sample_parser.add_argument(
        "--wsi-tissue-overview",
        help="Optional wsi_tissue_overview JSON used to constrain the non-background footprint.",
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
    condition_parser.add_argument(
        "--sampled-layout-mask",
        help="Optional sampled_layout_mask JSON used as the mask condition.",
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
    run_parser.add_argument(
        "--resume-tile-manifest",
        help="Optional resumable tile manifest JSON for smoke-cascade resume execution.",
    )
    run_parser.add_argument(
        "--wsi-writer",
        choices=["array", "tile-streaming"],
        default="array",
        help=(
            "WSI writer backend. array preserves the default in-memory pyramid path; "
            "tile-streaming is smoke-cascade only."
        ),
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
    output_summary_parser.add_argument(
        "--qc-review",
        help="Optional qc_review JSON included in the output summary.",
    )

    qc_review_parser = subparsers.add_parser(
        "create-qc-review",
        help="Build a qc_review JSON from metadata.json and qc.json.",
    )
    qc_review_parser.add_argument("--metadata", required=True, help="Input metadata JSON.")
    qc_review_parser.add_argument("--qc", required=True, help="Input QC JSON.")
    qc_review_parser.add_argument("--output", required=True, help="Path to write qc_review JSON.")

    qc_review_decision_parser = subparsers.add_parser(
        "apply-qc-review-decision",
        help="Apply a final decision to a pending qc_review JSON.",
    )
    qc_review_decision_parser.add_argument("--review", required=True, help="Input qc_review JSON.")
    qc_review_decision_parser.add_argument(
        "--decision",
        required=True,
        choices=["accepted", "rejected", "needs_rerun"],
        help="Final reviewer decision.",
    )
    qc_review_decision_parser.add_argument("--reviewer", required=True, help="Reviewer name/id.")
    qc_review_decision_parser.add_argument("--note", default="", help="Optional reviewer note.")

    ui_config_parser = subparsers.add_parser(
        "write-ui-config",
        help="Write the default single-page console UI config JSON or YAML.",
    )
    ui_config_parser.add_argument("output", help="Destination UI config JSON or YAML path.")

    launch_ui_parser = subparsers.add_parser(
        "launch-ui",
        help="Launch the optional PySide6 single-page desktop console.",
    )
    launch_ui_parser.add_argument("--config", help="Optional UI config JSON or YAML path.")

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

    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
