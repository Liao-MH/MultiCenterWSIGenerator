import unittest

from he_wsi_generator.schemas import (
    ValidationError,
    validate_generation_config,
    validate_input_manifest,
    validate_label_mapping,
    validate_metadata,
    validate_qc_report,
)


class SchemaValidationTests(unittest.TestCase):
    def test_manifest_accepts_required_record_fields(self):
        manifest = {
            "schema_version": "v0.64.0",
            "dataset_id": "demo-dataset",
            "created_at": "2026-05-23T08:00:00",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "wsi_path": "data/slide-001.svs",
                    "center_id": None,
                    "cancer_type": "lung",
                    "tissue_type": "lung",
                    "mpp_x": 0.25,
                    "mpp_y": 0.25,
                    "max_magnification": "40x",
                    "split": "train",
                    "annotations": [],
                }
            ],
        }

        validated = validate_input_manifest(manifest)

        self.assertEqual(validated["schema_version"], "v0.64.0")
        self.assertEqual(validated["records"][0]["wsi_id"], "slide-001")

    def test_manifest_rejects_missing_wsi_path(self):
        manifest = {
            "schema_version": "v0.64.0",
            "dataset_id": "demo-dataset",
            "created_at": "2026-05-23T08:00:00",
            "records": [
                {
                    "wsi_id": "slide-001",
                    "cancer_type": "lung",
                    "split": "train",
                    "annotations": [],
                }
            ],
        }

        with self.assertRaisesRegex(ValidationError, r"records\[0\]\.wsi_path is required"):
            validate_input_manifest(manifest)

    def test_label_mapping_accepts_six_class_mapping(self):
        mapping = {
            "schema_version": "v0.64.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-001",
            "classes": {
                "0": "background",
                "1": "tissue",
                "2": "target_pathology",
                "3": "supporting_tissue",
                "4": "necrosis_debris",
                "5": "artifact",
            },
            "mapping_source": "manual",
            "confidence": {
                "0": "high",
                "1": "high",
                "2": "high",
                "3": "medium",
                "4": "medium",
                "5": "medium",
            },
        }

        validated = validate_label_mapping(mapping)

        self.assertEqual(validated["classes"]["5"], "artifact")

    def test_label_mapping_rejects_non_project_mask_class(self):
        mapping = {
            "schema_version": "v0.64.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-001",
            "classes": {"0": "background", "1": "tumor"},
            "mapping_source": "manual",
            "confidence": {"0": "high", "1": "high"},
        }

        with self.assertRaisesRegex(ValidationError, "classes.1 has invalid mask class"):
            validate_label_mapping(mapping)

    def test_generation_config_accepts_documented_defaults(self):
        config = {
            "schema_version": "v0.64.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.0,
            "anchor_preset": "fully_de_novo",
            "style_seed": "auto",
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        validated = validate_generation_config(config)

        self.assertEqual(validated["tile_size_40x"], [512, 512])
        self.assertFalse(validated["non_copy_patch_nearest_neighbor_search"])

    def test_generation_config_rejects_anchor_outside_unit_interval(self):
        config = {
            "schema_version": "v0.64.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 1.5,
            "anchor_preset": "structure_preserving",
            "style_seed": "auto",
            "source_wsi_id": "slide-001",
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        with self.assertRaisesRegex(ValidationError, "structure_anchor must be between 0 and 1"):
            validate_generation_config(config)

    def test_generation_config_requires_source_for_source_anchored_modes(self):
        config = {
            "schema_version": "v0.64.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.8,
            "anchor_preset": "structure_preserving",
            "style_seed": "auto",
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        with self.assertRaisesRegex(ValidationError, "source_wsi_id is required"):
            validate_generation_config(config)

    def test_generation_config_rejects_invalid_canvas_size(self):
        config = {
            "schema_version": "v0.64.0",
            "random_seed": 0,
            "model_family": "latent_diffusion_unet",
            "max_magnification": "40x",
            "tile_size_40x": [512, 512],
            "canvas_size_40x": [0, 512],
            "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
            "structure_anchor": 0.0,
            "anchor_preset": "fully_de_novo",
            "style_seed": "auto",
            "source_wsi_id": None,
            "sample_steps": 50,
            "overlap_px_40x": 64,
            "non_copy_patch_nearest_neighbor_search": False,
        }

        with self.assertRaisesRegex(ValidationError, "canvas_size_40x values"):
            validate_generation_config(config)

    def test_metadata_requires_source_for_source_anchored_outputs(self):
        metadata = {
            "schema_version": "v0.64.0",
            "generated_id": "gen-001",
            "version": "v0.64.0",
            "created_at": "2026-05-23T08:00:00",
            "output": {
                "wsi_path": "outputs/gen-001/generated.ome.tiff",
                "mask_path": "outputs/gen-001/generated_mask",
                "qc_json_path": "outputs/gen-001/qc.json",
            },
            "source": {
                "source_wsi_id": None,
                "source_wsi_path": None,
                "source_region": None,
                "source_scale": None,
            },
            "generation": {
                "structure_anchor": 0.8,
                "style_seed": 12,
                "random_seed": 0,
                "model_checkpoint": "checkpoints/model.pt",
                "model_version": "v0.64.0",
                "cascade_levels": ["1/32", "1/16", "1/4", "1/1"],
                "max_magnification": "40x",
                "tile_size_40x": [512, 512],
            },
            "mask_schema": {
                "classes": [
                    "background",
                    "tissue",
                    "target_pathology",
                    "supporting_tissue",
                    "necrosis_debris",
                    "artifact",
                ],
                "input_label_mapping": {},
                "mapping_source": "manual",
                "confidence": {},
            },
            "qc": {
                "overall_status": "pass",
                "summary": {},
                "non_copy_report": {},
            },
        }

        with self.assertRaisesRegex(ValidationError, "source.source_wsi_id is required"):
            validate_metadata(metadata)

    def test_qc_report_requires_three_levels_and_non_copy_report(self):
        qc = {
            "schema_version": "v0.64.0",
            "generated_id": "gen-001",
            "overall_status": "warning",
            "levels": {
                "wsi": {"status": "pass", "metrics": []},
                "tile": {"status": "warning", "metrics": []},
                "mask_region": {"status": "pass", "metrics": []},
            },
            "non_copy_report": {
                "enabled": True,
                "patch_nearest_neighbor_search": False,
                "items": [],
            },
        }

        validated = validate_qc_report(qc)

        self.assertEqual(validated["levels"]["tile"]["status"], "warning")


if __name__ == "__main__":
    unittest.main()
