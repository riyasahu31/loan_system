from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import LoanUser, LoanApplication, Payment
from .serializers import LoanUserSerializer
from datetime import datetime, timedelta
from .tasks import calculate_credit_score
from calendar import monthrange

class RegisterUser(APIView):
    def post(self, request):
        serializer = LoanUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Trigger the Celery task to calculate the credit score asynchronously
            calculate_credit_score(user.aadhar_id)
            return Response({'unique_user_id': user.aadhar_id}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApplyLoan(APIView):
    def post(self, request):
        user_id = request.data.get('unique_user_id')
        loan_type = request.data.get('loan_type')
        loan_amount = request.data.get('loan_amount')
        interest_rate = request.data.get('interest_rate')
        term_period = request.data.get('term_period')
        disbursement_date = datetime.strptime(
            request.data.get('disbursement_date'), '%Y-%m-%d').date()

        try:
            user = LoanUser.objects.get(uuid=user_id)
        except LoanUser.DoesNotExist:
            return Response({'Error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if credit score is sufficient
        if user.credit_score < 450:
            return Response({'Error': 'Insufficient credit score'}, status=status.HTTP_400_BAD_REQUEST)

        # Check user income
        if user.annual_income < 150000:
            return Response({'Error': 'Income below minimum requirement'}, status=status.HTTP_400_BAD_REQUEST)

        # Check loan amount bounds based on loan type
        loan_type_bounds = {
            'Car': 750000,
            'Home': 8500000,
            'Education': 5000000,
            'Personal': 1000000
        }

        if loan_amount > loan_type_bounds.get(loan_type, 0):
            return Response({'Error': 'Loan amount exceeds bounds'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate EMI
        interest_per_month = interest_rate / (12 * 100)
        emi_numerator = loan_amount * interest_per_month * (1 + interest_per_month) ** term_period  
        emi_denominator = (1 + interest_per_month) ** term_period - 1
        emi_amount = round(emi_numerator / emi_denominator, 2)

        # Check EMI amount
        if emi_amount > (float(user.annual_income) / 12) * 0.6:
            return Response({'Error': 'EMI exceeds 60% of monthly income'}, status=status.HTTP_400_BAD_REQUEST)

        # Check interest rate and total interest
        if interest_rate < 14 or (emi_amount * term_period - loan_amount) < 10000:
            return Response({'Error': 'Invalid interest rate or insufficient total interest'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate EMI due dates
        emi_due_dates = []
        
        # Start from the next month on the 1st day
        current_date = disbursement_date.replace(day=1) + timedelta(days=32)
        for _ in range(term_period):
            # Calculate the last day of the current month
            last_day_of_month = current_date.replace(
                day=monthrange(current_date.year, current_date.month)[1])

            # Calculate the EMI due date as the 1st day of the next month
            next_month = last_day_of_month + timedelta(days=1)

            emi_due_dates.append({
                'Date': next_month.strftime('%Y-%m-%d'),
                'Amount_due': emi_amount
            })

            # Move to the next month
            current_date = next_month

        loan_application = LoanApplication(
            user=user,
            loan_type=loan_type,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            term_period=term_period,
            disbursement_date=disbursement_date,
            emi_amount=emi_amount
        )
        loan_application.save()

        # Update the status to 'Approved' and save last EMI amount
        loan_application.status = 'Approved'
        # loan_application.emi_amount = last_emi_amount
        loan_application.emi_amount = emi_amount
        loan_application.save()

        return Response({'Loan_id': loan_application.loan_id, 'Due_dates': emi_due_dates}, status=status.HTTP_200_OK)


class MakePayment(APIView):
    def post(self, request):
        loan_id = request.data.get('loan_id')
        amount = request.data.get('amount')
        payment_date = datetime.strptime(
            request.data.get('payment_date'), '%Y-%m-%d').date()

        try:
            loan_application = LoanApplication.objects.get(loan_id=loan_id)

            if loan_application.status == 'Closed':
                return Response({'Error': 'Loan is already closed'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if previous EMIs are due
            due_emis = payment_date.year*12+ payment_date.month - (loan_application.disbursement_date.month+  loan_application.disbursement_date.year*12+ loan_application.paid_emis)
            
            if due_emis > 1:
                return Response({'Error': f'{due_emis} previous EMIs are due'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if payment is already made for that date
            if due_emis <= 0:
                return Response({'message': 'Payment for this date already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create a Payment record
            principal= float(loan_application.loan_amount)
            interest_amount= principal*float(loan_application.interest_rate)/1200 
            Payment.objects.create(
                loan=loan_application,
                payment_date=payment_date, 
                principal_amount=principal,
                interest=interest_amount,
                amount_paid=amount, 
                status='PAID')
            
        # Update the principal amount EMIs count and create a payment record
            principal= principal-(amount-interest_amount)
            loan_application.loan_amount= principal

        # Update the paid EMIs count and create a payment record
            loan_application.paid_emis += 1

        # Check if all EMIs are paid, then close the loan
            if loan_application.paid_emis == loan_application.term_period:
                loan_application.status = 'Closed'
            
            loan_application.save()

            return Response({'message': 'Payment successful.'}, status=status.HTTP_200_OK)

        except LoanApplication.DoesNotExist:
            return Response({'Error': 'Loan application not found'}, status=status.HTTP_400_BAD_REQUEST)


class GetStatement(APIView):
    def get(self, request):
        loan_id = request.query_params.get('loan_id')

        try:
            loan_application = LoanApplication.objects.get(loan_id=loan_id)
        except LoanApplication.DoesNotExist:
            return Response({'Error': 'Loan application not found'}, status=status.HTTP_400_BAD_REQUEST)

        if loan_application.status == 'Closed':
            return Response({'Error': 'Loan is closed'}, status=status.HTTP_400_BAD_REQUEST)

        past_payments = Payment.objects.filter(
            loan=loan_application).order_by('payment_date')


        past_transactions = []
        for payment in past_payments:
            past_transactions.append({
                'Date': payment.payment_date.strftime('%Y-%m-%d'),
                'Principal': payment.principal_amount,
                'Interest': payment.interest,
                'Amount_paid': payment.amount_paid
            })


        upcoming_transactions = []
         # Calculate EMI
        remaining_months=loan_application.term_period-loan_application.paid_emis
        interest_per_month = loan_application.interest_rate / (12 * 100)
        emi_numerator = loan_application.loan_amount * interest_per_month * (1 + interest_per_month) ** remaining_months  
        emi_denominator = (1 + interest_per_month) ** remaining_months - 1
        emi_amount = round(emi_numerator / emi_denominator, 2)
        
        for i in range(loan_application.term_period - len(past_transactions)):
            emi_month = (loan_application.disbursement_date.month + len(past_transactions) +i )%12 +1
            emi_year= loan_application.disbursement_date.year+ int((loan_application.disbursement_date.month + len(past_transactions) +i+1)/12 )
            emi_date= datetime(emi_year, emi_month, 1)
            upcoming_transactions.append(
                {'Date': emi_date.strftime('%Y-%m-%d'), 'Amount_due': emi_amount})

        statement = {
            'Loan_id': loan_application.id,
            'Past_transactions': past_transactions,
            'Upcoming_transactions': upcoming_transactions,
            'Error': None
        }

        return Response(statement, status=status.HTTP_200_OK)
