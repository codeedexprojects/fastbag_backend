# users/authentication.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from users.models import CustomUser
# class AdminAuthenticationBackend(BaseBackend):
#     def authenticate(self, request, email=None, password=None):
#         try:
#             user = User.objects.get(email=email)
            
#             if not user.is_superuser:
#                 raise PermissionDenied("User is not an admin.")
            
#             if user.check_password(password):
#                 return user
#             return None
#         except User.DoesNotExist:
#             return None
    
#     def get_user(self, user_id):
#         try:
#             return User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return None
class MobileBackend(BaseBackend):
    def authenticate(self, request, mobile_number=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(mobile_number=mobile_number)
        except CustomUser.DoesNotExist:
            return None
        
        if user.check_password(password):
            return user
        return None
    
