from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from modules.elm.models import (
    LeaveType,
    LeaveRequest,
    LeaveBalance,
    SubstituteResponse,
)
from modules.elm.api.serializers import (
    LeaveTypeSerializer,
    LeaveRequestSerializer,
    LeaveBalanceSerializer,
    SubstituteResponseSerializer,
)

class LeaveTypeListView(generics.ListAPIView):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]

class LeaveRequestListView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user_id=self.request.user.id)

class LeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user_id=self.request.user.id)

class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=self.request.user.id)

class SubstituteResponseListView(generics.ListCreateAPIView):
    serializer_class = SubstituteResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SubstituteResponse.objects.filter(leave_request__user_id=self.request.user.id)
