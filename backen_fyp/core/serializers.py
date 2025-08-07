from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as django_exceptions
from django.contrib.auth.password_validation import validate_password
from core.models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = {}
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        # log user out if already logged in

        self.user = authenticate(**authenticate_kwargs)

        if not self.user or not self.user.is_active:
            raise serializers.ValidationError({
                "login_error": "Email/username or password is incorrect",
                }
            )
        # data["username"] = self.user.username
        # data["email"] = self.user.email
        # data["full_name"] = self.user.full_name
        # data["gender"] = self.user.gender
        return data
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['full_name'] = user.full_name
        token['gender'] = user.gender

        return token
    
class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'full_name', 'gender', "password")
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate(self, attrs):    
        user = User(**attrs)
        password = attrs.get("password")
        try:
            validate_password(password, user)
        except django_exceptions as e:
            serializer_error = serializers.as_serializer_error(e)
            raise serializers.ValidationError(
                {"password": serializer_error["non_field_errors"]}
            )
        tmp = attrs
        return tmp
    
    def create(self, validated_data):
        print("Creating user with data:", validated_data)
        user: User = super().create(validated_data)
        user.set_password(validated_data.get('password'))
        user.save()
        return user