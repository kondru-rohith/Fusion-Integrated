import { useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Drawer,
  Group,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Timeline,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaExternalLinkAlt, FaHistory } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useApplication,
  useApplicationHistory,
  useWithdrawApplication,
} from "../api/hooks";
import { CorrectionEditModal } from "./CorrectionEditModal";

interface Props {
  opened: boolean;
  onClose: () => void;
  applicationId: number | null;
  onUpdated?: () => void;
}

export function ApplicationDetailDrawer({
  opened,
  onClose,
  applicationId,
  onUpdated,
}: Props) {
  const { session } = useAuth();
  const { data: app, isPending } = useApplication(applicationId);
  const { data: history } = useApplicationHistory(applicationId);

  const [correctionOpen, setCorrectionOpen] = useState(false);

  const isOwner =
    session?.user?.kind === "student" &&
    app?.user_id !== undefined &&
    session?.user?.id === app.user_id;

  const withdraw = useWithdrawApplication();

  if (!applicationId) return null;

  function handleWithdraw() {
    if (!applicationId) return;
    if (!confirm("Are you sure you want to withdraw this application? This action is terminal.")) {
      return;
    }
    withdraw.mutate(
      { id: applicationId, reason: "Student requested withdrawal" },
      {
        onSuccess: () => {
          notifications.show({
            color: "gray",
            title: "Application Withdrawn",
            message: "Application marked withdrawn.",
          });
          onUpdated?.();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Withdrawal Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <>
      <Drawer
        opened={opened}
        onClose={onClose}
        position="right"
        size="lg"
        title={
          <Group gap="xs">
            <Title order={4}>{app?.application_number || "Application Details"}</Title>
            {app?.status && <StatusBadge status={app.status} />}
          </Group>
        }
      >
        <ScrollArea h="calc(100vh - 80px)">
          <Stack gap="md" p="xs">
            {isPending ? (
              <Text size="sm" c="dimmed">
                Loading details...
              </Text>
            ) : !app ? (
              <Text size="sm" c="red">
                Application not found or unauthorized.
              </Text>
            ) : (
              <>
                {/* Header Info */}
                <Paper withBorder p="sm">
                  <Stack gap={4}>
                    <Text size="sm" fw={600}>
                      {app.scheme_title}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Cycle: {app.cycle} {app.is_renewal ? "• Renewal" : "• Fresh Application"}
                    </Text>
                    <Group gap="lg" mt="xs">
                      <div>
                        <Text size="xs" c="dimmed">
                          CPI at Apply
                        </Text>
                        <Text size="sm" fw={600}>
                          {app.cpi_at_apply ? Number(app.cpi_at_apply).toFixed(2) : "—"}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Declared Income
                        </Text>
                        <Text size="sm" fw={600}>
                          {app.annual_income_declared
                            ? `₹${Number(app.annual_income_declared).toLocaleString()}`
                            : "—"}
                        </Text>
                      </div>
                    </Group>
                  </Stack>
                </Paper>

                {/* Verification Concern Banner */}
                {app.status === "verification_concern" && (
                  <Alert
                    icon={<FaExclamationTriangle />}
                    color="orange"
                    variant="filled"
                    title="Verification Concern Raised"
                    data-testid="verification-concern-drawer-banner"
                  >
                    <Stack gap="xs">
                      <Text size="sm">
                        A verification concern was recorded by SPACS Assistant{" "}
                        <strong>
                          u{app.verification_findings?.find((f) => f.action === "concern_raised")
                            ?.reviewer_id || app.assigned_assistant_id || "Staff"}
                        </strong>
                        {app.verification_findings?.find((f) => f.action === "concern_raised")
                          ?.created_at && (
                          <>
                            {" "}
                            on{" "}
                            <strong>
                              {new Date(
                                app.verification_findings.find(
                                  (f) => f.action === "concern_raised",
                                )!.created_at,
                              ).toLocaleString()}
                            </strong>
                          </>
                        )}
                        .
                      </Text>
                      <Paper p="xs" bg="white" c="dark" withBorder>
                        <Text size="xs" fw={700} c="dimmed">
                          Assistant's Verification Comments:
                        </Text>
                        <Text
                          size="sm"
                          mt={2}
                          style={{ whiteSpace: "pre-wrap" }}
                          data-testid="drawer-concern-comments"
                        >
                          {app.verification_findings?.find((f) => f.action === "concern_raised")
                            ?.comments || "Verification concern noted on this application."}
                        </Text>
                      </Paper>
                    </Stack>
                  </Alert>
                )}

                {/* Form Data */}
                <Card withBorder p="sm">
                  <Text size="sm" fw={600} mb="xs">
                    Bank &amp; Application Submission Details
                  </Text>
                  <Stack gap={6}>
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">
                        Bank Account:
                      </Text>
                      <Text size="xs" fw={500}>
                        {String(app.submission_data?.bank_account || "—")}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">
                        IFSC:
                      </Text>
                      <Text size="xs" fw={500}>
                        {String(app.submission_data?.bank_ifsc || "—")}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">
                        Bank Name:
                      </Text>
                      <Text size="xs" fw={500}>
                        {String(app.submission_data?.bank_name || "—")}
                      </Text>
                    </Group>
                    {app.submission_data?.statement_of_purpose ? (
                      <div>
                        <Text size="xs" c="dimmed">
                          Statement:
                        </Text>
                        <Text size="xs" mt={2}>
                          {String(app.submission_data.statement_of_purpose)}
                        </Text>
                      </div>
                    ) : null}
                  </Stack>
                </Card>

                {/* Documents List */}
                <Card withBorder p="sm">
                  <Text size="sm" fw={600} mb="xs">
                    Supporting Evidence &amp; Documents
                  </Text>
                  {!app.documents?.length ? (
                    <Text size="xs" c="dimmed">
                      No documents attached yet.
                    </Text>
                  ) : (
                    <Stack gap="xs">
                      {app.documents.map((doc) => (
                        <Paper key={doc.id} withBorder p="xs" bg="gray.0">
                          <Group justify="space-between" wrap="nowrap">
                            <Stack gap={2}>
                              <Text size="xs" fw={600}>
                                {doc.title}
                              </Text>
                              <Group gap={6}>
                                <Badge size="xs" variant="outline">
                                  {doc.doc_type.replace(/_/g, " ")}
                                </Badge>
                                {doc.verification_status && (
                                  <Badge
                                    size="xs"
                                    color={
                                      doc.verification_status === "valid"
                                        ? "green"
                                        : doc.verification_status === "invalid"
                                          ? "red"
                                          : "yellow"
                                    }
                                  >
                                    {doc.verification_status}
                                  </Badge>
                                )}
                              </Group>
                            </Stack>
                            <ActionIcon
                              component="a"
                              href={doc.drive_url}
                              target="_blank"
                              variant="light"
                              size="sm"
                            >
                              <FaExternalLinkAlt size={12} />
                            </ActionIcon>
                          </Group>
                        </Paper>
                      ))}
                    </Stack>
                  )}
                </Card>

                {/* Actions for Correction / Withdrawal (Student Owner Only) */}
                {isOwner && (
                  <Group justify="flex-end">
                    {app.status === "correction_required" && (
                      <Button
                        color="orange"
                        size="xs"
                        onClick={() => setCorrectionOpen(true)}
                        data-testid="open-correction-edit-btn"
                      >
                        Resubmit Corrected Application
                      </Button>
                    )}
                    {["submitted", "under_verification", "correction_required", "verified"].includes(
                      app.status,
                    ) && (
                      <Button
                        color="red"
                        variant="outline"
                        size="xs"
                        loading={withdraw.isPending}
                        onClick={handleWithdraw}
                      >
                        Withdraw Application
                      </Button>
                    )}
                  </Group>
                )}

                {/* History Timeline */}
                <Card withBorder p="sm" mt="xs">
                  <Group gap="xs" mb="sm">
                    <FaHistory />
                    <Text size="sm" fw={600}>
                      Application Timeline
                    </Text>
                  </Group>
                  {!history?.results?.length ? (
                    <Text size="xs" c="dimmed">
                      No recorded transitions yet.
                    </Text>
                  ) : (
                    <Timeline active={history.results.length - 1} bulletSize={18} lineWidth={2}>
                      {history.results.map((tr) => (
                        <Timeline.Item
                          key={tr.id}
                          title={tr.to_status.replace(/_/g, " ").toUpperCase()}
                        >
                          <Text size="xs" c="dimmed">
                            {new Date(tr.at).toLocaleString()} • {tr.actor_label}
                          </Text>
                          {tr.reason && (
                            <Text size="xs" mt={2}>
                              {tr.reason}
                            </Text>
                          )}
                        </Timeline.Item>
                      ))}
                    </Timeline>
                  )}
                </Card>
              </>
            )}
          </Stack>
        </ScrollArea>
      </Drawer>

      {/* Correction-edit modal — only rendered when we have an app */}
      {app && app.status === "correction_required" && isOwner && (
        <CorrectionEditModal
          opened={correctionOpen}
          onClose={() => setCorrectionOpen(false)}
          applicationId={app.id}
          requiredDocuments={app.required_documents ?? []}
          onSuccess={() => {
            setCorrectionOpen(false);
            onUpdated?.();
          }}
        />
      )}
    </>
  );
}
