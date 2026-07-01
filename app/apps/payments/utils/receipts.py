import datetime
from django.db import transaction
from apps.payments.models import Receipt    

def generate_receipt_number():
    with transaction.atomic():
        last = Receipt.objects.filter(
            receipt_number__startswith=f"RCP-{datetime.date.today().year}-"
        ).order_by("-receipt_number").first()
        if last:
            num = int(last.receipt_number.split("-")[-1]) + 1
        else:
            num = 1
        return f"RCP-{datetime.date.today().year}-{num:04d}"