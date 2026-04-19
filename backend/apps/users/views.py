from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import ChirriTokenObtainPairSerializer, ClientUserSerializer


class LoginView(TokenObtainPairView):
    serializer_class = ChirriTokenObtainPairSerializer


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = ClientUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
