Let me read the truncated middle section to understand the full codebase structure.Now I have a thorough understanding of the codebase. Let me also quickly check the payments models and the tenant model for the `blizon_id` field.Now I have a comprehensive picture of your codebase. Let me compile the full concerns report.Now I have everything I need to produce a well-structured, detailed concerns report.Here's a summary of what was found and where to focus:

**Critical gaps (build these first):**

Concern #5 (Blizon Tenant ID) requires a new `blizon_id` field on the `Tenant` model, a generator in `save()`, and search support in the repository and views. It's purely additive so no existing logic breaks.

Concern #8 (payment plans leaking across landlords) is an actual data bug. Right now `PaymentPlan` has no owner foreign key, so every landlord's plans are visible to all. This needs a model change, migration, and filter update in `PaymentPlanService.get_active_plans()` before you go to production.

Concern #1 (receipt generation) requires the most new work — a `Receipt` model, a generation service, a Celery task for PDF+email delivery, and a download endpoint.

**Partially done:**

Concern #2 (agreement acceptance via email) — the accept view and URL are wired, but you need to verify the email dispatch happens inside `RentalAgreementService.create_agreement()`. If it doesn't, add it using a helper from the new `apps/core/email.py` module (concern #6).

Concern #4 (maintenance reports) is mostly done on the backend. The gap is likely just confirming status-transition endpoints exist and connecting the frontend.

**Infrastructure to add once:**

Concern #6 recommends centralising all email sending into `apps/core/email.py` — all the other features (receipts, agreement acceptance, payout reminders) should call functions from that one place rather than duplicating logic.



<!-- updates -->

Here’s a **fast summary** of all problems I identified in your codebase, grouped by priority for later follow‑up:

---

## 🔴 CRITICAL (Production Blockers)

1. **No payment webhook** – `SMOBIL_PAY_WEBHOOK_URL` configured but no endpoint exists to consume it → status never updates after gateway confirms.
2. **Race condition** in `verify_and_complete` – no `select_for_update()` on Payment/RentalAgreement → double coverage or double counting.
3. **No idempotency** on payment initiation – network retries create duplicate MoMo prompts → tenant can be charged twice.
4. **Subscription billing is fake** – `assign_subscription` marks active without payment; no expiry job → landlords get unlimited free access.
5. **`pricing_model='subscription'` waives all fees** without checking if subscription is actually active/paid.
6. **`split` fee-payer option is broken** – behaves like "landlord" (no 50/50 split).
7. **Co‑ownership payouts ignored** – `PropertyOwnership.percentage` never used to split funds.
8. **30‑day month drift** – uses `days = months * 30` instead of `relativedelta` → tenants lose ~5–6 days per year.
9. **Manual payment recording exists on backend** but frontend UI is incomplete/inconsistent.
10. **No disbursement pipeline** – `DisbursementService` exists but not wired to Celery; landlords never get paid automatically.

---

## 🟠 HIGH (Business Logic / Integrity)

11. **Subscription expiry** – no Beat task to expire past_due/expired subscriptions.
12. **Fee recalculation** during verification – `fee_breakdown` snapshot is recomputed on verify, can change between phases.
13. **Missing DB constraints** – no unique `gateway_reference`; no unique pending payment per agreement.
14. **`gateway_reference` can be empty** – malformed response leads to stuck pending payment.
15. **No amount reconciliation** against gateway response – spoofed success with different amount is accepted.
16. **`is_outstanding` logic inverted** – in `terminate_agreement`, prepaid tenant is treated as "outstanding" (should be the opposite).
17. **Duplicate `RentalAgreementDetailView`** – the first version with proper permission is shadowed by a weaker second definition.
18. **`STAGING_MODE or DEBUG`** collapses correctness checks if accidentally true in prod.
19. **No link between `SubscriptionPlan` and any payment** – revenue is theoretical.

---

## 🟡 MEDIUM (Configurability / UX)

20. **Fee configuration is global** – all landlords pay the same platform/gateway fees; no per‑landlord discounts.
21. **`SubscriptionPlanSerializer`** drops critical fields (`max_properties`, etc.) → frontend can't show plan limits.
22. **No fee preview API** – tenants see only the final amount, not breakdown.
23. **Manual payment PIN** – works on backend but validation flow on frontend may be unclear; UI could be improved.
24. **Placeholder tabs** – "Documents", "Activity", etc. are empty or "Coming soon".
25. **Error handling** – some API errors are not displayed clearly; toast messages can be vague.
26. **Frontend missing wallet features** – no UI for tenant wallet (deposits, balance, payments from wallet).

---

## 🟢 LOW (Code Hygiene / Polish)

27. `print()` statements in production paths (payment logs).
28. `Decimal(2.0)` constructed from float – might round incorrectly in future (use strings).
29. Payment `save()` without `update_fields` – risk of overwriting concurrent changes.
30. `PlatformSettings` singleton has TOCTOU race – should use a UNIQUE constraint on `id=1`.
31. `installment_index` stored in `Payment.notes` as a string – stringly‑typed; should be a real column.
32. No retry/circuit‑breaker around SmobilPay calls.
33. Hardcoded error codes in `smobilpay_client.py` – should be configurable.
34. `RentalAgreement.start_date = auto_now_add=True` – cannot import existing leases.

---

We’ll tackle these in priority order later. For now, we focus on the immediate task at hand.