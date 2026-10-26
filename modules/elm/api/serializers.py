from rest_framework import serializers

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType, SubstituteResponse


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name']

class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())
    status = serializers.CharField(read_only=True, default='pending')

    class Meta:
        model = LeaveRequest
        fields = ['id', 'leave_type', 'user_id', 'start_date', 'end_date', 'reason', 'status']

    def create(self, validated_data):
        validated_data['status'] = 'pending'
        return super().create(validated_data)

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['id', 'leave_type', 'user_id', 'balance']

class SubstituteResponseSerializer(serializers.ModelSerializer):
    leave_request = serializers.PrimaryKeyRelatedField(queryset=LeaveRequest.objects.all())
    response = serializers.ChoiceField(choices=['accepted', 'rejected'])

    class Meta:
        model = SubstituteResponse
        fields = ['id', 'leave_request', 'substitute_user_id', 'response']
