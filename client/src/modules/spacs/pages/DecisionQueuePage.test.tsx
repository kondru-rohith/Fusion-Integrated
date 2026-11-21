import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import DecisionQueuePage from "./DecisionQueuePage";

const auth = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);

const hooks = vi.hoisted(() => ({
  useDecisionQueue: vi.fn(),
  useApplication: vi.fn(),
  useApplicationHistory: vi.fn(),
  useMakeDecision: vi.fn(),
  useWithdrawApplication: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleVerifiedRow: ScholarshipApplication = {
  id: 1,
  user_id: 1001,
  application_number: "SPACS-2026-001",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "verified",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.50",
  annual_income_declared: "450000.00",
  demographic_snapshot: {},
  submission_data: {},
  required_documents: [],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-10T10:00:00Z",
};

const sampleConcernRow: ScholarshipApplication = {
  id: 2,
  user_id: 1002,
  application_number: "SPACS-2026-002",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "verification_concern",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.20",
  annual_income_declared: "550000.00",
  demographic_snapshot: {},
  submission_data: {},
  required_documents: [],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: 1891,
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-10T10:00:00Z",
};

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderPage() {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <DecisionQueuePage />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("DecisionQueuePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1000, username: "convener", display_name: "Convener", kind: "staff" },
        roles: ["spacs_convener"],
      },
    });
    hooks.useDecisionQueue.mockReturnValue({
      data: [sampleVerifiedRow, sampleConcernRow],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useApplication.mockReturnValue({ data: null, isPending: false });
    hooks.useApplicationHistory.mockReturnValue({ data: { results: [] }, isPending: false });
    hooks.useMakeDecision.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useWithdrawApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("distinguishes concern applications from normal verified applications in action buttons", () => {
    renderPage();

    // Normal verified row has "Sanction Decision"
    expect(screen.getByTestId("sanction-btn-1")).toHaveTextContent(/Sanction Decision/i);

    // Concerned row has "Review Concern & Decide"
    expect(screen.getByTestId("review-concern-btn-2")).toHaveTextContent(
      /Review Concern & Decide/i,
    );
  });
});
