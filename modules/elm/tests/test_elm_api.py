from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from modules.elm.models import LeaveType, LeaveRequest, LeaveBalance, SubstituteResponse
from django.contrib.auth.models import User
from django.urls import reverse

class ElmAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.leave_type = LeaveType.objects.create(name='Sick Leave')
        self.leave_request = LeaveRequest.objects.create(
            user=self.user,
            leave_type=self.leave_type,
            start_date='2023-01-01',
            end_date='2023-01-05',
            reason='Sick'
        )
        self.leave_balance = LeaveBalance.objects.create(
            user=self.user,
            leave_type=self.leave_type,
            balance=10
        )
        self.substitute_response = SubstituteResponse.objects.create(
            leave_request=self.leave_request,
            substitute_user=self.user,
            response='Available'
        )

    def test_get_leave_types(self):
        url = reverse('leave-type-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.leave_type.name)

    def test_create_leave_request(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('leave-request-list')
        data = {
            'leave_type': self.leave_type.id,
            'start_date': '2023-02-01',
            'end_date': '2023-02-05',
            'reason': 'Sick'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['start_date'], '2023-02-01')
        self.assertEqual(response.data['end_date'], '2023-02-05')

    def test_get_leave_requests(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('leave-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['start_date'], '2023-01-01')
        self.assertEqual(response.data[0]['end_date'], '2023-01-05')

    def test_update_leave_request(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('leave-request-detail', args=[self.leave_request.id])
        data = {
            'leave_type': self.leave_request.leave_type.id,
            'start_date': '2023-03-01',
            'end_date': '2023-03-05',
            'reason': 'Sick'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['start_date'], '2023-03-01')
        self.assertEqual(response.data['end_date'], '2023-03-05')

    def test_delete_leave_request(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('leave-request-detail', args=[self.leave_request.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(LeaveRequest.objects.count(), 0)

    def test_get_leave_balances(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('leave-balance-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['balance'], 10)

    def test_create_substitute_response(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('substitute-response-list')
        data = {
            'leave_request': self.leave_request.id,
            'substitute_user': self.user.id,
            'response': 'Available'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['response'], 'Available')

    def test_get_substitute_responses(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('substitute-response-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['response'], 'Available')

    def test_unauthenticated_access(self):
        url = reverse('leave-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ownership_isolation(self):
        another_user = User.objects.create_user(username='anotheruser', password='anotherpassword')
        self.client.force_authenticate(user=another_user)
        url = reverse('leave-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
