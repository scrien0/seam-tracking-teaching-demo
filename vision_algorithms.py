"""Laser-stripe preprocessing and feature extraction for seam-tracking demos.

The functions operate on one camera image at a time. Pixel coordinates are
returned in (x, y) order. Calibrate the camera and robot frames before using
any result for motion; this module is not a robot controller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np


PointArray = np.ndarray  # shape (N, 2), columns are x_px, y_px


@dataclass
class StripeResult:
    """Intermediate data useful for teaching and visualization."""

    gray: np.ndarray
    binary: np.ndarray
    centerline: PointArray


@dataclass
class FeaturePoint:
    x_px: float
    y_px: float
    confidence: float
    kind: str

    def as_array(self) -> np.ndarray:
        return np.array([self.x_px, self.y_px], dtype=np.float64)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty array")
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 3 and image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError("image must be grayscale, BGR, or BGRA")
    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return gray


def preprocess_laser_stripe(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None = None,
    *,
    blur_size: int = 5,
    method: Literal["column", "otsu"] = "column",
    threshold_ratio: float = 0.62,
    min_intensity: int = 28,
) -> tuple[np.ndarray, np.ndarray]:
    """Denoise a laser image and create a binary stripe mask.

    Args:
        image: Grayscale, BGR, or BGRA image.
        roi: Optional (x, y, width, height). Pixels outside the ROI are zeroed.
        blur_size: Odd Gaussian kernel size; set to 1 to skip blur.
        method: ``column`` thresholds each image column relative to its peak;
            ``otsu`` uses Otsu's global threshold.
        threshold_ratio: Relative threshold for ``column`` mode, in (0, 1].
        min_intensity: Absolute floor that rejects dim background noise.

    Returns:
        A denoised uint8 grayscale image and a 0/255 binary mask.
    """
    gray = _to_gray(image)
    h, w = gray.shape
    if roi is None:
        x0, y0, x1, y1 = 0, 0, w, h
    else:
        x, y, rw, rh = roi
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(w, int(x + rw)), min(h, int(y + rh))
        if x1 <= x0 or y1 <= y0:
            raise ValueError("roi does not overlap the image")
    if blur_size < 1 or (blur_size > 1 and blur_size % 2 == 0):
        raise ValueError("blur_size must be 1 or a positive odd number")
    smooth = gray if blur_size == 1 else cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    binary = np.zeros_like(gray)
    crop = smooth[y0:y1, x0:x1]
    if method == "otsu":
        _, thresholded = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresholded[crop < min_intensity] = 0
    elif method == "column":
        peaks = crop.max(axis=0, keepdims=True).astype(np.float32)
        thresholds = np.maximum(min_intensity, peaks * float(threshold_ratio))
        thresholded = (crop >= thresholds).astype(np.uint8) * 255
    else:
        raise ValueError("method must be 'column' or 'otsu'")
    binary[y0:y1, x0:x1] = thresholded
    return smooth, binary


def _bright_groups(rows: np.ndarray) -> list[np.ndarray]:
    if rows.size == 0:
        return []
    split_at = np.flatnonzero(np.diff(rows) > 1) + 1
    return list(np.split(rows, split_at))


def extract_centerline(
    gray: np.ndarray,
    binary: np.ndarray,
    *,
    min_pixels: int = 2,
    max_jump_px: float = 18.0,
    median_window: int = 5,
) -> PointArray:
    """Extract a subpixel laser centerline with a per-column gray centroid.

    In columns with multiple bright blobs, the strongest candidate is used at
    the start; subsequent candidates are chosen by brightness and continuity.
    A small median filter suppresses isolated centerline spikes.
    """
    gray = _to_gray(gray)
    if binary.shape != gray.shape:
        raise ValueError("binary mask and image must have the same dimensions")
    if min_pixels < 1 or max_jump_px <= 0:
        raise ValueError("min_pixels and max_jump_px must be positive")
    if median_window < 1 or median_window % 2 == 0:
        raise ValueError("median_window must be a positive odd number")

    points: list[tuple[float, float]] = []
    previous_y: float | None = None
    for x in range(gray.shape[1]):
        rows = np.flatnonzero(binary[:, x] > 0)
        groups = [group for group in _bright_groups(rows) if len(group) >= min_pixels]
        if not groups:
            continue
        candidates: list[tuple[float, float, float]] = []
        for group in groups:
            weights = gray[group, x].astype(np.float64)
            weight_sum = float(weights.sum())
            if weight_sum <= 0:
                continue
            center_y = float(np.dot(group, weights) / weight_sum)
            candidates.append((center_y, weight_sum, float(weights.max())))
        if not candidates:
            continue
        if previous_y is None:
            chosen_y, _, _ = max(candidates, key=lambda item: item[1])
        else:
            continuous = [c for c in candidates if abs(c[0] - previous_y) <= max_jump_px]
            if not continuous:
                continue
            chosen_y, _, _ = max(
                continuous,
                key=lambda item: item[1] / (1.0 + abs(item[0] - previous_y)),
            )
        points.append((float(x), chosen_y))
        previous_y = chosen_y

    if len(points) < 3:
        raise ValueError("too few laser-stripe points; adjust ROI or threshold settings")
    result = np.asarray(points, dtype=np.float64)
    if median_window > 1 and len(result) >= median_window:
        pad = median_window // 2
        y = np.pad(result[:, 1], (pad, pad), mode="edge")
        result[:, 1] = np.array(
            [np.median(y[i : i + median_window]) for i in range(len(result))]
        )
    return result


def process_laser_image(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None = None,
    **kwargs: object,
) -> StripeResult:
    """Convenience wrapper that returns all three teaching stages."""
    preprocess_keys = {"blur_size", "method", "threshold_ratio", "min_intensity"}
    prep_args = {key: value for key, value in kwargs.items() if key in preprocess_keys}
    trace_args = {
        key: value
        for key, value in kwargs.items()
        if key in {"min_pixels", "max_jump_px", "median_window"}
    }
    gray, binary = preprocess_laser_stripe(image, roi, **prep_args)
    centerline = extract_centerline(gray, binary, **trace_args)
    return StripeResult(gray=gray, binary=binary, centerline=centerline)


def _line_fit(points: PointArray) -> tuple[float, float, float]:
    """Fit y = m*x + b and return slope, intercept, and mean squared error."""
    x, y = points[:, 0], points[:, 1]
    m, b = np.polyfit(x, y, 1)
    error = float(np.mean((y - (m * x + b)) ** 2))
    return float(m), float(b), error


def _intersection(
    line_a: tuple[float, float], line_b: tuple[float, float]
) -> tuple[float, float] | None:
    m1, b1 = line_a
    m2, b2 = line_b
    if abs(m1 - m2) < 1e-6:
        return None
    x = (b2 - b1) / (m1 - m2)
    return float(x), float(m1 * x + b1)


def detect_v_groove_bottom(
    centerline: PointArray,
    *,
    min_side_points: int = 8,
    shape: Literal["valley", "peak"] = "valley",
) -> FeaturePoint:
    """Find the V-groove root by fitting two line segments and intersecting.

    ``valley`` assumes image y increases toward the visible groove root. The
    ``peak`` option reverses that sign convention. Points should cover both
    flanks and be sorted left-to-right.
    """
    points = np.asarray(centerline, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("centerline must have shape (N, 2)")
    if len(points) < 2 * min_side_points + 1:
        raise ValueError("not enough points to fit both V-groove flanks")
    points = points[np.argsort(points[:, 0])]
    sign = 1 if shape == "valley" else -1 if shape == "peak" else 0
    if sign == 0:
        raise ValueError("shape must be 'valley' or 'peak'")

    best: tuple[float, float, float, float] | None = None
    for split in range(min_side_points, len(points) - min_side_points):
        left, right = points[:split], points[split:]
        m1, b1, e1 = _line_fit(left)
        m2, b2, e2 = _line_fit(right)
        if sign * m1 <= 0 or sign * m2 >= 0:
            continue
        cross = _intersection((m1, b1), (m2, b2))
        if cross is None:
            continue
        x_cross, y_cross = cross
        x_split = float(points[split, 0])
        if not (left[0, 0] <= x_cross <= right[-1, 0]):
            continue
        score = e1 + e2 + 0.02 * (x_cross - x_split) ** 2
        if best is None or score < best[0]:
            best = (score, x_cross, y_cross, x_split)
    if best is None:
        raise ValueError("opposing V flanks were not found; check view and shape sign")

    score, x, y, _ = best
    spread = float(np.var(points[:, 1])) + 1e-6
    confidence = float(np.clip(1.0 / (1.0 + score / spread), 0.0, 1.0))
    return FeaturePoint(x, y, confidence, "V-groove root intersection")


def detect_lap_step_corner(
    centerline: PointArray,
    *,
    min_step_px: float = 3.0,
    min_side_points: int = 5,
) -> FeaturePoint:
    """Locate a lap-joint step using the strongest local centerline jump.

    The detected feature is placed halfway between the last point before the
    step and the first point after it. This is suitable for a cross-section
    where the laser stripe shows a visible height discontinuity.
    """
    points = np.asarray(centerline, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 * min_side_points + 1:
        raise ValueError("centerline must contain enough (x, y) points")
    points = points[np.argsort(points[:, 0])]
    dx = np.diff(points[:, 0])
    dy = np.diff(points[:, 1])
    valid = (dx > 0) & (dx <= max(4.0, 2.5 * float(np.median(dx))))
    jump = np.abs(dy)
    jump[~valid] = 0
    # Reject edge artefacts by only searching where both sides have support.
    lo, hi = min_side_points - 1, len(points) - min_side_points
    candidates = np.arange(lo, hi)
    if candidates.size == 0:
        raise ValueError("not enough points around candidate lap-joint corner")
    idx = int(candidates[np.argmax(jump[candidates])])
    step = float(jump[idx])
    if step < min_step_px:
        raise ValueError("no clear lap-joint height step was found")
    x = float((points[idx, 0] + points[idx + 1, 0]) / 2)
    y = float((points[idx, 1] + points[idx + 1, 1]) / 2)
    baseline = float(np.median(jump[candidates])) + 1e-6
    confidence = float(np.clip(1.0 - baseline / max(step, baseline), 0.0, 1.0))
    return FeaturePoint(x, y, confidence, "lap-joint step corner")


def pixel_to_robot_xy(
    feature: FeaturePoint | np.ndarray,
    homography: np.ndarray,
) -> np.ndarray:
    """Map a pixel point to calibrated planar robot XY coordinates.

    ``homography`` is a 3x3 image-to-robot-plane matrix obtained from a real
    calibration procedure. The returned coordinates use the same units as the
    calibration targets, commonly millimetres.
    """
    point = feature.as_array() if isinstance(feature, FeaturePoint) else np.asarray(feature)
    matrix = np.asarray(homography, dtype=np.float64)
    if point.shape != (2,) or matrix.shape != (3, 3):
        raise ValueError("feature must be (x, y) and homography must be 3x3")
    mapped = matrix @ np.array([point[0], point[1], 1.0], dtype=np.float64)
    if abs(mapped[2]) < 1e-12:
        raise ValueError("homography maps this point to infinity")
    return mapped[:2] / mapped[2]


def draw_algorithm_overlay(
    image: np.ndarray,
    result: StripeResult,
    feature: FeaturePoint | None = None,
) -> np.ndarray:
    """Create a BGR visualization of the extracted centerline and feature."""
    output = cv2.cvtColor(_to_gray(image), cv2.COLOR_GRAY2BGR)
    for x, y in result.centerline:
        cv2.circle(output, (int(round(x)), int(round(y))), 1, (0, 220, 90), -1)
    if feature is not None:
        point = (int(round(feature.x_px)), int(round(feature.y_px)))
        cv2.drawMarker(output, point, (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
        cv2.putText(
            output,
            f"{feature.kind} ({feature.x_px:.1f}, {feature.y_px:.1f})",
            (max(5, point[0] + 8), max(20, point[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return output
