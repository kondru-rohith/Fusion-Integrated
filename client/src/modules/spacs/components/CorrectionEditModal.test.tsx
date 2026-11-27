import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ScholarshipApplication } from "../api/types";
import { CorrectionEditModal } from "./CorrectionEditModal";

const hooks = vi.hoisted(() => ({
  useApplication: vi.fn(),
  useUpdateDraft: vi.fn(),
  useResubmitApplication: vi.fn(),
  useAttachDocument: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleCorrectionApp: ScholarshipApplication = {
  id: 42,
  user_id: 1001,
  application_number: "SPACS-202627-0042",
  catalogue_entry: 10,
  catalogue_version: 1,
  scheme_title: "Merit-cum-Means Scholarship",
  scheme_kind: "scholarship",
  cycle: "2026-27",
  status: "correction_required",
  is_renewal: false,
  parent_application: null,
  cpi_at_apply: "8.50",
  annual_income_declared: "350000.00",
  demographic_snapshot: {},
  submission_data: {
    bank_account: "1122334455",
    bank_ifsc: "SBIN0001234",
    bank_name: "SBI Campus",
    statement_of_purpose: "Original statement of purpose.",
    document_ids: [10],
  },
  required_documents: ["income_certificate"],
  submitted_at: "2026-08-10T10:00:00Z",
  resubmitted_at: null,
  withdrawn_at: null,
  withdrawn_reason: "",
  assigned_assistant_id: null,
  documents: [
    {
      id: 10,
      user_id: 1001,
      application: 42,
      doc_type: "income_certificate",
      title: "Old Income Certificate",
      original_filename: "income.pdf",
      drive_url: "https://drive.google.com/file/d/abc/view",
      drive_file_id: "abc",
      issued_date: "2026-01-01",
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
  updated_at: "2026-08-10T10:00:00Z",
};

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderModal(props = {}) {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <CorrectionEditModal
          opened={true}
          onClose={vi.fn()}
          applicationId={42}
          requiredDocuments={["income_certificate"]}
          {...props}
        />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("CorrectionEditModal", () => {
  const mutateUpdateAsync = vi.fn().mockResolvedValue({ id: 42 });
  const mutateResubmitAsync = vi.fn().mockResolvedValue({ id: 42, status: "resubmitted" });

  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useApplication.mockReturnValue({ data: sampleCorrectionApp, isPending: false });
    hooks.useUpdateDraft.mockReturnValue({
      mutateAsync: mutateUpdateAsync,
      isPending: false,
    });
    hooks.useResubmitApplication.mockReturnValue({
      mutateAsync: mutateResubmitAsync,
      isPending: false,
    });
    hooks.useAttachDocument.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  it("prefills all previously submitted information and attached documents", () => {
    renderModal();

    expect(screen.getByDisplayValue("1122334455")).toBeInTheDocument();
    expect(screen.getByDisplayValue("SBIN0001234")).toBeInTheDocument();
    expect(screen.getByDisplayValue("SBI Campus")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Original statement of purpose.")).toBeInTheDocument();
    expect(screen.getByText(/Old Income Certificate/i)).toBeInTheDocument();
  });

  it("does not allow manual editing of CPI and shows notice", () => {
    renderModal();
    expect(screen.getByText(/CPI is verified automatically/i)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /CPI/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton", { name: /CPI/i })).not.toBeInTheDocument();
  });

  it("allows modifying fields and resubmitting the existing application", async () => {
    const handleSuccess = vi.fn();
    renderModal({ onSuccess: handleSuccess });

    const bankInput = screen.getByDisplayValue("1122334455");
    fireEvent.change(bankInput, { target: { value: "9988776655" } });

    const ifscInput = screen.getByDisplayValue("SBIN0001234");
    fireEvent.change(ifscInput, { target: { value: "HDFC0001234" } });

    const saveBtn = screen.getByTestId("save-resubmit-btn");
    fireEvent.click(saveBtn);

    await vi.waitFor(() => {
      expect(mutateUpdateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 42,
          submission_data: expect.objectContaining({
            bank_account: "9988776655",
            bank_ifsc: "HDFC0001234",
          }),
        }),
      );
      expect(mutateResubmitAsync).toHaveBeenCalledWith(42);
    });
  });
});
