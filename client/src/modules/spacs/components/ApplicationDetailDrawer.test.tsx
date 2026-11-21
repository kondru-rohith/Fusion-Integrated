import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import { ApplicationDetailDrawer } from "./ApplicationDetailDrawer";

const auth = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);

const hooks = vi.hoisted(() => ({
  useApplication: vi.fn(),
  useApplicationHistory: vi.fn(),
  useResubmitApplication: vi.fn(),
  useWithdrawApplication: vi.fn(),
  useUpdateDraft: vi.fn(),
  useAttachDocument: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleApplication = {
  id: 42,
  user_id: 1001,
  application_number: "SPACS-202627-0042",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "submitted",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.50",
  annual_income_declared: "450000.00",
  demographic_snapshot: {},
  submission_data: {},
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  documents: [],
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-10T10:00:00Z",
} as unknown as ScholarshipApplication;

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderDrawer() {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <ApplicationDetailDrawer opened={true} onClose={vi.fn()} applicationId={42} />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("ApplicationDetailDrawer withdrawal action visibility", () => {
  beforeEach(() => {
    hooks.useApplication.mockReturnValue({ data: sampleApplication, isPending: false });
    hooks.useApplicationHistory.mockReturnValue({ data: { results: [] }, isPending: false });
    hooks.useResubmitApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useWithdrawApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useUpdateDraft.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hooks.useAttachDocument.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders Withdraw Application button for the owning student", () => {
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1001, username: "stu00001", display_name: "Student One", kind: "student" },
        roles: ["student"],
      },
    });

    renderDrawer();
    expect(screen.getByRole("button", { name: /Withdraw Application/i })).toBeInTheDocument();
  });

  it("hides Withdraw Application button for SPACS Assistant", () => {
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1891, username: "usr01891", display_name: "Assistant User", kind: "staff" },
        roles: ["spacs_assistant"],
      },
    });

    renderDrawer();
    expect(screen.queryByRole("button", { name: /Withdraw Application/i })).not.toBeInTheDocument();
  });

  it("hides Withdraw Application button for SPACS Convener", () => {
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1000, username: "convener", display_name: "Convener User", kind: "staff" },
        roles: ["spacs_convener"],
      },
    });

    renderDrawer();
    expect(screen.queryByRole("button", { name: /Withdraw Application/i })).not.toBeInTheDocument();
  });

  it("hides Withdraw Application button for a different student", () => {
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1002, username: "stu00002", display_name: "Student Two", kind: "student" },
        roles: ["student"],
      },
    });

    renderDrawer();
    expect(screen.queryByRole("button", { name: /Withdraw Application/i })).not.toBeInTheDocument();
  });

  it("renders Resubmit Corrected Application button for owner when correction_required", () => {
    hooks.useApplication.mockReturnValue({
      data: { ...sampleApplication, status: "correction_required" },
      isPending: false,
    });
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1001, username: "stu00001", display_name: "Student One", kind: "student" },
        roles: ["student"],
      },
    });

    renderDrawer();
    expect(
      screen.getByRole("button", { name: /Resubmit Corrected Application/i }),
    ).toBeInTheDocument();
  });

  it("hides Resubmit button for assistant and convener even if correction_required", () => {
    hooks.useApplication.mockReturnValue({
      data: { ...sampleApplication, status: "correction_required" },
      isPending: false,
    });
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1891, username: "usr01891", display_name: "Assistant User", kind: "staff" },
        roles: ["spacs_assistant"],
      },
    });

    renderDrawer();
    expect(
      screen.queryByRole("button", { name: /Resubmit Corrected Application/i }),
    ).not.toBeInTheDocument();
  });

  it("hides Resubmit button when application status is not correction_required", () => {
    hooks.useApplication.mockReturnValue({
      data: { ...sampleApplication, status: "submitted" },
      isPending: false,
    });
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1001, username: "stu00001", display_name: "Student One", kind: "student" },
        roles: ["student"],
      },
    });

    renderDrawer();
    expect(
      screen.queryByRole("button", { name: /Resubmit Corrected Application/i }),
    ).not.toBeInTheDocument();
  });

  it("renders Verification Concern Raised banner and comments when status is verification_concern", () => {
    hooks.useApplication.mockReturnValue({
      data: {
        ...sampleApplication,
        status: "verification_concern",
        verification_findings: [
          {
            id: 1,
            reviewer_id: 1891,
            action: "concern_raised",
            comments: "Income certificate stamp is unclear and needs investigation.",
            created_at: "2026-08-11T12:00:00Z",
          },
        ],
      },
      isPending: false,
    });
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 1000, username: "convener", display_name: "Convener", kind: "staff" },
        roles: ["spacs_convener"],
      },
    });

    renderDrawer();
    expect(screen.getByTestId("verification-concern-drawer-banner")).toBeInTheDocument();
    expect(screen.getByText(/Income certificate stamp is unclear/i)).toBeInTheDocument();
    expect(screen.getByText(/u1891/i)).toBeInTheDocument();
  });
});
