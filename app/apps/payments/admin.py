from django.contrib import admin
from .models import PaymentPlan, Installment, RentalAgreement, Payment, AgreementAcceptance, Receipt

admin.site.register(PaymentPlan)
admin.site.register(Installment)
admin.site.register(RentalAgreement)
admin.site.register(Payment)
admin.site.register(AgreementAcceptance)
admin.site.register(Receipt)