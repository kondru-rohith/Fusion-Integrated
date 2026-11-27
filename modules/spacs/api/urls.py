from django.urls import path

from modules.spacs.api import views as v
from modules.spacs.api.exports import ApplicationExportView

urlpatterns = [
    # Catalogue
    path("catalogue/", v.CatalogueListView.as_view(), name="spacs-catalogue-list"),
    path(
        "catalogue/entries/",
        v.CatalogueEntryCreateView.as_view(),
        name="spacs-catalogue-entry-create",
    ),
    path(
        "catalogue/entries/<int:pk>/versions/",
        v.CatalogueVersionCreateView.as_view(),
        name="spacs-catalogue-version-create",
    ),
    path(
        "catalogue/versions/<int:pk>/publish/",
        v.CatalogueVersionPublishView.as_view(),
        name="spacs-catalogue-version-publish",
    ),
    path(
        "catalogue/entries/<int:pk>/retire/",
        v.CatalogueEntryRetireView.as_view(),
        name="spacs-catalogue-entry-retire",
    ),
    # Applications
    path("applications/mine/", v.MyApplicationsListView.as_view(), name="spacs-applications-mine"),
    path("applications/", v.ApplicationDraftCreateView.as_view(), name="spacs-applications-create"),
    path("applications/renew/", v.ApplyRenewalView.as_view(), name="spacs-applications-renew"),
    path(
        "applications/<int:pk>/", v.ApplicationDetailView.as_view(), name="spacs-application-detail"
    ),
    path(
        "applications/<int:pk>/submit/",
        v.ApplicationSubmitView.as_view(),
        name="spacs-application-submit",
    ),
    path(
        "applications/<int:pk>/resubmit/",
        v.ApplicationResubmitView.as_view(),
        name="spacs-application-resubmit",
    ),
    path(
        "applications/<int:pk>/withdraw/",
        v.ApplicationWithdrawView.as_view(),
        name="spacs-application-withdraw",
    ),
    path(
        "applications/<int:pk>/history/",
        v.ApplicationHistoryView.as_view(),
        name="spacs-application-history",
    ),
    path(
        "applications/<int:pk>/export/",
        ApplicationExportView.as_view(),
        name="spacs-application-export",
    ),
    # Verification Queue (Assistant)
    path("verification/queue/", v.VerificationQueueView.as_view(), name="spacs-verification-queue"),
    path(
        "verification/<int:pk>/finding/",
        v.VerificationFindingCreateView.as_view(),
        name="spacs-verification-finding",
    ),
    # Decisions Queue (Convener)
    path("decisions/queue/", v.DecisionQueueView.as_view(), name="spacs-decision-queue"),
    path(
        "decisions/<int:pk>/outcome/",
        v.DecisionOutcomeCreateView.as_view(),
        name="spacs-decision-outcome",
    ),
    # Documents
    path("documents/reusable/", v.ReusableDocumentsView.as_view(), name="spacs-documents-reusable"),
    path("documents/attach-link/", v.AttachDocumentView.as_view(), name="spacs-documents-attach"),
    path(
        "documents/<int:pk>/deactivate/",
        v.DeactivateDocumentView.as_view(),
        name="spacs-documents-deactivate",
    ),
    # Awards
    path("awards/cycles/", v.AwardCycleListCreateView.as_view(), name="spacs-awards-cycles"),
    path(
        "awards/cycles/<int:pk>/",
        v.AwardCycleDetailView.as_view(),
        name="spacs-awards-cycle-detail",
    ),
    path(
        "awards/cycles/<int:pk>/prepare-pool/",
        v.AwardPreparePoolView.as_view(),
        name="spacs-awards-prepare-pool",
    ),
    path(
        "awards/candidates/<int:pk>/evaluate/",
        v.AwardCandidateEvaluateView.as_view(),
        name="spacs-awards-candidate-evaluate",
    ),
    path(
        "awards/cycles/<int:pk>/record-outcome/",
        v.AwardRecordOutcomeView.as_view(),
        name="spacs-awards-record-outcome",
    ),
    path(
        "awards/cycles/<int:pk>/record-approval/",
        v.AwardRecordApprovalView.as_view(),
        name="spacs-awards-record-approval",
    ),
    path(
        "awards/cycles/<int:pk>/publish/", v.AwardPublishView.as_view(), name="spacs-awards-publish"
    ),
    # Audit
    path("audit/", v.AuditLogListView.as_view(), name="spacs-audit-list"),
]
