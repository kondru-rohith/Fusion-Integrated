import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useEvaluateAwardCandidate } from "../api/hooks";
import type { AwardCandidate } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  candidate: AwardCandidate | null;
  onSuccess?: () => void;
}

export function AwardEvaluateModal({ opened, onClose, candidate, onSuccess }: Props) {
  const [score, setScore] = useState<number | string>(
    candidate?.committee_score ? Number(candidate.committee_score) : 90,
  );
  const [status, setStatus] = useState<"nominated" | "shortlisted" | "rejected">(
    candidate?.shortlist_status || "shortlisted",
  );
  const [remarks, setRemarks] = useState(candidate?.remarks || "");

  const evaluate = useEvaluateAwardCandidate();

  if (!candidate) return null;

  function handleSubmit() {
    if (!candidate) return;
    const cand = candidate;
    evaluate.mutate(
      {
        candidateId: cand.id,
        score: Number(score),
        shortlist_status: status,
        remarks: remarks.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Evaluation Recorded",
            message: `Candidate score for u${cand.user_id} recorded.`,
          });
          onSuccess?.();
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Evaluation Failed",
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
      title={`Evaluate Candidate: u${candidate.user_id}`}
    >
      <Stack gap="md">
        <Group justify="space-between">
          <Text size="sm">
            <strong>Department:</strong> {candidate.department}
          </Text>
          <Text size="sm">
            <strong>CPI:</strong> {candidate.cpi}
          </Text>
        </Group>

        <NumberInput
          label="Committee Evaluation Score (0 - 100)"
          required
          min={0}
          max={100}
          step={0.5}
          value={score}
          onChange={(v) => setScore(v ?? 0)}
        />

        <Select
          label="Shortlist Recommendation"
          required
          data={[
            { value: "shortlisted", label: "Shortlisted" },
            { value: "nominated", label: "Nominated (Under Review)" },
            { value: "rejected", label: "Rejected / Ineligible" },
          ]}
          value={status}
          onChange={(v) => setStatus((v as "nominated" | "shortlisted" | "rejected") ?? "shortlisted")}
        />

        <Textarea
          label="Evaluation Remarks / Justification"
          placeholder="Research contributions, co-curricular merits, committee comments..."
          rows={3}
          value={remarks}
          onChange={(e) => setRemarks(e.currentTarget.value)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose} disabled={evaluate.isPending}>
            Cancel
          </Button>
          <Button loading={evaluate.isPending} onClick={handleSubmit}>
            Save Evaluation
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
