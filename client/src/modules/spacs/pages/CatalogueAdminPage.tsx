import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaPlus, FaPowerOff } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCatalogue,
  useCatalogueEntries,
  useCreateCatalogueEntry,
  useCreateCatalogueVersion,
  usePublishCatalogueVersion,
  useRetireCatalogueEntry,
} from "../api/hooks";
import type { CatalogueEntry, CatalogueVersion } from "../api/types";

export default function CatalogueAdminPage() {
  const {
    data: versions,
    isPending: versionsPending,
    error: versionsError,
    refetch: refetchVersions,
  } = useCatalogue({ manage: true });
  const {
    data: entries,
    isPending: entriesPending,
    error: entriesError,
    refetch: refetchEntries,
  } = useCatalogueEntries();

  function refetchAll() {
    refetchVersions();
    refetchEntries();
  }

  // Modals state
  const [entryModalOpen, setEntryModalOpen] = useState(false);
  const [publishModalVersion, setPublishModalVersion] = useState<CatalogueVersion | null>(null);
  const [newVersionModalEntry, setNewVersionModalEntry] = useState<{
    entryId: number;
    entryTitle: string;
  } | null>(null);

  // New Entry form
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<"scholarship" | "award">("scholarship");
  const [desc, setDesc] = useState("");

  // Publish form
  const [policyRef, setPolicyRef] = useState("");

  // New Version form
  const [versionYear, setVersionYear] = useState("2026-27");
  const [validFrom, setValidFrom] = useState(new Date().toISOString().slice(0, 10));
  const [validTo, setValidTo] = useState(
    new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10),
  );
  const [minCpi, setMinCpi] = useState<number | string>(7.0);
  const [incomeCeiling, setIncomeCeiling] = useState<number | string>(600000);
  const [reqDocs, setReqDocs] = useState("income_certificate");

  const createEntry = useCreateCatalogueEntry();
  const createVersion = useCreateCatalogueVersion();
  const publishVersion = usePublishCatalogueVersion();
  const retireEntry = useRetireCatalogueEntry();

  const error = versionsError || entriesError;
  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const versionedEntryIds = new Set((versions || []).map((v) => v.entry));
  const unversionedEntries = (entries || []).filter((e) => !versionedEntryIds.has(e.id));

  function handleCreateEntry() {
    if (!code.trim() || !title.trim()) {
      notifications.show({
        color: "red",
        title: "Required Fields",
        message: "Code and Title are required.",
      });
      return;
    }

    createEntry.mutate(
      {
        code: code.trim().toLowerCase(),
        title: title.trim(),
        kind,
        description: desc.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Scheme Created",
            message: `Catalogue entry ${title} created successfully.`,
          });
          setEntryModalOpen(false);
          setCode("");
          setTitle("");
          setDesc("");
          refetchAll();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Creation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handlePublishVersion() {
    if (!publishModalVersion || !policyRef.trim()) {
      notifications.show({
        color: "red",
        title: "Policy Reference Required",
        message: "Senate or institutional policy reference is required to publish (BR-SPACS-015).",
      });
      return;
    }

    publishVersion.mutate(
      {
        versionId: publishModalVersion.id,
        policyReference: policyRef.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Version Published",
            message: `Version published and open for applications.`,
          });
          setPublishModalVersion(null);
          setPolicyRef("");
          refetchAll();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Publish Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handleCreateVersion() {
    if (!newVersionModalEntry) return;

    createVersion.mutate(
      {
        entryId: newVersionModalEntry.entryId,
        academic_year: versionYear,
        valid_from: validFrom,
        valid_to: validTo,
        eligibility_criteria: {
          min_cpi: Number(minCpi),
          income_ceiling: Number(incomeCeiling),
        },
        required_documents: reqDocs.split(",").map((s) => s.trim()).filter(Boolean),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Version Created",
            message: "New policy version drafted successfully.",
          });
          setNewVersionModalEntry(null);
          refetchAll();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Version Draft Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handleRetire(v: CatalogueVersion) {
    if (!confirm(`Are you sure you want to retire scheme ${v.entry_title}?`)) {
      return;
    }
    retireEntry.mutate(v.entry, {
      onSuccess: () => {
        notifications.show({
          color: "gray",
          title: "Scheme Retired",
          message: `${v.entry_title} has been retired.`,
        });
        refetchAll();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Retire Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Scheme Catalogue & Policy Management"
        subtitle="Manage scholarship and convocation award schemes, versions, eligibility rules, and senate references"
        action={
          <Button
            leftSection={<FaPlus />}
            onClick={() => setEntryModalOpen(true)}
          >
            Create New Scheme
          </Button>
        }
      />

      {unversionedEntries.length > 0 && (
        <Card withBorder padding="md" mb="lg">
          <Stack gap="xs" mb="sm">
            <Group justify="space-between">
              <div>
                <Text fw={600} size="md">
                  Schemes Awaiting First Version
                </Text>
                <Text size="xs" c="dimmed">
                  These scheme entries have been registered but have no policy versions drafted yet.
                </Text>
              </div>
              <Badge color="yellow" variant="light">
                {unversionedEntries.length} unversioned
              </Badge>
            </Group>
          </Stack>

          <DataTable<CatalogueEntry>
            rows={unversionedEntries}
            loading={entriesPending}
            rowKey={(r) => r.id}
            empty={{
              title: "No unversioned schemes",
              description: "All registered schemes have at least one policy version.",
            }}
            minWidth={800}
            columns={[
              {
                key: "title",
                header: "Scheme Details",
                render: (r) => (
                  <Stack gap={0}>
                    <Text fw={600} size="sm">
                      {r.title}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Code: {r.code} • {r.kind.toUpperCase()}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "kind",
                header: "Kind",
                render: (r) => (
                  <Badge color={r.kind === "award" ? "orange" : "blue"} variant="light" size="sm">
                    {r.kind.toUpperCase()}
                  </Badge>
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
                  <Button
                    size="xs"
                    variant="light"
                    color="blue"
                    leftSection={<FaPlus />}
                    onClick={() =>
                      setNewVersionModalEntry({ entryId: r.id, entryTitle: r.title })
                    }
                  >
                    Create First Version
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      )}

      <Card withBorder padding="md">
        <DataTable<CatalogueVersion>
          rows={versions || []}
          loading={versionsPending}
          rowKey={(r) => r.id}
          empty={{
            title: "No scheme versions found",
            description: "Create a scheme entry and draft a version.",
          }}
          minWidth={950}
          columns={[
            {
              key: "entry_title",
              header: "Scheme Details",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.entry_title}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Code: {r.entry_code} • {r.entry_kind.toUpperCase()}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "version",
              header: "Version & Year",
              render: (r) => (
                <Text size="sm">
                  v{r.version_number} ({r.academic_year})
                </Text>
              ),
            },
            {
              key: "policy_reference",
              header: "Policy Ref",
              render: (r) => (
                <Text size="xs" fw={500}>
                  {r.policy_reference || "Pending Publication"}
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
                  {r.status === "draft" && (
                    <Tooltip label="Publish with Senate Reference">
                      <ActionIcon
                        aria-label="Publish with Senate Reference"
                        color="green"
                        variant="light"
                        onClick={() => setPublishModalVersion(r)}
                      >
                        <FaCheck />
                      </ActionIcon>
                    </Tooltip>
                  )}
                  <Tooltip label="Draft Next Cycle Version">
                    <ActionIcon
                      aria-label="Draft Next Cycle Version"
                      color="blue"
                      variant="light"
                      onClick={() =>
                        setNewVersionModalEntry({ entryId: r.entry, entryTitle: r.entry_title })
                      }
                    >
                      <FaPlus />
                    </ActionIcon>
                  </Tooltip>
                  {r.status !== "retired" && (
                    <Tooltip label="Retire Scheme Entry">
                      <ActionIcon
                        aria-label="Retire Scheme Entry"
                        color="red"
                        variant="light"
                        onClick={() => handleRetire(r)}
                      >
                        <FaPowerOff />
                      </ActionIcon>
                    </Tooltip>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Modal 1: Create Scheme Entry */}
      <Modal
        opened={entryModalOpen}
        onClose={() => setEntryModalOpen(false)}
        title="Create Scholarship or Award Scheme"
      >
        <Stack gap="md">
          <TextInput
            label="Scheme Code (Identifier)"
            required
            placeholder="e.g. director-gold-medal"
            value={code}
            onChange={(e) => setCode(e.currentTarget.value)}
          />
          <TextInput
            label="Scheme Title"
            required
            placeholder="e.g. Director Gold Medal for Academic Excellence"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <Select
            label="Scheme Kind"
            required
            data={[
              { value: "scholarship", label: "Scholarship / Financial Aid" },
              { value: "award", label: "Convocation Award / Medal" },
            ]}
            value={kind}
            onChange={(v) => setKind((v as "scholarship" | "award") ?? "scholarship")}
          />
          <Textarea
            label="Description / Objective"
            rows={3}
            value={desc}
            onChange={(e) => setDesc(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEntryModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={createEntry.isPending} onClick={handleCreateEntry}>
              Save Scheme Entry
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal 2: Publish Version */}
      <Modal
        opened={!!publishModalVersion}
        onClose={() => setPublishModalVersion(null)}
        title="Publish Policy Version"
      >
        <Stack gap="md">
          <Text size="sm">
            Publishing activates scheme <strong>{publishModalVersion?.entry_title}</strong> for
            student applications.
          </Text>
          <TextInput
            label="Senate / Board Policy Reference (BR-SPACS-015)"
            required
            placeholder="e.g. SENATE/54/2026/AWARDS/RES-3"
            value={policyRef}
            onChange={(e) => setPolicyRef(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setPublishModalVersion(null)}>
              Cancel
            </Button>
            <Button
              color="green"
              loading={publishVersion.isPending}
              onClick={handlePublishVersion}
            >
              Publish Version
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal 3: Draft Next Version */}
      <Modal
        opened={!!newVersionModalEntry}
        onClose={() => setNewVersionModalEntry(null)}
        title={`Draft Version for ${newVersionModalEntry?.entryTitle}`}
      >
        <Stack gap="md">
          <TextInput
            label="Academic Year"
            required
            placeholder="e.g. 2027-28"
            value={versionYear}
            onChange={(e) => setVersionYear(e.currentTarget.value)}
          />
          <Group grow>
            <TextInput
              label="Valid From"
              placeholder="YYYY-MM-DD"
              value={validFrom}
              onChange={(e) => setValidFrom(e.currentTarget.value)}
            />
            <TextInput
              label="Valid To"
              placeholder="YYYY-MM-DD"
              value={validTo}
              onChange={(e) => setValidTo(e.currentTarget.value)}
            />
          </Group>
          <NumberInput
            label="Minimum CPI Requirement"
            min={0}
            max={10}
            step={0.1}
            value={minCpi}
            onChange={(v) => setMinCpi(v ?? 0)}
          />
          <NumberInput
            label="Income Ceiling (₹)"
            min={0}
            step={25000}
            value={incomeCeiling}
            onChange={(v) => setIncomeCeiling(v ?? 0)}
          />
          <TextInput
            label="Required Documents (Comma-separated)"
            placeholder="income_certificate, grade_sheet"
            value={reqDocs}
            onChange={(e) => setReqDocs(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setNewVersionModalEntry(null)}>
              Cancel
            </Button>
            <Button loading={createVersion.isPending} onClick={handleCreateVersion}>
              Create Draft Version
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
