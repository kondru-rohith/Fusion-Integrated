import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import { DecisionModal } from "./DecisionModal";

const hooks = vi.hoisted(() => ({
  useApplication: vi.fn(),
  useMakeDecision: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleVerifiedApp: ScholarshipApplication = {
  id: 101,
  user_id: 1001,
  application_number: "SPACS-202627-0101",
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
  required_documents: ["income_certificate"],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  documents: [
    {
      id: 1,
      user_id: 1001,
      application: 101,
      doc_type: "income_certificate",
      title: "Valid Income Certificate",
      original_filename: "income.pdf",
      drive_url: "https://drive.google.com/file/d/123/view",
      drive_file_id: "123",
      issued_date: "2026-01-01",
      valid_until: null,
      is_active: true,
      is_reusable: true,
      verification_status: "valid",
      verification_notes: "Verified by u1891",
      verified_at: "2026-08-11T10:00:00Z",
      created_at: "2026-08-10T10:00:00Z",
    },
  ],
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-11T10:00:00Z",
};

const sampleConcernApp: ScholarshipApplication = {
  id: 102,
  user_id: 1002,
  application_number: "SPACS-202627-0102",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "verification_concern",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.10",
  annual_income_declared: "300000.00",
  demographic_snapshot: {},
  submission_data: {},
  required_documents: ["income_certificate"],
  verification_findings: [
    {
      id: 5,
      application: 102,
      reviewer_id: 1891,
      action: "concern_raised",
      comments: "Income certificate issuance date precedes current financial year.",
      correction_fields: [],
      created_at: "2026-08-12T11:00:00Z",
    },
  ],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: 1891,
  documents: [
    {
      id: 2,
      user_id: 1002,
      application: 102,
      doc_type: "income_certificate",
      title: "Dated Income Certificate",
      original_filename: "income.pdf",
      drive_url: "https://drive.google.com/file/d/456/view",
      drive_file_id: "456",
      issued_date: "2024-01-01",
      valid_until: null,
      is_active: true,
      is_reusable: true,
      verification_status: "pending",
      verification_notes: "",
      verified_at: null,
      created_at: "2026-08-10T10:00:00Z",
    },
  ],
  created_at: "2026-08-10T10:00:00Z",
  updated_at: "2026-08-12T11:00:00Z",
};

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderModal(app: ScholarshipApplication) {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <DecisionModal opened={true} onClose={vi.fn()} application={app} />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("DecisionModal Workflow", () => {
  const mutateDecision = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useMakeDecision.mockReturnValue({
      mutate: mutateDecision,
      isPending: false,
    });
  });

  describe("Normal verified application workflow", () => {
    beforeEach(() => {
      hooks.useApplication.mockReturnValue({
        data: sampleVerifiedApp,
        isPending: false,
      });
    });

    it("displays normal sanction workflow without concern banner or extra steps", () => {
      renderModal(sampleVerifiedApp);

      expect(screen.queryByTestId("verification-concern-banner")).not.toBeInTheDocument();
      expect(screen.queryByTestId("acknowledge-concern-checkbox")).not.toBeInTheDocument();
      expect(screen.getByText(/Approve & Sanction Scholarship/i)).toBeInTheDocument();
      expect(screen.getByText(/Reject Application/i)).toBeInTheDocument();
    });

    it("allows convener to sanction a verified application with valid documents", () => {
      renderModal(sampleVerifiedApp);

      const refInput = screen.getByLabelText(/Sanction Order Reference/i);
      fireEvent.change(refInput, { target: { value: "SPACS/2026/MCM/001" } });

      const rationaleInput = screen.getByLabelText(/Decision Rationale/i);
      fireEvent.change(rationaleInput, { target: { value: "Eligible and top ranker." } });

      const confirmBtn = screen.getByTestId("confirm-decision-btn");
      fireEvent.click(confirmBtn);

      expect(mutateDecision).toHaveBeenCalledWith(
        expect.objectContaining({
          applicationId: 101,
          decision: "approved",
          sanction_order_ref: "SPACS/2026/MCM/001",
          rationale: "Eligible and top ranker.",
        }),
        expect.anything(),
      );
    });
  });

  describe("Verification concern workflow", () => {
    beforeEach(() => {
      hooks.useApplication.mockReturnValue({
        data: sampleConcernApp,
        isPending: false,
      });
    });

    it("displays prominent warning banner, assistant comments, and actor timestamp", () => {
      renderModal(sampleConcernApp);

      expect(screen.getByTestId("verification-concern-banner")).toBeInTheDocument();
      expect(
        screen.getByText(/Income certificate issuance date precedes current financial year/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/u1891/i)).toBeInTheDocument();
      expect(screen.getByText(/Dated Income Certificate/i)).toBeInTheDocument();
    });

    it("requires convener to acknowledge concern before recording decision", () => {
      renderModal(sampleConcernApp);

      const confirmBtn = screen.getByTestId("confirm-decision-btn");
      expect(confirmBtn).toBeDisabled();

      const checkbox = screen.getByTestId("acknowledge-concern-checkbox");
      fireEvent.click(checkbox);

      // Confirm button is now enabled for return for correction
      expect(confirmBtn).not.toBeDisabled();
    });

    it("blocks sanction approval when required documents are pending", () => {
      renderModal(sampleConcernApp);

      const checkbox = screen.getByTestId("acknowledge-concern-checkbox");
      fireEvent.click(checkbox);

      // Select approved
      const approveRadio = screen.getByRole("radio", {
        name: /Resolve Concern & Sanction Scholarship/i,
      });
      // Option is disabled because required documents are pending
      expect(approveRadio).toBeDisabled();
    });

    it("allows convener to return application for correction", () => {
      renderModal(sampleConcernApp);

      const checkbox = screen.getByTestId("acknowledge-concern-checkbox");
      fireEvent.click(checkbox);

      const rationaleInput = screen.getByLabelText(/Decision Rationale/i);
      fireEvent.change(rationaleInput, {
        target: { value: "Please submit a current financial year income certificate." },
      });

      const confirmBtn = screen.getByTestId("confirm-decision-btn");
      fireEvent.click(confirmBtn);

      expect(mutateDecision).toHaveBeenCalledWith(
        expect.objectContaining({
          applicationId: 102,
          decision: "returned_for_correction",
          rationale: "Please submit a current financial year income certificate.",
        }),
        expect.anything(),
      );
    });
  });
});
