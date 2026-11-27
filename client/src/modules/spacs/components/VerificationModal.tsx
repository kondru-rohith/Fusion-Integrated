import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  Radio,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useRecordFinding } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  application: ScholarshipApplication | null;
  onSuccess?: () => void;
}

export function VerificationModal({ opened, onClose, application, onSuccess }: Props) {
  const [action, setAction] = useState<"verified" | "correction_required" | "concern_raised">(
    "verified",
  );
  const [comments, setComments] = useState("");
  const [correctionFields, setCorrectionFields] = useState("");

  const recordFinding = useRecordFinding();

  if (!application) return null;

  function handleSubmit() {
    if (!application) return;
    const app = application;
    if (!comments.trim()) {
      notifications.show({
        color: "red",
        title: "Comments Required",
        message: "Please enter verification remarks/findings.",
      });
      return;
    }

    const fields =
      action === "correction_required"
        ? correctionFields
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

    recordFinding.mutate(
      {
        applicationId: app.id,
        action,
        comments: comments.trim(),
        correction_fields: fields,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Verification Finding Recorded",
            message: `Application ${app.application_number} updated to ${action.replace(/_/g, " ")}.`,
          });
          onSuccess?.();
          onClose();
          setComments("");
          setCorrectionFields("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Verification Failed",
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
      title={`Verify Application: ${application.application_number}`}
    >
      <Stack gap="md">
        <Text size="sm">
          <strong>Applicant Scheme:</strong> {application.scheme_title} ({application.cycle})
        </Text>

        <Radio.Group
          label="Verification Finding"
          required
          value={action}
          onChange={(v) =>
            setAction(v as "verified" | "correction_required" | "concern_raised")
          }
        >
          <Stack gap="xs" mt="xs">
            <Radio
              value="verified"
              label="Verified (All documents and eligibility criteria verified)"
            />
            <Radio
              value="correction_required"
              label="Correction Required (Send back to student for resubmission)"
            />
            <Radio
              value="concern_raised"
              label="Concern Raised (Flag discrepancies for Convener attention)"
            />
          </Stack>
        </Radio.Group>

        {action === "correction_required" && (
          <TextInput
            label="Correction Field Names"
            placeholder="e.g. income_certificate, bank_ifsc"
            description="Comma-separated field/document names requiring student correction"
            value={correctionFields}
            onChange={(e) => setCorrectionFields(e.currentTarget.value)}
          />
        )}

        <Textarea
          label="Verification Comments / Audit Note"
          required
          placeholder="Document cross-verification details, portal references, or discrepancies..."
          rows={3}
          value={comments}
          onChange={(e) => setComments(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={recordFinding.isPending}>
            Cancel
          </Button>
          <Button
            color={
              action === "verified"
                ? "green"
                : action === "correction_required"
                  ? "orange"
                  : "red"
            }
            loading={recordFinding.isPending}
            onClick={handleSubmit}
          >
            Submit Finding
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
