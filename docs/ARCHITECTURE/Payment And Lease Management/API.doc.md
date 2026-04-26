# 🇨🇲 Blizton Rental Payments API Documentation

> **Version**: `v1.0`  
> **Base URL**: `https://blizton.com/api/v1`  
> **Authentication**: Bearer Token (JWT)  
> **Content-Type**: `application/json`  
> **Currency**: All amounts in **XAF** (Central African CFA Franc), integer values (no decimals)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Global Parameters](#global-parameters)
4. [Error Handling](#error-handling)
5. [Payment Plans](#payment-plans)
6. [Rental Agreements](#rental-agreements)
7. [Payment Options](#payment-options)
8. [Making Payments](#making-payments)
9. [Payment History](#payment-history)
10. [Webhooks](#webhooks)
11. [Cameroon-Specific Notes](#cameroon-specific-notes)
12. [Appendix: Data Models](#appendix-data-models)

---

## 🔍 Overview

This API enables landlords and property managers in Cameroon to define flexible payment rules for rental units, and allows tenants to pay rent via mobile money (MTN MoMo, Orange Money), bank transfer, or cash.

### Core Philosophy

- **No rigid leases**: Agreements are created on first payment and track coverage or installment progress.
- **Landlord-defined rules**: Each unit has a `PaymentPlan` that controls allowed payment amounts, frequencies, and flexibility.
- **Tenant-friendly**: Supports irregular payments, split payments, and custom amounts (when enabled).
- **Cameroon-first**: Built for MoMo rounding, XAF currency, and local payment behaviors.

### Key Concepts

| Concept             | Description                                                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **PaymentPlan**     | Rule set defined by landlord: monthly/yearly mode, allowed terms, custom amount toggle, installment structure.                            |
| **RentalAgreement** | Active contract between tenant and unit. Created on first payment. Tracks `coverage_end_date` (monthly) or `installment_status` (yearly). |
| **Installment**     | Sub-division of a yearly payment plan (e.g., 60% due March, 40% due September).                                                           |
| **Payment**         | Actual transaction record. Includes method, provider, transaction ID, and period covered.                                                 |

---

## 🔐 Authentication

All endpoints (except health checks) require authentication via **Bearer Token**.

### Obtain Token

```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response**:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Using the Token

Include in all subsequent requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Refresh

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 🌐 Global Parameters

### Query Parameters (Applicable to List Endpoints)

| Parameter   | Type    | Description                | Example                |
| ----------- | ------- | -------------------------- | ---------------------- |
| `page`      | integer | Page number for pagination | `?page=2`              |
| `page_size` | integer | Items per page (max 100)   | `?page_size=25`        |
| `is_active` | boolean | Filter by active status    | `?is_active=true`      |
| `unit_id`   | uuid    | Filter by unit             | `?unit_id=abc123...`   |
| `tenant_id` | uuid    | Filter by tenant           | `?tenant_id=def456...` |

### Headers

| Header            | Required            | Description                               |
| ----------------- | ------------------- | ----------------------------------------- |
| `Authorization`   | Yes (except health) | `Bearer <token>`                          |
| `Content-Type`    | Yes (for POST/PUT)  | `application/json`                        |
| `Accept-Language` | No                  | `en` or `fr` for localized error messages |

---

## ❌ Error Handling

All errors return standard HTTP status codes with a JSON body:

```json
{
  "error": {
    "code": "PAYMENT_STEP_MISMATCH",
    "message": "Amount must be a multiple of 10 XAF",
    "details": {
      "field": "amount",
      "received": 77777,
      "expected_step": 10
    }
  }
}
```

### Common Error Codes

| Code                          | HTTP Status | Description                                                                   |
| ----------------------------- | ----------- | ----------------------------------------------------------------------------- |
| `AUTHENTICATION_REQUIRED`     | 401         | Missing or invalid token                                                      |
| `PERMISSION_DENIED`           | 403         | User lacks required role/ownership                                            |
| `NOT_FOUND`                   | 404         | Resource (unit, tenant, plan) does not exist                                  |
| `VALIDATION_ERROR`            | 400         | Request body fails schema validation                                          |
| `PAYMENT_STEP_MISMATCH`       | 400         | Amount not multiple of `amount_step`                                          |
| `INSTALLMENT_ORDER_VIOLATION` | 400         | Tried to pay installment #2 before #1 (when `enforce_installment_order=true`) |
| `AGREEMENT_INACTIVE`          | 400         | Agreement is not active (expired/terminated)                                  |
| `OVERPAYMENT_REJECTED`        | 400         | Amount exceeds remaining balance for current period                           |
| `GATEWAY_ERROR`               | 502         | Mobile money provider returned error                                          |
| `WEBHOOK_SIGNATURE_INVALID`   | 400         | Webhook HMAC verification failed                                              |

---

## 💳 Payment Plans

Define how tenants can pay for a unit. Plans are reusable across units.

### Create Payment Plan

```http
POST /api/v1/payment-plans/
```

#### Request Body

| Field                       | Type      | Required          | Description                                                                | Constraints             |
| --------------------------- | --------- | ----------------- | -------------------------------------------------------------------------- | ----------------------- |
| `name`                      | string    | Yes               | Human-readable plan name                                                   | Max 100 chars           |
| `mode`                      | string    | Yes               | `"monthly"` or `"yearly"`                                                  | —                       |
| `allowed_monthly_terms`     | integer[] | No (monthly only) | Allowed month multiples (e.g., `[1,3,6]`). Empty = any up to `max_months`. | Values 1–12             |
| `max_months`                | integer   | No (monthly only) | Maximum months payable at once                                             | Default: `12`, Min: `1` |
| `show_full_payment_option`  | boolean   | No (yearly only)  | Show "Pay full year" button                                                | Default: `true`         |
| `enforce_installment_order` | boolean   | No (yearly only)  | Require installments paid in sequence                                      | Default: `true`         |
| `allow_custom_amount`       | boolean   | No                | Allow tenant to enter any amount (subject to `amount_step`)                | Default: `false`        |
| `amount_step`               | integer   | No                | Payment amounts must be multiples of this (XAF)                            | Default: `10`, Min: `1` |
| `late_fee_rules`            | object    | No                | Late fee configuration                                                     | See below               |
| `is_active`                 | boolean   | No                | Enable/disable plan                                                        | Default: `true`         |

**`late_fee_rules` schema**:

```json
{
  "grace_days": 5,
  "percentage": 5.0
}
```

#### Example: Monthly Flexible Plan

```json
{
  "name": "Monthly Flexible",
  "mode": "monthly",
  "allowed_monthly_terms": [],
  "max_months": 12,
  "allow_custom_amount": true,
  "amount_step": 10,
  "late_fee_rules": { "grace_days": 5, "percentage": 5.0 },
  "is_active": true
}
```

#### Example: Yearly 60/40 Installment Plan

```json
{
  "name": "Yearly 60/40 with due dates",
  "mode": "yearly",
  "show_full_payment_option": true,
  "enforce_installment_order": true,
  "allow_custom_amount": false,
  "amount_step": 1000,
  "is_active": true
}
```

**Response** (201 Created):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Monthly Flexible",
  "mode": "monthly",
  "allowed_monthly_terms": [],
  "max_months": 12,
  "allow_custom_amount": true,
  "amount_step": 10,
  "late_fee_rules": { "grace_days": 5, "percentage": 5.0 },
  "is_active": true,
  "created_at": "2026-04-23T10:30:00Z",
  "updated_at": "2026-04-23T10:30:00Z"
}
```

---

### Add Installment to Yearly Plan

```http
POST /api/v1/payment-plans/{plan_id}/installments/
```

#### Request Body

| Field         | Type    | Required | Description                       | Constraints      |
| ------------- | ------- | -------- | --------------------------------- | ---------------- |
| `percent`     | decimal | Yes      | Percentage of yearly rent (0–100) | 2 decimal places |
| `due_date`    | date    | No       | Suggested due date (YYYY-MM-DD)   | —                |
| `order_index` | integer | Yes      | Sequence order (0-based)          | Unique per plan  |

#### Example

```json
{
  "percent": 60.0,
  "due_date": "2026-03-01",
  "order_index": 0
}
```

**Response** (201 Created):

```json
{
  "id": "inst-uuid-here",
  "payment_plan": "550e8400-e29b-41d4-a716-446655440000",
  "percent": 60.0,
  "due_date": "2026-03-01",
  "order_index": 0,
  "amount_xaf": 180000
}
```

> 💡 `amount_xaf` is calculated server-side as `(unit.yearly_rent * percent / 100)`.

---

### List Payment Plans

```http
GET /api/v1/payment-plans/
```

**Query Parameters**: `is_active`, `mode`, `search`

**Response** (200 OK):

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Monthly Flexible",
      "mode": "monthly",
      "is_active": true,
      "created_at": "2026-04-23T10:30:00Z"
    }
  ]
}
```

---

### Retrieve Payment Plan

```http
GET /api/v1/payment-plans/{plan_id}/
```

**Response**: Full plan object including installments (if yearly).

---

### Update/Delete Payment Plan

```http
PATCH /api/v1/payment-plans/{plan_id}/   # Partial update
DELETE /api/v1/payment-plans/{plan_id}/  # Soft delete (sets is_active=false)
```

> ⚠️ **Important**: Changes to a `PaymentPlan` do **not** affect existing `RentalAgreement`s. Agreements snapshot the plan at creation time.

---

## 📄 Rental Agreements

An agreement is created on the **first successful payment**. It links a tenant, unit, and payment plan.

### Create Rental Agreement

```http
POST /api/v1/agreements/
```

#### Request Body

| Field             | Type | Required | Description                         |
| ----------------- | ---- | -------- | ----------------------------------- |
| `unit_id`         | uuid | Yes      | Target unit                         |
| `tenant_id`       | uuid | Yes      | Tenant (must have verified profile) |
| `payment_plan_id` | uuid | Yes      | Plan to apply                       |

#### Example

```json
{
  "unit_id": "unit-uuid-here",
  "tenant_id": "tenant-uuid-here",
  "payment_plan_id": "plan-uuid-here"
}
```

**Response** (201 Created):

```json
{
  "id": "agr-uuid-here",
  "unit": {
    "id": "unit-uuid-here",
    "name": "Studio A",
    "monthly_rent": 150000,
    "yearly_rent": 1800000
  },
  "tenant": {
    "id": "tenant-uuid-here",
    "name": "Jean Moukam",
    "phone": "+237677123456"
  },
  "payment_plan": {
    "id": "plan-uuid-here",
    "name": "Monthly Flexible",
    "mode": "monthly"
  },
  "start_date": "2026-04-23",
  "coverage_end_date": "2026-04-23",
  "installment_status": {},
  "is_active": true,
  "created_at": "2026-04-23T10:35:00Z"
}
```

> 🔄 **Monthly mode**: `coverage_end_date` starts at `start_date` and extends with each payment.  
> 🔄 **Yearly mode**: `installment_status` tracks progress: `{"0": "pending", "1": "pending"}`.

---

### Retrieve Agreement

```http
GET /api/v1/agreements/{agreement_id}/
```

**Response**: Full agreement with payment history summary.

```json
{
  "id": "agr-uuid-here",
  "unit": { ... },
  "tenant": { ... },
  "payment_plan": { ... },
  "start_date": "2026-04-23",
  "coverage_end_date": "2026-07-23",
  "installment_status": {
    "0": { "percent": 60, "paid": 180000, "status": "completed" },
    "1": { "percent": 40, "paid": 0, "status": "pending" }
  },
  "total_paid": 180000,
  "remaining_balance": 120000,
  "next_due_date": "2026-09-01",
  "is_active": true,
  "payments_count": 1,
  "created_at": "2026-04-23T10:35:00Z"
}
```

---

### List Agreements

```http
GET /api/v1/agreements/
```

**Query Parameters**: `unit_id`, `tenant_id`, `is_active`, `status`

**Response**: Paginated list of agreements.

---

### Terminate Agreement (Landlord Only)

```http
POST /api/v1/agreements/{agreement_id}/refund/
```

#### Request Body

```json
{
  "reason": "Tenant vacated early",
  "refund_amount": 50000
}
```

**Response**:

```json
{
  "message": "Agreement terminated. Refund of 50,000 XAF initiated.",
  "agreement_status": "terminated",
  "refund_transaction_id": "REF-123456"
}
```

> 💡 Refunds are processed via the original payment method where possible.

---

## 🧮 Payment Options

Get the list of valid payment amounts/options for an active agreement.

```http
GET /api/v1/agreements/{agreement_id}/options/
```

**Response** (200 OK):

### Monthly Mode Example

```json
[
  {
    "type": "monthly",
    "label": "Pay 1 month (150,000 XAF)",
    "amount": "150000",
    "months_covered": 1
  },
  {
    "type": "monthly",
    "label": "Pay 3 months (450,000 XAF)",
    "amount": "450000",
    "months_covered": 3
  },
  {
    "type": "monthly",
    "label": "Pay 6 months (900,000 XAF)",
    "amount": "900000",
    "months_covered": 6
  },
  {
    "type": "custom",
    "label": "Other amount",
    "min_amount": "10",
    "step": "10",
    "max_amount": "1800000"
  }
]
```

### Yearly Mode Example (60/40 Installments)

```json
[
  {
    "type": "installment",
    "label": "First installment (60% – 180,000 XAF)",
    "amount": "180000",
    "installment_index": 0,
    "due_date": "2026-03-01",
    "remaining": "180000"
  },
  {
    "type": "installment",
    "label": "Second installment (40% – 120,000 XAF)",
    "amount": "120000",
    "installment_index": 1,
    "due_date": "2026-09-01",
    "remaining": "120000",
    "requires_previous": true
  },
  {
    "type": "full_year",
    "label": "Pay full year (300,000 XAF)",
    "amount": "300000",
    "saves": "0"
  }
]
```

> 🔑 `requires_previous: true` indicates this option is locked until prior installments are paid (when `enforce_installment_order=true`).

---

## 💸 Making Payments

Process a payment against an active agreement.

```http
POST /api/v1/agreements/{agreement_id}/pay/
```

### Request Body

| Field            | Type    | Required    | Description                                                  | Constraints                               |
| ---------------- | ------- | ----------- | ------------------------------------------------------------ | ----------------------------------------- |
| `amount`         | integer | Yes         | Payment amount in XAF                                        | Must match an option or be allowed custom |
| `payment_method` | string  | Yes         | `mtn_momo`, `orange_money`, `bank_transfer`, `cash`, `other` | —                                         |
| `phone_number`   | string  | Conditional | Required for mobile money                                    | Cameroon format: `+2376XXXXXXXX`          |
| `provider`       | string  | Conditional | `MTN`, `ORANGE`, etc. (for mobile money)                     | —                                         |
| `bank_name`      | string  | Conditional | Required for `bank_transfer`                                 | —                                         |
| `check_number`   | string  | Optional    | For cash/check payments                                      | —                                         |
| `notes`          | string  | Optional    | Free-text notes                                              | Max 500 chars                             |

### Example: MTN MoMo Payment

```json
{
  "amount": 150000,
  "payment_method": "mtn_momo",
  "phone_number": "+237677123456",
  "provider": "MTN",
  "notes": "April rent payment"
}
```

### Example: Cash Payment

```json
{
  "amount": 75000,
  "payment_method": "cash",
  "notes": "Partial payment – balance next week"
}
```

### Response (201 Created)

```json
{
  "id": "pay-uuid-here",
  "agreement": "agr-uuid-here",
  "amount": 150000,
  "months_covered": 1.0,
  "period_start": "2026-04-23",
  "period_end": "2026-05-23",
  "payment_date": "2026-04-23",
  "payment_method": "mtn_momo",
  "status": "completed",
  "transaction_id": "TXN-MOMO-99887766",
  "mobile_provider": "MTN Cameroon",
  "mobile_phone": "+237677123456",
  "mobile_reference": "REF-556677",
  "gateway_response": {
    "code": 200,
    "message": "Success",
    "network_code": "0"
  },
  "created_at": "2026-04-23T10:40:00Z"
}
```

### Payment Status Flow

```mermaid
stateDiagram-v2
    [*] --> pending : Payment initiated
    pending --> completed : Gateway confirms
    pending --> failed : Gateway rejects / timeout
    completed --> refunded : Landlord issues refund
    failed --> [*]
```

> ⚠️ **Idempotency**: The API uses `transaction_id` + `agreement_id` to prevent duplicate processing. Retries with the same `transaction_id` return the original response.

---

## 📜 Payment History

### List Payments for Agreement

```http
GET /api/v1/payments/?agreement={agreement_id}
```

**Query Parameters**: `status`, `payment_method`, `date_from`, `date_to`

**Response**:

```json
{
  "count": 3,
  "results": [
    {
      "id": "pay-uuid-1",
      "amount": 150000,
      "payment_method": "mtn_momo",
      "status": "completed",
      "period_start": "2026-04-23",
      "period_end": "2026-05-23",
      "payment_date": "2026-04-23",
      "transaction_id": "TXN-MOMO-99887766"
    }
  ]
}
```

### Retrieve Single Payment

```http
GET /api/v1/payments/{payment_id}/
```

---

## 🔔 Webhooks

Receive real-time payment confirmations from mobile money providers.

### Endpoint

```http
POST /api/v1/webhooks/payment-gateway/
```

### Headers

| Header                | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| `X-Gateway-Signature` | HMAC-SHA256 signature of request body (secret shared out-of-band)   |
| `X-Gateway-Event`     | Event type: `payment.success`, `payment.failed`, `payment.refunded` |

### Payload Example (MTN MoMo)

```json
{
  "event": "payment.success",
  "data": {
    "transaction_id": "TXN-MOMO-99887766",
    "reference": "REF-556677",
    "amount": 150000,
    "currency": "XAF",
    "payer_phone": "+237677123456",
    "timestamp": "2026-04-23T10:40:15Z",
    "metadata": {
      "agreement_id": "agr-uuid-here"
    }
  }
}
```

### Response Requirements

- Return `200 OK` within 5 seconds to acknowledge receipt.
- Processing happens asynchronously; failures are retried with exponential backoff.

### Signature Verification

Your server must:

1. Read raw request body (do not parse first).
2. Compute `HMAC-SHA256(body, your_webhook_secret)`.
3. Compare with `X-Gateway-Signature` header (constant-time comparison).
4. Reject with `400` if mismatch.

---

## 🇨🇲 Cameroon-Specific Notes

### Mobile Money Providers

| Provider     | Code            | Phone Prefix         | Notes                 |
| ------------ | --------------- | -------------------- | --------------------- |
| MTN MoMo     | `mtn_momo`      | `+23767X`, `+23765X` | Most widely used      |
| Orange Money | `orange_money`  | `+23769X`, `+23768X` | Strong in rural areas |
| Nexttel      | `nexttel_money` | `+23766X`            | Emerging              |

### Phone Number Format

- Always store in **E.164 format**: `+2376XXXXXXXX`
- Validation regex: `^\+2376[5-9]\d{7}$`

### Currency Handling

- All amounts are **integers in XAF** (no decimals).
- `amount_step` prevents awkward values (e.g., 10 XAF step avoids 77,777 XAF).

### Late Fees

- Configured per `PaymentPlan` via `late_fee_rules`.
- Applied automatically by daily cron job (not real-time).
- Generates a separate `Payment` record with `type: "fee"`.

### Language Support

- All user-facing strings support `en`/`fr` via Django's `gettext`.
- Set `Accept-Language: fr` header to receive French error messages.

---

## 📎 Appendix: Data Models

### PaymentPlan

```json
{
  "id": "uuid",
  "name": "string",
  "mode": "monthly|yearly",
  "allowed_monthly_terms": [1, 3, 6],
  "max_months": 12,
  "show_full_payment_option": true,
  "enforce_installment_order": true,
  "allow_custom_amount": false,
  "amount_step": 10,
  "late_fee_rules": { "grace_days": 5, "percentage": 5.0 },
  "is_active": true,
  "created_at": "2026-04-23T10:30:00Z",
  "updated_at": "2026-04-23T10:30:00Z"
}
```

### Installment

```json
{
  "id": "uuid",
  "payment_plan": "uuid",
  "percent": 60.0,
  "due_date": "2026-03-01",
  "order_index": 0,
  "amount_xaf": 180000
}
```

### RentalAgreement

```json
{
  "id": "uuid",
  "unit": {
    "id": "uuid",
    "name": "Studio A",
    "monthly_rent": 150000,
    "yearly_rent": 1800000
  },
  "tenant": { "id": "uuid", "name": "Jean Moukam", "phone": "+237677123456" },
  "payment_plan": {
    "id": "uuid",
    "name": "Monthly Flexible",
    "mode": "monthly"
  },
  "start_date": "2026-04-23",
  "coverage_end_date": "2026-07-23",
  "installment_status": {
    "0": { "percent": 60, "paid": 180000, "status": "completed" }
  },
  "total_paid": 180000,
  "remaining_balance": 120000,
  "next_due_date": "2026-09-01",
  "is_active": true,
  "created_at": "2026-04-23T10:35:00Z"
}
```

### Payment

```json
{
  "id": "uuid",
  "agreement": "uuid",
  "amount": 150000,
  "months_covered": 1.0,
  "period_start": "2026-04-23",
  "period_end": "2026-05-23",
  "payment_date": "2026-04-23",
  "payment_method": "mtn_momo",
  "status": "completed",
  "transaction_id": "TXN-MOMO-99887766",
  "mobile_provider": "MTN Cameroon",
  "mobile_phone": "+237677123456",
  "mobile_reference": "REF-556677",
  "gateway_response": { "code": 200, "message": "Success" },
  "created_at": "2026-04-23T10:40:00Z"
}
```

---

## 🔄 State Machine: Agreement Lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft : Agreement created (first payment pending)
    draft --> active : Payment completed
    active --> active : Additional payments extend coverage
    active --> expired : coverage_end_date passed OR all installments paid
    expired --> active : Tenant makes new payment
    active --> terminated : Landlord issues refund
    terminated --> [*]
```

---

## 🧪 Testing Tips

1. **Use Postman/Insomnia**: Import the collection for quick testing.
2. **Mock Mobile Money**: Use the `dummy_payment_processor` in development (bypasses real gateways).
3. **Time Travel**: Use `freezegun` in tests to simulate coverage expiry.
4. **Idempotency Testing**: Retry the same `transaction_id` – should return original response, not create duplicate.

---

## 📞 Support

- **API Issues**: `api-support@yourdomain.com`
- **Payment Gateway Issues**: Contact provider directly (MTN: `api-support@mtn.cm`, Orange: `developer@orangecameroon.com`)
- **Documentation Updates**: This doc is versioned; check `GET /api/v1/docs/version` for latest.

---

> ✨ **Pro Tip**: Always call `GET /agreements/{id}/options/` before presenting payment buttons to tenants. This ensures your UI reflects the landlord's current rules and the tenant's payment history.

_Documentation: 2026-04-23_  
_Last updated: v1.0_
