import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import { FaGavel, FaEye, FaExclamationTriangle } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useDecisionQueue } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";
import { ApplicationDetailDrawer } from "../components/ApplicationDetailDrawer";
import { DecisionModal } from "../components/DecisionModal";

export default function DecisionQueuePage() {
  const { data: queue, isPending, error, refetch } = useDecisionQueue();
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [decidingApp, setDecidingApp] = useState<ScholarshipApplication | null>(null);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Scholarship Sanction Approvals"
        subtitle="SPACS Convener desk: Review verified applications and record formal award sanctions"
      />

      <Card withBorder padding="md">
        <DataTable<ScholarshipApplication>
          rows={queue || []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            title: "No applications awaiting sanction",
            description: "All verified scholarship applications have been reviewed.",
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
                    Cycle: {r.cycle}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "user_id",
              header: "Applicant",
              render: (r) => <Text size="sm">Student u{r.user_id}</Text>,
            },
            {
              key: "scheme_title",
              header: "Scheme",
              render: (r) => (
                <Text size="sm" fw={500}>
                  {r.scheme_title}
                </Text>
              ),
            },
            {
              key: "cpi_at_apply",
              header: "CPI at Apply",
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
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  <Tooltip label="View Application Dossier">
                    <ActionIcon
                      variant="light"
                      color="blue"
                      aria-label="View Application Dossier"
                      onClick={() => setSelectedAppId(r.id)}
                    >
                      <FaEye />
                    </ActionIcon>
                  </Tooltip>
                  {r.status === "verification_concern" ? (
                    <Button
                      size="xs"
                      leftSection={<FaExclamationTriangle />}
                      color="orange"
                      onClick={() => setDecidingApp(r)}
                      data-testid={`review-concern-btn-${r.id}`}
                    >
                      Review Concern &amp; Decide
                    </Button>
                  ) : (
                    <Button
                      size="xs"
                      leftSection={<FaGavel />}
                      color="indigo"
                      onClick={() => setDecidingApp(r)}
                      data-testid={`sanction-btn-${r.id}`}
                    >
                      Sanction Decision
                    </Button>
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

      {decidingApp && (
        <DecisionModal
          opened={!!decidingApp}
          onClose={() => setDecidingApp(null)}
          application={decidingApp}
          onSuccess={() => refetch()}
        />
      )}
    </Container>
  );
}
