import argparse
import json
import sys
from pathlib import Path

from .constants import DEFAULT_GENERATION_CONFIG
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
from .priors.sampler import LayoutMaskSamplerError, sample_layout_mask_from_prior
from .priors.style import StylePriorBuildError, build_style_prior_from_training_index
from .priors.tissue import WSITissueOverviewBuildError, build_wsi_tissue_overview_from_manifest
from .priors.texture import TexturePriorBuildError, build_texture_prior_from_embedding_cache
from .qc.reference import QCReferenceBuildError, build_qc_reference_distribution
from .qc.review import QCReviewError, apply_qc_review_decision, build_qc_review
from .schemas import ValidationError, load_document, validate_file
from .ui.config import create_default_ui_config, load_ui_config, save_ui_config
from .ui.controller import collect_output_summary
from .ui.jobs import JobRunner, JobRunnerError
from .ui.pyside_app import UIUnavailableError, launch_ui


def run_command(args: argparse.Namespace) -> int:
    if args.command == "validate":
        try:
            validate_file(args.kind, args.path)
        except (ValidationError, QCReviewError) as exc:
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
                wsi_tissue_overview_path=args.wsi_tissue_overview,
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
                estimator=args.estimator,
                outlier_policy=args.outlier_policy,
                stratify_by=args.stratify_by,
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

    if args.command == "build-wsi-tissue-overview":
        try:
            overview = build_wsi_tissue_overview_from_manifest(
                args.manifest,
                output_path=args.output,
                backend=args.backend,
                thumbnail_max_size=(args.thumbnail_max_size, args.thumbnail_max_size),
            )
        except WSITissueOverviewBuildError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"WSI tissue overview written: {args.output} "
            f"({overview['record_count']} records)"
        )
        return 0

    if args.command == "sample-layout-mask":
        try:
            manifest = sample_layout_mask_from_prior(
                layout_mask_prior_path=args.layout_mask_prior,
                output_dir=args.output_dir,
                sample_id=args.sample_id,
                mask_shape=(args.height, args.width),
                random_seed=args.random_seed,
                wsi_tissue_overview_path=args.wsi_tissue_overview,
            )
        except LayoutMaskSamplerError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"sampled layout mask written: {manifest['mask_path']}")
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
                sampled_layout_mask_path=args.sampled_layout_mask,
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
                    resume_tile_manifest_path=args.resume_tile_manifest,
                    wsi_writer=args.wsi_writer,
                )
            elif args.backend == "torch-diffusion-smoke":
                if args.resume_tile_manifest:
                    raise GenerationExecutionError(
                        "--resume-tile-manifest is only supported for smoke-cascade"
                    )
                if args.wsi_writer != "array":
                    raise GenerationExecutionError(
                        "--wsi-writer tile-streaming is only supported for smoke-cascade"
                    )
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
            summary = collect_output_summary(args.metadata, args.qc, qc_review_path=args.qc_review)
        except (ValidationError, ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "create-qc-review":
        try:
            review = build_qc_review(args.metadata, args.qc, output_path=args.output)
        except (QCReviewError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"qc review written: {args.output} ({len(review['review_items'])} review items)")
        return 0

    if args.command == "apply-qc-review-decision":
        try:
            review = apply_qc_review_decision(
                args.review,
                decision=args.decision,
                reviewer=args.reviewer,
                note=args.note,
            )
        except (QCReviewError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"qc review decision applied: {args.review} ({review['decision']})")
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

    print(f"unknown command {args.command!r}", file=sys.stderr)
    return 2
