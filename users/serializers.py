from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


# Validates + saves a new signup (checks passwords match, creates user).
# If removed, account registration stops working.
# Used by RegisterView in users/views.py.
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


# Turns a user object into JSON for the profile/register responses.
# If removed, profile data can't be sent to the frontend.
# Used by RegisterView and ProfileView in users/views.py.
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'bio', 'avatar', 'avatar_base64',
            'display_name', 'title', 'theme', 'level', 'xp', 'coins', 'diamonds',
            'preferences', 'profile_visibility', 'date_joined',
            'flex_effect', 'name_effect', 'avatar_border', 'bg_effect',
        ]
