import { useState } from "react";
import {
  ActionIcon,
  Card,
  Container,
  Group,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { FaEye, FaRedo, FaTrash } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMyApplications, useWithdrawApplication } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";
import { ApplicationDetailDrawer } from "../components/ApplicationDetailDrawer";
import { RenewalModal } from "../components/RenewalModal";

export default function MyApplicationsPage() {
  const { data: applications, isPending, error, refetch } = useMyApplications();
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [renewalApp, setRenewalApp] = useState<ScholarshipApplication | null>(null);

  const withdraw = useWithdrawApplication();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleWithdraw(app: ScholarshipApplication) {
    if (!confirm(`Are you sure you want to withdraw ${app.application_number}?`)) {
      return;
    }
    withdraw.mutate(
      { id: app.id, reason: "Student withdrew application" },
      { onSuccess: () => refetch() },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Scholarship Applications"
        subtitle="Track submitted applications, verification findings, and renewal status"
      />

      <Card withBorder padding="md">
        <DataTable<ScholarshipApplication>
          rows={applications || []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            title: "No applications submitted yet",
            description: "Browse the scheme catalogue to find and apply for scholarships.",
          }}
          columns={[
            {
              key: "application_number",
              header: "Application Number",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.application_number}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Cycle: {r.cycle} {r.is_renewal && "• Renewal"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "scheme_title",
              header: "Scheme Title",
              render: (r) => (
                <Text size="sm" fw={500}>
                  {r.scheme_title}
                </Text>
              ),
            },
            {
              key: "cpi_at_apply",
              header: "CPI",
              render: (r) => (
                <Text size="sm">{r.cpi_at_apply ? Number(r.cpi_at_apply).toFixed(2) : "—"}</Text>
              ),
            },
            {
              key: "annual_income_declared",
              header: "Declared Income",
              render: (r) => (
                <Text size="sm">
                  {r.annual_income_declared
                    ? `₹${Number(r.annual_income_declared).toLocaleString()}`
                    : "—"}
                </Text>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Submitted",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.created_at).toLocaleDateString()}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  <Tooltip label="View Details & Timeline">
                    <ActionIcon
                      variant="light"
                      color="blue"
                      onClick={() => setSelectedAppId(r.id)}
                    >
                      <FaEye />
                    </ActionIcon>
                  </Tooltip>

                  {/* Can apply for renewal if approved and parent */}
                  {(r.status === "approved" || r.status === "renewed") && (
                    <Tooltip label="Apply for Scholarship Renewal">
                      <ActionIcon
                        variant="light"
                        color="teal"
                        onClick={() => setRenewalApp(r)}
                      >
                        <FaRedo />
                      </ActionIcon>
                    </Tooltip>
                  )}

                  {/* Can withdraw if in pre-sanction state */}
                  {["submitted", "under_verification", "correction_required", "verified"].includes(
                    r.status,
                  ) && (
                    <Tooltip label="Withdraw Application">
                      <ActionIcon
                        variant="light"
                        color="red"
                        onClick={() => handleWithdraw(r)}
                      >
                        <FaTrash />
                      </ActionIcon>
                    </Tooltip>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <ApplicationDetailDrawer
        opened={!!selectedAppId}
        onClose={() => setSelectedAppId(null)}
        applicationId={selectedAppId}
        onUpdated={() => refetch()}
      />

      {renewalApp && (
        <RenewalModal
          opened={!!renewalApp}
          onClose={() => setRenewalApp(null)}
          parentApplication={renewalApp}
          onSuccess={() => refetch()}
        />
      )}
    </Container>
  );
}
