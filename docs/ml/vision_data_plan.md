# Computer Vision Produce Quality Data Collection Plan

**Phase**: ML-4 Remote Computer Vision Quality & Defect Checks  
**Crops**: Banana (*Musa acuminata*) first, then Tomato (*Solanum lycopersicum*)  
**Status**: Data Collection Specification & Annotation Protocol  
**Principle**: *Do not train models without high-fidelity, agronomist-verified labelled data. Build the safe collection pipeline, define rigorous grading taxonomy, and enforce photo integrity.*

---

## 1. Ethical & Safe Farmer Photo Collection Plan

### Statutory DPDP Act 2023 Consent
Before any produce photo is uploaded, farmers receive a clear, plain-language consent prompt in their native tongue:
- **English**: *"Allow GrowCircle to analyze photos of your produce to suggest quality grades to buyers and help train our quality verification models. Your photos will never be shared publicly without consent."*
- **Telugu (తెలుగు)**: *"కొనుగోలుదారులకు నాణ్యత గ్రేడ్‌లను సూచించడానికి మరియు నాణ్యత తనిఖీ వ్యవస్థను మెరుగుపరచడానికి మీ పంట ఫోటోలను విశ్లేషించడానికి గ్రోసర్కిల్‌ను అనుమతించండి. మీ అనుమతి లేకుండా మీ ఫోటోలు బయట పంచుకోబడవు."*
- **Hindi (हिंदी)**: *"खरीदारों को गुणवत्ता ग्रेड सुझाने और हमारी गुणवत्ता जांच प्रणाली को बेहतर बनाने के लिए ग्रोसर्कल को अपनी फसल के फोटो का विश्लेषण करने की अनुमति दें।"*
- **Gujarati (ગુજરાતી)**: *"વેપારીઓને ગુણવત્તા ગ્રેડ સૂચવવા અને અમારી સિસ્ટમને તાલીમ આપવા માટે ગ્રોસર્કલને તમારા પાકના ફોટાનું વિશ્લેષણ કરવાની મંજૂરી આપો."*

### Privacy & PII Safeguards
1. **Automated PII Obfuscation**: Client-side face detection and vehicle number plate blurring before upload.
2. **Crop-Only Framing**: The in-app camera viewfinder guides the farmer to fill 80% of the frame with the produce lot or crates, excluding background farmhouses, family members, or personal belongings.
3. **Data Rights**: Farmers can request deletion of their contributed training photos at any time under DPDP Right to Erasure (`POST /dpdp/delete-account`).

---

## 2. Standardized Capture Protocol: The 3-Photo Checklist

A single photo cannot reliably represent an entire 500 kg commercial lot. GrowCircle enforces a mandatory 3-photo capture sequence in the mobile PWA and WhatsApp flows:

```
+-----------------------------------------------------------------------------------------+
|                                THE 3-PHOTO CHECKLIST                                    |
+------------------------------+------------------------------+---------------------------+
|      Photo 1: Whole Lot      |      Photo 2: Close-up       |   Photo 3: Opened Crate   |
|         (Overview)           |        (Defect Scan)         |      (Internal Pulp)      |
+------------------------------+------------------------------+---------------------------+
| Distance: 2.0 to 3.0 meters  | Distance: 0.3 to 0.5 meters  | Distance: 0.4 meters      |
| Angle: 45° downward oblique  | Angle: 90° nadir top-down    | Angle: Top crate opened   |
| Purpose: Stacking, total     | Purpose: Skin blemishes,     | Purpose: Internal decay,  |
| volume, overall color hue,   | thrips marks, crown rot,     | fruit firmness, core cuts,|
| crate uniformity.            | calyx condition.             | layer consistency.        |
+------------------------------+------------------------------+---------------------------+
```

### Environmental & Device Diversity Requirements
To prevent model brittleness, the collection protocol deliberately samples across challenging rural field conditions:
1. **Lighting Regimes**:
   - *Harsh Tropical Sunlight*: Midday field loading with strong shadows and white glare/over-exposure.
   - *Diffused Shade*: Morning / late afternoon natural ambient light (optimal).
   - *Indoor Sorting Shed*: Low-light incandescent bulbs, compact fluorescent (CFL), or unlit godown shade.
2. **Device Variety**:
   - Minimum 60% of dataset collected on entry-level smartphones popular in rural AP (Redmi 9/10, Realme C-series, Samsung Galaxy M04/M13) with budget 8 MP–13 MP sensors.
   - Realistic artifacts: Camera lens oil smudges, hand-shake motion blur, and aggressive JPEG compression.
