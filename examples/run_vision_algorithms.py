"""Run the seam feature extraction example on a captured laser-stripe image."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import cv2

# Keep the command runnable as ``python examples/run_vision_algorithms.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision_algorithms import (
    detect_lap_step_corner,
    detect_v_groove_bottom,
    draw_algorithm_overlay,
    process_laser_image,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="path to a laser-stripe image")
    parser.add_argument("--feature", choices=("v-groove", "lap-step"), required=True)
    parser.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("X", "Y", "WIDTH", "HEIGHT"),
        help="optional region of interest around the laser stripe",
    )
    parser.add_argument("--output", type=Path, default=Path("feature-overlay.png"))
    args = parser.parse_args()

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        parser.error(f"cannot read image: {args.image}")

    try:
        result = process_laser_image(image, tuple(args.roi) if args.roi else None)
        if args.feature == "v-groove":
            point = detect_v_groove_bottom(result.centerline)
        else:
            point = detect_lap_step_corner(result.centerline)
    except ValueError as error:
        parser.error(str(error))

    overlay = draw_algorithm_overlay(image, result, point)
    if not cv2.imwrite(str(args.output), overlay):
        parser.error(f"cannot write output image: {args.output}")
    print(
        f"feature={point.kind}, x={point.x_px:.2f}px, y={point.y_px:.2f}px, "
        f"confidence={point.confidence:.3f}"
    )
    print(f"overlay={args.output.resolve()}")


if __name__ == "__main__":
    main()
