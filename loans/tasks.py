from celery import shared_task
from .models import LoanUser
import csv


@shared_task
def calculate_credit_score(user_aadhar_id):
    user = LoanUser.objects.get(aadhar_id=user_aadhar_id)

    csv_file_path = 'transactions_data_backend.csv'
    try:
        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            total_balance = 0

            for row in csv_reader:
                transaction_type = row['transaction_type']
                amount = float(row['amount'])

                if transaction_type == 'CREDIT':
                    total_balance += amount
                elif transaction_type == 'DEBIT':
                    total_balance -= amount

            # Calculate credit score based on the total_balance
            if total_balance >= 1000000:
                user.credit_score = 900
            elif total_balance <= 100000:
                user.credit_score = 300
            else:
                balance_difference = total_balance - 100000
                user.credit_score = max(
                    300, min(900, 300 + (balance_difference / 15000) * 10))

            user.save()

    except FileNotFoundError:
        print(f"CSV file '{csv_file_path}' not found.")
