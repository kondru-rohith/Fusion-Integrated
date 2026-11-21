import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CatalogueVersion } from "../api/types";
import CataloguePage from "./CataloguePage";

const hooks = vi.hoisted(() => ({
  useCatalogue: vi.fn(),
  useDraftApplication: vi.fn(),
  useSubmitApplication: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);

const sampleScheme = {
  id: 1,
  entry: 10,
  entry_code: "mcm-2026",
  entry_title: "Merit-cum-Means Scholarship",
  entry_kind: "scholarship",
  version_number: 1,
  academic_year: "2026-27",
  status: "published",
  policy_reference: "SENATE/2026/04",
  published_at: "2026-07-01T00:00:00Z",
  published_by: 1,
  eligibility_criteria: {
    min_cpi: 6.5,
    income_ceiling: 600000,
  },
  required_documents: ["income_certificate", "grade_sheet"],
  valid_from: "2026-08-01",
  valid_to: "2027-05-31",
  application_window_start: "2026-08-01T00:00:00Z",
  application_window_end: "2027-09-30T23:59:59Z",
  created_at: "2026-07-01T00:00:00Z",
} as unknown as CatalogueVersion;

describe("CataloguePage", () => {
  beforeEach(() => {
    auth.useAuth.mockReturnValue({
      can: (p: string) => p === "spacs.application.create",
    });
    hooks.useCatalogue.mockReturnValue({
      data: [sampleScheme],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useDraftApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useSubmitApplication.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders active schemes with eligibility details and Apply button", () => {
    render(
      <MantineProvider>
        <CataloguePage />
      </MantineProvider>,
    );

    expect(screen.getByText("Merit-cum-Means Scholarship")).toBeInTheDocument();
    expect(screen.getByText(/Min CPI: 6.5/i)).toBeInTheDocument();
    expect(screen.getByText(/Income: <= ₹/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Apply Now/i })).toBeInTheDocument();
  });

  it("does not render Apply Now button for staff or assistant without application.create permission", () => {
    auth.useAuth.mockReturnValue({
      can: () => false,
    });

    render(
      <MantineProvider>
        <CataloguePage />
      </MantineProvider>,
    );

    expect(screen.getByText("Merit-cum-Means Scholarship")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Apply Now/i })).not.toBeInTheDocument();
  });
});
