import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaExclamationCircle, FaGoogleDrive, FaInfoCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useUpdateDraft, useResubmitApplication, useApplication } from "../api/hooks";
import type { ApplicationDocument } from "../api/types";
import { DocumentAttachModal } from "./DocumentAttachModal";

interface Props {
  opened: boolean;
  onClose: () => void;
  applicationId: number;
  requiredDocuments?: string[];
  onSuccess?: () => void;
}

/** Modal that lets a student edit a correction_required application and resubmit it. */
export function CorrectionEditModal({
  opened,
  onClose,
  applicationId,
  requiredDocuments = [],
  onSuccess,
}: Props) {
  const { data: app } = useApplication(opened ? applicationId : null);

  const [income, setIncome] = useState<number | string>(0);
  const [bankAccount, setBankAccount] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [remarks, setRemarks] = useState("");

  // Docs that have been newly attached during this correction session.
  const [attachedDocs, setAttachedDocs] = useState<ApplicationDocument[]>([]);
  const [docModalOpen, setDocModalOpen] = useState(false);

  const updateDraft = useUpdateDraft();
  const resubmit = useResubmitApplication();

  // Prefill form from the loaded application whenever the modal opens.
  useEffect(() => {
    if (opened && app) {
      const sub = (app.submission_data as Record<string, unknown>) || {};
      setIncome(
        app.annual_income_declared != null
          ? Number(app.annual_income_declared)
          : sub.annual_income != null
            ? Number(sub.annual_income)
            : 0,
      );
      setBankAccount(String(sub.bank_account || sub.bank_account_number || ""));
      setBankIfsc(String(sub.bank_ifsc || sub.ifsc || sub.ifsc_code || ""));
      setBankName(String(sub.bank_name || ""));
      setRemarks(String(sub.statement_of_purpose || sub.justification || ""));
      // Pre-populate the attached doc list from already-linked documents.
      setAttachedDocs((app.documents ?? []).filter((d) => d.is_active));
    }
    // Reset on close.
    if (!opened) {
      setAttachedDocs([]);
    }
  }, [opened, app]);

  const normalizeDocType = (dt: string) =>
    (dt || "").trim().toLowerCase().replace(/[\s-]+/g, "_");

  const missingDocs = requiredDocuments.filter(
    (rd) => !attachedDocs.some((ad) => normalizeDocType(ad.doc_type) === normalizeDocType(rd)),
  );

  const isLoading = updateDraft.isPending || resubmit.isPending;

  async function handleSaveAndResubmit() {
    if (!bankAccount.trim() || !bankIfsc.trim()) {
      notifications.show({
        color: "red",
        title: "Incomplete Form",
        message: "Bank account and IFSC code are required.",
      });
      return;
    }

    if (missingDocs.length > 0) {
      notifications.show({
        color: "red",
        title: "Missing Required Documents",
        message: `Please attach: ${missingDocs.join(", ")}`,
      });
      return;
    }

    try {
      // 1. Save updated data back into the existing application.
      await updateDraft.mutateAsync({
        id: applicationId,
        annual_income_declared: income,
        submission_data: {
          bank_account: bankAccount.trim(),
          bank_ifsc: bankIfsc.trim().toUpperCase(),
          bank_name: bankName.trim(),
          statement_of_purpose: remarks.trim(),
          document_ids: attachedDocs.map((d) => d.id),
        },
      });

      // 2. Resubmit the corrected application back into the verification queue.
      await resubmit.mutateAsync(applicationId);

      notifications.show({
        color: "green",
        title: "Application Resubmitted",
        message: "Your corrected application has been sent back for verification.",
      });

      onSuccess?.();
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Resubmission Failed",
        message: errorMessage(err),
      });
    }
  }

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        size="lg"
        title="Edit & Resubmit Corrected Application"
        data-testid="correction-edit-modal"
      >
        <Stack gap="md">
          <Alert
            icon={<FaInfoCircle />}
            color="orange"
            variant="light"
            title="Correction Required"
          >
            Your application has been returned for corrections. Please update the required
            information and resubmit. Your application number and history are preserved.
          </Alert>

          <Alert
            icon={<FaInfoCircle />}
            color="blue"
            variant="light"
            title="CPI is verified automatically"
          >
            CPI is fetched from academic records at submission time — you cannot modify it here.
          </Alert>

          <NumberInput
            label="Declared Annual Family Income (₹)"
            required
            min={0}
            step={10000}
            value={income}
            onChange={(val) => setIncome(val ?? 0)}
          />

          <Group grow>
            <TextInput
              label="Bank Account Number"
              required
              placeholder="e.g. 501002345678"
              value={bankAccount}
              onChange={(e) => setBankAccount(e.currentTarget.value)}
            />
            <TextInput
              label="IFSC Code"
              required
              placeholder="e.g. SBIN0001234"
              value={bankIfsc}
              onChange={(e) => setBankIfsc(e.currentTarget.value)}
            />
          </Group>

          <TextInput
            label="Bank & Branch Name"
            placeholder="e.g. State Bank of India, Dumna Campus"
            value={bankName}
            onChange={(e) => setBankName(e.currentTarget.value)}
          />

          <Textarea
            label="Statement of Purpose / Justification"
            placeholder="Briefly state your family circumstances or motivation..."
            rows={3}
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />

          {/* Documents Section */}
          <Paper withBorder p="sm">
            <Group justify="space-between" mb="xs">
              <Text size="sm" fw={600}>
                Required Supporting Evidence
              </Text>
              <Button
                size="xs"
                variant="light"
                leftSection={<FaGoogleDrive />}
                onClick={() => setDocModalOpen(true)}
              >
                Attach / Replace Document
              </Button>
            </Group>

            {requiredDocuments.length > 0 && (
              <Stack gap={4}>
                {requiredDocuments.map((docType) => {
                  const attached = attachedDocs.find(
                    (d) => normalizeDocType(d.doc_type) === normalizeDocType(docType),
                  );
                  return (
                    <Group key={docType} justify="space-between">
                      <Group gap="xs">
                        {attached ? (
                          <FaCheckCircle color="green" data-testid={`doc-ok-${docType}`} />
                        ) : (
                          <FaExclamationCircle
                            color="orange"
                            data-testid={`doc-missing-${docType}`}
                          />
                        )}
                        <Text size="xs" fw={500}>
                          {docType.replace(/_/g, " ")}:
                        </Text>
                      </Group>
                      {attached ? (
                        <Text size="xs" c="dimmed">
                          Attached ({attached.title})
                        </Text>
                      ) : (
                        <Badge size="xs" color="orange" variant="outline">
                          Required
                        </Badge>
                      )}
                    </Group>
                  );
                })}
              </Stack>
            )}
          </Paper>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              color="orange"
              loading={isLoading}
              onClick={handleSaveAndResubmit}
              data-testid="save-resubmit-btn"
            >
              Save & Resubmit
            </Button>
          </Group>
        </Stack>
      </Modal>

      <DocumentAttachModal
        opened={docModalOpen}
        onClose={() => setDocModalOpen(false)}
        applicationId={applicationId}
        defaultDocType={missingDocs[0] || (requiredDocuments[0] ?? "income_certificate")}
        onAttached={(newDoc) => {
          // Replace any existing doc of the same type, then add the new one.
          setAttachedDocs((prev) => {
            const filtered = prev.filter(
              (d) => normalizeDocType(d.doc_type) !== normalizeDocType(newDoc.doc_type),
            );
            return [...filtered, newDoc];
          });
        }}
      />
    </>
  );
}
