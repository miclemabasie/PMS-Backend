# ADR-002: JWT Authentication via Djoser + SimpleJWT

| Metadata | Value                                        |
| -------- | -------------------------------------------- |
| Status   | `accepted`                                   |
| Date     | 2026-03-15                                   |
| Deciders | Backend Team                                 |
| Related  | `requirements.txt`, `apps/users/api/urls.py` |

## Context

Session auth requires sticky state, complicates horizontal scaling, and forces CORS handling. Mobile/frontend apps need stateless, portable tokens.

## Decision

Use **Djoser** for user management (register, reset, profile) + **djangorestframework-simplejwt** for stateless JWT issuance and validation.

## Consequences

✅ Stateless → scales horizontally without Redis sessions  
✅ Native mobile/web compatibility (Bearer header)  
✅ Built-in refresh rotation + blacklist support  
⚠️ Token revocation requires blacklist table or short lifetimes  
⚠️ Larger payload size vs session cookies

## Validation

- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days with rotation
- All protected endpoints enforce `IsAuthenticated` + custom role permissions
- Postman collection includes auth flow automation

## References

- `app/pms/settings/base.py` → `SIMPLE_JWT` config
- `apps/users/api/urls.py` → Djoser routes
- DRF `JWTAuthentication` class in auth backends
