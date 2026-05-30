# 🔬 Payment System — Critical Audit & Way Forward

> **Status**: Documentation only — no code changes have been made.  
> **Scope**: `apps/payments/`, `apps/properties/PaymentConfiguration`, `apps/core/PlatformSettings`, the SmobilPay gateway integration, and every place these touch each other.  
> **Goal**: Enumerate every production-blocking, integrity, and design issue in the current payment flow; describe what the connections between transaction fees / subscriptions / per-payer fee config actually do today (and where they break); and propose a concrete way forward, including a manual-payment recording feature for landlords.

---

## 0. TL;DR

The payment system is **architecturally promising but operationally unsafe to run in production today**. The most serious problems are:

1. **No webhook endpoint exists** — `SMOBIL_PAY_WEBHOOK_URL` is configured but never consumed; verification is polling-only and signature verification is a `# TODO: return True` stub.
2. **Tenants can be charged twice** — no idempotency on `make_payment`, common on low-bandwidth retries.
3. **A single payment can extend coverage multiple times** — no `select_for_update`, no DB constraint on concurrent `verify_and_complete` calls.
4. **Subscription billing is theatre** — assigning a plan flips `status='active'` for 30 days **without taking any money**. There is no scheduler that expires subscriptions and no link between the `SubscriptionPlan` and any `Payment`. Anyone gets Pro/Business indefinitely for free.
5. **`pricing_model='subscription'` waives 100% of platform + gateway fees** without checking if the landlord's subscription is actually active or paid.
6. **The `split` fee-payer choice is silently broken** — coded as an `else` branch, so `split` behaves identically to `landlord`.
7. **No manual landlord payment recording** — cash, bank transfer, and "other" are model choices but unreachable from the API. In Cameroon, much rent is paid in cash; the platform's record is permanently incomplete.
8. **Co-ownership is not paid out** — `PropertyOwnership.percentage` exists but is never used to split funds.
9. **Multi-month rent math is wrong** — fee multiplication does not equal multiplied fee due to caps and fixed fees.
10. **30-day "months" drift** the lease end date by ~5–6 days per year.

A concrete remediation roadmap is in §6.

---

## 1. The current model — what each thing is supposed to do

### 1.1 Three overlapping fee sources

| Component | Owner | Per | Used at |
|-----------|-------|-----|---------|
| **`PlatformSettings`** (singleton, `apps/core/models.py`) | Codebuff | global | `RentCalculator.calculate()` |
| **`PaymentConfiguration`** (`apps/properties/models.py`) | per `Property` | property-scope | `RentCalculator` (who pays, gateway methods, pricing model) |
| **`SubscriptionPlan`** (`apps/payments/models.py`) | per `Owner` | landlord-scope | `properties/services.py` — quota gating only |

**Current data flow on a tenant payment:**

```
Tenant → MakePaymentView 
        → RentalAgreementService.make_payment 
        → PaymentManager.initiate_payment
            ├─ RentCalculator(net_rent, PaymentConfiguration, owner_payout_method)
            │    └─ uses PlatformSettings for the actual percentages/caps
            ├─ SmobilPay quote + collection
            └─ Payment row created with status='pending'

Later: client polls VerifyPaymentView
        → PaymentManager.verify_and_complete
            ├─ Re-runs RentCalculator (recomputes fees from current settings ⚠️)
            ├─ Updates RentalAgreement coverage / installments
            └─ Marks Payment 'completed'
```

### 1.2 What the connections really are

```
PlatformSettings              ←── (rates only) ──── RentCalculator
   ▲                                                   ▲
   │                                                   │
   └ admin tweaks here apply globally                  │
                                                       │
PaymentConfiguration ── (who-pays / gateway methods / pricing_model) ──┘
   ▲
   │
Property ── 1:1 ── PaymentConfiguration

Owner ── FK ──→ SubscriptionPlan      (used only to gate property/unit creation)
                       ▲
                       └── Never charges the landlord. No Payment row, no Celery task.
```

