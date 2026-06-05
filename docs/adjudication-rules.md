# Adjudication Rules

The LLM never decides claim outcomes. It only extracts structured fields. The deterministic rule engine evaluates policy conditions in this order:

1. Eligibility
2. Document Validation
3. Coverage Validation
4. Limit Validation
5. Medical Necessity
6. Fraud Validation

## Eligibility

| Rule Code | Result | Condition |
|---|---|---|
| `ELIGIBLE_MEMBER` | Pass | Treatment date is at least `waiting_period_days` after policy start |
| `WAITING_PERIOD_NOT_SERVED` | Fail | Treatment date is before the waiting period ends |
| `TREATMENT_DATE_MISSING` | Fail | Treatment date could not be extracted |

## Document Validation

| Rule Code | Result | Condition |
|---|---|---|
| `REQUIRED_DOCUMENTS_PRESENT` | Pass | Prescription and medical bill are uploaded |
| `REQUIRED_DOCUMENTS_MISSING` | Fail | Prescription or medical bill is missing |
| `REQUIRED_FIELDS_EXTRACTED` | Pass | Required extracted fields are present |
| `REQUIRED_FIELDS_MISSING` | Fail | Required extracted fields need reviewer verification |

Required extracted fields: patient name, doctor name, doctor registration number, diagnosis, treatment date, hospital name, and bill amount.

## Coverage Validation

| Rule Code | Result | Condition |
|---|---|---|
| `COVERED_OPD_SERVICE` | Pass | No configured exclusion appears in extracted service text |
| `MIXED_COVERED_AND_EXCLUDED_SERVICES` | Adjusted | Claim has both covered and excluded services, such as root canal plus teeth whitening |
| `EXCLUDED_TREATMENT` | Fail | Claim only matches excluded service categories |
| `NETWORK_PROVIDER_VALID` | Pass | Network provider rule passes |
| `OUT_OF_NETWORK_PROVIDER` | Fail | Provider violates the network rule |

Covered services and exclusions are loaded from `backend/config/opd_policy.json`.

## Limit Validation

| Rule Code | Result | Condition |
|---|---|---|
| `PER_CLAIM_LIMIT_WITHIN_LIMIT` | Pass | Bill amount is within per-claim limit |
| `PER_CLAIM_LIMIT_EXCEEDED` | Fail | Bill amount exceeds per-claim limit |
| `{CATEGORY}_SUB_LIMIT_EXCEEDED` | Adjusted | Consultation, pharmacy, diagnostics, or procedure sub-limit is exceeded |
| `ANNUAL_LIMIT_EXHAUSTED` | Fail | Annual OPD limit is exhausted |
| `ANNUAL_LIMIT_PARTIAL_AVAILABLE` | Adjusted | Only part of the annual OPD limit remains |

The assignment example "Per Claim Limit Exceeded -> Rejected" is implemented as a rejection code.

## Medical Necessity

| Rule Code | Result | Condition |
|---|---|---|
| `MEDICAL_NECESSITY_PRESENT` | Pass | Diagnosis and treatment details are present |
| `MEDICAL_NECESSITY_UNVERIFIABLE` | Fail for audit | Diagnosis is missing, so reviewer verification is required |
| `MEDICAL_NECESSITY_NOT_ESTABLISHED` | Fail | Diagnosis exists but no medicines, procedures, or tests support necessity |

## Fraud Validation

Fraud findings do not automatically reject claims. They route claims to manual review.

Checks:

- Duplicate claims
- Excessive same-day claims
- Invalid doctor registration format
- Suspicious claim frequency
- Unusual amount patterns

## Confidence Scoring

```text
score = (ocr_confidence * 0.4)
      + (extraction_completeness * 0.4)
      + (document_score * 0.2)
      - fraud_penalty
```

| Component | Weight | Calculation |
|---|---|---|
| OCR confidence | 40% | Average OCR confidence across uploaded documents |
| Extraction completeness | 40% | Extraction completeness confidence, reduced for missing required fields |
| Document score | 20% | 100 if both required documents are present, 40 otherwise |
| Fraud penalty | Penalty only | Low 3, medium 5, high 8 |

Clean prescription and bill submissions should normally score between 85 and 98.

## Final Decision Priority

```text
1. If any rejection code triggered  -> REJECTED
2. If fraud findings exist          -> MANUAL_REVIEW
3. If confidence score < 70         -> MANUAL_REVIEW
4. If required fields are missing   -> MANUAL_REVIEW
5. If approved amount <= 0          -> REJECTED
6. If any negative adjustment       -> PARTIAL
7. Otherwise                        -> APPROVED
```

Rejection codes:

- `WAITING_PERIOD_NOT_SERVED`
- `REQUIRED_DOCUMENTS_MISSING`
- `EXCLUDED_TREATMENT`
- `PER_CLAIM_LIMIT_EXCEEDED`
- `OUT_OF_NETWORK_PROVIDER`
- `MEDICAL_NECESSITY_NOT_ESTABLISHED`
- `ANNUAL_LIMIT_EXHAUSTED`

Decision explanations include:

- Decision
- Reason
- Impact
- Recommended Action
