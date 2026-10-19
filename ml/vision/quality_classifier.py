"""
Produce Quality Grading & Ripeness Assessment Engine (Phase ML-4).
Banana first, then Tomato.
Suggestive-only grading with confidence calibration.
Policy: Never auto-rejects a farmer; low confidence yields 'buyer to check'.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# Ripeness definitions
BANANA_RIPENESS_STAGES = {
    1: {"name": "Deep Green", "desc": "Solid emerald green; unripened; hard pulp for distant transport"},
    2: {"name": "Green with Trace Yellow", "desc": "Slight softening of green; first yellow flush"},
    3: {"name": "More Green than Yellow", "desc": "Lime green color transition; commercial turning"},
    4: {"name": "More Yellow than Green", "desc": "60% yellow skin; ideal wholesale turning stage"},
    5: {"name": "Yellow with Green Tip", "desc": "Firm yellow body with green neck; optimal institutional delivery"},
    6: {"name": "Full Yellow", "desc": "Pure yellow; eating ripe; direct retail consumption"},
    7: {"name": "Sugar Flecks / Over-Ripe", "desc": "Brown sugar spots; softened pulp; for processing only"},
}

TOMATO_RIPENESS_STAGES = {
    1: {"name": "Green", "desc": "Entire surface green; firm fruit for long-distance transit"},
    2: {"name": "Breaker", "desc": "First definite color break; <= 10% pink/yellow at blossom end"},
    3: {"name": "Turning", "desc": "10% to 30% of surface shows pink, red, or yellow"},
    4: {"name": "Pink", "desc": "30% to 60% of surface shows pinkish-red color"},
    5: {"name": "Light Red", "desc": "60% to 90% of surface shows reddish-pink color"},
    6: {"name": "Red", "desc": "> 90% surface mature red; ready for immediate kitchen consumption"},
}


@dataclass
class QualitySuggestionResult:
    crop_id: str
    suggested_grade: str  # 'Grade_A', 'Grade_B', 'Grade_C', or 'uncertain'
    confidence: float  # 0.0 to 1.0
    buyer_decision_needed: bool
    buyer_guidance_note: str
    ripeness_stage: int
    ripeness_name: str
    detected_defects: list[str]
    grade_probabilities: dict[str, float]
    human_rule_baseline_grade: str
    image_quality_metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProduceQualityClassifier:
    """
    Lightweight visual feature extractor and probabilistic quality classifier.
    Combines:
    1. HSV color space hue-saturation histograms (ripeness & discoloration).
    2. Gradient Laplacian edge density (bruising, surface blemishes, cracks).
    3. Color-heuristic human-rule baseline for comparison.
    4. Calibrated confidence thresholds with 'buyer to check' guardrail.
    """

    def __init__(self, confidence_threshold: float = 0.65) -> None:
        self.conf_threshold = confidence_threshold

    def extract_visual_features(self, image: Image.Image) -> dict[str, float]:
        """Extracts color hue, saturation, brightness, and edge roughness features."""
        # Standardize size
        resized = image.convert("RGB").resize((128, 128), Image.Resampling.BILINEAR)
        rgb_arr = np.array(resized, dtype=float) / 255.0

        r, g, b = rgb_arr[:, :, 0], rgb_arr[:, :, 1], rgb_arr[:, :, 2]
        brightness = float(np.mean(0.299 * r + 0.587 * g + 0.114 * b))

        # Hue and saturation approximations
        mx = np.maximum(np.maximum(r, g), b)
        mn = np.minimum(np.minimum(r, g), b)
        diff = mx - mn + 1e-6
        saturation = float(np.mean(np.where(mx == 0, 0, diff / (mx + 1e-6))))

        # Dominant color ratios
        green_ratio = float(np.mean((g > r * 1.22) & (g > b * 1.22)))
        yellow_ratio = float(np.mean((r > 0.40) & (g > 0.40) & (abs(r - g) < 0.22) & (b < 0.35)))
        red_ratio = float(np.mean((r > g * 1.25) & (r > b * 1.25)))

        # Edge roughness / blemish density via Laplacian gradient variance
        gray = image.convert("L").resize((128, 128), Image.Resampling.BILINEAR)
        g_arr = np.array(gray, dtype=float)
        # 3x3 Laplacian kernel filter
        lap = (
            -4 * g_arr[1:-1, 1:-1]
            + g_arr[:-2, 1:-1]
            + g_arr[2:, 1:-1]
            + g_arr[1:-1, :-2]
            + g_arr[1:-1, 2:]
        )
        edge_variance = float(np.var(lap))
        dark_spot_ratio = float(np.mean(g_arr < 45))

        return {
            "brightness": round(brightness, 3),
            "saturation": round(saturation, 3),
            "green_ratio": round(green_ratio, 3),
            "yellow_ratio": round(yellow_ratio, 3),
            "red_ratio": round(red_ratio, 3),
            "edge_roughness": round(edge_variance, 2),
            "dark_spot_ratio": round(dark_spot_ratio, 3),
        }

    def evaluate_human_rule_baseline(self, crop_id: str, feats: dict[str, float]) -> str:
        """
        Simple deterministic human-rule baseline:
        Uses rigid color ratios and dark spot threshold to assign grades.
        """
        c_id = crop_id.lower()
        if c_id == "banana":
            # Rule: High dark spots (> 10%) -> Grade C. Balanced yellow (> 40%) -> Grade A. Else Grade B.
            if feats["dark_spot_ratio"] > 0.12 or feats["edge_roughness"] > 350.0:
                return "Grade_C"
            if feats["yellow_ratio"] > 0.35 and feats["dark_spot_ratio"] < 0.05:
                return "Grade_A"
            return "Grade_B"
        else:  # tomato
            if feats["dark_spot_ratio"] > 0.08 or feats["edge_roughness"] > 320.0:
                return "Grade_C"
            if (feats["red_ratio"] > 0.45 or feats["yellow_ratio"] > 0.30) and feats["dark_spot_ratio"] < 0.04:
                return "Grade_A"
            return "Grade_B"

    def assess_quality(self, image: Image.Image, crop_id: str = "banana") -> QualitySuggestionResult:
        """
        Generates suggestive produce grading, ripeness stage, and defect hints.
        """
        crop = crop_id.lower().strip()
        feats = self.extract_visual_features(image)
        baseline_grade = self.evaluate_human_rule_baseline(crop, feats)

        defects: list[str] = []
        ripeness_stage: int = 4
        ripeness_name: str = "Turning"

        # Check image quality (blurriness / extreme dark / glare)
        is_corrupted = False
        if feats["edge_roughness"] < 15.0:  # Excessive blur
            is_corrupted = True
        if feats["brightness"] < 0.15 or feats["brightness"] > 0.90:  # Bad lighting
            is_corrupted = True

        if crop == "banana":
            # Ripeness stage inference from green-to-yellow hue ratio
            g_rat = feats["green_ratio"]
            y_rat = feats["yellow_ratio"]
            d_rat = feats["dark_spot_ratio"]

            if g_rat > 0.65:
                ripeness_stage = 1
            elif g_rat > 0.45:
                ripeness_stage = 2
            elif g_rat > 0.25 and y_rat < 0.35:
                ripeness_stage = 3
            elif y_rat > 0.45 and g_rat > 0.10:
                ripeness_stage = 4
            elif y_rat > 0.55 and g_rat <= 0.10:
                ripeness_stage = 5
            elif y_rat > 0.40 and d_rat < 0.08:
                ripeness_stage = 6
            else:
                ripeness_stage = 7

            ripeness_name = BANANA_RIPENESS_STAGES[ripeness_stage]["name"]

            # Defect tagging
            if d_rat > 0.06:
                defects.append("surface_blemishes_or_thrips")
            if feats["edge_roughness"] > 250.0 and d_rat > 0.08:
                defects.append("mechanical_bruising")
            # Calibrated scoring
            # Grade A: Stage 3 to 6 with low dark spots (< 0.04)
            is_good_ripeness = 3 <= ripeness_stage <= 6
            score_a = max(0.1, 2.5 * (1.0 - d_rat * 9.0) * (1.4 if is_good_ripeness else 0.5))
            score_c = max(0.1, 2.6 * (d_rat * 9.0 + (1.2 if ripeness_stage == 7 or d_rat > 0.08 else 0.0)))
            score_b = max(0.2, 1.8 * (1.0 - abs(d_rat - 0.04) * 6.0))

        else:  # tomato
            r_rat = feats["red_ratio"]
            g_rat = feats["green_ratio"]
            y_rat = feats["yellow_ratio"]
            d_rat = feats["dark_spot_ratio"]

            if g_rat > 0.60:
                ripeness_stage = 1
            elif g_rat > 0.35 and y_rat > 0.10:
                ripeness_stage = 2
            elif y_rat > 0.30 and r_rat < 0.25:
                ripeness_stage = 3
            elif r_rat > 0.30 and r_rat < 0.55:
                ripeness_stage = 4
            elif r_rat >= 0.55 and r_rat < 0.80:
                ripeness_stage = 5
            else:
                ripeness_stage = 6

            ripeness_name = TOMATO_RIPENESS_STAGES[ripeness_stage]["name"]

            if d_rat > 0.03:
                defects.append("skin_specks_or_minor_blemish")
            if feats["edge_roughness"] > 240.0:
                defects.append("catfacing_or_growth_cracks")
            if d_rat > 0.05 or feats["brightness"] < 0.25:
                defects.append("blossom_end_rot_or_soft_rot")

            is_good_ripeness = 3 <= ripeness_stage <= 6
            score_a = max(0.1, 2.5 * (1.0 - d_rat * 9.0) * (1.4 if is_good_ripeness and d_rat < 0.04 else 0.5))
            score_c = max(0.1, 2.6 * (d_rat * 9.0 + (1.2 if d_rat > 0.05 or feats["brightness"] < 0.25 else 0.0)))
            score_b = max(0.2, 1.8 * (1.0 - abs(d_rat - 0.03) * 6.0))

        # Softmax normalization of calibrated logits
        logits = np.array([score_a, score_b, score_c], dtype=float)
        exp_scores = np.exp(logits - np.max(logits))
        probs = exp_scores / np.sum(exp_scores)
        p_a, p_b, p_c = round(float(probs[0]), 3), round(float(probs[1]), 3), round(float(probs[2]), 3)

        prob_dict = {"Grade_A": p_a, "Grade_B": p_b, "Grade_C": p_c}
        best_grade = max(prob_dict, key=prob_dict.get)
        confidence = prob_dict[best_grade]

        # Policy: If low confidence or corrupted photo, suggest 'uncertain' & 'buyer to check'
        if is_corrupted or confidence < self.conf_threshold:
            suggested_grade = "uncertain"
            buyer_decision_needed = True
            buyer_guidance_note = (
                "Model confidence is below threshold; buyer must inspect physical crates before finalizing."
                if not is_corrupted
                else "Photo lighting or blur level is outside calibrated bounds; buyer physical check required."
            )
        else:
            suggested_grade = best_grade
            buyer_decision_needed = False
            buyer_guidance_note = f"Suggested as {best_grade.replace('_', ' ')} based on visual cues. Buyer retains final acceptance authority."

        return QualitySuggestionResult(
            crop_id=crop,
            suggested_grade=suggested_grade,
            confidence=confidence,
            buyer_decision_needed=buyer_decision_needed,
            buyer_guidance_note=buyer_guidance_note,
            ripeness_stage=ripeness_stage,
            ripeness_name=ripeness_name,
            detected_defects=defects,
            grade_probabilities=prob_dict,
            human_rule_baseline_grade=baseline_grade,
            image_quality_metrics=feats,
        )


def apply_rural_photo_augmentations(image: Image.Image, aug_type: str) -> Image.Image:
    """
    Simulates real-world rural budget phone photo degradations:
    - 'blur': camera lens out of focus or hand tremor
    - 'low_light': dark indoor sorting shed / evening shade
    - 'glare': over-exposed tropical midday noon sunlight
    - 'smudge': camera lens fingerprint grease
    """
    img = image.copy()
    if aug_type == "blur":
        return img.filter(ImageFilter.GaussianBlur(radius=2.5))
    elif aug_type == "low_light":
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(0.40)
    elif aug_type == "glare":
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(1.85)
    elif aug_type == "smudge":
        blurred = img.filter(ImageFilter.GaussianBlur(radius=1.5))
        enhancer = ImageEnhance.Contrast(blurred)
        return enhancer.enhance(0.70)
    return img
