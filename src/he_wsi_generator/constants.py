PROJECT_VERSION = "v0.66.0"
PACKAGE_VERSION = "0.66.0"

MASK_CLASSES = (
    "background",
    "tissue",
    "target_pathology",
    "supporting_tissue",
    "necrosis_debris",
    "artifact",
)

CASCADE_LEVELS = ("1/32", "1/16", "1/4", "1/1")
TILE_SIZE_40X = (512, 512)
MAX_MAGNIFICATION = "40x"
MODEL_FAMILY = "latent_diffusion_unet"
STATUS_LEVELS = ("pass", "warning", "fail")

ANCHOR_PRESETS = {
    "rescan_simulation": 0.95,
    "structure_preserving": 0.80,
    "layout_recombination": 0.50,
    "fully_de_novo": 0.05,
}

SOURCE_ANCHORED_PRESETS = (
    "rescan_simulation",
    "structure_preserving",
    "layout_recombination",
)

DEFAULT_GENERATION_CONFIG = {
    "schema_version": PROJECT_VERSION,
    "random_seed": 0,
    "model_family": MODEL_FAMILY,
    "max_magnification": MAX_MAGNIFICATION,
    "tile_size_40x": list(TILE_SIZE_40X),
    "canvas_size_40x": list(TILE_SIZE_40X),
    "cascade_levels": list(CASCADE_LEVELS),
    "structure_anchor": 0.0,
    "anchor_preset": "fully_de_novo",
    "style_seed": "auto",
    "source_wsi_id": None,
    "sample_steps": 50,
    "overlap_px_40x": 64,
    "non_copy_patch_nearest_neighbor_search": False,
}
