import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CatalogueEntry, CatalogueVersion } from "../api/types";
import CatalogueAdminPage from "./CatalogueAdminPage";

const hooks = vi.hoisted(() => ({
  useCatalogue: vi.fn(),
  useCatalogueEntries: vi.fn(),
  useCreateCatalogueEntry: vi.fn(),
  useCreateCatalogueVersion: vi.fn(),
  usePublishCatalogueVersion: vi.fn(),
  useRetireCatalogueEntry: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleVersionedEntry: CatalogueEntry = {
  id: 10,
  code: "mcm-2026",
  title: "Merit-cum-Means Scholarship",
  kind: "scholarship",
  description: "Financial assistance for meritorious students",
  status: "active",
  allow_multiple_applications: false,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

const sampleUnversionedEntry: CatalogueEntry = {
  id: 20,
  code: "director-gold-medal",
  title: "Director Gold Medal",
  kind: "award",
  description: "Top graduating student in the institute",
  status: "draft",
  allow_multiple_applications: false,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

const sampleVersion: CatalogueVersion = {
  id: 1,
  entry: 10,
  entry_code: "mcm-2026",
  entry_title: "Merit-cum-Means Scholarship",
  entry_kind: "scholarship",
  version_number: 1,
  academic_year: "2026-27",
  status: "published",
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
  eligibility_criteria: { min_cpi: 6.5, income_ceiling: 600000 },
  required_documents: ["income_certificate"],
  renewal_criteria: {},
  committee_config: {},
  published_at: "2026-07-01T00:00:00Z",
  published_by: 1,
  created_at: "2026-07-01T00:00:00Z",
};

describe("CatalogueAdminPage", () => {
  let mutateCreateVersion: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mutateCreateVersion = vi.fn();

    hooks.useCatalogue.mockReturnValue({
      data: [sampleVersion],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useCatalogueEntries.mockReturnValue({
      data: [sampleVersionedEntry, sampleUnversionedEntry],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useCreateCatalogueEntry.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useCreateCatalogueVersion.mockReturnValue({
      mutate: mutateCreateVersion,
      isPending: false,
    });
    hooks.usePublishCatalogueVersion.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useRetireCatalogueEntry.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("displays an entry with no versions and a 'Create First Version' action", () => {
    render(
      <MantineProvider>
        <CatalogueAdminPage />
      </MantineProvider>,
    );

    expect(screen.getByText("Schemes Awaiting First Version")).toBeInTheDocument();
    expect(screen.getByText("Director Gold Medal")).toBeInTheDocument();
    expect(screen.getByText(/Code: director-gold-medal/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create First Version/i })).toBeInTheDocument();
  });

  it("opens the version modal when clicking 'Create First Version' and submits with correct entry ID", async () => {
    render(
      <MantineProvider>
        <CatalogueAdminPage />
      </MantineProvider>,
    );

    const firstVersionBtn = screen.getByRole("button", { name: /Create First Version/i });
    fireEvent.click(firstVersionBtn);

    expect(await screen.findByText("Draft Version for Director Gold Medal")).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Create Draft Version/i });
    fireEvent.click(submitBtn);

    expect(mutateCreateVersion).toHaveBeenCalledWith(
      expect.objectContaining({
        entryId: 20,
        academic_year: "2026-27",
      }),
      expect.any(Object),
    );
  });

  it("preserves 'Draft Next Cycle Version' action for existing version rows", async () => {
    render(
      <MantineProvider>
        <CatalogueAdminPage />
      </MantineProvider>,
    );

    const nextCycleBtn = screen.getByRole("button", { name: /Draft Next Cycle Version/i });
    expect(nextCycleBtn).toBeInTheDocument();

    fireEvent.click(nextCycleBtn);

    expect(
      await screen.findByText("Draft Version for Merit-cum-Means Scholarship"),
    ).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Create Draft Version/i });
    fireEvent.click(submitBtn);

    expect(mutateCreateVersion).toHaveBeenCalledWith(
      expect.objectContaining({
        entryId: 10,
        academic_year: "2026-27",
      }),
      expect.any(Object),
    );
  });
});
