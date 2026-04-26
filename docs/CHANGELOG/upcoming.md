As of commit commit e52064f8605cca7fdec0e0d18ca4ac73bcc570a6

the system no longer support lease management, the architecture has been swapped to rental agreements so as to allow for flexibility in payments and contracts in the cameroon property rental market, nice

Models that where changed:

Unit -> Property.models
Payment -> Payments.Payment

Models Added

Payment Plan -> Payments.PaymentPlan
Installment -> Payments.Installment
RentalAgreement -> Payments.RentalAgreement
