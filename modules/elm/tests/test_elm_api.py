import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from modules.elm.models import LeaveType, LeaveRequest, LeaveBalance, SubstituteResponse
from modules.elm.api.serializers import LeaveTypeSerializer, LeaveRequestSerializer, LeaveBalanceSerializer, SubstituteResponseSerializer
from django.contrib.auth.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpassword')

@pytest.fixture
def leave_type():
    return LeaveType.objects.create(name='Sick Leave')

@pytest.fixture
def leave_request(user, leave_type):
    return LeaveRequest.objects.create(user=user, leave_type=leave_type, start_date='2023-01-01', end_date='2023-01-05')

@pytest.fixture
def leave_balance(user, leave_type):
    return LeaveBalance.objects.create(user=user, leave_type=leave_type, balance=10)

@pytest.fixture
def substitute_response(user, leave_request):
    return SubstituteResponse.objects.create(leave_request=leave_request, substitute_user=user, response_date='2023-01-01')

def test_get_leave_types(api_client, leave_type):
    url = reverse('leave-type-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['name'] == leave_type.name

def test_create_leave_request(api_client, user, leave_type):
    api_client.force_authenticate(user=user)
    url = reverse('leave-request-list')
    data = {
        'leave_type': leave_type.id,
        'start_date': '2023-02-01',
        'end_date': '2023-02-05'
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['start_date'] == '2023-02-01'
    assert response.data['end_date'] == '2023-02-05'

def test_get_leave_requests(api_client, user, leave_request):
    api_client.force_authenticate(user=user)
    url = reverse('leave-request-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['start_date'] == '2023-01-01'
    assert response.data[0]['end_date'] == '2023-01-05'

def test_update_leave_request(api_client, user, leave_request):
    api_client.force_authenticate(user=user)
    url = reverse('leave-request-detail', args=[leave_request.id])
    data = {
        'leave_type': leave_request.leave_type.id,
        'start_date': '2023-03-01',
        'end_date': '2023-03-05'
    }
    response = api_client.put(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['start_date'] == '2023-03-01'
    assert response.data['end_date'] == '2023-03-05'

def test_delete_leave_request(api_client, user, leave_request):
    api_client.force_authenticate(user=user)
    url = reverse('leave-request-detail', args=[leave_request.id])
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert LeaveRequest.objects.count() == 0

def test_get_leave_balances(api_client, user, leave_balance):
    api_client.force_authenticate(user=user)
    url = reverse('leave-balance-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['balance'] == 10

def test_create_substitute_response(api_client, user, leave_request):
    api_client.force_authenticate(user=user)
    url = reverse('substitute-response-list')
    data = {
        'leave_request': leave_request.id,
        'substitute_user': user.id,
        'response_date': '2023-04-01'
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['response_date'] == '2023-04-01'

def test_get_substitute_responses(api_client, user, substitute_response):
    api_client.force_authenticate(user=user)
    url = reverse('substitute-response-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['response_date'] == '2023-01-01'
