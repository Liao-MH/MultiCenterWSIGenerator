import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.annotations.alignment import validate_mask_alignment
from he_wsi_generator.annotations.pipeline import (
    AnnotationPipelineError,
    cleanup_temporary_six_class_masks,
)
from he_wsi_generator.annotations.masks import (
    build_six_class_mask,
    load_annotation_source,
    MaskMappingError,
    apply_label_mapping,
    read_mask_labels,
)


class AnnotationTests(unittest.TestCase):
    def test_read_mask_labels_from_png(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mask_path = Path(tmpdir) / "mask.png"
            mask = Image.fromarray(
                np.array([[0, 1, 1], [2, 0, 2]], dtype=np.uint8),
                mode="L",
            )
            mask.save(mask_path)

            labels = read_mask_labels(mask_path)

        self.assertEqual(labels, [0, 1, 2])

    def test_apply_label_mapping_outputs_project_class_ids(self):
        mask = np.array([[0, 1, 2], [5, 0, 1]], dtype=np.uint8)
        mapping = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-001",
            "classes": {
                "0": "background",
                "1": "tissue",
                "2": "target_pathology",
                "5": "artifact",
            },
            "mapping_source": "manual",
            "confidence": {
                "0": "high",
                "1": "high",
                "2": "medium",
                "5": "medium",
            },
        }

        mapped = apply_label_mapping(mask, mapping)

        self.assertEqual(mapped.tolist(), [[0, 1, 2], [5, 0, 1]])

    def test_apply_label_mapping_rejects_unmapped_label(self):
        mask = np.array([[0, 1, 3]], dtype=np.uint8)
        mapping = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-001",
            "classes": {
                "0": "background",
                "1": "tissue",
            },
            "mapping_source": "manual",
            "confidence": {"0": "high", "1": "high"},
        }

        with self.assertRaisesRegex(MaskMappingError, "unmapped mask label 3"):
            apply_label_mapping(mask, mapping)

    def test_mask_alignment_accepts_scaled_level0_extent(self):
        report = validate_mask_alignment(
            mask_size=(4, 2),
            wsi_level0_size=(8, 4),
            transform_to_level0={"scale_x": 2.0, "scale_y": 2.0, "offset_x": 0, "offset_y": 0},
        )

        self.assertEqual(report["level0_extent"], [0.0, 0.0, 8.0, 4.0])
        self.assertEqual(report["status"], "aligned")

    def test_mask_alignment_rejects_out_of_bounds_extent(self):
        with self.assertRaisesRegex(ValueError, "exceeds WSI level0 bounds"):
            validate_mask_alignment(
                mask_size=(4, 2),
                wsi_level0_size=(8, 4),
                transform_to_level0={
                    "scale_x": 2.0,
                    "scale_y": 2.0,
                    "offset_x": 2,
                    "offset_y": 0,
                },
            )

    def test_load_annotation_source_reads_roi_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            roi_path = root / "roi.json"
            roi_path.write_text(
                """
                {
                  "rois": [
                    {
                      "label": 2,
                      "bounding_box_xywh": [1, 0, 3, 2]
                    }
                  ]
                }
                """.strip(),
                encoding="utf-8",
            )

            loaded = load_annotation_source(
                {
                    "annotation_id": "roi-001",
                    "annotation_path": str(roi_path),
                    "annotation_type": "roi_json",
                    "coordinate_level": 0,
                    "label_encoding": "integer_index",
                    "transform_to_level0": {
                        "scale_x": 1.0,
                        "scale_y": 1.0,
                        "offset_x": 0,
                        "offset_y": 0,
                    },
                    "status": "validated",
                }
            )

        self.assertEqual(loaded["annotation_type"], "roi_json")
        self.assertEqual(loaded["roi_records"][0]["bounding_box_xywh"], [1, 0, 3, 2])
        self.assertEqual(loaded["roi_records"][0]["label"], 2)

    def test_build_six_class_mask_merges_manual_roi_and_pseudo_sources(self):
        manual_mask = np.zeros((4, 4), dtype=np.uint8)
        manual_mask[0:2, 0:2] = 1
        pseudo_mask = np.zeros((4, 4), dtype=np.uint8)
        pseudo_mask[:, 2:] = 3

        manual_mapping = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-manual",
            "classes": {
                "0": "background",
                "1": "tissue",
            },
            "mapping_source": "manual",
            "confidence": {
                "0": "high",
                "1": "high",
            },
        }
        pseudo_mapping = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-pseudo",
            "classes": {
                "0": "background",
                "3": "supporting_tissue",
            },
            "mapping_source": "cluster",
            "confidence": {
                "0": "medium",
                "3": "low",
            },
        }

        merged = build_six_class_mask(
            wsi_id="slide-001",
            wsi_level0_size=(4, 4),
            annotation_sources=[
                {
                    "annotation_id": "ann-pseudo",
                    "annotation_type": "cluster_pseudo_mask",
                    "annotation_path": "pseudo.npy",
                    "priority": "cluster_pseudo_mask",
                    "data": pseudo_mask,
                    "transform_to_level0": {
                        "scale_x": 1.0,
                        "scale_y": 1.0,
                        "offset_x": 0,
                        "offset_y": 0,
                    },
                    "label_mapping": pseudo_mapping,
                },
                {
                    "annotation_id": "ann-roi",
                    "annotation_type": "roi_json",
                    "annotation_path": "roi.json",
                    "priority": "roi_json",
                    "roi_records": [{"label": 2, "bounding_box_xywh": [2, 1, 2, 2]}],
                    "transform_to_level0": {
                        "scale_x": 1.0,
                        "scale_y": 1.0,
                        "offset_x": 0,
                        "offset_y": 0,
                    },
                    "label_mapping": {
                        "schema_version": "v0.80.0",
                        "wsi_id": "slide-001",
                        "source_annotation_id": "ann-roi",
                        "classes": {
                            "2": "target_pathology",
                        },
                        "mapping_source": "roi",
                        "confidence": {
                            "2": "high",
                        },
                    },
                },
                {
                    "annotation_id": "ann-manual",
                    "annotation_type": "numpy_mask",
                    "annotation_path": "manual.npy",
                    "priority": "manual_mask",
                    "data": manual_mask,
                    "transform_to_level0": {
                        "scale_x": 1.0,
                        "scale_y": 1.0,
                        "offset_x": 0,
                        "offset_y": 0,
                    },
                    "label_mapping": manual_mapping,
                },
            ],
            block_size=2,
        )

        self.assertEqual(merged["mask"].shape, (4, 4))
        self.assertEqual(merged["mask"][0, 0], 1)
        self.assertEqual(merged["mask"][1, 2], 2)
        self.assertEqual(merged["mask"][3, 3], 3)
        self.assertEqual(merged["source_priority_order"], ["manual_mask", "roi_json", "cluster_pseudo_mask"])
        self.assertNotIn("source_trace", merged)
        provenance = merged["compact_provenance_summary"]
        self.assertEqual(provenance["class_pixel_counts_by_id"], {"0": 4, "1": 4, "2": 4, "3": 4})
        self.assertEqual(provenance["annotation_pixel_counts_by_id"]["ann-manual"], {"1": 4})
        self.assertEqual(provenance["annotation_pixel_counts_by_id"]["ann-roi"], {"2": 4})
        self.assertEqual(provenance["annotation_pixel_counts_by_id"]["ann-pseudo"], {"3": 4})
        self.assertEqual(provenance["same_priority_conflict_count"], 0)
        self.assertEqual(provenance["same_priority_conflict_examples"], [])
        self.assertEqual(len(provenance["block_summaries"]), 4)
        self.assertEqual(
            provenance["block_summaries"][1]["class_pixel_counts_by_id"],
            {"2": 2, "3": 2},
        )

    def test_build_six_class_mask_rejects_same_priority_conflict(self):
        mask_left = np.zeros((2, 2), dtype=np.uint8)
        mask_left[:, :] = 1
        mask_right = np.zeros((2, 2), dtype=np.uint8)
        mask_right[:, :] = 2

        mapping_left = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-left",
            "classes": {"1": "tissue"},
            "mapping_source": "manual",
            "confidence": {"1": "high"},
        }
        mapping_right = {
            "schema_version": "v0.80.0",
            "wsi_id": "slide-001",
            "source_annotation_id": "ann-right",
            "classes": {"2": "target_pathology"},
            "mapping_source": "manual",
            "confidence": {"2": "high"},
        }

        with self.assertRaisesRegex(MaskMappingError, "same-priority conflict"):
            build_six_class_mask(
                wsi_id="slide-001",
                wsi_level0_size=(2, 2),
                annotation_sources=[
                    {
                        "annotation_id": "ann-left",
                        "annotation_type": "numpy_mask",
                        "annotation_path": "left.npy",
                        "priority": "manual_mask",
                        "data": mask_left,
                        "transform_to_level0": {
                            "scale_x": 1.0,
                            "scale_y": 1.0,
                            "offset_x": 0,
                            "offset_y": 0,
                        },
                        "label_mapping": mapping_left,
                    },
                    {
                        "annotation_id": "ann-right",
                        "annotation_type": "numpy_mask",
                        "annotation_path": "right.npy",
                        "priority": "manual_mask",
                        "data": mask_right,
                        "transform_to_level0": {
                            "scale_x": 1.0,
                            "scale_y": 1.0,
                            "offset_x": 0,
                            "offset_y": 0,
                        },
                        "label_mapping": mapping_right,
                    },
                ],
            )

    def test_cleanup_temporary_six_class_masks_requires_target_outputs_before_deleting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            temporary_mask = root / "mask-artifacts" / "slide-001" / "mask.npy"
            temporary_mask.parent.mkdir(parents=True)
            np.save(temporary_mask, np.zeros((2, 2), dtype=np.uint8))
            final_mask = root / "generated" / "generated_mask" / "mask.npy"
            summary = {
                "records": [
                    {
                        "wsi_id": "slide-001",
                        "mask_path": str(temporary_mask),
                        "temporary_intermediate": True,
                    }
                ]
            }

            with self.assertRaisesRegex(AnnotationPipelineError, "required output does not exist"):
                cleanup_temporary_six_class_masks(summary, required_output_paths=[final_mask])

            self.assertTrue(temporary_mask.exists())

            final_mask.parent.mkdir(parents=True)
            np.save(final_mask, np.ones((2, 2), dtype=np.uint8))
            report = cleanup_temporary_six_class_masks(summary, required_output_paths=[final_mask])

            self.assertEqual(report["deleted_count"], 1)
            self.assertFalse(temporary_mask.exists())
            self.assertTrue(final_mask.exists())


if __name__ == "__main__":
    unittest.main()
