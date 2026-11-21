import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useAttachDocument } from "../api/hooks";
import type { ApplicationDocument } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  applicationId?: number | null;
  defaultDocType?: string;
  onAttached?: (doc: ApplicationDocument) => void;
}

const COMMON_DOC_TYPES = [
  { value: "income_certificate", label: "Income Certificate" },
  { value: "caste_certificate", label: "Caste / Category Certificate" },
  { value: "fee_receipt", label: "Fee Receipt" },
  { value: "grade_sheet", label: "Grade Sheet" },
  { value: "bank_passbook", label: "Bank Passbook" },
  { value: "other", label: "Other Supporting Document" },
];

export function DocumentAttachModal({
  opened,
  onClose,
  applicationId,
  defaultDocType = "income_certificate",
  onAttached,
}: Props) {
  const [docType, setDocType] = useState(defaultDocType);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [validUntil, setValidUntil] = useState<Date | null>(null);
  const [isReusable, setIsReusable] = useState(true);

  useEffect(() => {
    if (opened) {
      setDocType(defaultDocType);
    }
  }, [opened, defaultDocType]);

  const docTypeOptions = [
    ...COMMON_DOC_TYPES,
    ...(defaultDocType &&
    !COMMON_DOC_TYPES.some(
      (d) => d.value.toLowerCase() === defaultDocType.toLowerCase(),
    )
      ? [
          {
            value: defaultDocType,
            label: defaultDocType
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase()),
          },
        ]
      : []),
  ];

  const attach = useAttachDocument();

  function handleSubmit() {
    if (!url.trim()) {
      notifications.show({
        color: "red",
        title: "Required URL",
        message: "Please enter a valid Google Drive URL.",
      });
      return;
    }

    attach.mutate(
      {
        doc_type: docType,
        url: url.trim(),
        title: title.trim() || docType.replace(/_/g, " "),
        application_id: applicationId,
        valid_until: validUntil ? validUntil.toISOString().split("T")[0] : null,
        is_reusable: isReusable,
      },
      {
        onSuccess: (doc) => {
          notifications.show({
            color: "green",
            title: "Document Attached",
            message: "Google Drive document link attached successfully.",
          });
          onAttached?.(doc);
          onClose();
          setUrl("");
          setTitle("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Attachment Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Attach Supporting Document (Google Drive)">
      <Stack gap="md">
        <Select
          label="Document Type"
          required
          data={docTypeOptions}
          value={docType}
          onChange={(v) => setDocType(v ?? "other")}
        />
        <TextInput
          label="Document Title"
          placeholder="e.g. FY 2025-26 Tehsildar Income Certificate"
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
        />
        <TextInput
          label="Google Drive Link"
          required
          placeholder="https://drive.google.com/file/d/..."
          description="Link will be canonicalized to standard viewer format"
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
        />
        <DateInput
          label="Valid Until (if applicable)"
          placeholder="YYYY-MM-DD"
          clearable
          value={validUntil}
          onChange={setValidUntil}
        />
        <Checkbox
          label="Save to reusable document wallet for future cycles (BR-SPACS-003)"
          checked={isReusable}
          onChange={(e) => setIsReusable(e.currentTarget.checked)}
        />
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={attach.isPending} onClick={handleSubmit}>
            Attach Link
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
