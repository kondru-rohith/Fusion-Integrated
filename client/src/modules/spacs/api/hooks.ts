/** Data access hooks for SPACS using TanStack React Query and the platform http client. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ApplicationDocument,
  ApplicationTransition,
  AwardCandidate,
  AwardCycle,
  CatalogueEntry,
  CatalogueVersion,
  ScholarshipApplication,
  SpacsAuditLog,
  VerificationFinding,
} from "./types";

const KEY = "spacs";

export const keys = {
  catalogue: () => [KEY, "catalogue"] as const,
  catalogueEntries: () => [KEY, "catalogue-entries"] as const,
  catalogueEntry: (id: number) => [KEY, "catalogue-entry", id] as const,
  myApplications: () => [KEY, "my-applications"] as const,
  application: (id: number) => [KEY, "application", id] as const,
  applicationHistory: (id: number) => [KEY, "application-history", id] as const,
  verificationQueue: () => [KEY, "verification-queue"] as const,
  decisionQueue: () => [KEY, "decision-queue"] as const,
  reusableDocs: (docType: string) => [KEY, "reusable-docs", docType] as const,
  awardCycles: () => [KEY, "award-cycles"] as const,
  awardCycle: (id: number) => [KEY, "award-cycle", id] as const,
  auditLogs: (targetType?: string) => [KEY, "audit-logs", targetType] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Catalogue -----------------------------------------------------------------
export function useCatalogue(params?: { manage?: boolean }) {
  const manage = params?.manage;
  return useQuery({
    queryKey: [...keys.catalogue(), { manage: Boolean(manage) }],
    queryFn: async () => {
      const url = manage ? "/spacs/catalogue/?manage=true" : "/spacs/catalogue/";
      return (await http.get<CatalogueVersion[]>(url)).data;
    },
    staleTime: 30_000,
  });
}

export function useCatalogueEntries() {
  return useQuery({
    queryKey: keys.catalogueEntries(),
    queryFn: async () => (await http.get<CatalogueEntry[]>("/spacs/catalogue/entries/")).data,
    staleTime: 30_000,
  });
}

export function useCreateCatalogueEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      code: string;
      title: string;
      kind: "scholarship" | "award";
      description?: string;
      allow_multiple_applications?: boolean;
    }) => (await http.post<CatalogueEntry>("/spacs/catalogue/entries/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCreateCatalogueVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      entryId,
      ...payload
    }: {
      entryId: number;
      academic_year: string;
      policy_reference?: string;
      candidate_source?: string;
      valid_from: string;
      valid_to: string;
      application_window_start?: string;
      application_window_end?: string;
      renewal_window_start?: string;
      renewal_window_end?: string;
      is_renewable?: boolean;
      sla_threshold_days?: number;
      eligibility_criteria?: Record<string, unknown>;
      required_documents?: string[];
    }) =>
      (
        await http.post<CatalogueVersion>(
          `/spacs/catalogue/entries/${entryId}/versions/`,
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishCatalogueVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      versionId,
      policyReference,
      validFrom,
      validTo,
    }: {
      versionId: number;
      policyReference: string;
      validFrom?: string;
      validTo?: string;
    }) =>
      (
        await http.post<CatalogueVersion>(
          `/spacs/catalogue/versions/${versionId}/publish/`,
          {
            policy_reference: policyReference,
            valid_from: validFrom,
            valid_to: validTo,
          },
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRetireCatalogueEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (entryId: number) =>
      (await http.post<CatalogueEntry>(`/spacs/catalogue/entries/${entryId}/retire/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Student Applications ------------------------------------------------------
export function useMyApplications() {
  return useQuery({
    queryKey: keys.myApplications(),
    queryFn: async () =>
      (await http.get<ScholarshipApplication[]>("/spacs/applications/mine/")).data,
    staleTime: 15_000,
  });
}

export function useApplication(id: number | null) {
  return useQuery({
    queryKey: id ? keys.application(id) : [KEY, "application", "none"],
    queryFn: async () => (await http.get<ScholarshipApplication>(`/spacs/applications/${id}/`)).data,
    enabled: !!id,
  });
}

export function useCreateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      catalogue_version_id: number;
      cycle: string;
      submission_data?: Record<string, unknown>;
    }) => (await http.post<ScholarshipApplication>("/spacs/applications/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      submission_data,
      annual_income_declared,
    }: {
      id: number;
      submission_data?: Record<string, unknown>;
      annual_income_declared?: number | string | null;
    }) =>
      (
        await http.put<ScholarshipApplication>(`/spacs/applications/${id}/`, {
          submission_data,
          annual_income_declared,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ScholarshipApplication>(`/spacs/applications/${id}/submit/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useResubmitApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<ScholarshipApplication>(`/spacs/applications/${id}/resubmit/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useWithdrawApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason?: string }) =>
      (
        await http.post<ScholarshipApplication>(`/spacs/applications/${id}/withdraw/`, {
          reason,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApplyRenewal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      parent_application_id: number;
      cycle: string;
      submission_data?: Record<string, unknown>;
      annual_income_declared?: number | string | null;
    }) => (await http.post<ScholarshipApplication>("/spacs/applications/renew/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useApplicationHistory(id: number | null) {
  return useQuery({
    queryKey: id ? keys.applicationHistory(id) : [KEY, "application-history", "none"],
    queryFn: async () =>
      (
        await http.get<{
          application_id: number;
          redacted: boolean;
          results: ApplicationTransition[];
        }>(`/spacs/applications/${id}/history/`)
      ).data,
    enabled: !!id,
  });
}

// -- Documents -----------------------------------------------------------------
export function useAttachDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      doc_type: string;
      url: string;
      title?: string;
      application_id?: number | null;
      valid_until?: string | null;
      is_reusable?: boolean;
    }) => (await http.post<ApplicationDocument>("/spacs/documents/attach-link/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReusableDocuments(docType: string) {
  return useQuery({
    queryKey: keys.reusableDocs(docType),
    queryFn: async () =>
      (
        await http.get<ApplicationDocument[]>(
          `/spacs/documents/reusable/?doc_type=${encodeURIComponent(docType)}`,
        )
      ).data,
    enabled: !!docType,
  });
}

export function useDeactivateDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (docId: number) =>
      (await http.post<{ status: string }>(`/spacs/documents/${docId}/deactivate/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Verification (Assistant) ---------------------------------------------------
export function useVerificationQueue() {
  return useQuery({
    queryKey: keys.verificationQueue(),
    queryFn: async () =>
      (await http.get<ScholarshipApplication[]>("/spacs/verification/queue/")).data,
    staleTime: 15_000,
  });
}

export function useRecordFinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      action,
      comments,
      correction_fields,
    }: {
      applicationId: number;
      action: "verified" | "correction_required" | "concern_raised";
      comments: string;
      correction_fields?: string[];
    }) =>
      (
        await http.post<VerificationFinding>(
          `/spacs/verification/${applicationId}/finding/`,
          {
            action,
            comments,
            correction_fields,
          },
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Decisions (Convener) -------------------------------------------------------
export function useDecisionQueue() {
  return useQuery({
    queryKey: keys.decisionQueue(),
    queryFn: async () =>
      (await http.get<ScholarshipApplication[]>("/spacs/decisions/queue/")).data,
    staleTime: 15_000,
  });
}

export function useMakeDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      applicationId,
      decision,
      sanction_order_ref,
      rationale,
    }: {
      applicationId: number;
      decision: "approved" | "rejected" | "returned_for_correction";
      sanction_order_ref?: string;
      rationale?: string;
    }) =>
      (
        await http.post<{ id: number }>(`/spacs/decisions/${applicationId}/outcome/`, {
          decision,
          sanction_order_ref,
          rationale,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Convocation Awards ---------------------------------------------------------
export function useAwardCycles() {
  return useQuery({
    queryKey: keys.awardCycles(),
    queryFn: async () => (await http.get<AwardCycle[]>("/spacs/awards/cycles/")).data,
    staleTime: 30_000,
  });
}

export function useAwardCycle(id: number | null) {
  return useQuery({
    queryKey: id ? keys.awardCycle(id) : [KEY, "award-cycle", "none"],
    queryFn: async () => (await http.get<AwardCycle>(`/spacs/awards/cycles/${id}/`)).data,
    enabled: !!id,
  });
}

export function useOpenAwardCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { catalogue_version_id: number; convocation_year: number }) =>
      (await http.post<AwardCycle>("/spacs/awards/cycles/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePrepareAwardPool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      cycleId,
      candidates,
    }: {
      cycleId: number;
      candidates: { user_id: number; cpi?: number; department?: string }[];
    }) =>
      (
        await http.post<AwardCycle>(`/spacs/awards/cycles/${cycleId}/prepare-pool/`, {
          candidates,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useEvaluateAwardCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      candidateId,
      score,
      remarks,
      shortlist_status,
    }: {
      candidateId: number;
      score: number;
      remarks?: string;
      shortlist_status?: "nominated" | "shortlisted" | "rejected";
    }) =>
      (
        await http.post<AwardCandidate>(
          `/spacs/awards/candidates/${candidateId}/evaluate/`,
          {
            score,
            remarks,
            shortlist_status,
          },
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordAwardOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      cycleId,
      candidate_outcomes,
      approval_ref,
    }: {
      cycleId: number;
      candidate_outcomes: { candidate_id: number; outcome: "winner" | "runner_up" | "none" }[];
      approval_ref?: string;
    }) =>
      (
        await http.post<AwardCycle>(`/spacs/awards/cycles/${cycleId}/record-outcome/`, {
          candidate_outcomes,
          approval_ref,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRecordAwardApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      cycleId,
      approval_ref,
    }: {
      cycleId: number;
      approval_ref: string;
    }) =>
      (
        await http.post<AwardCycle>(`/spacs/awards/cycles/${cycleId}/record-approval/`, {
          approval_ref,
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishAward() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (cycleId: number) =>
      (await http.post<AwardCycle>(`/spacs/awards/cycles/${cycleId}/publish/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Audit Logs ----------------------------------------------------------------
export function useAuditLogs(targetType?: string) {
  return useQuery({
    queryKey: keys.auditLogs(targetType),
    queryFn: async () => {
      const params = targetType ? `?target_type=${encodeURIComponent(targetType)}` : "";
      return (await http.get<SpacsAuditLog[]>(`/spacs/audit/${params}`)).data;
    },
    staleTime: 10_000,
  });
}
