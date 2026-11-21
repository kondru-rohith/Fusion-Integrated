import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { FaGraduationCap, FaMedal, FaSearch } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCatalogue } from "../api/hooks";
import type { CatalogueVersion } from "../api/types";
import { ApplyModal } from "../components/ApplyModal";

export default function CataloguePage() {
  const { data: schemes, isPending, error, refetch } = useCatalogue();
  const { can } = useAuth();
  const [query, setQuery] = useState("");
  const [selectedScheme, setSelectedScheme] = useState<CatalogueVersion | null>(null);

  const canApply = can("spacs.application.create");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const filteredSchemes = (schemes || []).filter((s) => {
    const q = query.toLowerCase();
    return (
      s.entry_title.toLowerCase().includes(q) ||
      s.entry_code.toLowerCase().includes(q) ||
      s.academic_year.toLowerCase().includes(q)
    );
  });

  return (
    <Container size="xl">
      <PageHeader
        title="Scholarship & Award Opportunities"
        subtitle="Explore active institutional scholarships, endowments, and convocation awards (SPACS)"
      />

      <Group mb="lg">
        <TextInput
          placeholder="Search by scheme title, code, or academic year..."
          leftSection={<FaSearch />}
          w={400}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
        />
      </Group>

      {isPending ? (
        <Text size="sm" c="dimmed">
          Loading scheme opportunities...
        </Text>
      ) : filteredSchemes.length === 0 ? (
        <Paper withBorder p="xl" ta="center">
          <Text c="dimmed">No active scholarship opportunities found.</Text>
        </Paper>
      ) : (
        <Grid>
          {filteredSchemes.map((scheme) => {
            const isAward = scheme.entry_kind === "award";
            const isOpen =
              !scheme.application_window_end ||
              new Date(scheme.application_window_end) >= new Date();

            return (
              <Grid.Col key={scheme.id} span={{ base: 12, md: 6 }}>
                <Card withBorder padding="lg" radius="md" h="100%">
                  <Stack justify="space-between" h="100%">
                    <Stack gap="xs">
                      <Group justify="space-between" align="flex-start">
                        <Group gap="xs">
                          {isAward ? (
                            <FaMedal color="#d97706" size={20} />
                          ) : (
                            <FaGraduationCap color="#2563eb" size={20} />
                          )}
                          <Title order={4}>{scheme.entry_title}</Title>
                        </Group>
                        <Badge color={isAward ? "orange" : "blue"} variant="light">
                          {scheme.entry_kind.toUpperCase()}
                        </Badge>
                      </Group>

                      <Text size="xs" c="dimmed">
                        Code: {scheme.entry_code} • Cycle: {scheme.academic_year} • Policy Ref:{" "}
                        {scheme.policy_reference}
                      </Text>

                      {/* Criteria Highlights */}
                      <Paper p="xs" withBorder bg="gray.0" mt="xs">
                        <Stack gap={4}>
                          <Text size="xs" fw={600}>
                            Eligibility & Requirements:
                          </Text>
                          <Group gap="xs">
                            {scheme.eligibility_criteria.min_cpi && (
                              <Badge size="xs" color="blue" variant="outline">
                                Min CPI: {scheme.eligibility_criteria.min_cpi}
                              </Badge>
                            )}
                            {scheme.eligibility_criteria.income_ceiling && (
                              <Badge size="xs" color="teal" variant="outline">
                                Income: &lt;= ₹
                                {Number(scheme.eligibility_criteria.income_ceiling).toLocaleString()}
                              </Badge>
                            )}
                            {scheme.eligibility_criteria.allowed_programmes?.length ? (
                              <Badge size="xs" color="violet" variant="outline">
                                {scheme.eligibility_criteria.allowed_programmes.join(", ")}
                              </Badge>
                            ) : null}
                          </Group>
                        </Stack>
                      </Paper>

                      {/* Window Deadlines */}
                      <Group gap="xs" mt="xs">
                        <Text size="xs" c="dimmed">
                          Application Window:
                        </Text>
                        <Text size="xs" fw={500}>
                          {scheme.application_window_end
                            ? `Closes ${new Date(scheme.application_window_end).toLocaleDateString()}`
                            : "Open"}
                        </Text>
                      </Group>
                    </Stack>

                    {canApply && (
                      <Group justify="flex-end" mt="md">
                        <Button
                          variant={isOpen ? "filled" : "default"}
                          disabled={!isOpen}
                          onClick={() => setSelectedScheme(scheme)}
                        >
                          {isOpen ? "Apply Now" : "Application Window Closed"}
                        </Button>
                      </Group>
                    )}
                  </Stack>
                </Card>
              </Grid.Col>
            );
          })}
        </Grid>
      )}

      {selectedScheme && (
        <ApplyModal
          opened={!!selectedScheme}
          onClose={() => setSelectedScheme(null)}
          schemeVersion={selectedScheme}
          onSuccess={() => refetch()}
        />
      )}
    </Container>
  );
}