3. **Background Variety**:
   - Plastic crates (blue, red, green), wooden crates, gunny bags, tarpaulin ground sorting, and pickup truck metal beds.

---

## 3. Label Studio Configuration & Schema

Label Studio is used as the centralized human-in-the-loop annotation workspace for agricultural extension officers and university agronomists.

### Annotation Interface (XML Template)
```xml
<View>
  <Image name="image" value="$image" zoom="true"/>
  
  <Header value="1. Overall Commercial Grade (Suggestive Only)"/>
  <Choices name="grade" toName="image" choice="single" showInline="true" required="true">
    <Choice value="Grade_A" hint="Premium wholesale/supermarket/export standard"/>
    <Choice value="Grade_B" hint="Standard commercial mandi grade"/>
    <Choice value="Grade_C" hint="Processing/juice/sauce or severe blemish"/>
  </Choices>

  <Header value="2. Ripeness Stage Classification"/>
  <Choices name="ripeness_stage" toName="image" choice="single" showInline="true" required="true">
    <!-- Banana: CSIRO 7-stage; Tomato: USDA 6-stage -->
    <Choice value="stage_1" hint="Green / Immature"/>
    <Choice value="stage_2" hint="Breaker / Trace yellow"/>
    <Choice value="stage_3" hint="Turning / More green than yellow"/>
    <Choice value="stage_4" hint="Pink / More yellow than green"/>
    <Choice value="stage_5" hint="Light Red / Yellow with green tips"/>
    <Choice value="stage_6" hint="Full Red / Full Yellow (Eating ripe)"/>
    <Choice value="stage_7" hint="Sugar flecks / Over-ripe (Banana only)"/>
  </Choices>

  <Header value="3. Defect Tagging & Localization"/>
  <RectangleLabels name="defect_boxes" toName="image">
    <Label value="crown_rot" background="#8B0000"/>
    <Label value="anthracnose_spots" background="#A0522D"/>
    <Label value="mechanical_bruise" background="#4682B4"/>
    <Label value="blossom_end_rot" background="#000000"/>
    <Label value="sunscald_blister" background="#FFD700"/>
    <Label value="growth_cracks" background="#FF4500"/>
    <Label value="insect_puncture" background="#9932CC"/>
    <Label value="under_calibre" background="#708090"/>
  </RectangleLabels>
</View>
```

---

## 4. Agronomist-Reviewed Quality Definitions

### 4.1. Banana (*Musa acuminata* – Grand Naine, Robusta, Amruthapani)

#### Ripeness Scale (CSIRO 7-Stage Color Standard)
1. **Stage 1 (Deep Green)**: Solid emerald green; hard pulp. Harvest standard for distant interstate transit (> 72 hours).
2. **Stage 2 (Green with Trace Yellow)**: Slight softening of dark green; first trace of yellow flush.
3. **Stage 3 (More Green than Yellow)**: Noticeable lime-green color transition.
4. **Stage 4 (More Yellow than Green)**: 60% yellow skin; ideal turning stage for wholesale distribution.
5. **Stage 5 (Yellow with Green Tip & Neck)**: Clear yellow body with firm green tip. **Optimal delivery stage for institutional buyers** (hostels, hotels) allowing 2–3 days storage.
6. **Stage 6 (Full Yellow)**: Pure yellow; peak sweetness and aroma; direct consumer retail stage.
7. **Stage 7 (Yellow with Brown Flecks)**: Sugar spots visible; pulp softens rapidly. Suitable for immediate consumption only.

#### Defect Taxonomy
- **Crown Rot (*Colletotrichum musae*)**: Black fungal discoloration at the finger cluster neck. If soft or mouldy, downgrades cluster immediately to Grade C.
- **Anthracnose / Leaf Spot**: Circular dark sunken lesions on fingers. Acceptable up to 5% surface area for Grade B.
- **Mechanical Bruising**: Friction scuffs and impact gouges from rough carting. Darkens skin; risks fungal entry.
- **Under-Calibre Fingers**: Finger length $< 15$ cm or caliper diameter $< 32$ mm.
- **Sunburn**: Yellowish-white bleached skin patches with dry pulp underneath.

#### Grade Rules for Banana
- **Grade A (Premium Commercial)**:
  - Ripeness Stage 1–3 (or Stage 4–5 if explicitly requested by local institution).
  - Finger length $\ge 16$ cm; minimum 14 fingers per hand.
  - Zero crown rot, zero split skins. Cosmetic thrips blemishes $< 5\%$ total surface area.
