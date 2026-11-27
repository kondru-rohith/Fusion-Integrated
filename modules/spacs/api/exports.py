"""Application export and print service (UC-SPACS-007, BR-SPACS-012)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.directory import contracts as directory
from modules.spacs.api.permissions import MODULE, P_APP_EXPORT
from modules.spacs.selectors import applications as app_selectors


class ApplicationExportView(APIView):
    """Generate structured printable export of a student's application (UC-007, BR-012)."""

    permission_classes = [MODULE, HasPermission(P_APP_EXPORT)]

    @extend_schema(responses={200: dict})
    def get(self, request, pk: int):
        app = app_selectors.get_application_or_404(pk, request.principal)

        user_info = directory.get_users([app.user_id]).get(app.user_id)
        docs = [
            {
                "doc_type": d.doc_type,
                "title": d.title,
                "drive_url": d.drive_url,
                "verified": d.verification_status,
            }
            for d in app.documents.filter(is_active=True)
        ]

        summary = {
            "application_number": app.application_number,
            "status": app.status,
            "scheme_code": app.catalogue_entry.code,
            "scheme_title": app.catalogue_entry.title,
            "academic_year": app.academic_year,
            "cycle": app.cycle,
            "is_renewal": app.is_renewal,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "applicant": {
                "user_id": app.user_id,
                "name": user_info.display_name if user_info else "",
                "username": user_info.username if user_info else "",
                "department": user_info.department if user_info else "",
                "programme": user_info.programme if user_info else "",
                "cpi_at_apply": str(app.cpi_at_apply) if app.cpi_at_apply else None,
                "declared_income": str(app.annual_income_declared)
                if app.annual_income_declared
                else None,
            },
            "submission_data": app.submission_data,
            "documents": docs,
        }
        return Response(summary)
