from django.urls import path
from .views import RegisterUser
from .views import ApplyLoan, MakePayment, GetStatement
urlpatterns = [
    path('api/register-user/', RegisterUser.as_view(), name='register-user'),
    path('api/apply-loan/', ApplyLoan.as_view(), name='apply-loan'),
    path('api/make-payment/', MakePayment.as_view(), name='make-payment'),
    path('api/get-statement/', GetStatement.as_view(), name='get-statement'),
]
