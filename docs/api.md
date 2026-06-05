# API Documentation

Base URL: `http://localhost:8000`

All authenticated endpoints require an `Authorization: Bearer <token>` header. Tokens are obtained from the login endpoint.

---

## Authentication

### `POST /auth/register`

Create a new user or admin account.

**Request:**

```json
{
  "email": "member@plum.demo",
  "name": "Demo Member",
  "password": "member123",
  "role": "USER"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `email` | string | Yes | Must be a valid email address |
| `name` | string | Yes | Display name |
| `password` | string | Yes | Plaintext, hashed server-side |
| `role` | string | No | `USER` (default) or `ADMIN` |

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "USER"
}
```

**Error (409):**

```json
{
  "detail": "User already exists"
}
```

---

### `POST /auth/login`

Authenticate and receive a JWT bearer token.

**Request:**

```json
{
  "email": "admin@plum.demo",
  "password": "admin123"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "ADMIN"
}
```

**Error (401):**

```json
{
  "detail": "Invalid email or password"
}
```

---

## Claims

### `POST /claims`

Submit a new OPD claim with document uploads. This is a multipart/form-data request.

**Request (multipart/form-data):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `prescription` | file | Yes | PDF, PNG, JPG, or JPEG |
| `medical_bill` | file | Yes | PDF, PNG, JPG, or JPEG |
| `diagnostic_report` | file | No | PDF, PNG, JPG, or JPEG |

**Response (200):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_name": "Rajesh Kumar",
  "status": "APPROVED",
  "claimed_amount": 1850.0,
  "approved_amount": 1850.0,
  "confidence_score": 87.5,
  "created_at": "2026-06-04T10:30:00Z",
  "documents": [
    {
      "id": "doc-uuid-1",
      "type": "PRESCRIPTION",
      "filename": "prescription.pdf",
      "ocr_confidence": 91.2
    },
    {
      "id": "doc-uuid-2",
      "type": "MEDICAL_BILL",
      "filename": "bill.jpg",
      "ocr_confidence": 88.7
    }
  ],
  "extracted_information": {
    "patient_name": "Rajesh Kumar",
    "patient_age": 34,
    "doctor_name": "Dr. Priya Sharma",
    "doctor_registration_number": "MH/12345/2019",
    "diagnosis": "Upper respiratory tract infection",
    "medicines": ["Amoxicillin 500mg", "Paracetamol 650mg"],
    "procedures": [],
    "tests": ["CBC"],
    "treatment_date": "2026-05-28",
    "hospital_name": "CityCare Clinic",
    "bill_amount": 1850.0,
    "consultation_amount": 500.0,
    "pharmacy_amount": 850.0,
    "diagnostic_amount": 500.0
  },
  "policy_evaluation": [
    {
      "rule": "ELIGIBLE_MEMBER",
      "decision": "APPROVED",
      "explanation": "Member is eligible for OPD adjudication on the treatment date."
    },
    {
      "rule": "REQUIRED_DOCUMENTS_PRESENT",
      "decision": "APPROVED",
      "explanation": "Prescription and medical bill were uploaded."
    },
    {
      "rule": "COVERED_OPD_SERVICE",
      "decision": "APPROVED",
      "explanation": "No configured OPD exclusion matched the extracted diagnosis."
    },
    {
      "rule": "NETWORK_PROVIDER_VALID",
      "decision": "APPROVED",
      "explanation": "Provider network rule passed."
    },
    {
      "rule": "PER_CLAIM_LIMIT_WITHIN_LIMIT",
      "decision": "APPROVED",
      "explanation": "Claim amount is within the configured per-claim limit."
    },
    {
      "rule": "MEDICAL_NECESSITY_PRESENT",
      "decision": "APPROVED",
      "explanation": "Diagnosis and treatment details support OPD medical necessity."
    },
    {
      "rule": "NO_FRAUD_SIGNALS",
      "decision": "APPROVED",
      "explanation": "No configured fraud signal was detected."
    }
  ],
  "fraud_signals": [],
  "decision_explanation": "Decision: Approved. Triggered Rule: ALL_POLICY_RULES_PASSED. Explanation: Claim passed eligibility, document, coverage, limit, medical necessity and fraud checks. Approved amount is Rs 1850."
}
```

**Error (400):**

```json
{
  "detail": "File type not allowed. Accepted: PDF, PNG, JPG, JPEG."
}
```

---

### `GET /claims`

List all claims for the authenticated user, ordered by most recent first.

**Response (200):**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "patient_name": "Rajesh Kumar",
    "status": "APPROVED",
    "claimed_amount": 1850.0,
    "approved_amount": 1850.0,
    "confidence_score": 87.5,
    "created_at": "2026-06-04T10:30:00Z"
  }
]
```

