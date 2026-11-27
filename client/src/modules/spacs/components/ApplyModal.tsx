import { useState } from "react";
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
import { useCreateDraft, useSubmitApplication, useUpdateDraft } from "../api/hooks";
import type { ApplicationDocument, CatalogueVersion } from "../api/types";
import { DocumentAttachModal } from "./DocumentAttachModal";

interface Props {
  opened: boolean;
  onClose: () => void;
  schemeVersion: CatalogueVersion;
  onSuccess?: () => void;
}

export function ApplyModal({ opened, onClose, schemeVersion, onSuccess }: Props) {
  const [income, setIncome] = useState<number | string>(350000);
  const [bankAccount, setBankAccount] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [remarks, setRemarks] = useState("");

  const [attachedDocs, setAttachedDocs] = useState<ApplicationDocument[]>([]);
  const [docModalOpen, setDocModalOpen] = useState(false);

  const createDraft = useCreateDraft();
  const updateDraft = useUpdateDraft();
  const submitApp = useSubmitApplication();

  const normalizeDocType = (dt: string) => (dt || "").trim().toLowerCase().replace(/[\s-]+/g, "_");

  const requiredDocs = schemeVersion.required_documents || [];
  const missingDocs = requiredDocs.filter(
    (rd) => !attachedDocs.some((ad) => normalizeDocType(ad.doc_type) === normalizeDocType(rd)),
  );

  async function handleApply(asDraft = false) {
    if (!bankAccount.trim() || !bankIfsc.trim()) {
      notifications.show({
        color: "red",
        title: "Incomplete Form",
        message: "Bank account and IFSC code are required mandatory fields.",
      });
      return;
    }

    if (!asDraft && missingDocs.length > 0) {
      notifications.show({
        color: "red",
        title: "Missing Required Documents",
        message: `Please attach required documents: ${missingDocs.join(", ")}`,
      });
      return;
    }

    try {
      // 1. Create Draft
      const draft = await createDraft.mutateAsync({
        catalogue_version_id: schemeVersion.id,
        cycle: schemeVersion.academic_year,
        submission_data: {
          bank_account: bankAccount.trim(),
          bank_ifsc: bankIfsc.trim().toUpperCase(),
          bank_name: bankName.trim(),
          statement_of_purpose: remarks.trim(),
          document_ids: attachedDocs.map((d) => d.id),
        },
      });

      // 2. Update with annual income
      await updateDraft.mutateAsync({
        id: draft.id,
        annual_income_declared: income,
        submission_data: {
          bank_account: bankAccount.trim(),
          bank_ifsc: bankIfsc.trim().toUpperCase(),
          bank_name: bankName.trim(),
          statement_of_purpose: remarks.trim(),
          document_ids: attachedDocs.map((d) => d.id),
        },
      });

      // 3. If final submit
      if (!asDraft) {
        await submitApp.mutateAsync(draft.id);
        notifications.show({
          color: "green",
          title: "Application Submitted",
          message: `Application ${draft.application_number} submitted successfully for verification.`,
        });
      } else {
        notifications.show({
          color: "blue",
          title: "Draft Saved",
          message: `Application ${draft.application_number} saved as draft. You can complete it anytime.`,
        });
      }

      onSuccess?.();
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: asDraft ? "Draft Save Failed" : "Submission Failed",
        message: errorMessage(err),
      });
    }
  }

  const isLoading = createDraft.isPending || updateDraft.isPending || submitApp.isPending;

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        size="lg"
        title={`Apply for ${schemeVersion.entry_title} (${schemeVersion.academic_year})`}
      >
        <Stack gap="md">
          <Paper p="sm" withBorder bg="gray.0">
            <Text size="sm" fw={600}>
              Scheme Criteria Snapshot:
            </Text>
            <Group gap="xs" mt={4}>
              {schemeVersion.eligibility_criteria.min_cpi && (
                <Badge size="sm" color="blue">
                  Min CPI: {schemeVersion.eligibility_criteria.min_cpi}
                </Badge>
              )}
              {schemeVersion.eligibility_criteria.income_ceiling && (
                <Badge size="sm" color="teal">
                  Income Ceiling: ₹{Number(schemeVersion.eligibility_criteria.income_ceiling).toLocaleString()}
                </Badge>
              )}
              {schemeVersion.eligibility_criteria.allowed_programmes?.length && (
                <Badge size="sm" color="violet">
                  {schemeVersion.eligibility_criteria.allowed_programmes.join(", ")}
                </Badge>
              )}
            </Group>
          </Paper>

          {/* CPI notice: shown only when scheme has a minimum CPI requirement */}
          {schemeVersion.eligibility_criteria.min_cpi && (
            <Alert
              icon={<FaInfoCircle />}
              color="blue"
              variant="light"
              title="CPI is verified automatically"
              data-testid="cpi-info-alert"
            >
              This scheme requires a minimum CPI of{" "}
              <strong>{schemeVersion.eligibility_criteria.min_cpi}</strong>. Your
              CPI is fetched directly from academic records at the time of
              submission — you do not need to enter it here. If your results have
              not yet been declared for this semester, your application cannot be
              submitted until they are.
            </Alert>
          )}

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
                Attach Drive Link
              </Button>
            </Group>

            {requiredDocs.length > 0 && (
              <Stack gap={4}>
                {requiredDocs.map((docType) => {
                  const attached = attachedDocs.find(
                    (d) => normalizeDocType(d.doc_type) === normalizeDocType(docType),
                  );
                  return (
                    <Group key={docType} justify="space-between">
                      <Group gap="xs">
                        {attached ? (
                          <FaCheckCircle color="green" />
                        ) : (
                          <FaExclamationCircle color="orange" />
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

            {attachedDocs.length > 0 && (
              <Stack gap="xs" mt="sm">
                <Text size="xs" fw={600} c="dimmed">
                  Attached Links:
                </Text>
                {attachedDocs.map((d, i) => (
                  <Text key={i} size="xs" c="blue" component="a" href={d.drive_url} target="_blank">
                    🔗 {d.title} ({d.doc_type})
                  </Text>
                ))}
              </Stack>
            )}
          </Paper>

          {missingDocs.length > 0 && (
            <Alert color="orange" title="Notice">
              You can save this application as a <strong>Draft</strong> now and attach missing
              documents before final submission.
            </Alert>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              variant="outline"
              color="gray"
              loading={isLoading}
              onClick={() => handleApply(true)}
            >
              Save as Draft
            </Button>
            <Button
              color="blue"
              loading={isLoading}
              onClick={() => handleApply(false)}
            >
              Submit Application
            </Button>
          </Group>
        </Stack>
      </Modal>

      <DocumentAttachModal
        opened={docModalOpen}
        onClose={() => setDocModalOpen(false)}
        defaultDocType={missingDocs[0] || "income_certificate"}
        onAttached={(newDoc) => setAttachedDocs((prev) => [...prev, newDoc])}
      />
    </>
  );
}
