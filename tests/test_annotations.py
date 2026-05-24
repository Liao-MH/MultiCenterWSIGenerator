import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from he_wsi_generator.annotations.alignment import validate_mask_alignment
from he_wsi_generator.annotations.masks import (
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
            "schema_version": "v0.70.0",
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
            "schema_version": "v0.70.0",
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


if __name__ == "__main__":
    unittest.main()
