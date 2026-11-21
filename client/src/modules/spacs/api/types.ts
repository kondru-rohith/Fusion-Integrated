/** Wire types for the SPACS (Awards and Scholarships) API.
 * Matches backend DRF serializers and models.
 */

export interface CatalogueEntry {
  id: number;
  code: string;
  title: string;
  kind: "scholarship" | "award";
  description: string;
  status: "draft" | "active" | "retired";
  allow_multiple_applications: boolean;
  created_at: string;
  updated_at: string;
}

export interface EligibilityCriteria {
  min_cpi?: number | string;
  income_ceiling?: number | string;
  allowed_programmes?: string[];
  allowed_disciplines?: string[];
  allowed_batches?: number[];
  allowed_categories?: string[];
  max_backlogs?: number;
  mandatory_fields?: string[];
}

export interface CatalogueVersion {
  id: number;
  entry: number;
  entry_code: string;
  entry_title: string;
  entry_kind: "scholarship" | "award";
  version_number: number;
  academic_year: string;
  policy_reference: string;
  candidate_source: "student_application" | "system_generated" | "nomination";
  valid_from: string;
  valid_to: string;
  application_window_start: string | null;
  application_window_end: string | null;
  renewal_window_start: string | null;
  renewal_window_end: string | null;
  is_renewable: boolean;
  sla_threshold_days: number;
  eligibility_criteria: EligibilityCriteria;
  required_documents: string[];
  renewal_criteria: Record<string, unknown>;
  committee_config: Record<string, unknown>;
  status: "draft" | "published" | "retired";
  published_at: string | null;
  published_by: number | null;
  created_at: string;
}

export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "under_verification"
  | "correction_required"
  | "resubmitted"
  | "verified"
  | "verification_concern"
  | "under_convener_review"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "renewal_submitted"
  | "renewal_under_verification"
  | "renewal_resubmitted"
  | "renewal_verified"
  | "renewal_under_decision"
  | "renewed"
  | "renewal_rejected";

export interface ApplicationDocument {
  id: number;
  user_id: number;
  application?: number | null;
  doc_type: string;
  title: string;
  original_filename: string;
  drive_url: string;
  drive_file_id: string;
  issued_date: string | null;
  valid_until: string | null;
  is_active: boolean;
  is_reusable: boolean;
  verification_status: "pending" | "valid" | "invalid" | "expired";
  verification_notes: string;
  verified_at: string | null;
  created_at: string;
}

export interface ScholarshipApplication {
  id: number;
  user_id: number;
  catalogue_entry: number;
  catalogue_version: number;
  scheme_title: string;
  scheme_kind: "scholarship" | "award";
  cycle: string;
  application_number: string;
  status: ApplicationStatus;
  is_renewal: boolean;
  parent_application: number | null;
  cpi_at_apply: string | null;
  annual_income_declared: string | null;
  demographic_snapshot: Record<string, unknown>;
  submission_data: Record<string, unknown>;
  /** Required documents inherited from the scheme version. */
  required_documents: string[];
  submitted_at: string | null;
  resubmitted_at: string | null;
  withdrawn_at: string | null;
  withdrawn_reason: string;
  assigned_assistant_id: number | null;
  documents?: ApplicationDocument[];
  verification_findings?: VerificationFinding[];
  decisions?: ScholarshipDecision[];
  created_at: string;
  updated_at: string;
}

export interface VerificationFinding {
  id: number;
  application: number;
  reviewer_id?: number;
  assistant_id?: number;
  action: "verified" | "correction_required" | "concern_raised";
  comments: string;
  correction_fields: string[];
  created_at: string;
}

export interface ScholarshipDecision {
  id: number;
  application: number;
  convener_id: number;
  decision: "approved" | "rejected" | "returned_for_correction";
  sanction_order_ref: string;
  rationale: string;
  decided_at: string;
}

export interface AwardCycle {
  id: number;
  catalogue_version: number;
  scheme_title: string;
  convocation_year: number;
  status:
    | "cycle_open"
    | "candidate_pool_prepared"
    | "under_committee_evaluation"
    | "committee_result_recorded"
    | "awaiting_institutional_approval"
    | "ready_for_publication"
    | "published";
  institutional_approval_ref: string;
  published_at: string | null;
  published_by: number | null;
  candidates?: AwardCandidate[];
  created_at: string;
}

export interface AwardCandidate {
  id: number;
  award_cycle: number;
  scheme_title?: string;
  user_id: number;
  student_name?: string;
  roll_number?: string;
  cpi: string;
  department: string;
  committee_score: string | null;
  shortlist_status: "nominated" | "shortlisted" | "rejected";
  final_outcome: "winner" | "runner_up" | "none";
  remarks: string;
  created_at: string;
}

export interface ApplicationTransition {
  id: number;
  from_status: string;
  to_status: string;
  actor_user_id?: number | null;
  actor_label: string;
  reason?: string;
  at: string;
}

export interface SpacsAuditLog {
  id: number;
  actor_id: number;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
  created_at: string;
}
