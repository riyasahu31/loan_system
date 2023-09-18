from django.db import models
from django.contrib.auth.models import User as DjangoUser
import uuid

class Db(models.Model):
    user = models.CharField(max_length=255, null=False, blank=False)
    date = models.DateField()
    transaction_type = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class LoanUser(models.Model):
    aadhar_id = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    annual_income = models.DecimalField(max_digits=10, decimal_places=2)
    credit_score = models.PositiveIntegerField(default=0,  editable=False)
    uuid = models.CharField(max_length=12, default="default",  editable=False)

    def save(self, *args, **kwargs):
        
        self.uuid = self.aadhar_id
        super(LoanUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class LoanApplication(models.Model):
    user = models.ForeignKey(LoanUser, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=50, choices=[(
        'Car', 'Car'), ('Home', 'Home'), ('Education', 'Education'), ('Personal', 'Personal')])
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_period = models.PositiveIntegerField()
    disbursement_date = models.DateField()
    emi_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, default='Pending')
    paid_emis = models.PositiveIntegerField(
        default=0) 
    loan_id = models.UUIDField(default=uuid.uuid4, unique=True)

    def save(self, *args, **kwargs):
        if not self.loan_id:
            self.loan_id = uuid.uuid4()
        super(LoanApplication, self).save(*args, **kwargs)

    def __str__(self):
        return f"Loan Application for {self.user.name} - {self.loan_type}"


class Payment(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE)
    payment_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    interest= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    amount_paid= models.DecimalField(max_digits=10, decimal_places=2, null=True)
    status = models.CharField(
        max_length=20, default='Pending') 
