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
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaCheck, FaEdit, FaPlus, FaUsers } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAwardCycle,
  useAwardCycles,
  useCatalogue,
  useOpenAwardCycle,
  usePrepareAwardPool,
  usePublishAward,
  useRecordAwardOutcome,
} from "../api/hooks";
import type { AwardCandidate, AwardCycle } from "../api/types";
import { AwardEvaluateModal } from "../components/AwardEvaluateModal";

export default function AwardsPage() {
  const { data: cycles, isPending, error, refetch } = useAwardCycles();
  const { data: catalogue } = useCatalogue();

  const [openCycleModal, setOpenCycleModal] = useState(false);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);

  // Pool preparation modal
  const [prepareModalCycle, setPrepareModalCycle] = useState<AwardCycle | null>(null);
  const [poolCandidates, setPoolCandidates] = useState("");

  // Committee Evaluation modal
  const [evaluateCandidate, setEvaluateCandidate] = useState<AwardCandidate | null>(null);

  // Outcome / Approval modal
  const [outcomeModalCycle, setOutcomeModalCycle] = useState<AwardCycle | null>(null);
  const [winnerCandidateId, setWinnerCandidateId] = useState<string>("");
  const [approvalRef, setApprovalRef] = useState("");

  // Cycle creation state
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [convocationYear, setConvocationYear] = useState<number | string>(2026);

  const openCycle = useOpenAwardCycle();
  const preparePool = usePrepareAwardPool();
  const recordOutcome = useRecordAwardOutcome();
  const publishAward = usePublishAward();

  const { data: cycleDetail, refetch: refetchCycle } = useAwardCycle(selectedCycleId);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const awardVersions = (catalogue || []).filter((v) => v.entry_kind === "award");

  function handleOpenCycle() {
    if (!selectedVersionId) {
      notifications.show({
        color: "red",
        title: "Scheme Required",
        message: "Please select an award scheme version.",
      });
      return;
    }

    openCycle.mutate(
      {
        catalogue_version_id: Number(selectedVersionId),
        convocation_year: Number(convocationYear),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Award Cycle Opened",
            message: `Convocation ${convocationYear} cycle opened for evaluation.`,
          });
          setOpenCycleModal(false);
          refetch();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Cycle Open Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handlePreparePool() {
    if (!prepareModalCycle || !poolCandidates.trim()) return;

    // Parse candidate lines: "userId, cpi, dept"
    const parsed: { user_id: number; cpi?: number; department?: string }[] = [];
    for (const line of poolCandidates.split("\n")) {
      const parts = line.split(",").map((s) => s.trim());
      const uid = Number(parts[0]);
      if (uid) {
        parsed.push({
          user_id: uid,
          cpi: parts[1] ? Number(parts[1]) : undefined,
          department: parts[2] || "CSE",
        });
      }
    }

    if (!parsed.length) {
      notifications.show({
        color: "red",
        title: "Invalid Candidates",
        message: "Enter at least one candidate (user_id, cpi, dept).",
      });
      return;
    }

    preparePool.mutate(
      { cycleId: prepareModalCycle.id, candidates: parsed },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Candidate Pool Prepared",
            message: `Pool populated with ${parsed.length} candidate(s).`,
          });
          setPrepareModalCycle(null);
          setPoolCandidates("");
          refetch();
          refetchCycle();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Preparation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handleRecordOutcome() {
    if (!outcomeModalCycle || !winnerCandidateId) {
      notifications.show({
        color: "red",
        title: "Winner Required",
        message: "Please select the winner candidate.",
      });
      return;
    }

    recordOutcome.mutate(
      {
        cycleId: outcomeModalCycle.id,
        candidate_outcomes: [
          { candidate_id: Number(winnerCandidateId), outcome: "winner" },
        ],
        approval_ref: approvalRef.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Award Outcome Recorded",
            message: "Winner outcome and recommendations recorded.",
          });
          setOutcomeModalCycle(null);
          setWinnerCandidateId("");
          refetch();
          refetchCycle();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Recording Outcome Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  function handlePublish(cycle: AwardCycle) {
    if (!confirm(`Are you ready to publish final award winners for ${cycle.scheme_title}?`)) {
      return;
    }
    publishAward.mutate(cycle.id, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Results Published",
          message: "Award winner announcements published and students notified.",
        });
        refetch();
        refetchCycle();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Publication Failed",
          message: errorMessage(err),
        });
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Convocation Awards & Medals"
        subtitle="Manage convocation cycles, committee candidate scoring, and senate award publications (SPACS)"
        action={
          <Button leftSection={<FaPlus />} onClick={() => setOpenCycleModal(true)}>
            Open New Award Cycle
          </Button>
        }
      />

      <Card withBorder padding="md" mb="lg">
        <DataTable<AwardCycle>
          rows={cycles || []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            title: "No award cycles found",
            description: "Open a new convocation award cycle.",
          }}
          minWidth={900}
          columns={[
            {
              key: "scheme_title",
              header: "Award Scheme",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.scheme_title}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Convocation Year: {r.convocation_year}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "status",
              header: "Cycle State",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "actions",
              header: "Cycle Actions",
              render: (r) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() => setSelectedCycleId(r.id)}
                  >
                    View Pool ({r.candidates?.length ?? "Inspect"})
                  </Button>

                  {r.status === "cycle_open" && (
                    <Button
                      size="xs"
                      color="blue"
                      leftSection={<FaUsers />}
                      onClick={() => setPrepareModalCycle(r)}
                    >
                      Prepare Pool
                    </Button>
                  )}

                  {r.status === "committee_result_recorded" && (
                    <Button
                      size="xs"
                      color="indigo"
                      leftSection={<FaCheck />}
                      onClick={() => setOutcomeModalCycle(r)}
                    >
                      Record Senate Approval
                    </Button>
                  )}

                  {r.status === "ready_for_publication" && (
                    <Button
                      size="xs"
                      color="green"
                      leftSection={<FaBullhorn />}
                      onClick={() => handlePublish(r)}
                    >
                      Publish Results
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Selected Cycle Candidate Pool */}
      {selectedCycleId && cycleDetail && (
        <Card withBorder padding="lg">
          <Group justify="space-between" mb="md">
            <div>
              <Title order={4}>Candidate Pool: {cycleDetail.scheme_title}</Title>
              <Text size="xs" c="dimmed">
                Convocation {cycleDetail.convocation_year} • Status: {cycleDetail.status}
              </Text>
            </div>
            {cycleDetail.status === "under_committee_evaluation" && (
              <Button
                size="xs"
                color="indigo"
                onClick={() => setOutcomeModalCycle(cycleDetail)}
              >
                Finalize Committee Outcome
              </Button>
            )}
          </Group>

          {!cycleDetail.candidates?.length ? (
            <Paper withBorder p="md" ta="center">
              <Text c="dimmed">No candidates populated in this pool yet.</Text>
            </Paper>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>User ID</Table.Th>
                  <Table.Th>Dept</Table.Th>
                  <Table.Th>CPI</Table.Th>
                  <Table.Th>Committee Score</Table.Th>
                  <Table.Th>Shortlist Status</Table.Th>
                  <Table.Th>Outcome</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {cycleDetail.candidates.map((cand) => (
                  <Table.Tr key={cand.id}>
                    <Table.Td>Student u{cand.user_id}</Table.Td>
                    <Table.Td>{cand.department}</Table.Td>
                    <Table.Td>{cand.cpi}</Table.Td>
                    <Table.Td>
                      {cand.committee_score ? <strong>{cand.committee_score}</strong> : "—"}
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs" variant="outline">
                        {cand.shortlist_status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {cand.final_outcome !== "none" ? (
                        <Badge size="xs" color={cand.final_outcome === "winner" ? "yellow" : "teal"}>
                          {cand.final_outcome.toUpperCase()}
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Tooltip label="Evaluate Candidate">
                        <ActionIcon
                          variant="light"
                          color="blue"
                          onClick={() => setEvaluateCandidate(cand)}
                        >
                          <FaEdit />
                        </ActionIcon>
                      </Tooltip>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      )}

      {/* Modal 1: Open Cycle */}
      <Modal
        opened={openCycleModal}
        onClose={() => setOpenCycleModal(false)}
        title="Open Convocation Award Cycle"
      >
        <Stack gap="md">
          <Select
            label="Convocation Award Scheme"
            required
            data={awardVersions.map((v) => ({
              value: String(v.id),
              label: `${v.entry_title} (v${v.version_number})`,
            }))}
            value={selectedVersionId}
            onChange={setSelectedVersionId}
          />
          <NumberInput
            label="Convocation Year"
            required
            min={2020}
            max={2035}
            value={convocationYear}
            onChange={(v) => setConvocationYear(v ?? 2026)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpenCycleModal(false)}>
              Cancel
            </Button>
            <Button loading={openCycle.isPending} onClick={handleOpenCycle}>
              Open Cycle
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal 2: Prepare Pool */}
      <Modal
        opened={!!prepareModalCycle}
        onClose={() => setPrepareModalCycle(null)}
        title="Populate Candidate Pool"
      >
        <Stack gap="md">
          <Text size="xs" c="dimmed">
            Enter candidate roster (one per line: <code>user_id, cpi, department</code>):
          </Text>
          <Textarea
            rows={5}
            placeholder="1001, 9.8, CSE&#10;1002, 9.6, ECE"
            value={poolCandidates}
            onChange={(e) => setPoolCandidates(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setPrepareModalCycle(null)}>
              Cancel
            </Button>
            <Button loading={preparePool.isPending} onClick={handlePreparePool}>
              Load Candidate Pool
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal 3: Committee Evaluation */}
      {evaluateCandidate && (
        <AwardEvaluateModal
          opened={!!evaluateCandidate}
          onClose={() => setEvaluateCandidate(null)}
          candidate={evaluateCandidate}
          onSuccess={() => {
            refetch();
            refetchCycle();
          }}
        />
      )}

      {/* Modal 4: Record Outcome & Senate Reference */}
      <Modal
        opened={!!outcomeModalCycle}
        onClose={() => setOutcomeModalCycle(null)}
        title="Record Award Committee Outcome"
      >
        <Stack gap="md">
          <Select
            label="Select Award Winner"
            required
            data={(outcomeModalCycle?.candidates || cycleDetail?.candidates || []).map((c) => ({
              value: String(c.id),
              label: `Student u${c.user_id} (${c.department}) — Score: ${c.committee_score || "N/A"}`,
            }))}
            value={winnerCandidateId}
            onChange={(v) => setWinnerCandidateId(v || "")}
          />
          <TextInput
            label="Senate / Approval Reference (Optional if pending)"
            placeholder="e.g. SENATE/AWARDS/2026/01"
            value={approvalRef}
            onChange={(e) => setApprovalRef(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOutcomeModalCycle(null)}>
              Cancel
            </Button>
            <Button loading={recordOutcome.isPending} onClick={handleRecordOutcome}>
              Record Winner
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
