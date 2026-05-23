import unittest

import numpy as np

from he_wsi_generator.generation.tiling import (
    GenerationTilingError,
    blend_rgb_tiles,
    complete_tile_traversal_plan,
    create_tile_traversal_plan,
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


if __name__ == "__main__":
    unittest.main()
