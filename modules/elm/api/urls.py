from django.urls import path
from .views import (
    LeaveTypeListView,
    LeaveRequestListView,
    LeaveRequestDetailView,
    LeaveRequestUpdateView,
    LeaveRequestDeleteView,
    LeaveBalanceListView,
    SubstituteResponseListView,
)

urlpatterns = [
    path("leave-types/", LeaveTypeListView.as_view(), name="leave-type-list"),
    path("leave-requests/", LeaveRequestListView.as_view(), name="leave-request-list"),
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path("leave-requests/<int:pk>/update/", LeaveRequestUpdateView.as_view(), name="leave-request-update"),
    path("leave-requests/<int:pk>/delete/", LeaveRequestDeleteView.as_view(), name="leave-request-delete"),
    path("leave-balances/", LeaveBalanceListView.as_view(), name="leave-balance-list"),
    path("substitute-responses/", SubstituteResponseListView.as_view(), name="substitute-response-list"),
]
