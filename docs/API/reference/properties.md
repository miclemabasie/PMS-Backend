# 🏠 Properties API

Base URL: `/api/v1/properties/`

## Endpoints

### Property CRUD

| Method   | Endpoint                        | Description                     | Permissions        |
| -------- | ------------------------------- | ------------------------------- | ------------------ |
| `GET`    | `/api/v1/properties/`           | List properties (role-filtered) | Authenticated      |
| `POST`   | `/api/v1/properties/`           | Create property                 | Manager, Superuser |
| `GET`    | `/api/v1/properties/<uuid:pk>/` | Get property details            | Authenticated      |
| `PATCH`  | `/api/v1/properties/<uuid:pk>/` | Partial update                  | Owner, Manager     |
| `PUT`    | `/api/v1/properties/<uuid:pk>/` | Full update                     | Owner, Manager     |
| `DELETE` | `/api/v1/properties/<uuid:pk>/` | Delete property                 | Superuser          |

### Units (Nested)

| Method | Endpoint                              | Description                    | Permissions        |
| ------ | ------------------------------------- | ------------------------------ | ------------------ |
| `GET`  | `/api/v1/properties/units/`           | List all units (role-filtered) | Authenticated      |
| `POST` | `/api/v1/properties/units/`           | Create unit                    | Manager, Superuser |
| `GET`  | `/api/v1/properties/units/<uuid:pk>/` | Get unit details               | Authenticated      |

### Property Managers

| Method   | Endpoint                                 | Description                | Permissions        |
| -------- | ---------------------------------------- | -------------------------- | ------------------ |
| `GET`    | `/api/v1/properties/managers/`           | List managers              | Manager, Superuser |
| `POST`   | `/api/v1/properties/managers/`           | Assign manager to property | Superuser          |
| `DELETE` | `/api/v1/properties/managers/<uuid:pk>/` | Remove manager             | Superuser          |

### Property Images

| Method   | Endpoint                               | Description              | Permissions    |
| -------- | -------------------------------------- | ------------------------ | -------------- |
| `GET`    | `/api/v1/properties/<uuid:pk>/images/` | List property images     | Authenticated  |
| `POST`   | `/api/v1/properties/<uuid:pk>/images/` | Upload image (multipart) | Owner, Manager |
| `DELETE` | `/api/v1/properties/images/<uuid:pk>/` | Delete image             | Owner, Manager |

## Example: Create Property with Images

`POST /api/v1/properties/`

```json
{
  "name_en": "Le Palmier Residences",
  "name_fr": "Résidences Le Palmier",
  "address": "Avenue de la Réunification, Douala",
  "starting_amount": "250000",
  "currency": "XAF",
  "description_en": "Luxury apartments with city views...",
  "amenities": ["pool", "gym", "24h_security", "parking"],
  "is_active": true
}
```
