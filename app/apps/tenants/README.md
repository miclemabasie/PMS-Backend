## 📝 Documentation Updates

### API Documentation Addition

**File:** `app/apps/tenants/README.md` (create if doesn't exist)

```markdown
# Tenant API Documentation

## Tenant Model Constraints

### ID Number (CNI/Passport)
- **Unique:** Yes - Each ID number can only be registered once
- **Normalized:** Yes - All ID numbers are stored uppercase, trimmed
- **Purpose:** Prevents tenants from creating multiple accounts to hide rental history

### Error Responses

| Status Code | Error | Message |
|-------------|-------|---------|
| 400 | Duplicate ID | "This ID number (CNI/Passport) is already registered. Each tenant can only have one account in the system." |
| 400 | Invalid Format | "ID number is required" |

## Business Rules

1. One CNI = One Tenant Account
2. ID numbers are case-insensitive
3. Leading/trailing spaces are automatically trimmed
4. Duplicate detection happens at both serializer and database level
```

---

## ⚠️ Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing duplicates in DB | Migration fails | Run data migration first (Step 4) |
| Production downtime | Medium | Schedule during low-traffic period |
| API breaking changes | Low | Backward compatible (only rejects new duplicates) |
| User confusion | Low | Clear error messages in serializer |

---

## ✅ Completion Checklist

- [ ] Update `Tenant` model with `unique=True`
- [ ] Add `UniqueConstraint` in Meta class
- [ ] Update `TenantSerializer` with validation
- [ ] Create data migration for existing duplicates
- [ ] Create schema migration for uniqueness constraint
- [ ] Test duplicate creation (should fail)
- [ ] Test unique creation (should succeed)
- [ ] Test case insensitivity
- [ ] Test update own record
- [ ] Update API documentation
- [ ] Run migrations on development database
- [ ] Run migrations on staging database
- [ ] Deploy to production

---

## 🎯 Next Steps

Once Task 1.1 is complete and verified, we proceed to:

**Task 1.2:** Tenant Search Endpoint - Create `GET /api/v1/tenants/search/?id_number=XXX`

---

## 📋 Decision Log

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| `unique=True` on field | Database-level enforcement is most reliable | Application-level validation only (rejected - can be bypassed) |
| Case normalization | Prevents `CNI123` vs `cni123` duplicates | Case-sensitive uniqueness (rejected - user confusion) |
| Named constraint | Better migration tracking and debugging | Anonymous constraint (rejected - harder to debug) |
| Data migration first | Prevents migration failure on existing data | Manual cleanup (rejected - error-prone) |
| Serializer validation | User-friendly error messages before DB error | DB error only (rejected - poor UX) |

---

**Ready to proceed?** Let me know if you want me to:
1. Generate the actual migration files
2. Move to Task 1.2 (Tenant Search Endpoint)
3. Adjust any part of this implementation