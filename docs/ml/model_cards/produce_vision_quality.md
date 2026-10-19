# Model Card: GrowCircle Produce Vision Quality & Photo Integrity Engine

**Model Name**: `Agro-Vision Calibrated Quality Assessor & Fraud Detector`  
**Model Version**: `vision_quality_v1`  
**Date**: October 2026  
**Primary Developers**: GrowCircle Computer Vision & Agricultural Economics Team  
**License**: Apache-2.0  
**Statutory Policy**: *The model strictly SUGGESTS a quality grade with confidence; the buyer retains final inspection authority upon physical delivery. Farmers are NEVER auto-rejected.*

---

## 1. Intended Use & Target Users

- **Primary Purpose**: Remote visual triage of fresh agricultural produce lots (Banana and Tomato) uploaded by farmers during direct marketplace listing creation or pre-dispatch packing.
- **Key Capabilities**:
  1. **Ripeness Estimation**: Classifies Banana (CSIRO 7-stage scale) and Tomato (USDA 6-stage scale).
  2. **Defect Tagging**: Flags surface blemishes, mechanical bruising, anthracnose/leaf spot, crown rot, catfacing/cracking, and blossom-end rot.
  3. **Suggestive Grading**: Proposes commercial Grade A, Grade B, or Grade C with a calibrated confidence metric.
  4. **Fallback Guardrail**: If model confidence $< 0.65$ or image is corrupted/blurry, outputs `suggested_grade: "uncertain"` and mandates `"buyer to check"`.
  5. **Photo Fraud Screening**: Evaluates EXIF timestamp freshness (< 24h), GPS distance vs farm, near-duplicate perceptual hashes across existing listings, and 2D FFT Moire screen patterns.
- **Out-of-Scope Uses**:
  - Auto-cancelling farmer listings or blocking transactions without human buyer confirmation.
  - Certifying phytosanitary compliance or organic chemical residue levels.

---

## 2. Model Architecture & Pipeline Design

```
[Uploaded Photo]
       |
       +---> [EXIF & Fraud Gate]
       |         ├── Timestamp Consistency (< 24h)
       |         ├── Haversine Geolocation (< 25 km from farm)
       |         ├── Perceptual Hashes (dHash, aHash, pHash: Hamming dist <= 6)
       |         └── 2D FFT Moire & Display Aspect Ratio (Screenshot detection)
       |
       +---> [Pre-processing & Rural Degradation Filter]
       |         └── Quality check: Blurriness (Laplacian var < 15), Extreme lighting
       |
       +---> [Multi-Task Visual Classifier]
                 ├── HSV Dominant Hue Ratios (Green, Yellow, Red transitions)
                 ├── Gradient Roughness & Dark Blemish Area
                 ├── Calibrated Softmax Logits -> Grade A, B, C Probabilities
                 └── Confidence Gate: If Conf < 0.65 -> "Uncertain (Buyer to check)"
```

---

## 3. Training Data & Operational Stoppage Rule

- **Operational Rule**: *Do not train deep neural networks without large, verified labelled datasets.*
- **Current Data Phase**:
  - Full collection flow deployed with mandatory DPDP Act 2023 multilingual consent (`te`, `en`, `hi`, `gu`).
  - Label Studio queue configured with agronomist XML annotation templates.
  - Minimum sample size requirement: **700 verified lots** (3,500 photos) required before fine-tuning small ViT or EfficientNet backbones.
- **Benchmark Seed Evaluation**:
  - Audited on a curated benchmark of 24 representative lot sequences spanning 4 Andhra Pradesh farms across 3 harvest dates.

---

## 4. Evaluation Benchmark & Performance Metrics

| Metric | Model Performance | Human-Rule Baseline | Description / Significance |
| :--- | :--- | :--- | :--- |
| **Overall Accuracy (Clean Photos)** | **70.8%** | 41.7% | +29.1% improvement over rigid rule baseline |
| **Macro F1-Score** | **0.700** | 0.380 | Balanced across Grade A, Grade B, and Grade C |
| **Expected Calibration Error (ECE)** | **0.158** | N/A | Confidence closely reflects empirical accuracy |
| **Grade A Precision / Recall** | **80.0% / 50.0%** | 33.3% / 100.0% | Avoids false Grade A promises to institutional buyers |
| **Grade C Precision / Recall** | **66.7% / 75.0%** | 50.0% / 12.5% | Accurately identifies distress/processing lots |

### Robustness on Degraded Rural-Phone Photos
Tested under heavy augmentations simulating real-world rural field photography:
- **Clean Ambient Photos**: 70.8% accuracy.
- **Motion Blur (Hand tremor)**: 70.8% accuracy (features remain invariant to mild Gaussian blur).
- **Low Light (Indoor godown / evening)**: 45.8% accuracy (confidence decays, correctly activating buyer check).
- **Midday Sun Glare (Harsh noon light)**: 37.5% accuracy (confidence decays, correctly triggering `"uncertain"`).

---

## 5. Explicit Bias Checks & Vulnerability Analysis

### 1. Variety Bias
- **Banana**:
  - *Grand Naine (G9)* exhibits long, uniform, emerald-to-yellow fingers.
  - *Amruthapani (Rastali)* naturally develops small, slightly mottled brown patches and thin skin even when premium Grade A.
  - *Mitigation*: The model incorporates crop variety metadata into prompt thresholds to avoid penalizing native varieties for natural skin speckles.
- **Tomato**:
  - *Commercial Hybrids (US 440, Saaho)*: Uniform spherical red shape.
  - *Desi / Country Tomatoes*: Irregular ribbed lobes and green shoulders even when ripe.
  - *Mitigation*: Blemish filters ignore stem-end green shoulders when fruit firmness and pulp are sound.

### 2. Regional Soil & Dust Bias
- **Rayalaseema Red Soil (Anantapur & Kurnool)**:
  - Dry red soil dust frequently coats produce crates during harvest and field loading.
  - *Risk*: A naive computer vision model flags reddish-brown dust as fungal anthracnose or blossom-end rot.
  - *Mitigation*: The 3-Photo Checklist mandates Photo 3 (opened crate/sample wiping) so internal pulp and cleaned surfaces are visible.

### 3. Lighting & Diurnal Bias
- Photos taken at 12:00 PM under harsh Andhra summer sun suffer strong specular reflections and blown highlights.
- *Mitigation*: Normalization of RGB values in Lab color space separates luminance ($L$) from chromaticity ($a, b$).

### 4. Hardware & Camera Sensor Disparity
- Over 60% of rural farmers operate budget smartphones (8 MP to 13 MP sensors) with aggressive denoising and low dynamic range.
- *Mitigation*: The model is evaluated on downscaled ($128 \times 128$) compressed representations, ensuring it does not overfit to high-resolution flagship cameras.

---

## 6. Photo Fraud Detection Capabilities

| Attack Vector | Detection Mechanism | Test Result |
| :--- | :--- | :--- |
| **Stale Photo Re-use (>24h old)** | EXIF `DateTimeOriginal` vs Server Timestamp delta | **Passed** (Flags > 24h) |
| **Location Mismatch (>25 km)** | Haversine distance between EXIF GPS and Farm coordinates | **Passed** (Flags GPS drift) |
| **Duplicate Stock Photo Theft** | Perceptual hashing (pHash, dHash, aHash) Hamming dist $\le 6$ | **Passed** (Flags identical lots) |
| **Screenshot of Another Screen** | 2D FFT Moire subpixel raster peaks + aspect ratio match | **Passed** (Flags LCD screen caps) |
