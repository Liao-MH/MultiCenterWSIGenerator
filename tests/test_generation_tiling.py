import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = str(REPO_ROOT / "src")
if SRC_ROOT not in sys.path:
    # Worker worktrees may not be the active editable install in the shared env.
    sys.path.insert(0, SRC_ROOT)

import numpy as np

from he_wsi_generator.generation.tiling import (
    GenerationTilingError,
    blend_rgb_tiles,
    build_resumable_tile_manifest,
    complete_tile_traversal_plan,
    create_tile_traversal_plan,
    require_complete_tile_manifest,
    update_resumable_tile_manifest,
    validate_resumable_tile_manifest,
)


class GenerationTilingTests(unittest.TestCase):
    def test_tile_traversal_records_row_major_resume_and_edge_crop(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=1,
            cascade_level="1/1",
        )

        self.assertEqual(plan["tile_traversal"], "row_major_with_resume_index")
        self.assertEqual(plan["tile_count"], 2)
        self.assertEqual(plan["completed_tile_count"], 1)
        self.assertEqual(plan["pending_tile_count"], 1)
        self.assertEqual(plan["next_tile_index"], 1)
        self.assertEqual(
            [tile["tile_origin_40x"] for tile in plan["tiles"]],
            [[0, 0], [448, 0]],
        )
        self.assertEqual(plan["tiles"][0]["status"], "completed")
        self.assertEqual(plan["tiles"][1]["status"], "pending")
        self.assertEqual(plan["tiles"][1]["write_region_40x"], [448, 0, 320, 512])
        self.assertEqual(plan["edge_policy"], "crop_tile_to_canvas")

    def test_tile_traversal_rejects_invalid_resume_index(self):
        with self.assertRaisesRegex(GenerationTilingError, "resume_index"):
            create_tile_traversal_plan(
                canvas_size_40x=[512, 512],
                tile_size_40x=[512, 512],
                overlap_px_40x=64,
                resume_index=2,
            )

    def test_tile_traversal_rejects_overlap_that_eliminates_stride(self):
        with self.assertRaisesRegex(GenerationTilingError, "overlap_px_40x"):
            create_tile_traversal_plan(
                canvas_size_40x=[512, 512],
                tile_size_40x=[512, 512],
                overlap_px_40x=512,
            )

    def test_blend_rgb_tiles_uses_weighted_overlap(self):
        left = np.zeros((2, 3, 3), dtype=np.uint8)
        right = np.full((2, 3, 3), 100, dtype=np.uint8)

        canvas = blend_rgb_tiles(
            [
                {"tile_origin_40x": [0, 0], "image": left},
                {"tile_origin_40x": [2, 0], "image": right},
            ],
            canvas_size_40x=[4, 2],
            overlap_px_40x=1,
        )

        self.assertEqual(canvas.shape, (2, 4, 3))
        self.assertEqual(canvas[0, :, 0].tolist(), [0, 0, 50, 100])

    def test_blend_rgb_tiles_avoids_whole_rgb_float64_tile_cast(self):
        cast_events: list[tuple[tuple[int, ...], np.dtype]] = []

        class TrackingTile(np.ndarray):
            def __new__(cls, values, events):
                instance = np.asarray(values).view(cls)
                instance._cast_events = events
                return instance

            def __array_finalize__(self, source):
                self._cast_events = getattr(source, "_cast_events", None)

            def astype(self, dtype, *args, **kwargs):
                if self._cast_events is not None:
                    self._cast_events.append((tuple(self.shape), np.dtype(dtype)))
                return super().astype(dtype, *args, **kwargs)

        tile = TrackingTile(np.full((4, 4, 3), 37, dtype=np.uint8), cast_events)

        canvas = blend_rgb_tiles(
            [{"tile_origin_40x": [0, 0], "image": tile}],
            canvas_size_40x=[4, 4],
            overlap_px_40x=1,
        )

        self.assertTrue(np.array_equal(canvas, np.full((4, 4, 3), 37, dtype=np.uint8)))
        self.assertNotIn(((4, 4, 3), np.dtype(np.float64)), cast_events)

    def test_blend_rgb_tiles_rejects_uncovered_canvas(self):
        tile = np.zeros((2, 2, 3), dtype=np.uint8)

        with self.assertRaisesRegex(GenerationTilingError, "cover canvas"):
            blend_rgb_tiles(
                [{"tile_origin_40x": [0, 0], "image": tile}],
                canvas_size_40x=[4, 2],
                overlap_px_40x=1,
            )

    def test_complete_tile_traversal_plan_records_partial_progress(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )

        completed = complete_tile_traversal_plan(plan, completed_tile_count=1)

        self.assertEqual(plan["completed_tile_count"], 0)
        self.assertEqual(completed["completed_tile_count"], 1)
        self.assertEqual(completed["pending_tile_count"], 1)
        self.assertEqual(completed["resume_index"], 1)
        self.assertEqual(completed["next_tile_index"], 1)
        self.assertEqual([tile["status"] for tile in completed["tiles"]], ["completed", "pending"])

    def test_resumable_tile_manifest_tracks_progress_and_next_tile(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )

        manifest = build_resumable_tile_manifest(plan)
        manifest = update_resumable_tile_manifest(
            manifest,
            tile_index=0,
            status="completed",
            output_path="tiles/tile-000.npy",
        )

        self.assertEqual(manifest["manifest_type"], "resumable_tile_manifest")
        self.assertEqual(manifest["completed_tile_count"], 1)
        self.assertEqual(manifest["pending_tile_count"], 1)
        self.assertEqual(manifest["failed_tile_count"], 0)
        self.assertEqual(manifest["next_tile_index"], 1)
        self.assertEqual(manifest["execution_status"], "in_progress")
        self.assertEqual(manifest["tiles"][0]["status"], "completed")
        self.assertEqual(manifest["tiles"][0]["output_path"], "tiles/tile-000.npy")
        self.assertEqual(manifest["tiles"][1]["status"], "pending")

    def test_resumable_tile_manifest_records_failed_tile_and_blocks_completion(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )
        manifest = build_resumable_tile_manifest(plan)

        failed = update_resumable_tile_manifest(
            manifest,
            tile_index=1,
            status="failed",
            error_message="tile writer crashed",
        )

        self.assertEqual(failed["completed_tile_count"], 0)
        self.assertEqual(failed["pending_tile_count"], 1)
        self.assertEqual(failed["failed_tile_count"], 1)
        self.assertEqual(failed["next_tile_index"], 0)
        self.assertEqual(failed["execution_status"], "failed")
        self.assertEqual(failed["tiles"][1]["error_message"], "tile writer crashed")
        with self.assertRaisesRegex(GenerationTilingError, "failed"):
            require_complete_tile_manifest(failed)

    def test_resumable_tile_manifest_requires_contiguous_resume(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[1280, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )
        manifest = build_resumable_tile_manifest(plan)

        updated = update_resumable_tile_manifest(manifest, tile_index=1, status="completed")

        self.assertEqual(updated["completed_tile_count"], 1)
        self.assertEqual(updated["next_tile_index"], 0)
        self.assertEqual(updated["resume_index"], 0)
        self.assertEqual(updated["execution_status"], "in_progress")
        with self.assertRaisesRegex(GenerationTilingError, "row-major"):
            require_complete_tile_manifest(updated)

    def test_resumable_tile_manifest_validates_counts_and_tile_indexes(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )
        manifest = build_resumable_tile_manifest(plan)
        bad_count = dict(manifest)
        bad_count["completed_tile_count"] = 99
        bad_tile = dict(manifest)
        bad_tile["tiles"] = [dict(tile) for tile in manifest["tiles"]]
        bad_tile["tiles"][1]["tile_index"] = 0

        with self.assertRaisesRegex(GenerationTilingError, "completed_tile_count"):
            validate_resumable_tile_manifest(bad_count)
        with self.assertRaisesRegex(GenerationTilingError, "tile_index"):
            validate_resumable_tile_manifest(bad_tile)

    def test_resumable_tile_manifest_requires_complete_without_pending_tiles(self):
        plan = create_tile_traversal_plan(
            canvas_size_40x=[768, 512],
            tile_size_40x=[512, 512],
            overlap_px_40x=64,
            resume_index=0,
            cascade_level="1/1",
        )
        manifest = build_resumable_tile_manifest(plan)

        with self.assertRaisesRegex(GenerationTilingError, "pending"):
            require_complete_tile_manifest(manifest)

        completed = update_resumable_tile_manifest(manifest, tile_index=0, status="completed")
        completed = update_resumable_tile_manifest(completed, tile_index=1, status="completed")

        required = require_complete_tile_manifest(completed)
        self.assertEqual(required["execution_status"], "completed")
        self.assertIsNone(required["next_tile_index"])


if __name__ == "__main__":
    unittest.main()
