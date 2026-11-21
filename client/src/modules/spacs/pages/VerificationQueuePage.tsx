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
import { FaCheckSquare, FaEye } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useVerificationQueue } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";
import { ApplicationDetailDrawer } from "../components/ApplicationDetailDrawer";
import { VerificationModal } from "../components/VerificationModal";

export default function VerificationQueuePage() {
  const { data: queue, isPending, error, refetch } = useVerificationQueue();
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [verifyingApp, setVerifyingApp] = useState<ScholarshipApplication | null>(null);

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
        title="Application Verification Queue"
        subtitle="SPACS Assistant desk: Review supporting documents and record verification findings"
      />

      <Card withBorder padding="md">
        <DataTable<ScholarshipApplication>
          rows={queue || []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            title: "No pending applications",
            description: "Verification queue is empty.",
          }}
          minWidth={900}
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
              key: "user_id",
              header: "Applicant",
              render: (r) => (
                <Text size="sm">Student u{r.user_id}</Text>
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
                  <Tooltip label="View Full Details">
                    <ActionIcon
                      variant="light"
                      color="blue"
                      onClick={() => setSelectedAppId(r.id)}
                    >
                      <FaEye />
                    </ActionIcon>
                  </Tooltip>
                  <Button
                    size="xs"
                    leftSection={<FaCheckSquare />}
                    color="teal"
                    onClick={() => setVerifyingApp(r)}
                  >
                    Verify
                  </Button>
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

      {verifyingApp && (
        <VerificationModal
          opened={!!verifyingApp}
          onClose={() => setVerifyingApp(null)}
          application={verifyingApp}
          onSuccess={() => refetch()}
        />
      )}
    </Container>
  );
}
