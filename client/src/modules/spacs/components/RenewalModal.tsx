import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useApplyRenewal } from "../api/hooks";
import type { ScholarshipApplication } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  parentApplication: ScholarshipApplication | null;
  onSuccess?: () => void;
}

export function RenewalModal({ opened, onClose, parentApplication, onSuccess }: Props) {
  const [income, setIncome] = useState<number | string>(
    parentApplication?.annual_income_declared ? Number(parentApplication.annual_income_declared) : 350000,
  );
  const [academicRemarks, setAcademicRemarks] = useState("");

  const applyRenewal = useApplyRenewal();

  if (!parentApplication) return null;

  function handleRenewal() {
    if (!parentApplication) return;
    const parent = parentApplication;
    applyRenewal.mutate(
      {
        parent_application_id: parent.id,
        cycle: "2026-27",
        annual_income_declared: income,
        submission_data: {
          renewal_remarks: academicRemarks.trim(),
          parent_application_number: parent.application_number,
        },
      },
      {
        onSuccess: (res) => {
          notifications.show({
            color: "green",
            title: "Renewal Application Submitted",
            message: `Renewal application ${res.application_number} submitted for fresh verification.`,
          });
          onSuccess?.();
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Renewal Failed",
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
      title={`Apply for Renewal: ${parentApplication.scheme_title}`}
    >
      <Stack gap="md">
        <Text size="sm">
          <strong>Previous Award:</strong> {parentApplication.application_number} ({parentApplication.cycle})
        </Text>
        <Text size="xs" c="dimmed">
          Scholarship renewals require declaration of updated annual household income and fresh verification of academic standing (BR-SPACS-017).
        </Text>

        <NumberInput
          label="Updated Annual Family Income (₹)"
          required
          min={0}
          step={10000}
          value={income}
          onChange={(val) => setIncome(val ?? 0)}
        />

        <Textarea
          label="Current Academic Status / Notes"
          placeholder="Semester CPI, no active backlogs declaration, or special remarks..."
          rows={3}
          value={academicRemarks}
          onChange={(e) => setAcademicRemarks(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={applyRenewal.isPending}>
            Cancel
          </Button>
          <Button
            color="teal"
            loading={applyRenewal.isPending}
            onClick={handleRenewal}
          >
            Submit Renewal Application
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
