from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.tenants.models import Brand, Client

from .models import ClientUser


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "logo_url")


class ClientSerializer(serializers.ModelSerializer):
    brands = BrandSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = ("id", "name", "logo_url", "primary_color", "secondary_color", "brands")


class ClientUserSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)

    class Meta:
        model = ClientUser
        fields = ("id", "email", "full_name", "role", "client", "is_staff")


class ChirriTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Return the user + client payload alongside the JWT pair, so the frontend
    can render branded chrome on the first render without a follow-up /me call."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["client_id"] = user.client_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = ClientUserSerializer(self.user).data
        return data
