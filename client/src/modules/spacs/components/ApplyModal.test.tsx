/**
 * ApplyModal – CPI information notice tests (BR-SPACS-001, ADR-0008).
 *
 * CPI is fetched from academic records at submission time.  The form must:
 *  - Show a CPI info alert when the scheme has a min_cpi requirement.
 *  - NOT show the CPI info alert when the scheme has no min_cpi requirement.
 */
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CatalogueVersion } from "../api/types";
import { ApplyModal } from "./ApplyModal";

// Stub all hooks so the modal renders without network
const hooks = vi.hoisted(() => ({
  useCreateDraft: vi.fn(),
  useUpdateDraft: vi.fn(),
  useSubmitApplication: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

// Stub the DocumentAttachModal (heavy dependency, not under test here)
vi.mock("./DocumentAttachModal", () => ({
  DocumentAttachModal: ({ opened }: { opened: boolean }) =>
    opened ? <div data-testid="doc-attach-modal" /> : null,
}));

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function wrap(ui: React.ReactElement) {
  return (
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <Notifications />
        {ui}
      </MantineProvider>
    </QueryClientProvider>
  );
}

function makeVersion(overrides?: Partial<CatalogueVersion>): CatalogueVersion {
  return {
    id: 1,
    entry: 10,
    entry_code: "mcm-2026",
    entry_title: "Merit-cum-Means Scholarship",
    entry_kind: "scholarship",
    version_number: 1,
    academic_year: "2026-27",
    policy_reference: "SENATE/2026/04",
    candidate_source: "student_application",
    valid_from: "2026-08-01",
    valid_to: "2027-05-31",
    application_window_start: "2026-08-01T00:00:00Z",
    application_window_end: "2027-09-30T23:59:59Z",
    renewal_window_start: null,
    renewal_window_end: null,
    is_renewable: false,
    sla_threshold_days: 7,
    eligibility_criteria: { min_cpi: 7.0, income_ceiling: 600000 },
    required_documents: ["income_certificate"],
    renewal_criteria: {},
    committee_config: {},
    status: "published",
    published_at: "2026-07-01T00:00:00Z",
    published_by: 1,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  } as CatalogueVersion;
}

describe("ApplyModal – CPI notice", () => {
  beforeEach(() => {
    hooks.useCreateDraft.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hooks.useUpdateDraft.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hooks.useSubmitApplication.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  it("shows CPI info alert when scheme has a min_cpi requirement", () => {
    const version = makeVersion({ eligibility_criteria: { min_cpi: 7.0 } });

    render(
      wrap(
        <ApplyModal
          opened
          onClose={vi.fn()}
          schemeVersion={version}
        />,
      ),
    );

    const alert = screen.getByTestId("cpi-info-alert");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toMatch(/CPI.*academic records/i);
    expect(alert.textContent).toMatch(/7/);
  });

  it("does NOT show CPI info alert when scheme has no min_cpi requirement", () => {
    const version = makeVersion({ eligibility_criteria: { income_ceiling: 600000 } });

    render(
      wrap(
        <ApplyModal
          opened
          onClose={vi.fn()}
          schemeVersion={version}
        />,
      ),
    );

    expect(screen.queryByTestId("cpi-info-alert")).not.toBeInTheDocument();
  });
});
