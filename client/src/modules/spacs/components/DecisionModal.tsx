import { useState, useEffect } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Modal,
  Paper,
  Radio,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaExternalLinkAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useApplication, useMakeDecision } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  application: ScholarshipApplication | null;
  onSuccess?: () => void;
}

export function DecisionModal({ opened, onClose, application, onSuccess }: Props) {
  const { data: fullApp } = useApplication(opened && application ? application.id : null);
  const app = fullApp || application;

  const isConcern = app?.status === "verification_concern";

  const [decision, setDecision] = useState<
    "approved" | "rejected" | "returned_for_correction"
  >("approved");
  const [sanctionOrderRef, setSanctionOrderRef] = useState("");
  const [rationale, setRationale] = useState("");
  const [concernAcknowledged, setConcernAcknowledged] = useState(false);

  // Reset or adjust default decision when opening or changing application
  useEffect(() => {
    if (opened) {
      if (isConcern) {
        setDecision("returned_for_correction");
      } else {
        setDecision("approved");
      }
      setSanctionOrderRef("");
      setRationale("");
      setConcernAcknowledged(false);
    }
  }, [opened, isConcern]);

  const makeDecision = useMakeDecision();

  if (!app) return null;

  // Retrieve concern finding (assistant comments and metadata)
  const concernFinding =
    app.verification_findings?.find((f) => f.action === "concern_raised") ||
    app.verification_findings?.[0];

  // Document validation: check if required documents are valid
  const normalizeDocType = (dt: string) => (dt || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  const requiredDocs = app.required_documents || [];
  const validDocTypes = new Set(
    (app.documents || [])
      .filter((d) => d.is_active && d.verification_status === "valid")
      .map((d) => normalizeDocType(d.doc_type)),
  );
  const unverifiedRequiredDocs = requiredDocs.filter(
    (rd) => !validDocTypes.has(normalizeDocType(rd)),
  );
  const hasInvalidDocs = (app.documents || []).some(
    (d) => d.is_active && d.verification_status === "invalid",
  );
  const cannotApprove = unverifiedRequiredDocs.length > 0 || hasInvalidDocs;

  function handleSubmit() {
    if (!app) return;

    if (isConcern && !concernAcknowledged) {
      notifications.show({
        color: "orange",
        title: "Acknowledgment Required",
        message: "Please review and acknowledge the verification concern before proceeding.",
      });
      return;
    }

    if (decision === "approved") {
      if (cannotApprove) {
        notifications.show({
          color: "red",
          title: "Cannot Sanction Application",
          message:
            "Required documents are pending or unverified. Applications cannot be sanctioned until all documents are valid.",
        });
        return;
      }
      if (!sanctionOrderRef.trim()) {
        notifications.show({
          color: "red",
          title: "Sanction Reference Required",
          message: "Approval requires an official Sanction Order Reference number.",
        });
        return;
      }
    }

    if (!rationale.trim()) {
      notifications.show({
        color: "red",
        title: "Rationale Required",
        message: "Please state the decision rationale for the audit record.",
      });
      return;
    }

    makeDecision.mutate(
      {
        applicationId: app.id,
        decision,
        sanction_order_ref: sanctionOrderRef.trim(),
        rationale: rationale.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: decision === "approved" ? "green" : decision === "rejected" ? "red" : "orange",
            title: `Application ${decision.replace(/_/g, " ").toUpperCase()}`,
            message: `Decision for ${app.application_number} recorded successfully.`,
          });
          onSuccess?.();
          onClose();
          setSanctionOrderRef("");
          setRationale("");
          setConcernAcknowledged(false);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Decision Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size={isConcern ? "lg" : "md"}
      title={
        isConcern
          ? `Review Verification Concern: ${app.application_number}`
          : `Convener Sanction: ${app.application_number}`
      }
    >
      <Stack gap="md">
        <Text size="sm">
          <strong>Applicant:</strong> Student u{app.user_id} • {app.scheme_title} ({app.cycle})
        </Text>

        {/* Verification Concern Banner & Details */}
        {isConcern && (
          <>
            <Alert
              icon={<FaExclamationTriangle />}
              color="orange"
              variant="filled"
              title="Verification Concern Raised"
              data-testid="verification-concern-banner"
            >
              <Stack gap="xs">
                <Text size="sm">
                  A verification concern was recorded by SPACS Assistant{" "}
                  <strong>
                    u{concernFinding?.reviewer_id || app.assigned_assistant_id || "Staff"}
                  </strong>
                  {concernFinding?.created_at && (
                    <>
                      {" "}
                      on{" "}
                      <strong>
                        {new Date(concernFinding.created_at).toLocaleString()}
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
                    data-testid="concern-comments"
                  >
                    {concernFinding?.comments || "Verification concern noted on this application."}
                  </Text>
                </Paper>
              </Stack>
            </Alert>

            {/* Supporting Evidence Review */}
            <Card withBorder p="sm" bg="gray.0">
              <Text size="sm" fw={600} mb="xs">
                Supporting Evidence &amp; Documents
              </Text>
              {!app.documents?.length ? (
                <Text size="xs" c="dimmed">
                  No documents attached.
                </Text>
              ) : (
                <Stack gap="xs">
                  {app.documents.map((doc) => (
                    <Paper key={doc.id} withBorder p="xs" bg="white">
                      <Group justify="space-between" wrap="nowrap">
                        <Stack gap={2}>
                          <Text size="xs" fw={600}>
                            {doc.title}
                          </Text>
                          <Group gap={6}>
                            <Badge size="xs" variant="outline">
                              {doc.doc_type.replace(/_/g, " ")}
                            </Badge>
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

            {/* Mandatory Acknowledgment */}
            <Checkbox
              label="I have reviewed and acknowledge the verification concern comments and supporting evidence above."
              checked={concernAcknowledged}
              onChange={(e) => setConcernAcknowledged(e.currentTarget.checked)}
              color="orange"
              required
              data-testid="acknowledge-concern-checkbox"
            />
          </>
        )}

        {/* Decision Radio Group */}
        <Radio.Group
          label={isConcern ? "Concern Resolution & Sanction Decision" : "Sanction Decision"}
          required
          value={decision}
          onChange={(v) =>
            setDecision(v as "approved" | "rejected" | "returned_for_correction")
          }
        >
          <Stack mt="xs" gap="xs">
            {isConcern ? (
              <>
                <Radio
                  value="returned_for_correction"
                  label="Return to Applicant for Clarification / Correction"
                />
                <Radio
                  value="approved"
                  label="Resolve Concern & Sanction Scholarship"
                  disabled={cannotApprove}
                />
                <Radio value="rejected" label="Reject Application" />
              </>
            ) : (
              <Group>
                <Radio value="approved" label="Approve & Sanction Scholarship" />
                <Radio value="rejected" label="Reject Application" />
              </Group>
            )}
          </Stack>
        </Radio.Group>

        {/* Cannot Sanction Alert if Approved Selected with Unverified Docs */}
        {decision === "approved" && cannotApprove && (
          <Alert color="red" variant="light" title="Sanction Blocked">
            This application cannot be approved because required supporting documents are
            unverified or rejected (
            {unverifiedRequiredDocs.join(", ") || "pending documents"}
            ). Under SPACS rules, all required documents must be marked valid before sanctioning.
          </Alert>
        )}

        {decision === "approved" && !cannotApprove && (
          <TextInput
            label="Sanction Order Reference (BR-SPACS-015)"
            required
            placeholder="e.g. SPACS/2026/MCM/042"
            value={sanctionOrderRef}
            onChange={(e) => setSanctionOrderRef(e.currentTarget.value)}
          />
        )}

        <Textarea
          label={
            isConcern
              ? "Decision Rationale & Concern Resolution Remarks"
              : "Decision Rationale / Committee Remarks"
          }
          required
          placeholder={
            isConcern
              ? "State how the concern was evaluated, justification, or clarification needed..."
              : "Quota limit, merits, standing considerations..."
          }
          rows={3}
          value={rationale}
          onChange={(e) => setRationale(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={makeDecision.isPending}>
            Cancel
          </Button>
          <Button
            color={
              decision === "approved"
                ? "green"
                : decision === "rejected"
                  ? "red"
                  : "orange"
            }
            loading={makeDecision.isPending}
            onClick={handleSubmit}
            disabled={
              (isConcern && !concernAcknowledged) ||
              (decision === "approved" && cannotApprove)
            }
            data-testid="confirm-decision-btn"
          >
            {decision === "approved"
              ? isConcern
                ? "Resolve & Sanction"
                : "Confirm Sanction"
              : decision === "rejected"
                ? "Confirm Rejection"
                : "Return for Correction"}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