The only **logical** connection between subscription and per-transaction fees today is the `pricing_model='subscription'` flag on `PaymentConfiguration`, which **waives all per-transaction fees**. But that flag (a) doesn't check the landlord's `subscription_status`, (b) doesn't reference `Owner.subscription_plan`, (c) doesn't enforce the subscription is paid for. So in production, a landlord can flip every property to `subscription` and pay zero fees indefinitely.

---

## 2. Severity 1 — Money-loss / data-corruption blockers

### 2.1 No webhook endpoint at all (PROD BLOCKER)
- Settings define `SMOBIL_PAY_WEBHOOK_URL`, `SMOBIL_PAY_WEBHOOK_SECRET`, and a staging variant. **No URL or view consumes it.**
- `SmobilPayGateway.process_webhook` is a stub returning `"use_webhook_endpoint"`.
- `_verify_webhook_signature` is a literal `# TODO: ... return True` — even if a route existed, **any unauthenticated POST could mark any payment paid**.
- Verification today is **polling-only** via `/verify/<payment_id>/`. A tenant who closes the app after their MoMo prompt will leave the platform unaware that SmobilPay cleared the collection → tenant remains in arrears, money trapped in escrow.

> **Real-world frequency**: very high in low-bandwidth Cameroon. This is the primary reason rent will silently desync from reality.

### 2.2 Race condition / double-coverage in `verify_and_complete`
- The only guard is `if payment.status != "pending": return`.
- No `select_for_update()` on the `Payment` row, no advisory lock on the `RentalAgreement`.
- Two concurrent verifies (tenant poll + landlord poll, or future webhook + poll) both read `status='pending'`, both call `_update_agreement` → `coverage_end_date` extended by N months **twice** for one payment. For yearly mode, `installment_status["total_paid"]` doubles, installments marked paid twice.

### 2.3 No idempotency on `make_payment`
- A network retry from the tenant's mobile creates a **second SmobilPay collection** → tenant gets **two MoMo prompts and can be debited twice**.
- No `Idempotency-Key` header support, no client-token deduplication, no DB constraint preventing two `pending` payments per `agreement`.

### 2.4 Silent fee-absorption fallback
```python
# payment_manager.py initiate_payment
if amount != expected_total:
    if amount == net_rent:
        pass            # ← silently accepts net rent without fees
    else:
        raise ValueError(...)
```
A tenant who pays only the **net rent** (no fees) is accepted. Combined with `_recalculate_landlord_net`, the landlord may receive less than the agreed rent **and** the platform/gateway fees vanish. With `allow_custom_amount=True`, a tenant could pay 1 XAF and have `coverage_end_date` extended by `months_covered` months — **a full month for 1 XAF**.

### 2.5 30-day months drift
- `_update_monthly_coverage` uses `days_covered = months * 30`. Over a 12-month lease, the tenant **loses ~5–6 calendar days**. Should use `dateutil.relativedelta(months=+N)`.

### 2.6 Fee re-computation between initiate and verify
- `fee_breakdown` is computed in `initiate_payment` (snapshot stored on `Payment`), then **recomputed and overwritten** in `verify_and_complete` from current `PlatformSettings`.
- An admin changing platform fees between phases will retroactively re-price an in-flight payment → **non-deterministic landlord payouts**.
- The snapshot already exists — verify must read from it, never recompute.

### 2.7 Empty `gateway_reference` is not blocked
- `_execute_gateway` returns `gateway_reference=execution.get("gateway_transaction_id")`. If the gateway response is malformed, this is `None`/`""`. The `Payment` is still saved as `pending` and verification will never succeed → **money may have left the customer with no platform record**.
- No DB unique constraint on `gateway_reference` either; collisions are also possible.

### 2.8 No amount reconciliation against gateway
- SmobilPay returns `priceLocalCur` and `amountLocalCur`. **Neither is compared** to `payment.amount` in `verify_and_complete`. A spoofed/altered "success" with a different amount is accepted.

### 2.9 Multi-month months-inference is wrong (narrow but real)
When the client omits `months` and only sends `amount`, `initiate_payment` infers months as:
```python
single_month_total = tenant_total_for(monthly_rent)   # one month with fees
months = round(amount / single_month_total)           # ← arithmetic error here
```
But `tenant_total(monthly_rent × N)` ≠ `N × tenant_total(monthly_rent)` because `platform_fee_cap` applies once to the multiplied amount and `fixed_extra_fee` is added once, not per month.

