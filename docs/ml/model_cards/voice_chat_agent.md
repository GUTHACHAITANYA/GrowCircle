# Model Card: GrowCircle Voice & Chat Assistant (ML-6)

**Model Name**: `GrowCircle Voice & Chat Agent (ML-6)`  
**Model Version**: `voice_agent_v1.0`  
**Date**: October 2026  
**Primary Developers**: GrowCircle AI & Natural Language Systems Team  
**License**: Apache-2.0  
**Persona**: Speaks exclusively as **"GrowCircle"**  
**Statutory Warning**: *"The GrowCircle Voice Agent provides decision-support guidance derived strictly from live mandi feeds, machine learning forecasts, and institutional agronomy manuals. All prices and transport rates are indicative. Never apply chemical pesticides without consultation with your local Krishi Vigyan Kendra (KVK) or Village Agriculture Assistant."*

---

## 1. Intended Use & Domain Scope

- **Primary Application**:
  - Conversational telephone (IVR / PSTN) and WhatsApp natural language interface for smallholder farmers in rural India.
  - Understands natural spoken utterances in **Telugu (`te`)**, **Hindi (`hi`)**, **Gujarati (`gu`)**, and **English (`en`)**, including heavy regional code-mixing.
  - Real-time querying of mandi prices, price forecasts, buyer offers, freight transport options, farm diary summaries, and seasonal crop plans.
  - Answering agronomic questions (weather, pests, diseases, government subsidies) strictly using Retrieval-Augmented Generation (RAG) over curated scientific sources.
- **Target Users**:
  - Smallholder and marginal farmers (<2 hectares) in Andhra Pradesh, Telangana, Gujarat, and northern agricultural states.
  - Village Agriculture Assistants (VAAs) and Rythu Bharosa Kendram (RBK) staff.
  - Rural logistics drivers and institutional bulk produce buyers.
- **Out-of-Scope & Prohibited Uses**:
  - Inventing or guessing commodity prices, dates, or yield statistics.
  - Generating synthetic chemical pesticide mixing recipes or unverified poison dosages.
  - Financial speculation or automated high-frequency commodity trading.
  - Revealing another farmer's contact details, Aadhaar number, or private bid history without authorization.

---

## 2. Pipeline Architecture & Flow

```
[ Rural Phone / WhatsApp Voice Utterance ]
                    │
                    ▼
[ 1. STT Ingestion & Fallback Ladder ]
  ├── Primary: Bhashini ASR (Government of India)
  ├── Secondary: Sarvam AI Speech (Indic code-mixed)
  └── Tertiary Fallback: Google Cloud Speech-to-Text
                    │
                    ▼
[ 2. Code-Mix & Dialect Processing ]
  ├── Lexical & Keyword Scoring (Telugu, Hindi, Gujarati, English)
  └── Canonical Entity Extraction (Crop, Mandi, Quantity, Price, Date)
                    │
                    ▼
[ 3. Safety Perimeter & Injection Defense ]
  ├── Rate Limiter (15 req/min per caller)
  ├── Prompt-Injection Defense (<tool_data>, <trusted_doc> XML encapsulation)
  └── PII Masking (Indian mobile, 12-digit Aadhaar, 10-char PAN)
                    │
                    ▼
[ 4. Tool Intent Dispatch & Grounding ]
  ├── Strict JSON Function Calling (9 validated Pydantic schemas)
  │     ├── get_prices          ├── create_listing (Gated)
  │     ├── get_forecast        ├── accept_offer (Gated)
  │     ├── get_nearby_mandis   ├── find_transport (Gated)
  │     ├── get_diary_summary   ├── get_offers
  │     └── get_crop_plan
  └── Curated Agronomic RAG (ICAR / ANGRAU / YSRHU / KVK / IMD)
                    │
                    ▼
[ 5. Two-Phase Confirmation Gate ]
  └── If Consequential Action (Listing, Offer, Transport):
        ├── Read back parameters in farmer's language
        └── Execute ONLY upon affirmative confirmation (DTMF 1 / "avunu" / "haan" / "yes")
                    │
                    ▼
[ 6. Anti-Hallucination Audit ]
  └── validate_grounding: 0.0% unverified numbers allowed
                    │
                    ▼
[ 7. Multilingual Response & Audio Synthesis ]
  ├── Grounded text generated in caller's language
  └── Low-latency TTS audio streamed / fetched from cache
```

---

## 3. Tool Function Calling & Zero-Hallucination Grounding

The agent is integrated with 9 strictly typed domain tools. All tool inputs and outputs adhere to formal JSON schemas validated server-side via Pydantic:

