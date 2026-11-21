import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** Lazy chunks per page matching server navigation contract */
const CataloguePage = lazy(() => import("./pages/CataloguePage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const VerificationQueuePage = lazy(() => import("./pages/VerificationQueuePage"));
const DecisionQueuePage = lazy(() => import("./pages/DecisionQueuePage"));
const CatalogueAdminPage = lazy(() => import("./pages/CatalogueAdminPage"));
const AwardsPage = lazy(() => import("./pages/AwardsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));

// Guard office pages according to permissions declared in registry.py
function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="catalogue" replace /> },
  { path: "catalogue", element: <CataloguePage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  {
    path: "verification-queue",
    element: office("spacs.application.review", <VerificationQueuePage />),
  },
  {
    path: "decision-queue",
    element: office("spacs.application.approve", <DecisionQueuePage />),
  },
  {
    path: "catalogue-admin",
    element: office("spacs.catalogue.manage", <CatalogueAdminPage />),
  },
  {
    path: "awards",
    element: office("spacs.award_candidate.review", <AwardsPage />),
  },
  {
    path: "audit",
    element: office("spacs.audit.view", <AuditPage />),
  },
];