The explicit-`months` path *is* consistent (both `AvailablePaymentOptionsView` and validation call `tenant_total_for(monthly_rent × months)`). But any client that only posts an amount — or any future feature that lets tenants pay an arbitrary amount and infers months — will silently miscount or be rejected. **Recommendation: make `months` required** for monthly mode and remove the inference fallback.

### 2.10 `period_start = period_end = today` placeholders are misleading
- `Payment.period_start` / `period_end` are set to today on initiate and only overwritten on completion.
- Any pending-but-never-completed payment carries a same-day range forever. This is not currently aggregated by `reports/services/financial_service.py` (which uses `fee_breakdown` JSON keys and `net_landlord_amount`), but it **will** poison any future period-based report and shows up as nonsense in the admin and Payment list endpoints today. Either set the fields nullable or compute them at completion only.

---

## 3. Severity 2 — Trust / integrity / business-logic holes

### 3.1 Subscription is a UI label — completely unenforced
- `OwnerService.assign_subscription` immediately sets `status='active'` and `end_date = today + 30 days` **without any payment**. No link from `SubscriptionPlan` to a `Payment` of any kind.
- The platform has **no mechanism to actually charge landlords for their subscription**. Subscription revenue is theoretical.
- `monthly_subscription_fee` field used to exist on `PaymentConfiguration` but was removed in migration `0020` and **not replaced**.

### 3.2 No subscription expiry job
- `subscription_end_date` exists, `subscription_status` has `expired`/`past_due`, but no Celery beat task transitions states.
- `app/pms/celery.py` has only `autodiscover_tasks()` — **no `CELERY_BEAT_SCHEDULE` is defined anywhere**. README says "(Optional) Start beat scheduler".
- Trial/active subscriptions live forever, regardless of dates.

### 3.3 `pricing_model='subscription'` = free fee waiver
- `RentCalculator` short-circuits: if `pricing_model == 'subscription'`, returns `platform_fee=0, gateway_fee=0`.
- It **does not verify** the landlord's subscription is active or paid. Any landlord can flip their property to `subscription` and pay zero platform fees forever.

### 3.4 `split` payer is silently broken
```python
# rent_calculator.py
if self.config.platform_fee_payer == "tenant":
    tenant_total += platform_fee
else:                                       # ← matches "landlord" AND "split"
    landlord_net -= platform_fee
```
Same for `gateway_fee_payer`. **No 50/50 splitting is implemented**, despite the model and admin offering the choice.

### 3.5 Co-ownership payouts are broken
- `Property.get_payout_owner()` returns the primary owner (or first). The `PropertyOwnership.percentage` field is **never used to distribute funds**. Joint owners get 0%.
- Reports also use a single owner per property → false aggregations for properties with shared ownership.

### 3.6 Two FKs to `SubscriptionPlan` — one of them is dead
- `Owner.subscription_plan` (used to gate quotas).
- `PaymentConfiguration.subscription_plan` (**never read anywhere** — dead column).

This dual reference creates persistent confusion about which plan governs which property, and is a footgun for future contributors.

### 3.7 `is_outstanding` logic inversion in `terminate_agreement`
- `is_outstanding` becomes `True` when `coverage_end_date >= today` — i.e. when the tenant has **prepaid future coverage** (the *good* state).
- It should mean "the tenant owes money". As coded:
  - A tenant who prepaid 6 months → cannot be terminated easily (treated as "outstanding").
  - A tenant whose coverage expired yesterday and **owes back rent** → not outstanding → **landlord can force-terminate without mutual agreement**. Tenants in arrears can be evicted unilaterally.

### 3.8 Two `RentalAgreementDetailView` classes shadow each other
- `views.py` defines `RentalAgreementDetailView` once with a proper `service.get_agreement_for_user` permission flow, then **redefines the same class name** later with a weaker permission path.
- Python keeps only the second definition. Both `/agreements/<id>/` and `/agreements/<id>/detail/` resolve to the second class. **The first one — and its careful permission logic — is dead code.**