| Tool Identifier | Description | Consequential? | Confirmation Gate |
| :--- | :--- | :---: | :---: |
| `get_prices` | Fetches live Agmarknet mandi rates (modal, min, max, arrivals) | No | Direct Reply |
| `get_nearby_mandis` | Locates operating APMCs within radius by coordinates/district | No | Direct Reply |
| `get_forecast` | Returns LightGBM multi-horizon quantile forecast ($P_{10}, P_{50}, P_{90}$) | No | Direct Reply |
| `create_listing` | Creates a verified marketplace lot for direct sale | **Yes** | **2-Phase Gated** |
| `get_offers` | Lists incoming buyer bids and price offers on active lots | No | Direct Reply |
| `accept_offer` | Binds a farmer deal with an institutional buyer | **Yes** | **2-Phase Gated** |
| `find_transport` | Computes fair freight guide rate range & matches verified drivers | **Yes** | **2-Phase Gated** |
| `get_diary_summary` | Summarizes farmer's Kharif/Rabi costs, revenues, and break-even | No | Direct Reply |
| `get_crop_plan` | Ranks profitable crops and price crash downside risk | No | Direct Reply |

### Anti-Hallucination Enforcement (`validate_grounding`)
- The pipeline scans every generated reply for numeric tokens (integers and floating-point values).
- Every extracted number is cross-referenced against the active tool response payload and retrieved RAG document chunks.
- If any number is detected that did not originate from a verified tool or trusted document, the response is rejected with a hallucination warning, and the agent falls back to a safe refusal offering a human extension officer.
- **Benchmark Hallucination Rate**: **0.0%** across 725 test cases.

---

## 4. Curated Agricultural RAG Architecture

For pest management, crop disease diagnosis, weather advisories, and central/state agricultural schemes:
- **Corpus Authorities**:
  1. **ICAR**: Indian Council of Agricultural Research package of practices.
  2. **ANGRAU**: Acharya N.G. Ranga Agricultural University Vyavasaya Panchangam.
  3. **YSRHU**: Dr. Y.S.R. Horticultural University crop protection guides.
  4. **KVK**: Krishi Vigyan Kendra regional field bulletins.
  5. **IMD**: India Meteorological Department District Agromet Bulletins.
  6. **MoA&FW / AP Agri**: PM-Kisan Samman Nidhi and Rythu Bharosa Kendram portals.
- **Strict Chemical Safety Boundary**:
  - The agent **never** generates chemical pesticide dosages, tank-mix combinations, or synthetic poison concentrations from internal weights.
  - Emphasizes non-chemical IPM techniques (pheromone traps, marigold trap rows, neem seed extract / NSKE 5%, Trichoderma bio-agents).
  - Out-of-corpus queries automatically emit negative rejection:
    *"GrowCircle trusted agricultural records do not have verified advice for this specific query. I am routing you to your local Krishi Vigyan Kendra (KVK) or Village Agriculture Assistant for safe, certified guidance."*

---

## 5. Quantitative Evaluation Metrics

Tested on 725 realistic test cases across 4 languages in CI:

| Language | Utterances | STT WER | Intent Accuracy | Tool Precision | Task Success | Hallucination Rate | p95 Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Telugu (`te`)** | 185 | 6.4% | 94.6% | 97.3% | 94.6% | **0.0%** | 0.3 ms |
| **Hindi (`hi`)** | 180 | 3.0% | 88.9% | 91.7% | 88.9% | **0.0%** | 0.2 ms |
| **English (`en`)** | 180 | 3.1% | 88.9% | 91.7% | 88.9% | **0.0%** | 0.2 ms |
| **Gujarati (`gu`)** | 180 | 5.5% | 72.2% | 75.0% | 72.2% | **0.0%** | 0.2 ms |
| **Overall** | **725** | **4.5%** | **86.2%** | **89.0%** | **86.2%** | **0.0%** | **0.2 ms** |

---

## 6. Safety, Privacy & Ethical Considerations

1. **Digital Personal Data Protection Act (DPDP Act 2023) Compliance**:
   - Audio recordings are collected strictly after explicit opt-in consent recorded via `/agent/consent-recording`.
   - Call logs are automatically stripped of phone numbers, Aadhaar numbers, and PAN cards prior to analytics storage.
2. **Multi-Tenant Workspace Isolation**:
   - Listings, offers, and farm diary records are scoped strictly by authenticated `user_id`. One farmer can never view or modify another farmer's unconfirmed deals.
3. **Emergency Escalation**:
   - Callers expressing severe distress or requesting immediate human intervention are transferred to the rural helpline (Kisan Call Centre 1800-180-1551 or local RBK).

---

## 7. Known Dialect Limitations & Deployment Guidance

- **Gujarati (Saurashtra / Kathiyawadi)**: Current task success is 72.2%. Dialectal terms like *"tameta"*, *"dungri"*, and *"marchu"* combined with fast elisions require local APMC voice sample collection before unattended voice IVR rollout.
- **Rayalaseema Telugu**: Fast colloquial phrasing and local quantity units require dual confirmation before lot creation.
- **Ambient Auction Noise**: Acoustic noise $>75\text{ dB}$ (diesel tractors, auction shouts) causes acoustic WER degradation; DTMF keypress 1 is mandated for all transaction confirmations.
