from .models import Payment
from .models import LoanApplication
from .models import LoanUser
from django.contrib import admin

admin.site.register(LoanUser)

admin.site.register(Payment)

admin.site.register(LoanApplication)
