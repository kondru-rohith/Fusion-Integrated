import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AwardCycle, CatalogueVersion } from "../api/types";
import AwardsPage from "./AwardsPage";

const hooks = vi.hoisted(() => ({
  useAwardCycles: vi.fn(),
  useAwardCycle: vi.fn(),
  useCatalogue: vi.fn(),
  useOpenAwardCycle: vi.fn(),
  usePrepareAwardPool: vi.fn(),
  useRecordAwardOutcome: vi.fn(),
  usePublishAward: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleCycle: AwardCycle = {
  id: 1,
  catalogue_version: 10,
  scheme_title: "Director Gold Medal",
  convocation_year: 2026,
  status: "cycle_open",
  institutional_approval_ref: "",
  published_at: null,
  published_by: null,
  candidates: [],
  created_at: "2026-08-01T00:00:00Z",
};

const sampleCatalogueVersion: CatalogueVersion = {
  id: 10,
  entry: 100,
  entry_code: "director-gold-medal",
  entry_title: "Director Gold Medal",
  entry_kind: "award",
  version_number: 1,
  academic_year: "2026-27",
  status: "published",
  policy_reference: "SENATE/2026/05",
  candidate_source: "system_generated",
  valid_from: "2026-08-01",
  valid_to: "2027-05-31",
  application_window_start: null,
  application_window_end: null,
  renewal_window_start: null,
  renewal_window_end: null,
  is_renewable: false,
  sla_threshold_days: 7,
  eligibility_criteria: {},
  required_documents: [],
  renewal_criteria: {},
  committee_config: {},
  published_at: "2026-07-01T00:00:00Z",
  published_by: 1,
  created_at: "2026-07-01T00:00:00Z",
};

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderPage() {
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <AwardsPage />
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("AwardsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useAwardCycles.mockReturnValue({
      data: [sampleCycle],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });
    hooks.useAwardCycle.mockReturnValue({
      data: null,
      isPending: false,
    });
    hooks.useCatalogue.mockReturnValue({
      data: [sampleCatalogueVersion],
      isPending: false,
    });
    hooks.useOpenAwardCycle.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.usePrepareAwardPool.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useRecordAwardOutcome.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.usePublishAward.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders page header and list of award cycles", () => {
    renderPage();

    expect(screen.getByText("Convocation Awards & Medals")).toBeInTheDocument();
    expect(screen.getByText("Director Gold Medal")).toBeInTheDocument();
    expect(screen.getByText(/Convocation Year: 2026/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open New Award Cycle/i })).toBeInTheDocument();
  });

  it("renders empty state when no award cycles exist", () => {
    hooks.useAwardCycles.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText("No award cycles found")).toBeInTheDocument();
  });

  it("renders error state when hook fails", () => {
    hooks.useAwardCycles.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Awards network error"),
      refetch: vi.fn(),
    });

    renderPage();

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders 'View Pool' action button for cycle", () => {
    renderPage();

    expect(screen.getByRole("button", { name: /View Pool/i })).toBeInTheDocument();
  });
});