- **Grade B (Standard Mandi Grade)**:
  - Ripeness Stage 2–6.
  - Finger length $\ge 13$ cm.
  - Minor mechanical scuffs $< 15\%$ surface area. Zero active watery rot.
- **Grade C (Processing / Distress Grade)**:
  - Over-ripe (Stage 7), under-calibre (< 13 cm), crown rot present, or skin cracks. Diverted to local bakeries/puree processors.

---

### 4.2. Tomato (*Solanum lycopersicum* – Arka Rakshak, US 440, Saaho)

#### Ripeness Scale (USDA 6-Stage Standard)
1. **Stage 1 (Green)**: Completely green surface; firm flesh.
2. **Stage 2 (Breaker)**: First definite break in color showing tannish-yellow or pink on $\le 10\%$ of surface.
3. **Stage 3 (Turning)**: Definite pink or red color on $10\% - 30\%$ of surface.
4. **Stage 4 (Pink)**: Pinkish-red color on $30\% - 60\%$ of surface.
5. **Stage 5 (Light Red)**: Pinkish-red or red on $60\% - 90\%$ of surface.
6. **Stage 6 (Red)**: $> 90\%$ surface shows mature red color; full culinary ripeness.

#### Defect Taxonomy
- **Blossom-End Rot (BER)**: Sunken, dark brown/black leathery lesion at the blossom end due to calcium deficiency.
- **Catfacing & Radial Growth Cracks**: Deep concentric or radial fissures near stem scar. If unhealed, leads to rapid fungal breakdown.
- **Sunscald**: White or golden-yellow bleached blistered patches caused by intense sun exposure on unshaded fruit.
- **Soft Rot / Sour Rot (*Rhizopus*)**: Water-soaked soft, leaky spots with rapid pulp liquefaction.
- **Borer / Pinworm Holes**: Small entry punctures with dark frass.

#### Grade Rules for Tomato
- **Grade A (Supermarket & Export Quality)**:
  - Breaker to Pink (Stage 2–4 for long transit) or Firm Red (Stage 5–6 for same-day kitchen delivery).
  - Fruit diameter $\ge 50$ mm.
  - Firm to touch; zero blossom-end rot; zero growth cracks; blemishes $< 5\%$.
- **Grade B (Standard Mandi Quality)**:
  - Stage 2–6.
  - Fruit diameter $\ge 40$ mm.
  - Minor superficial corky blemishes or small healed micro-cracks $< 10$ mm; completely firm; zero water leaks.
- **Grade C (Processing Quality)**:
  - Over-ripe, soft/leaking fruit, active blossom-end rot, or unhealed mechanical crush. Diverted to chutney/sauce processing.

---

## 5. Sample Size Requirements: How Much Data Is Needed for Reliable Grading?

A common failure in agricultural computer vision is deploying models trained on a few hundred convenience photos taken in clean laboratory lighting.

### Statistical Power & Diversity Analysis
To achieve $\ge 85\%$ macro F1 score across 5 agro-climatic zones in Andhra Pradesh with resilience to budget phone sensors and uneven sunlight, the following dataset scales are required:

| Target Task | Minimum Viable Sample (Pilot) | Recommended Production Scale | Diversity Stratification |
| :--- | :--- | :--- | :--- |
| **Ripeness Classification** (7 stages banana / 6 stages tomato) | 700 images (100 per stage) | **3,500 images** (500 per stage) | Across 50 unique farms, 3 seasons, 4 times of day |
| **Defect Detection** (8 defect classes) | 1,200 annotated instances (150 per class) | **6,000 annotated instances** (750 per class) | Mixed single & multiple defect co-occurrences |
| **Commercial Grade Assignment** (Grades A/B/C) | 600 lot sequences (200 per grade $\times$ 3 photos) | **3,000 lot sequences** (9,000 photos total) | Minimum 10 mobile handset models |

### Operational Stoppage Rule
> **MANDATORY POLICY**: Do not train deep neural networks without labelled data.
> In Phase ML-4, GrowCircle establishes:
> 1. The complete mobile collection flow and DPDP consent intake.
> 2. The perceptual and EXIF photo fraud screening gate.
> 3. A calibrated rule-based baseline and benchmark reference dataset to validate the suggestion flow.
> Full deep model weights are trained only once the Label Studio queue reaches the **700-image verified threshold**.