### 3.9 `STAGING_MODE or DEBUG` collapses correctness checks
- `PaymentManager.is_staging = STAGING_MODE or DEBUG`. If `DEBUG=True` ever slips into prod (very common accident), missing `PaymentConfiguration` is silently auto-created mid-transaction and guards are relaxed.

### 3.10 No DB constraints to prevent multiple pending payments per agreement
- A tenant can stack N concurrent `pending` Payment rows on the same agreement, each holding a different SmobilPay quote. Add a partial unique constraint:
  ```python
  UniqueConstraint(fields=["agreement"], condition=Q(status="pending"), name="uniq_pending_payment_per_agreement")
  ```

---

## 4. Severity 3 — Configurability / extensibility gaps

### 4.1 Manual landlord payment recording — completely absent

Only the SmobilPay flow can write a `Payment` row. `Payment.payment_method` includes `cash`, `bank_transfer`, `cheque`, and `other` but **none are reachable from the API**. `Payment.payment_date = auto_now_add=True` so landlords cannot backdate.

> **Concrete impact**: in Cameroon a large fraction of rent is cash or bank transfer. Without manual recording, the platform's record will be permanently incomplete; reports will lie; tenants who paid cash will be wrongly flagged in arrears and may receive automated eviction warnings.

#### Proposed design

