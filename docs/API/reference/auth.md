# 🔐 Authentication API

Base URL: `/api/v1/auth/`

## Endpoints

| Method | Endpoint                                     | Description              | Auth       |
| ------ | -------------------------------------------- | ------------------------ | ---------- |
| `POST` | `/api/v1/auth/users/`                        | Register new user        | ❌         |
| `POST` | `/api/v1/auth/users/me/`                     | Get current user profile | ✅ Bearer  |
| `PUT`  | `/api/v1/auth/users/me/`                     | Update current user      | ✅ Bearer  |
| `POST` | `/api/v1/auth/jwt/create/`                   | Obtain JWT tokens        | ❌         |
| `POST` | `/api/v1/auth/jwt/refresh/`                  | Refresh access token     | ✅ Refresh |
| `POST` | `/api/v1/auth/jwt/verify/`                   | Verify token validity    | ✅ Bearer  |
| `POST` | `/api/v1/auth/users/reset_password/`         | Request password reset   | ❌         |
| `POST` | `/api/v1/auth/users/reset_password_confirm/` | Confirm password reset   | ❌         |

## Example: Login Flow

### 1. Register

`POST /api/v1/auth/users/`

```json
{
  "email": "tenant@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```
