from rest_framework import serializers
from .models import LoanUser
from .models import LoanApplication, Payment

class LoanUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanUser
        fields = ('aadhar_id', 'name', 'email', 'annual_income', 'credit_score', 'uuid')

class LoanApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanApplication
        fields = ('loan_type', 'loan_amount', 'interest_rate', 'term_period', 'disbursement_date', 'emi_amount', 'status', 'loan_id')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('payment_date', 'principal_amount', 'interest', 'amount_paid', 'status')
