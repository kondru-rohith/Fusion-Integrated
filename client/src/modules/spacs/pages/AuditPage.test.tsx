import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SpacsAuditLog } from "../api/types";
import AuditPage from "./AuditPage";

const hooks = vi.hoisted(() => ({
  useAuditLogs: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleAuditLogs: SpacsAuditLog[] = [
  {
    id: 1,
    actor_id: 1001,
    actor_role: "spacs_assistant",
    action: "verify_satisfied",
    target_type: "ScholarshipApplication",
    target_id: "10",
    details: { finding: "verified", comments: "Valid documents" },
    created_at: "2026-08-10T12:00:00Z",
  },
  {
    id: 2,
    actor_id: 1002,
    actor_role: "spacs_convener",
    action: "approve",
    target_type: "ScholarshipApplication",
    target_id: "20",
    details: { decision: "approved", order: "SANCTION/01" },
    created_at: "2026-08-11T14:30:00Z",
  },
];

describe("AuditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page title and subtitle", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: sampleAuditLogs,
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );

    expect(screen.getByText("SPACS System Audit Trail")).toBeInTheDocument();
    expect(screen.getByText(/Append-only immutable record/i)).toBeInTheDocument();
  });

  it("renders audit log entries with actor, action, and target", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: sampleAuditLogs,
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );

    expect(screen.getByText("u1001")).toBeInTheDocument();
    expect(screen.getByText("spacs_assistant")).toBeInTheDocument();
    expect(screen.getByText("verify_satisfied")).toBeInTheDocument();
    expect(screen.getByText("ScholarshipApplication #10")).toBeInTheDocument();
    expect(screen.getByText("ScholarshipApplication #20")).toBeInTheDocument();
  });

  it("renders empty state when no audit logs match", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: [],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );

    expect(screen.getByText("No audit logs found")).toBeInTheDocument();
  });

  it("renders error state when hook returns error", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Failed to load audit logs"),
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });
});
