from django.contrib.auth.backends import BaseBackend
from vendors.models import Vendor

class VendorEmailBackend(BaseBackend):
    def authenticate(self, request, username=None, **kwargs):
        try:
            vendor = Vendor.objects.get(email=username, is_approved=True)
            return vendor  # Directly return Vendor
        except Vendor.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Vendor.objects.get(pk=user_id)
        except Vendor.DoesNotExist:
            return None


from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from .models import Vendor
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Vendor

class VendorJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Get the raw token from the request header
        raw_token = self.get_raw_token(self.get_header(request))
        if raw_token is None:
            return None  # No token provided

        # Validate the token and get its payload
        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception as e:
            raise AuthenticationFailed("Invalid token.")  # Token is invalid

        # Retrieve the vendor using the user_id from the token payload
        user = self.get_user(validated_token)

        return user, validated_token  # Return vendor instance and token

    def get_user(self, validated_token):
        # Extract user_id from the token's payload
        user_id = validated_token.get("user_id")

        if not user_id:
            raise AuthenticationFailed("User ID not found in token.")  # Missing user_id in token

        try:
            # Find the vendor using the user_id in the token
            vendor = Vendor.objects.get(id=user_id)
            return vendor
        except Vendor.DoesNotExist:
            raise AuthenticationFailed("Vendor not found.")  # No vendor found with the given user_id

