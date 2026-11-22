import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import VerificationQueuePage from "./VerificationQueuePage";

const auth = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);

const hooks = vi.hoisted(() => ({
  useVerificationQueue: vi.fn(),
  useApplication: vi.fn(),
  useApplicationHistory: vi.fn(),
  useRecordVerification: vi.fn(),
  useRecordFinding: vi.fn(),
  useWithdrawApplication: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleQueueItem: ScholarshipApplication = {
  id: 101,
  user_id: 2001,
  application_number: "SPACS-2026-VQ-001",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "under_verification",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.45",
  annual_income_declared: "350000.00",
  demographic_snapshot: {},
  submission_data: {},
  required_documents: ["income_certificate"],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-10T10:00:00Z",
};

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderPage() {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <VerificationQueuePage />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("VerificationQueuePage", () => {
  let refetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    auth.useAuth.mockReturnValue({
      session: { user: { id: 1001, kind: "staff" }, roles: ["spacs_assistant"] },
      can: () => true,
    });
    refetchMock = vi.fn();
    hooks.useVerificationQueue.mockReturnValue({
      data: [sampleQueueItem],
      isPending: false,
      error: null,
      refetch: refetchMock,
    });
    hooks.useApplication.mockReturnValue({ data: null, isPending: false });
    hooks.useApplicationHistory.mockReturnValue({ data: { results: [] }, isPending: false });
    hooks.useRecordVerification.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useRecordFinding.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useWithdrawApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders page header and pending applications table", () => {
    renderPage();

    expect(screen.getByText("Application Verification Queue")).toBeInTheDocument();
    expect(screen.getByText("SPACS-2026-VQ-001")).toBeInTheDocument();
    expect(screen.getByText("Merit-cum-Means Scholarship")).toBeInTheDocument();
    expect(screen.getByText("Student u2001")).toBeInTheDocument();
    expect(screen.getByText("8.45")).toBeInTheDocument();
  });

  it("renders empty state when queue is empty", () => {
    hooks.useVerificationQueue.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
      refetch: refetchMock,
    });

    renderPage();

    expect(screen.getByText("No pending applications")).toBeInTheDocument();
    expect(screen.getByText("Verification queue is empty.")).toBeInTheDocument();
  });

  it("renders error state on hook failure", () => {
    hooks.useVerificationQueue.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Queue network error"),
      refetch: refetchMock,
    });

    renderPage();

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders verify button and opens verification modal on click", () => {
    renderPage();

    const verifyBtn = screen.getByRole("button", { name: /Verify/i });
    expect(verifyBtn).toBeInTheDocument();

    fireEvent.click(verifyBtn);
    expect(screen.getByText(/Record Verification Finding/i)).toBeInTheDocument();
  });
});