---

### `GET /claims/{claim_id}`

Get full detail for a specific claim owned by the authenticated user.

**Response (200):** Same structure as the `POST /claims` response.

**Error (404):**

```json
{
  "detail": "Claim not found"
}
```

---

### `GET /claims/{claim_id}/processing`

Get the processing stage status for a claim. Used by the frontend to show a progress indicator.

**Response (200):**

```json
[
  { "name": "Files Uploaded", "status": "Completed", "progress": 100, "confidence_score": null },
  { "name": "OCR Processing", "status": "Completed", "progress": 100, "confidence_score": null },
  { "name": "Information Extraction", "status": "Completed", "progress": 100, "confidence_score": null },
  { "name": "Policy Validation", "status": "Completed", "progress": 100, "confidence_score": null },
  { "name": "Fraud Detection", "status": "Completed", "progress": 100, "confidence_score": null },
  { "name": "Decision Generation", "status": "Completed", "progress": 100, "confidence_score": 87.5 }
]
```

---

## Admin

All admin endpoints require the authenticated user to have `role: ADMIN`.

### `GET /admin/dashboard`

Returns aggregate metrics for the admin dashboard.

**Response (200):**

```json
{
  "total_claims": 42,
  "approved": 25,
  "rejected": 8,
  "partial": 5,
  "partial_approval": 5,
  "manual_review": 4,
  "decision_distribution": {
    "SUBMITTED": 0,
    "PROCESSING": 0,
    "APPROVED": 25,
    "REJECTED": 8,
    "PARTIAL": 5,
    "MANUAL_REVIEW": 4
  }
}
```

---

### `GET /admin/claims`

List all claims across all users, ordered by most recent first.

**Response (200):**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "patient_name": "Rajesh Kumar",
    "status": "APPROVED",
    "claimed_amount": 1850.0,
    "approved_amount": 1850.0,
    "confidence_score": 87.5,
    "created_at": "2026-06-04T10:30:00Z"
  }
]
```

---

### `GET /admin/manual-reviews`

List all claims that have been flagged for manual review.

**Response (200):**

```json
[
  {
    "review_id": "rev-uuid-1",
    "claim_id": "claim-uuid-1",
    "reason": "Fraud signals were detected and the claim requires manual review.",
    "confidence_score": 62.4,
    "fraud_signals": [
      {
        "code": "DUPLICATE_CLAIM",
        "severity": "HIGH",
        "description": "A claim with the same patient, treatment date and amount already exists."
      }
    ],
    "override_decision": null
  }
]
```

---

### `POST /admin/manual-reviews/{review_id}/override`

Override the decision for a manually reviewed claim. Writes an audit log entry.

**Request:**

```json
{
  "decision": "APPROVED",
  "reason": "Reviewer verified doctor registration and prescription clarity."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `decision` | string | Yes | One of `APPROVED`, `REJECTED`, `PARTIAL`, `MANUAL_REVIEW` |
| `reason` | string | Yes | Reviewer's justification for the override |

**Response (200):**

```json
{
  "status": "saved",
  "claim_id": "claim-uuid-1",
  "decision": "APPROVED"
}
```

**Error (404):**

```json
{
  "detail": "Manual review not found"
}
```

---

## Health Check

### `GET /health`

**Response (200):**

```json
{
  "status": "ok"
}
```
