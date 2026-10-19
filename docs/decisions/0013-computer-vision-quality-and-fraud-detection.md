# ADR 0013: Computer Vision Produce Quality Grading, Photo Fraud Detection, and Ethical Collection

## Context
In GrowCircle's direct farm-to-institution marketplace, buyers (hostels, hotels, restaurants, supermarkets) purchase fresh produce directly from farmers based on mobile app listings. This introduces two severe vulnerabilities:
1. **Photo Fraud & Misrepresentation**: Unscrupulous sellers can reuse old photos from previous seasons, upload stock photos downloaded from Google Images, screenshot another seller's listing, or photograph produce in a different district.
2. **Subjective Quality Disputes**: Produce grading in India is traditionally informal and fraught with disputes over ripeness, bruising, and cosmetic blemishes.
3. **Risk of Algorithmic Discrimination**: An automated computer vision system that auto-rejects farmer listings based on imperfect budget-phone photos would disenfranchise smallholders with low-cost hardware.

---

## Decisions

### 1. Ethical Data Plan & Operational Stoppage Rule
- **Mandatory Policy**: We do not train deep neural networks without large, verified, agronomist-labelled datasets.
- Implemented `docs/ml/vision_data_plan.md` defining:
  - Multilingual DPDP Act 2023 statutory consent in 4 languages (`te`, `en`, `hi`, `gu`).
  - Standardized 3-Photo Checklist: *Photo 1 (Whole Lot Overview)*, *Photo 2 (Close-up Defect Scan)*, *Photo 3 (Opened Crate / Cross-Section)*.
  - Hosted Label Studio integration with XML annotation templates for Banana (CSIRO 7-stage ripeness) and Tomato (USDA 6-stage ripeness) and 8 agronomic defect classes.
  - Minimum sample size threshold: **700 verified lot sequences** (3,500 photos) required before fine-tuning small ViT or EfficientNet backbones.

### 2. Multi-Layer Photo Fraud Detection Gate
Every uploaded produce photo undergoes automated fraud screening prior to quality grading:
1. **EXIF Timestamp Freshness**: Checks `DateTimeOriginal` vs server upload time. Photos $> 24$ hours old or future-dated are flagged.
2. **Geolocation Consistency**: Calculates haversine distance between EXIF GPS coordinates and registered farm coordinates. Drift $> 25$ km is flagged.
3. **Perceptual Near-Duplicate Detection**: Computes aHash, dHash, and 2D-DCT pHash. Compares candidate hash against active database listings using Hamming distance. Distance $\le 6$ bits flags recycled stock photos.
4. **Screenshot of a Screen Detection**:
   - Matches display aspect ratios (16:9, 19.5:9, 20:9).
   - Evaluates 2D FFT frequency spectrum for discrete harmonic peaks characteristic of LCD/OLED Moire interference patterns.

### 3. Fiduciary Guardrail: Suggestive-Only Grading & Buyer Authority
- **Core Principle**: The model only **SUGGESTS** a grade (`Grade_A`, `Grade_B`, `Grade_C`) accompanied by a confidence value ($0.0 \text{ to } 1.0$).
- **The Buyer Decides**: The buyer retains sole legal authority to accept or reject produce upon physical inspection at delivery.
- **Low-Confidence Safeguard**: If confidence $< 0.65$ or image quality is degraded (blur variance $< 15$, extreme light/dark), the engine outputs `suggested_grade: "uncertain"` and mandates `"buyer to check"`.
- **Never Auto-Reject**: Farmers are **never** auto-rejected by the algorithm.

### 4. Architecture: FastAPI Router First with Timeout & Graceful Fallback
- Deployed as a modular FastAPI router (`/vision/inspect`, `/vision/fraud-check`, `/vision/collect`).
- Incorporates a 3.5-second `asyncio.wait_for` processing timeout:
  - If processing times out or fails, returns a structured graceful fallback with `suggested_grade: "uncertain"`, `buyer_decision_needed: True`, and `fallback_triggered: True`.

---

## Consequences
- **Positive**: Eliminates photo recycling fraud; provides buyers with transparent ripeness stages and defect hints; protects farmers from arbitrary algorithmic rejection.
- **Data Governance**: Directs incoming farmer photos into the Label Studio queue with clean consent records.
- **Scalability**: Sub-100 ms local inference using CPU-optimized spatial and spectral feature extractors avoids costly GPU cloud infrastructure during the pilot phase.