| Aspect | Recommendation |
|---|---|
| **Endpoint** | `POST /api/v1/agreements/<id>/manual-payment/` |
| **Auth** | landlord/manager of property, or superuser |
| **Payload** | `amount`, `payment_method` (`cash` / `bank_transfer` / `cheque` / `other`), `payment_date` (allow backdating, validate ≤ today and ≥ agreement.start_date), `external_reference` (e.g. bank slip #), `notes`, `months` (monthly mode) or `installment_index` (yearly), optional `attachment` (receipt photo) |
| **Behavior** | Skip gateway entirely. `status='completed'`, `gateway_reference=''`, `fee_breakdown={platform_fee:0, gateway_fee:0, ...}`, `net_landlord_amount=amount`. Update agreement coverage / installments immediately within `@transaction.atomic` with `select_for_update`. |
| **Schema additions** | `Payment.recorded_by = FK(User)`, `Payment.payment_source = Enum(gateway, manual_landlord, manual_admin)`, `Payment.is_verified_by_tenant = bool`, `Payment.verified_at = datetime`, `Payment.attachment = ImageField(null=True)` |
| **Audit** | New `PaymentAuditLog` model with `(payment, actor, action, before_json, after_json, at)`. Append on every manual-payment create / reverse / dispute. |
| **Tenant verification** | After creation, mark `is_verified_by_tenant=False`. Send notification to tenant. They have N days to confirm or dispute in-app. Auto-confirm after deadline. Disputes pause coverage extension and notify the landlord. |
| **Reverse** | `POST /api/v1/payments/<id>/reverse/` with required reason. Creates a new `Payment` with `status='refunded'` linked via `reversed_payment_id`, rolls back coverage / installment_status. Landlord-only, audited. |
| **Fee policy** | Two options to keep landlords from bypassing the platform: (1) deduct a small "manual entry" platform fee from the landlord's wallet/subscription; or (2) require an active subscription to record manual payments. Recommended: option 2 — manual recording is a *Pro tier feature*. |
| **Frontend** | "Record cash payment" CTA on each unit / agreement detail screen. Show clear visual distinction (badge "MANUAL — not verified by tenant"). |
| **Tests** | Idempotency (same `external_reference + agreement` cannot be recorded twice within X days), permission, audit trail, backdate guards, reverse flow, dispute flow. |

### 4.2 Fee config: what's per-landlord vs hard-global today

| Knob | Source | Per-property? | Per-landlord? | Issue |
|---|---|---|---|---|
| `platform_fee_percent` | `PlatformSettings` (singleton) | ❌ | ❌ | All landlords pay the same % |
| `platform_fee_cap` | `PlatformSettings` (singleton) | ❌ | ❌ | No volume-based override |
| `gateway_fee_percent` | `PlatformSettings` (singleton) | ❌ | ❌ | All landlords equal |
| `fixed_extra_fee` | `PlatformSettings` (singleton) | ❌ | ❌ | No tier discount |
| `platform_fee_payer` | `PaymentConfiguration` | ✅ | indirect | `split` is broken |
| `gateway_fee_payer` | `PaymentConfiguration` | ✅ | indirect | `split` is broken |
| `gateway_methods` | `PaymentConfiguration` (or fallback) | ✅ | indirect | OK |
| `pricing_model` (subscription vs per_tx) | `PaymentConfiguration` | ✅ | indirect | Free-waiver — no enforcement |
| Subscription discount on fees | nowhere | ❌ | ❌ | Business-tier landlord pays the same fees as Basic |

#### Recommended fee-resolution precedence

```
PaymentConfiguration override
   → Owner-level override (new column)
      → Owner.subscription_plan tier discount (new column on SubscriptionPlan)
         → PlatformSettings (default)
```

Concrete schema additions:

- `SubscriptionPlan.transaction_fee_discount_percent` (Decimal, e.g. 0 / 25 / 50 / 100)
- `SubscriptionPlan.platform_fee_cap_override` (nullable PositiveInt)
- `Owner.fee_overrides` (JSONField for ad-hoc deals with specific landlords)
- `PaymentConfiguration.fee_overrides` (JSONField for per-property overrides — highest precedence)

Then `RentCalculator` walks the chain instead of hitting `PlatformSettings` directly. **This is the single most useful change to make the system "dynamic" as the user requested.**

### 4.3 `SubscriptionPlanSerializer` drops critical fields
- Excludes `max_properties`, `max_units_total`, `max_units_per_property`, `has_api_access`, `has_advanced_reports`, `has_priority_support`, `has_bulk_sms`. Frontend cannot show plan limits or enforce them client-side; will inevitably hard-code → drift.

### 4.4 No fee preview API
- `AvailablePaymentOptionsView` returns only `amount`. Tenants cannot see the breakdown before paying. Add a `fee_breakdown` block to each option so the UI can show "Rent 50,000 + Platform 500 + Gateway 1,000 = 51,500 XAF".

---

## 5. Severity 4 — Code smells / hygiene (incomplete list)

1. **`print()` statements in production paths** (`print("@@@@@@ monthly")`, gateway response prints) — sensitive data leaks to stdout/logs.
2. **`Decimal(2.0)` and `Decimal(1)` in `PlatformSettings.get_settings`** — `Decimal(2.0)` happens to be exact for this specific float, so it's not currently buggy. But constructing `Decimal` from float is a footgun for future edits (e.g. `Decimal(2.5)` would round). Switch to `Decimal("2.0")` defensively.
3. **`payment.save()` (no `update_fields`)** in `verify_and_complete` — full save on a row that may be modified concurrently.
4. **`PlatformSettings.save` singleton enforcement has TOCTOU race** — should use a UNIQUE constraint on a fixed `id=1`.
5. **`installment_index` stored in `Payment.notes` field as a stringified `f"installment_index:{idx}"`** — stringly-typed, parsing-required, clobbers user notes. Add a real `Payment.installment_index` integer column.
6. **`PaymentConfiguration` auto-create races** with the post_save signal under concurrency (OneToOne `IntegrityError` possible). The signal already creates it — the manager should never auto-create.
7. **`MakePaymentView` references undefined `e`** in the validation-failed branch (`print("This is the error ", e)` outside the try/except scope) — `NameError` returned to client when the serializer is invalid. Real bug, easy fix.
8. **`Payment.gateway_reference` not unique in DB** — could collide across pending payments.
9. **`coverage_end_date = today` on monthly agreement creation** — tenant appears pre-covered for day zero. Should be `None` or `start_date - 1 day`.
10. **`Payment.mobile_reference` declared but never written**.
11. **`Owner.save` mutates `self.user.role`** and triggers an extra `User.save` on every `Owner.save` — fires unnecessary writes, can race with concurrent profile creates.
12. **No retry / circuit-breaker** around SmobilPay calls — any transient blip kills the request.
13. **Error dictionary in `smobilpay_client.py`** is hardcoded (`703202`, `703108`, etc.). Should live in a config / be exhaustive.
14. **`RentalAgreement.start_date = auto_now_add=True`** — landlords cannot import existing leases. Critical for onboarding.
15. **Currency hardcoded `XAF`** — no `Payment.currency` field. Blocks geographic expansion.
16. **`unit_id` is sometimes referenced as bigint pkid, sometimes as UUID** (see `RentalAgreementRepository.find_all_by_user`). Mixing integer and UUID lookups is fragile; document and enforce one.
17. **No reconciliation report** with SmobilPay (clearing date, settled amount). Drift between platform and gateway is undetectable.
18. **No partial-refund / dispute path** even though `Payment.status='refunded'` exists.
19. **`is_outstanding` boundary** — `coverage_end_date >= today` includes a tenant whose coverage ends today (debatable).
20. **Tests for payment paths are thin** — `payments/tests.py` and `payments/tests/` package coexist; pytest may emit a namespace warning, and one of the two will be effectively shadowed depending on import order. No factory chain covers the full `initiate → verify → fail → retry` lifecycle.

---

## 6. The big-picture missing pieces

These are not bugs — they are entire features that the current architecture promises but does not implement.

### 6.1 No landlord payout pipeline
- `SmobilPayGateway.cashout` exists, but **no scheduled job or service** disburses `net_landlord_amount` to landlords.
- Money sits in the SmobilPay merchant balance with no automated payout scheduler. **This is implicitly the most expensive missing feature.**

### 6.2 No platform-revenue ledger
- The platform's slice of fees is never persisted as a "revenue" record. It's just the difference between two computed numbers in a `Payment.fee_breakdown` JSON.
- Reconciliation, refunds, accounting, tax filings are impossible without an explicit `PlatformRevenue` / `LedgerEntry` model.

### 6.3 No tax/withholding integration
- Cameroonian law has rental withholding tax. `Owner.tax_id` (NIU) is collected but never used. No VAT line on `fee_breakdown`.

### 6.4 No GDPR / financial-record-retention policy
- `Payment` cascades with `RentalAgreement`, which cascades with `Tenant`, which cascades with `User`. **A tenant deleting their account wipes all their payment records** — a legal liability for the landlord and the platform.
- Use `on_delete=PROTECT` on `Payment.agreement` and soft-delete the parent objects.

### 6.5 No subscription billing loop
- A complete subscription billing loop would need:
  1. A monthly Celery beat task `charge_subscriptions` that creates a `SubscriptionInvoice` row per active owner whose `subscription_end_date` is approaching.
  2. Same SmobilPay flow as rent: a `Payment` row of type `subscription` with `gateway_reference`.
  3. On success, `subscription_end_date += relativedelta(months=1)` (calendar-aware, **not** `+= 30 days` — see §2.5).
  4. On failure (3 retries), flip to `past_due`. After grace period, `expired` → block fee waiver and feature flags.

---

## 7. Way forward — prioritized roadmap

### Phase 1 — Stop the bleeding (1 week)
- [ ] Remove `print()` statements; fix `NameError` in `MakePaymentView`; remove the duplicate `RentalAgreementDetailView`.
- [ ] Add `select_for_update()` on `Payment` in `verify_and_complete`.
- [ ] Add unique constraint on `Payment.gateway_reference` (where non-empty).
- [ ] Snapshot `fee_breakdown` at initiate; in `verify_and_complete`, **read from snapshot — never recompute**.
- [ ] Replace `days = months * 30` with `dateutil.relativedelta(months=N)`.
- [ ] Fix the `split` payer logic (an explicit `elif`).
- [ ] Fix the `is_outstanding` logic inversion in `terminate_agreement`.

### Phase 2 — Webhooks + idempotency (1–2 weeks)
- [ ] Implement webhook endpoint at `/api/v1/payments/webhooks/smobilpay/` with **real HMAC signature verification** per SmobilPay docs.
- [ ] Add `Idempotency-Key` header support on `MakePaymentView`; persist in a small `PaymentRequestKey` model.
- [ ] In webhook + verify flow, **reconcile `priceLocalCur` against `payment.amount`**. Reject mismatches.
- [ ] Add partial unique constraint on `(agreement, status='pending')`.

### Phase 3 — Manual landlord payments (2–3 weeks)
- [ ] Schema: `Payment.recorded_by`, `payment_source`, `is_verified_by_tenant`, `verified_at`, `attachment`, real `installment_index` column.
- [ ] `POST /agreements/<id>/manual-payment/` and `POST /payments/<id>/reverse/`.
- [ ] `PaymentAuditLog` model + signals.
- [ ] Tenant verification / dispute flow.
- [ ] Frontend "Record cash payment" CTA + dispute UI.

### Phase 4 — Subscription enforcement (3–4 weeks)
- [ ] `SubscriptionInvoice` model and `Payment.payment_type='subscription'`.
- [ ] Wire `OwnerService.assign_subscription` to the SmobilPay flow (it must take money).
- [ ] Celery beat: nightly `expire_subscriptions` (`active`→`past_due`→`expired`); monthly `charge_subscriptions`.
- [ ] Block the per-transaction fee waiver when `subscription_status` not in `(active, trial)`.
- [ ] Surface `max_*` fields in `SubscriptionPlanSerializer`.

### Phase 5 — Dynamic fees + co-ownership (3–4 weeks)
- [ ] Add `transaction_fee_discount_percent` and `platform_fee_cap_override` to `SubscriptionPlan`.
- [ ] Add `Owner.fee_overrides` and `PaymentConfiguration.fee_overrides` JSON.
- [ ] Refactor `RentCalculator` to walk the precedence chain.
- [ ] Use `PropertyOwnership.percentage` to split `net_landlord_amount` across joint owners; persist per-owner payout intents.

### Phase 6 — Payout pipeline + ledger + reconciliation (4–6 weeks)
- [ ] `PlatformRevenue` / `LedgerEntry` model — every fee becomes a real ledger row.
- [ ] Celery beat `disburse_landlord_payouts` using `gateway.cashout`, with retry & exponential back-off, and `Payout` model state machine.
- [ ] Daily reconciliation report comparing platform `Payment` rows vs SmobilPay statement.
- [ ] Add fee preview to `AvailablePaymentOptionsView`.

### Phase 7 — Calendar correctness, currency, tax, retention (ongoing)
- [ ] Make `RentalAgreement.start_date` writable; allow lease import.
- [ ] Add `Payment.currency` field.
- [ ] Wire `Owner.tax_id` (NIU) into `fee_breakdown` (withholding line).
- [ ] Use `on_delete=PROTECT` on financial records; soft-delete `User`/`Tenant`.

---

## 8. Appendix — file map of the issues

| File | Issues referenced |
|------|-------------------|
| `app/apps/payments/managers/payment_manager.py` | 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 3.9, 5.1, 5.3, 5.5, 5.7 |
| `app/apps/payments/utils/rent_calculator.py` | 3.3, 3.4, 4.2 |
| `app/apps/payments/views.py` | 3.8, 4.4, 5.1, 5.7 |
| `app/apps/payments/services.py` | 3.7 (terminate_agreement), 4.1 |
| `app/apps/payments/models.py` | 4.1 schema, 5.5, 5.8, 5.10, 5.14, 5.15 |
| `app/apps/payments/gateway_SDKs/smobilpay_gateway.py` | 2.1 (process_webhook stub, _verify_webhook_signature TODO) |
| `app/apps/payments/serializers.py` | 4.3 |
| `app/apps/properties/models.py` | 3.5, 3.6, 5.11 |
| `app/apps/properties/services.py` | 3.1 (assign_subscription) |
| `app/apps/properties/repositories.py` | 3.1 (update_subscription) |
| `app/apps/core/models.py` | 5.2, 5.4 (PlatformSettings) |
| `app/pms/celery.py` | 3.2 (no beat schedule) |
| `app/pms/settings/base.py` | 2.1 (webhook URL configured but unused) |
| `app/apps/payments/dummy_payment_processor.py` | dead-code fallback that should be removed once webhook+idempotency land |

---

*Document author: code audit, 2026-05-25. No code in the repository was modified to produce this report.*
