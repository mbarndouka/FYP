from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as django_exceptions
from django.contrib.auth.password_validation import validate_password
from core.models import User, SeismicData

from django.utils import timezone
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

import pandas as pd
from django.core.files.base import ContentFile
import io
import os
import matplotlib.pyplot as plt
from django.conf import settings
from django.core.files.base import ContentFile
import plotly.graph_objects as go
import plotly.offline as pyo
import numpy as np
class SeismicDataSerializer(serializers.ModelSerializer):
    csv_file = serializers.FileField(required=True)
    data_processed = serializers.SerializerMethodField(
        read_only=True,
        help_text="Processed data in b, MB, GB or TB."
    )
    row_data = serializers.SerializerMethodField(
        read_only=True,
        help_text="Data in the CSV file."
    )
    traces_analyzed = serializers.SerializerMethodField(
        read_only=True,
        help_text="Number of traces analyzed in the CSV file."
    )
    seismic_volum_in_3d = serializers.SerializerMethodField(
        read_only=True,
        help_text="3D seismic volume data."
    )

    def validate_csv_file(self, value: serializers.FileField):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("File must be a CSV.")
        try:
            df = pd.read_csv(value)
            if df.empty:
                raise serializers.ValidationError("CSV file cannot be empty.")
            # lower case the column names
            df.columns = [col.lower() for col in df.columns]
            # Check for required columns
            df = df[SeismicData.CSV_COLUMN_NAMES]

            self.cleaned_df = df
        except Exception as e:
            raise serializers.ValidationError(f"Invalid CSV file: {str(e)}")
        return value
     
    def get_traces_analyzed(self, obj):
        if obj.csv_file:
            try:
                df = pd.read_csv(obj.csv_file)
                self.cleaned_df = df
                return len(df)
            except Exception as e:
                return {"error": f"Error reading CSV file: {str(e)}"}
        return "No data available."
    
    def get_seismic_volum_in_3d(self, obj):
        request = self.context.get('request')
        if not obj.csv_file:
            return None

        try:
            df = self.cleaned_df
            if df.empty:
                return None

            # Create plot
            fig = plt.figure(
                figsize=(10, 7),
                facecolor='#1c2739',
                edgecolor='red'
            )
            ax = fig.add_subplot(111, projection='3d')
            ax.scatter(
                df['longitude'],
                df['latitude'],
                df['depth'],
                c=df['mag'],
                cmap='viridis',
                s=20
            )
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_zlabel('Depth')
            ax.set_title('Seismic Volume (3D)')

            # Save file to MEDIA_ROOT
            filename = f"seismic_plot_{obj.id}.png"
            filepath = os.path.join(settings.MEDIA_ROOT, filename)
            plt.savefig(filepath, format='png', bbox_inches='tight')
            plt.close(fig)

            # Return full URL
            if request:
                return request.build_absolute_uri(settings.MEDIA_URL + filename)
            return settings.MEDIA_URL + filename

        except Exception as e:
            return str(e)
    
    def get_row_data(self, obj):
        if obj.csv_file and not self.cleaned_df.empty:
            # Convert DataFrame to a list of dictionaries
            return self.cleaned_df.to_dict(orient='records')
        return "No data available."
    
    def get_data_processed(self, obj):
        if obj.csv_file:
            file_size = obj.csv_file.size
            if file_size < 1024:
                return f"{file_size:.2f} bytes"
            elif file_size < 1048576:
                return f"{file_size / 1024:.2f} KB"
            elif file_size < 1073741824:
                return f"{file_size / 1048576:.2f} MB"
            else:
                return f"{file_size / 1073741824:.2f} GB"
        return "No data processed yet."
    
    def _convert_time(self, time):
        # return in seconds, minute or hours
        if time < 60:
            return f"{time:.2f} seconds"
        elif time < 3600:
            return f"{time / 60:.2f} minutes"
        elif time < 86400:
            return f"{time / 3600:.2f} hours"
        else:
            return f"{time / 86400:.2f} days"
    class Meta:
        model = SeismicData
        fields = [
            'id',
            'csv_file',
            'processing_time',
            'data_processed',
            'traces_analyzed',
            'seismic_volum_in_3d',
            'row_data',
            'created_at',
        ]

    def create(self, validated_data: dict):
        processing_time = timezone.now()
        csv_file = validated_data.pop('csv_file')

        csv_buffer = io.StringIO()
        self.cleaned_df.to_csv(csv_buffer, index=False)

        # Give the file a name (use original filename or something new)
        csv_filename = getattr(csv_file, 'name', 'processed.csv')
        csv_content = ContentFile(csv_buffer.getvalue().encode('utf-8'))
        csv_content.name = csv_filename

        seismic_data = SeismicData.objects.create(
            csv_file=csv_content,
            **validated_data
        )

        processing_time = timezone.now() - processing_time
        seismic_data.processing_time = self._convert_time(processing_time.total_seconds())
        seismic_data.save()

        return seismic_data