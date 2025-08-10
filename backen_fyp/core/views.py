from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q

from core.serializers import CustomTokenObtainPairSerializer, UserCreateSerializer, SeismicDataSerializer, RoomChatSerializer
from core.models import SeismicData, RoomChat, User

class UserLogin(viewsets.ModelViewSet):
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer

    @action(detail=False, methods=['post'], url_path='login')
    def user_login(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            token = serializer.get_token(serializer.user)
            return Response({
                "successMessage": "Login successful",
                "status_code": status.HTTP_200_OK,
                "refresh": str(token),
                "access": str(token.access_token),
                **serializer.validated_data
                }, status=status.HTTP_200_OK)
        
        error_data = ''
        
        for key, value in serializer.errors.items():
            error_data += f"{key}: {value}"

        return Response({
            "errorMessage": error_data,
            "status_code": status.HTTP_400_BAD_REQUEST,
        }, status=status.HTTP_400_BAD_REQUEST)
    
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserCreateSerializer

    def get_queryset(self):
        return User.objects.all()
    
    def get_permissions(self):
        if self.action == "user_registration":
            self.permission_classes = (AllowAny,)

        return super().get_permissions()
    
    @action(detail=False, methods=['get'], url_path='profile')
    def user_profile(self, request):
        user = self.get_queryset()
        serializer = self.get_serializer(user)
        return Response({
            "successMessage": "User profile retrieved successfully",
            "status_code": status.HTTP_200_OK,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post', 'get'], url_path='chat')
    def room_chat(self, request):
        if request.method == 'POST':
            serializer = RoomChatSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                room = serializer.save()
                return Response({
                    "successMessage": "Chat room created successfully",
                    "status_code": status.HTTP_201_CREATED,
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

            error_data = ''
            for field, errors in serializer.errors.items():
                for error in errors:
                    error_data += f"{field}: {error}. "

            return Response({
                "errorMessage": error_data,
                "status_code": status.HTTP_400_BAD_REQUEST,
            }, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            room_id = request.query_params.get('room_id', None)

            if room_id:
                try:
                    room = RoomChat.objects.get(id=room_id)
                    serializer = RoomChatSerializer(room, context={'request': request})
                    return Response({
                        "successMessage": "Chat room retrieved successfully",
                        "status_code": status.HTTP_200_OK,
                        "data": serializer.data
                    }, status=status.HTTP_200_OK)
                except RoomChat.DoesNotExist:
                    return Response({
                        "errorMessage": "Chat room not found",
                        "status_code": status.HTTP_404_NOT_FOUND,
                    }, status=status.HTTP_404_NOT_FOUND)
                
            all_rooms = RoomChat.objects.filter(
                Q(sender=request.user) | Q(receiver=request.user)
            )
            serializer = RoomChatSerializer(all_rooms, many=True, context={'request': request})
            return Response({
                "successMessage": "All chat rooms retrieved successfully",
                "status_code": status.HTTP_200_OK,
                "data": serializer.data
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='registration')
    def user_registration(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "successMessage": "User created successfully",
                "status_code": status.HTTP_201_CREATED,
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        error_data = ''
        for field, errors in serializer.errors.items():
            for error in errors:
                error_data += f"{field}: {error}. "

        return Response({
            "errorMessage": error_data,
            "status_code": status.HTTP_400_BAD_REQUEST,
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post', 'get'], url_path='data-processor')
    def data_processor(self, request):
        if request.method == 'POST':
            serializer = SeismicDataSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                seismic_data = serializer.save()
                return Response({
                    "successMessage": "Seismic data processed successfully",
                    "status_code": status.HTTP_201_CREATED,
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

            error_data = ''
            for field, errors in serializer.errors.items():
                for error in errors:
                    error_data += f"{field}: {error}. "

            return Response({
                "errorMessage": error_data,
                "status_code": status.HTTP_400_BAD_REQUEST,
            }, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            all_file = SeismicData.objects.all()
            serializer = SeismicDataSerializer(all_file, many=True, context={'request': request})
            return Response({
                "successMessage": "All seismic data retrieved successfully",
                "status_code": status.HTTP_200_OK,
                "data": serializer.data
            }, status=status.HTTP_200_OK)