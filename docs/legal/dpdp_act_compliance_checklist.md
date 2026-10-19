# Digital Personal Data Protection Act (DPDP Act 2023) Compliance Checklist

**Data Fiduciary**: GrowCircle Technologies Private Limited  
**Jurisdiction**: Republic of India  
**Target Group**: Smallholder Farmers, Institutional Buyers, Transporters, Consumers  
**Statutory Framework**: Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023)

---

## 1. Compliance Matrix & Verification Status

| Statutory Provision | Requirement | GrowCircle Technical Implementation | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Section 6: Consent & Notice** | Prior notice in clear, plain language; itemised consent; available in 8th Schedule languages. | • Notice presented at onboarding in Telugu, Hindi, Gujarati, English.<br>• `User.consent_at`, `consent_version`, and `consent_purpose` tracked.<br>• `POST /dpdp/consent` records explicit affirmative action. | **COMPLIANT** |
| **Section 6(4): Withdrawal of Consent** | Data principal can withdraw consent as easily as giving it. | • `User.consent_withdrawn_at` recorded.<br>• Triggered via web toggle or IVR voice command. | **COMPLIANT** |
| **Section 8(2): Data Minimisation** | Collect only personal data necessary for specified purpose. | • Phone numbers masked in public interfaces (`+91 98XXX XXX10`).<br>• GPS locations rounded to mandi / district centroid until deal confirmation.<br>• No Aadhaar or biometric data collected. | **COMPLIANT** |
| **Section 8(5): Security Safeguards** | Reasonable security safeguards to prevent data breach. | • Fernet AES-256 encryption for GST and trade licences.<br>• OWASP Top-10 security headers enforced.<br>• Rate limiting on OTP, IVR callbacks, and webhooks.<br>• `AuditLog` records access to sensitive documents. | **COMPLIANT** |
| **Section 8(7): Retention & Erasure** | Erase personal data once purpose is fulfilled or consent withdrawn. | • Automated 30-day lifecycle expiration on temporary voice recordings (`temp_audio/`).<br>• Location tracks purged 30 days post-trip completion. | **COMPLIANT** |
| **Section 11: Right to Information & Portability** | Right to obtain summary of personal data and export in machine-readable format. | • `GET /dpdp/export?user_id={id}` returns structured, machine-readable JSON.<br>• Single-click CSV export on Farm Diary (`GET /diary/seasons/{id}/export?format=csv`). | **COMPLIANT** |
| **Section 12: Right to Erasure / Correction** | Right to correction, completion, updating, and erasure of personal data. | • `POST /dpdp/delete-account` executes Right to Erasure.<br>• Irreversibly anonymizes phone identifiers (`deleted_{id}_{hash}`) while retaining necessary statutory audit trails. | **COMPLIANT** |
| **Section 13: Grievance Redressal** | Published Grievance Redressal Officer with response within statutory period. | • Published at `GET /dpdp/grievance` and in app footer.<br>• 72-hour acknowledgment SLA, 30-day resolution timeline. | **COMPLIANT** |
| **Section 16: Processing Children's Data** | No tracking, behavioral monitoring, or targeted advertising directed at children. | • GrowCircle serves commercial agricultural trade; zero behavioral profiling or advertising trackers. | **COMPLIANT** |

---

## 2. Statutory Grievance Redressal Officer
- **Officer Name**: Smt. Radhika Varma
- **Designation**: Data Protection Officer & Grievance Redressal Officer
- **Company**: GrowCircle Technologies Private Limited
- **Official Email**: `grievance@growcircle.in`
- **Helpline Phone**: `+91 863 294 5678`
- **Registered Address**: 4th Floor, Agriculture Innovation Hub, Ring Road, Guntur, Andhra Pradesh - 522002
- **Escalation Hierarchy**: If unresolved within 30 days, users have the right to register a complaint with the **Data Protection Board of India (DPBI)** under Section 27.
