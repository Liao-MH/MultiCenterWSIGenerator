import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = str(REPO_ROOT / "src")
if SRC_ROOT not in sys.path:
    # Worker worktrees may not be the active editable install in the shared env.
    sys.path.insert(0, SRC_ROOT)

import numpy as np
import tifffile

from he_wsi_generator.metadata.archive import (
    append_batch_index,
    archive_sample,
    write_metadata,
)
from he_wsi_generator.outputs.masks import write_mask_array
from he_wsi_generator.outputs.ome_tiff import OutputWriteError, write_pyramid_ome_tiff
from he_wsi_generator.qc.engine import QCReferenceError, build_qc_report
from he_wsi_generator.schemas import validate_metadata, validate_qc_report


class OutputQCArchiveTests(unittest.TestCase):
    def metadata_payload(self, root: Path, qc_path: Path) -> dict:
        return {
            "schema_version": "v0.65.1",
            "generated_id": "gen-001",
            "version": "v0.65.1",
            "created_at": "2026-05-23T12:00:00",
            "output": {
                "wsi_path": str(root / "generated.ome.tiff"),
                "mask_path": str(root / "generated_mask" / "mask.npy"),
                "qc_json_path": str(qc_path),
            },
            "source": {
                "source_wsi_id": None,
                "source_wsi_path": None,
                "source_region": None,
                "source_scale": None,
            },
            "generation": {
                "structure_anchor": 0.0,
                "style_seed": 12,
                "random_seed": 0,
                "model_checkpoint": "checkpoints/model.pt",
                "model_version": "unit-test",
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

    def write_tile_record(
        self,
        root: Path,
        name: str,
        array: np.ndarray,
        *,
        level_index: int,
        tile_index: int,
        status: str = "completed",
    ) -> dict:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, array)
        return {
            "level_index": level_index,
            "tile_index": tile_index,
            "path": str(path),
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "status": status,
        }

    def test_write_pyramid_ome_tiff_smoke(self):
        levels = [
            np.zeros((8, 8, 3), dtype=np.uint8),
            np.ones((4, 4, 3), dtype=np.uint8) * 50,
            np.ones((2, 2, 3), dtype=np.uint8) * 100,
            np.ones((1, 1, 3), dtype=np.uint8) * 150,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "generated.ome.tiff"

            report = write_pyramid_ome_tiff(levels, output_path)

            with tifffile.TiffFile(output_path) as tiff:
                shapes = [page.shape for page in tiff.series[0].levels]

        self.assertEqual(report["status"], "written")
        self.assertEqual(report["level_count"], 4)
        self.assertTrue(report["is_ome"])
        self.assertEqual(shapes, [(8, 8, 3), (4, 4, 3), (2, 2, 3), (1, 1, 3)])

    def test_write_pyramid_ome_tiff_records_chunked_write_audit(self):
        levels = [
            np.zeros((8, 10, 3), dtype=np.uint8),
            np.ones((4, 5, 3), dtype=np.uint8) * 50,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "generated.ome.tiff"

            report = write_pyramid_ome_tiff(
                levels,
                output_path,
                chunk_shape=(4, 4),
                bigtiff_threshold_bytes=128,
            )

        audit = report["chunked_write_audit"]
        self.assertEqual(report["write_mode"], "chunked_pyramid_write")
        self.assertEqual(audit["writer_backend"], "tifffile")
        self.assertFalse(audit["production_streaming"])
        self.assertTrue(audit["bigtiff"])
        self.assertGreater(audit["estimated_total_bytes"], 128)
        self.assertEqual(audit["chunk_shape"], [4, 4])
        self.assertEqual(len(audit["levels"]), 2)
        self.assertEqual(audit["levels"][0]["shape"], [8, 10, 3])
        self.assertEqual(audit["levels"][0]["chunk_grid"], [2, 3])
        self.assertEqual(audit["levels"][0]["chunk_count"], 6)
        self.assertEqual(audit["levels"][0]["edge_chunk_shape"], [4, 2])
        self.assertIn("in_memory_array_writer", audit["streaming_limitations"])

    def test_write_pyramid_ome_tiff_records_disk_tile_source_contract(self):
        levels = [
            np.zeros((8, 8, 3), dtype=np.uint8),
            np.ones((4, 4, 3), dtype=np.uint8) * 50,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tile_root = root / "tiles"
            records = [
                self.write_tile_record(
                    tile_root,
                    "level0_tile0.npy",
                    np.zeros((4, 4, 3), dtype=np.uint8),
                    level_index=0,
                    tile_index=0,
                ),
                self.write_tile_record(
                    tile_root,
                    "level0_tile1.npy",
                    np.ones((4, 4, 3), dtype=np.uint8),
                    level_index=0,
                    tile_index=1,
                ),
                self.write_tile_record(
                    tile_root,
                    "level1_tile0.npy",
                    np.ones((4, 4, 3), dtype=np.uint8) * 2,
                    level_index=1,
                    tile_index=0,
                ),
            ]
            manifest = {
                "expected_tile_count": 3,
                "levels": [
                    {"level_index": 0, "expected_tile_count": 2},
                    {"level_index": 1, "expected_tile_count": 1},
                ],
                "tiles": records,
            }
            manifest_path = root / "tile_source_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            report = write_pyramid_ome_tiff(
                levels,
                root / "generated.ome.tiff",
                tile_source_manifest=manifest_path,
            )

        contract = report["streaming_contract"]
        coverage_by_level = {
            level["level_index"]: level for level in contract["coverage"]["levels"]
        }
        self.assertEqual(contract["contract_status"], "partial_contract_only")
        self.assertFalse(contract["production_streaming"])
        self.assertTrue(contract["partial_contract_only"])
        self.assertEqual(contract["tile_source"]["manifest_path"], str(manifest_path))
        self.assertEqual(contract["coverage"]["expected_tile_count"], 3)
        self.assertEqual(contract["coverage"]["completed_tile_count"], 3)
        self.assertEqual(contract["coverage"]["missing_tile_count"], 0)
        self.assertEqual(contract["coverage"]["pending_tile_count"], 0)
        self.assertEqual(contract["coverage"]["failed_tile_count"], 0)
        self.assertEqual(coverage_by_level[0]["completed_tile_count"], 2)
        self.assertEqual(coverage_by_level[1]["expected_tile_count"], 1)
        self.assertIn(
            "tile_source_validated_but_writer_still_in_memory",
            contract["streaming_limitations"],
        )

    def test_write_pyramid_ome_tiff_rejects_invalid_chunk_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "generated.ome.tiff"

            with self.assertRaisesRegex(OutputWriteError, "chunk_shape"):
                write_pyramid_ome_tiff(
                    [np.zeros((8, 8, 3), dtype=np.uint8)],
                    output_path,
                    chunk_shape=(0, 4),
                )

    def test_write_pyramid_ome_tiff_rejects_incomplete_tile_source_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tile_root = root / "tiles"
            completed = self.write_tile_record(
                tile_root,
                "completed.npy",
                np.zeros((4, 4, 3), dtype=np.uint8),
                level_index=0,
                tile_index=0,
            )
            duplicate = self.write_tile_record(
                tile_root,
                "duplicate.npy",
                np.zeros((4, 4, 3), dtype=np.uint8),
                level_index=0,
                tile_index=0,
            )
            pending = dict(completed)
            pending["status"] = "pending"
            failed = dict(completed)
            failed["status"] = "failed"
            cases = [
                ("pending", [pending], 1, "pending"),
                ("failed", [failed], 1, "failed"),
                ("missing", [completed], 2, "missing"),
                ("duplicate", [completed, duplicate], 2, "duplicate"),
            ]

            for name, records, expected_tile_count, pattern in cases:
                with self.subTest(name=name):
                    with self.assertRaisesRegex(OutputWriteError, pattern):
                        write_pyramid_ome_tiff(
                            [np.zeros((4, 4, 3), dtype=np.uint8)],
                            root / f"{name}.ome.tiff",
                            tile_source_manifest={
                                "expected_tile_count": expected_tile_count,
                                "tiles": records,
                            },
                        )

    def test_write_pyramid_ome_tiff_rejects_invalid_tile_source_file_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tile_root = root / "tiles"
            completed = self.write_tile_record(
                tile_root,
                "completed.npy",
                np.zeros((4, 4, 3), dtype=np.uint8),
                level_index=0,
                tile_index=0,
            )
            cases = [
                ("missing_path", {**completed, "path": str(tile_root / "missing.npy")}, "exist"),
                ("shape_mismatch", {**completed, "shape": [2, 2, 3]}, "shape"),
                ("dtype_mismatch", {**completed, "dtype": "float32"}, "dtype"),
            ]

            for name, record, pattern in cases:
                with self.subTest(name=name):
                    with self.assertRaisesRegex(OutputWriteError, pattern):
                        write_pyramid_ome_tiff(
                            [np.zeros((4, 4, 3), dtype=np.uint8)],
                            root / f"{name}.ome.tiff",
                            tile_source_manifest={
                                "expected_tile_count": 1,
                                "tiles": [record],
                            },
                        )

    def test_write_mask_array_saves_npy_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "generated_mask"
            mask = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.uint8)

            report = write_mask_array(mask, output_dir, "mask")
            loaded = np.load(report["path"])

        self.assertEqual(report["status"], "written")
        self.assertEqual(report["classes"], 6)
        np.testing.assert_array_equal(loaded, mask)

    def test_build_qc_report_validates_three_levels_and_non_copy_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [
                    np.array(
                        [
                            [[90, 100, 110], [120, 130, 140]],
                            [[150, 160, 170], [180, 190, 200]],
                        ],
                        dtype=np.uint8,
                    ),
                    np.ones((1, 1, 3), dtype=np.uint8) * 100,
                ],
                wsi_path,
            )
            np.save(mask_path, np.array([[0, 1], [1, 2]], dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
            )
            validated = validate_qc_report(qc)

        self.assertEqual(validated["overall_status"], "pass")
        self.assertIn("wsi", validated["levels"])
        self.assertFalse(validated["non_copy_report"]["patch_nearest_neighbor_search"])

    def test_build_qc_report_records_non_copy_similarity_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [
                    np.array(
                        [
                            [[90, 100, 110], [120, 130, 140]],
                            [[150, 160, 170], [180, 190, 200]],
                        ],
                        dtype=np.uint8,
                    ),
                    np.ones((1, 1, 3), dtype=np.uint8) * 100,
                ],
                wsi_path,
            )
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.array([[0, 1], [1, 2]], dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
            )

        metrics = {metric["name"]: metric for metric in qc["non_copy_report"].get("metrics", [])}
        self.assertIn("thumbnail_similarity_proxy", metrics)
        self.assertIn("tissue_contour_similarity_proxy", metrics)
        self.assertIn("mask_layout_similarity_proxy", metrics)
        self.assertIn("global_embedding_similarity_proxy", metrics)

    def test_build_qc_report_records_wsi_tissue_fraction_reference_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [
                    np.ones((4, 4, 3), dtype=np.uint8) * 100,
                    np.ones((2, 2, 3), dtype=np.uint8) * 100,
                ],
                wsi_path,
            )
            mask_path.parent.mkdir(parents=True)
            mask = np.zeros((1000, 1000), dtype=np.uint8)
            mask.ravel()[:156500] = 1
            np.save(mask_path, mask)

            reference_fraction = 0.156499895
            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
                wsi_tissue_overview_summary={
                    "record_count": 1,
                    "records": [
                        {
                            "wsi_id": "slide-001",
                            "tissue_fraction": reference_fraction,
                            "bounding_box_xywh": [0, 0, 4, 2],
                            "connected_component_count": 1,
                        }
                    ],
                },
            )

        metrics = {metric["name"]: metric for metric in qc["non_copy_report"].get("metrics", [])}
        self.assertEqual(metrics["wsi_tissue_fraction_reference_proxy"]["status"], "pass")
        self.assertEqual(metrics["wsi_tissue_fraction_reference_proxy"]["value"], 1.0)
        self.assertEqual(
            metrics["wsi_tissue_fraction_reference_proxy"]["reference"]["tissue_fraction"],
            reference_fraction,
        )
        self.assertEqual(metrics["wsi_tissue_fraction_reference_proxy"]["generated_mask_fraction"], 0.1565)

    def test_build_qc_report_records_sampled_layout_mask_match_proxy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            sampled_mask_path = root / "sampled_layout_mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [
                    np.ones((4, 4, 3), dtype=np.uint8) * 100,
                    np.ones((2, 2, 3), dtype=np.uint8) * 100,
                ],
                wsi_path,
            )
            mask_path.parent.mkdir(parents=True)
            generated_mask = np.array(
                [
                    [0, 1, 2, 3],
                    [0, 1, 2, 3],
                    [4, 4, 5, 5],
                    [4, 4, 5, 5],
                ],
                dtype=np.uint8,
            )
            np.save(mask_path, generated_mask)
            np.save(sampled_mask_path, generated_mask.copy())

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
                sampled_layout_mask_summary={
                    "source": "sampled_layout_mask",
                    "artifact_path": str(root / "sampled_layout_mask.json"),
                    "mask_path": str(sampled_mask_path),
                    "sample_id": "layout-001",
                    "mask_shape": [4, 4],
                    "class_pixel_counts_by_id": [2, 2, 4, 4, 4, 4],
                    "class_fractions_by_id": [0.125, 0.125, 0.25, 0.25, 0.25, 0.25],
                },
            )

        metrics = {metric["name"]: metric for metric in qc["non_copy_report"].get("metrics", [])}
        metric = metrics["sampled_layout_mask_match_proxy"]
        self.assertEqual(metric["status"], "pass")
        self.assertEqual(metric["value"], 1.0)
        self.assertEqual(metric["matched_pixel_fraction"], 1.0)
        self.assertEqual(metric["reference"]["sample_id"], "layout-001")
        self.assertEqual(metric["reference"]["mask_shape"], [4, 4])

    def test_build_qc_report_rejects_missing_sampled_layout_mask_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [np.ones((2, 2, 3), dtype=np.uint8) * 100],
                wsi_path,
            )
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.ones((2, 2), dtype=np.uint8))

            with self.assertRaisesRegex(QCReferenceError, "sampled layout mask file does not exist"):
                build_qc_report(
                    generated_id="gen-001",
                    wsi_path=wsi_path,
                    mask_path=mask_path,
                    pyramid_report=pyramid_report,
                    non_copy_items=[],
                    sampled_layout_mask_summary={
                        "source": "sampled_layout_mask",
                        "artifact_path": str(root / "sampled_layout_mask.json"),
                        "mask_path": str(root / "missing.npy"),
                        "sample_id": "layout-001",
                        "mask_shape": [2, 2],
                        "class_pixel_counts_by_id": [0, 4, 0, 0, 0, 0],
                        "class_fractions_by_id": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                    },
                )

    def test_build_qc_report_rejects_invalid_wsi_tissue_overview_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(
                [np.ones((2, 2, 3), dtype=np.uint8) * 100],
                wsi_path,
            )
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.ones((2, 2), dtype=np.uint8))

            with self.assertRaisesRegex(QCReferenceError, "tissue_fraction"):
                build_qc_report(
                    generated_id="gen-001",
                    wsi_path=wsi_path,
                    mask_path=mask_path,
                    pyramid_report=pyramid_report,
                    non_copy_items=[],
                    wsi_tissue_overview_summary={
                        "record_count": 1,
                        "records": [{"wsi_id": "slide-001"}],
                    },
                )

    def test_build_qc_report_reads_outputs_and_records_quality_metrics(self):
        levels = [
            np.stack(
                [
                    np.tile(np.arange(8, dtype=np.uint8), (8, 1)) + 90,
                    np.tile(np.arange(8, dtype=np.uint8).reshape(8, 1), (1, 8)) + 80,
                    np.ones((8, 8), dtype=np.uint8) * 120,
                ],
                axis=2,
            ),
            np.ones((4, 4, 3), dtype=np.uint8) * 100,
            np.ones((2, 2, 3), dtype=np.uint8) * 110,
            np.ones((1, 1, 3), dtype=np.uint8) * 120,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            mask_path.parent.mkdir(parents=True)
            np.save(
                mask_path,
                np.array(
                    [
                        [0, 1, 2, 3, 4, 5, 1, 2],
                        [1, 2, 3, 4, 5, 1, 2, 3],
                        [2, 3, 4, 5, 1, 2, 3, 4],
                        [3, 4, 5, 1, 2, 3, 4, 5],
                        [4, 5, 1, 2, 3, 4, 5, 1],
                        [5, 1, 2, 3, 4, 5, 1, 2],
                        [1, 2, 3, 4, 5, 1, 2, 3],
                        [2, 3, 4, 5, 1, 2, 3, 4],
                    ],
                    dtype=np.uint8,
                ),
            )

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
            )

        wsi_metrics = {metric["name"]: metric for metric in qc["levels"]["wsi"]["metrics"]}
        tile_metrics = {metric["name"]: metric for metric in qc["levels"]["tile"]["metrics"]}
        mask_metrics = {metric["name"]: metric for metric in qc["levels"]["mask_region"]["metrics"]}
        self.assertEqual(qc["overall_status"], "pass")
        self.assertEqual(wsi_metrics["pyramid_level_count"]["value"], 4)
        self.assertIn("mean_red", wsi_metrics)
        self.assertIn("style_consistency_proxy", wsi_metrics)
        self.assertIn("sharpness_laplacian_proxy", tile_metrics)
        self.assertIn("seam_score_proxy", tile_metrics)
        self.assertEqual(mask_metrics["mask_classes_present"]["value"], 6)
        self.assertEqual(mask_metrics["mask_shape_matches_wsi"]["status"], "pass")

    def test_build_qc_report_fails_when_mask_shape_does_not_align_to_wsi(self):
        levels = [
            np.ones((8, 8, 3), dtype=np.uint8) * 100,
            np.ones((4, 4, 3), dtype=np.uint8) * 100,
            np.ones((2, 2, 3), dtype=np.uint8) * 100,
            np.ones((1, 1, 3), dtype=np.uint8) * 100,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.zeros((3, 3), dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
            )

        mask_metrics = {metric["name"]: metric for metric in qc["levels"]["mask_region"]["metrics"]}
        self.assertEqual(qc["overall_status"], "fail")
        self.assertEqual(mask_metrics["mask_shape_matches_wsi"]["status"], "fail")

    def test_build_qc_report_applies_reference_distribution_thresholds(self):
        levels = [
            np.ones((8, 8, 3), dtype=np.uint8) * 100,
            np.ones((4, 4, 3), dtype=np.uint8) * 100,
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.ones((8, 8), dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
                qc_reference_distribution={
                    "metrics": {
                        "mean_red": {
                            "warning_min": 120,
                            "warning_max": 180,
                            "fail_min": 80,
                            "fail_max": 220,
                        },
                        "mask_tissue_fraction": {
                            "warning_min": 0.2,
                            "warning_max": 0.8,
                            "fail_min": 0.05,
                            "fail_max": 0.95,
                        },
                    }
                },
            )

        wsi_metrics = {metric["name"]: metric for metric in qc["levels"]["wsi"]["metrics"]}
        mask_metrics = {metric["name"]: metric for metric in qc["levels"]["mask_region"]["metrics"]}
        self.assertEqual(qc["overall_status"], "fail")
        self.assertEqual(wsi_metrics["mean_red"]["status"], "warning")
        self.assertEqual(mask_metrics["mask_tissue_fraction"]["status"], "fail")
        self.assertEqual(wsi_metrics["mean_red"]["reference"]["warning_min"], 120)

    def test_build_qc_report_uses_matching_stratified_reference_distribution(self):
        levels = [np.ones((8, 8, 3), dtype=np.uint8) * 100]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.ones((8, 8), dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
                qc_reference_context={"metadata.cancer_type": "breast_cancer"},
                qc_reference_distribution={
                    "stratification": {
                        "enabled": True,
                        "fields": ["metadata.cancer_type"],
                        "stratum_count": 2,
                    },
                    "strata": {
                        "metadata.cancer_type=breast_cancer": {
                            "group_values": {"metadata.cancer_type": "breast_cancer"},
                            "metrics": {
                                "mean_red": {
                                    "warning_min": 90,
                                    "warning_max": 110,
                                    "fail_min": 80,
                                    "fail_max": 120,
                                }
                            },
                        },
                        "metadata.cancer_type=lung_cancer": {
                            "group_values": {"metadata.cancer_type": "lung_cancer"},
                            "metrics": {
                                "mean_red": {
                                    "warning_min": 150,
                                    "warning_max": 180,
                                    "fail_min": 140,
                                    "fail_max": 190,
                                }
                            },
                        },
                    },
                    "metrics": {
                        "mean_red": {
                            "warning_min": 150,
                            "warning_max": 180,
                            "fail_min": 140,
                            "fail_max": 190,
                        }
                    },
                },
            )

        wsi_metrics = {metric["name"]: metric for metric in qc["levels"]["wsi"]["metrics"]}
        reference = wsi_metrics["mean_red"]["reference"]
        self.assertEqual(wsi_metrics["mean_red"]["status"], "pass")
        self.assertEqual(reference["selection"], "stratified")
        self.assertEqual(reference["stratum_key"], "metadata.cancer_type=breast_cancer")
        self.assertEqual(reference["group_values"], {"metadata.cancer_type": "breast_cancer"})
        self.assertEqual(reference["warning_min"], 90)

    def test_build_qc_report_records_global_fallback_when_stratified_context_missing(self):
        levels = [np.ones((8, 8, 3), dtype=np.uint8) * 100]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.ones((8, 8), dtype=np.uint8))

            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report=pyramid_report,
                non_copy_items=[],
                qc_reference_distribution={
                    "stratification": {
                        "enabled": True,
                        "fields": ["metadata.cancer_type"],
                        "stratum_count": 1,
                    },
                    "strata": {
                        "metadata.cancer_type=breast_cancer": {
                            "group_values": {"metadata.cancer_type": "breast_cancer"},
                            "metrics": {
                                "mean_red": {
                                    "warning_min": 90,
                                    "warning_max": 110,
                                    "fail_min": 80,
                                    "fail_max": 120,
                                }
                            },
                        }
                    },
                    "metrics": {
                        "mean_red": {
                            "warning_min": 120,
                            "warning_max": 180,
                            "fail_min": 80,
                            "fail_max": 220,
                        }
                    },
                },
            )

        wsi_metrics = {metric["name"]: metric for metric in qc["levels"]["wsi"]["metrics"]}
        reference = wsi_metrics["mean_red"]["reference"]
        self.assertEqual(wsi_metrics["mean_red"]["status"], "warning")
        self.assertEqual(reference["selection"], "global_fallback")
        self.assertEqual(reference["fallback_reason"], "missing_context_field:metadata.cancer_type")
        self.assertEqual(reference["stratification_fields"], ["metadata.cancer_type"])

    def test_build_qc_report_rejects_invalid_reference_distribution(self):
        levels = [np.ones((2, 2, 3), dtype=np.uint8) * 100]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            np.save(mask_path, np.ones((2, 2), dtype=np.uint8))

            with self.assertRaisesRegex(QCReferenceError, "warning_min"):
                build_qc_report(
                    generated_id="gen-001",
                    wsi_path=wsi_path,
                    mask_path=mask_path,
                    pyramid_report=pyramid_report,
                    non_copy_items=[],
                    qc_reference_distribution={
                        "metrics": {
                            "mean_red": {
                                "warning_min": 200,
                                "warning_max": 100,
                                "fail_min": 80,
                                "fail_max": 220,
                            }
                        }
                    },
                )

    def test_build_qc_report_rejects_invalid_stratified_reference_metrics_path(self):
        levels = [np.ones((2, 2, 3), dtype=np.uint8) * 100]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "mask.npy"
            pyramid_report = write_pyramid_ome_tiff(levels, wsi_path)
            np.save(mask_path, np.ones((2, 2), dtype=np.uint8))

            with self.assertRaisesRegex(
                QCReferenceError,
                r"qc_reference_distribution\.strata\.metadata\.cancer_type=breast_cancer\.metrics",
            ):
                build_qc_report(
                    generated_id="gen-001",
                    wsi_path=wsi_path,
                    mask_path=mask_path,
                    pyramid_report=pyramid_report,
                    non_copy_items=[],
                    qc_reference_context={"metadata.cancer_type": "breast_cancer"},
                    qc_reference_distribution={
                        "stratification": {
                            "enabled": True,
                            "fields": ["metadata.cancer_type"],
                            "stratum_count": 1,
                        },
                        "strata": {
                            "metadata.cancer_type=breast_cancer": {
                                "group_values": {"metadata.cancer_type": "breast_cancer"},
                                "metrics": [],
                            }
                        },
                        "metrics": {
                            "mean_red": {
                                "warning_min": 90,
                                "warning_max": 110,
                                "fail_min": 80,
                                "fail_max": 120,
                            }
                        },
                    },
                )

    def test_metadata_and_batch_index_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            qc_path = root / "qc.json"
            qc_path.write_text(
                json.dumps(
                    build_qc_report(
                        generated_id="gen-001",
                        wsi_path=root / "generated.ome.tiff",
                        mask_path=root / "generated_mask" / "mask.npy",
                        pyramid_report={"status": "written", "level_count": 4},
                        non_copy_items=[],
                    )
                ),
                encoding="utf-8",
            )
            metadata = self.metadata_payload(root, qc_path)
            metadata_path = write_metadata(metadata, root / "metadata.json")
            batch_path = root / "batch.jsonl"

            append_batch_index(
                batch_path,
                {
                    "generated_id": "gen-001",
                    "metadata_path": str(metadata_path),
                    "qc_json_path": str(qc_path),
                    "wsi_path": metadata["output"]["wsi_path"],
                    "mask_path": metadata["output"]["mask_path"],
                    "status": "pass",
                },
            )
            line = batch_path.read_text(encoding="utf-8").strip()

            self.assertEqual(
                validate_metadata(json.loads(metadata_path.read_text(encoding="utf-8")))[
                    "generated_id"
                ],
                "gen-001",
            )
            self.assertEqual(json.loads(line)["generated_id"], "gen-001")

    def test_archive_sample_writes_metadata_qc_and_batch_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            wsi_path.write_bytes(b"placeholder")
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.zeros((2, 2), dtype=np.uint8))
            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report={"status": "written", "level_count": 4},
                non_copy_items=[],
            )
            metadata = self.metadata_payload(root, root / "qc.json")

            archive = archive_sample(root, metadata, qc)

            self.assertTrue(Path(archive["metadata_path"]).exists())
            self.assertTrue(Path(archive["qc_json_path"]).exists())
            self.assertTrue(Path(archive["batch_index_path"]).exists())

    def test_cli_archives_sample(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            wsi_path = root / "generated.ome.tiff"
            mask_path = root / "generated_mask" / "mask.npy"
            qc_path = root / "qc-input.json"
            metadata_path = root / "metadata-input.json"
            wsi_path.write_bytes(b"placeholder")
            mask_path.parent.mkdir(parents=True)
            np.save(mask_path, np.zeros((2, 2), dtype=np.uint8))
            qc = build_qc_report(
                generated_id="gen-001",
                wsi_path=wsi_path,
                mask_path=mask_path,
                pyramid_report={"status": "written", "level_count": 4},
                non_copy_items=[],
            )
            qc_path.write_text(json.dumps(qc), encoding="utf-8")
            metadata_path.write_text(
                json.dumps(self.metadata_payload(root, root / "qc.json")),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "he_wsi_generator.cli",
                    "archive-sample",
                    str(root),
                    "--metadata",
                    str(metadata_path),
                    "--qc",
                    str(qc_path),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sample archived", result.stdout)


if __name__ == "__main__":
    unittest.main()
