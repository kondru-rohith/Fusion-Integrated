import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import MyApplicationsPage from "./MyApplicationsPage";

const auth = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);

const hooks = vi.hoisted(() => ({
  useMyApplications: vi.fn(),
  useApplication: vi.fn(),
  useApplicationHistory: vi.fn(),
  useSubmitApplication: vi.fn(),
  useResubmitApplication: vi.fn(),
  useWithdrawApplication: vi.fn(),
  useAttachDocument: vi.fn(),
  useDeactivateDocument: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleApplication = {
  id: 101,
  application_number: "SPACS-2026-0001",
  catalogue_entry: 10,
  catalogue_version: 1,
  user_id: 42,
  cycle: "2026-27",
  scheme_kind: "scholarship",
  is_renewal: false,
  parent_application: null,
  status: "submitted",
  cpi_at_apply: "8.45",
  annual_income_declared: "450000.00",
  demographic_snapshot: {},
  submission_data: {
    bank_account_number: "987654321012",
    bank_ifsc: "SBIN0001234",
    bank_name: "State Bank of India",
    statement_of_purpose: "Pursuing research in distributed systems.",
  },
  submitted_at: "2026-08-15T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  created_at: "2026-08-15T09:00:00Z",
  updated_at: "2026-08-15T10:00:00Z",
  scheme_title: "Merit-cum-Means Scholarship",
} as unknown as ScholarshipApplication;

describe("MyApplicationsPage", () => {
  beforeEach(() => {
    auth.useAuth.mockReturnValue({
      session: {
        user: { id: 42, username: "stu00001", display_name: "Student One", kind: "student" },
        roles: ["student"],
      },
      can: () => true,
    });
    hooks.useMyApplications.mockReturnValue({
      data: [sampleApplication],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useApplication.mockReturnValue({
      data: sampleApplication,
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useApplicationHistory.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });
    hooks.useSubmitApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useResubmitApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useWithdrawApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useAttachDocument.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useDeactivateDocument.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders student applications with tracking details", () => {
    render(
      <MantineProvider>
        <MyApplicationsPage />
      </MantineProvider>,
    );

    expect(screen.getByText("SPACS-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Merit-cum-Means Scholarship")).toBeInTheDocument();
    expect(screen.getByText("8.45")).toBeInTheDocument();
    expect(screen.getByText(/450000|4,50,000|450,000/)).toBeInTheDocument();
  });

  it("renders error state when useMyApplications returns an error (R2-12)", () => {
    hooks.useMyApplications.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Failed to load applications"),
      refetch: vi.fn(),
    });

    render(
      <MantineProvider>
        <MyApplicationsPage />
      </MantineProvider>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Could not load this/i)).toBeInTheDocument();
    expect(screen.queryByText("SPACS-2026-0001")).not.toBeInTheDocument();
  });

  it("renders empty state when student has zero applications (R2-12)", () => {
    hooks.useMyApplications.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <MantineProvider>
        <MyApplicationsPage />
      </MantineProvider>,
    );

    expect(screen.getByText(/No applications submitted yet/i)).toBeInTheDocument();
  });
});
