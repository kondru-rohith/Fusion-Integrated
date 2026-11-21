import { useState } from "react";
import {
  Badge,
  Card,
  Code,
  Container,
  Group,
  Select,
  Stack,
  Text,
} from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuditLogs } from "../api/hooks";
import type { SpacsAuditLog } from "../api/types";

export default function AuditPage() {
  const [targetType, setTargetType] = useState<string | null>(null);
  const { data: logs, isPending, error } = useAuditLogs(targetType || undefined);

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
        title="SPACS System Audit Trail"
        subtitle="Append-only immutable record of all policy changes, sanctions, and scheme transitions (BR-SPACS-012, 021)"
      />

      <Group mb="md">
        <Select
          label="Filter by Target Entity"
          placeholder="All target entities"
          clearable
          data={[
            { value: "ScholarshipApplication", label: "Scholarship Applications" },
            { value: "AwardCycle", label: "Award Cycles" },
            { value: "CatalogueVersion", label: "Catalogue Versions" },
            { value: "CatalogueEntry", label: "Catalogue Entries" },
            { value: "ApplicationDocument", label: "Documents" },
          ]}
          value={targetType}
          onChange={setTargetType}
          w={280}
        />
      </Group>

      <Card withBorder padding="md">
        <DataTable<SpacsAuditLog>
          rows={logs || []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={950}
          empty={{
            title: "No audit logs found",
            description: "No administrative or state transition logs match the selected filter.",
          }}
          columns={[
            {
              key: "created_at",
              header: "Timestamp",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.created_at).toLocaleString()}
                </Text>
              ),
            },
            {
              key: "actor",
              header: "Actor (User & Role)",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm" fw={500}>
                    u{r.actor_id}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.actor_role}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "action",
              header: "Action",
              render: (r) => (
                <Badge color="blue" variant="light" size="sm">
                  {r.action}
                </Badge>
              ),
            },
            {
              key: "target",
              header: "Target Entity",
              render: (r) => (
                <Text size="xs" fw={500}>
                  {r.target_type} #{r.target_id}
                </Text>
              ),
            },
            {
              key: "details",
              header: "Event Payload / Changes",
              render: (r) => (
                <Code block style={{ maxHeight: 60, overflow: "auto", fontSize: 11 }}>
                  {JSON.stringify(r.details, null, 2)}
                </Code>
              ),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
