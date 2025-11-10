/**
 * TypeScript types for Neo4j graph entities.
 *
 * These types mirror the Pydantic schemas from backend/src/schemas/graph.py.
 * All regulatory entities include citation fields for source traceability.
 */

/**
 * Confidence score for regulatory claims.
 */
export enum ConfidenceLevel {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
}

/**
 * Categories of government processes.
 */
export enum ProcessCategory {
  PERMITS = 'permits',
  LICENSES = 'licenses',
  BENEFITS = 'benefits',
}

/**
 * Types of web resources.
 */
export enum WebResourceType {
  HOW_TO = 'how_to',
  PROGRAM = 'program',
  PORTAL = 'portal',
  PDF_FORM = 'pdf_form',
}

/**
 * Status of a user application.
 */
export enum ApplicationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  DENIED = 'denied',
}

/**
 * Category of application.
 */
export enum ApplicationCategory {
  NEW = 'new',
  RENEWAL = 'renewal',
  REPLACEMENT = 'replacement',
  RENTAL = 'rental',
}

/**
 * Base interface for timestamp fields.
 */
export interface TimestampFields {
  /** Timestamp when record was created (ISO 8601) */
  created_at: string
  /** Timestamp when record was last updated (ISO 8601) */
  updated_at: string
}

/**
 * Base interface for citation/provenance fields.
 * All regulatory data must be traceable to official sources.
 */
export interface CitationFields {
  /** URL to official source (regulation, webpage, PDF) */
  source_url: string
  /** Date when information was last verified (YYYY-MM-DD) */
  last_verified: string
  /** Confidence level in this data */
  confidence: ConfidenceLevel
}

/**
 * High-level government service or process.
 * Example: "Boston Resident Parking Permit"
 */
export interface Process extends CitationFields, TimestampFields {
  /** Unique process identifier (e.g., "boston_rpp") */
  process_id: string
  /** Human-readable process name */
  name: string
  /** One-sentence summary of the process */
  description: string
  /** Process category */
  category: ProcessCategory
  /** Governing authority (e.g., "City of Boston") */
  jurisdiction: string
}

/**
 * Actionable task within a process.
 * Example: "Gather proof of residency"
 */
export interface Step extends CitationFields, TimestampFields {
  /** Unique step identifier (e.g., "rpp.gather_proof") */
  step_id: string
  /** Parent process ID */
  process_id: string
  /** Short step label */
  name: string
  /** Full action description */
  description: string
  /** Sequence number (1-indexed) */
  order: number
  /** Official time estimate in minutes */
  estimated_time_minutes: number | null
  /** Median time from user feedback */
  observed_time_minutes: number | null
  /** Cost in USD */
  cost_usd: number
  /** Whether this step can be skipped */
  optional: boolean
}

/**
 * Eligibility condition or rule.
 * Example: "MA registration at Boston address"
 */
export interface Requirement extends CitationFields, TimestampFields {
  /** Unique requirement identifier (e.g., "rpp.req.ma_registration") */
  requirement_id: string
  /** Human-readable requirement description */
  text: string
  /** Reference to Facts Registry (e.g., "rpp.eligibility.registration_state") */
  fact_id: string
  /** Process ID this requirement applies to */
  applies_to_process: string
  /** Whether this blocks progress if not met */
  hard_gate: boolean
  /** Page or PDF section reference */
  source_section: string | null
}

/**
 * Atomic regulatory fact.
 * Example: "Proof of residency ≤30 days"
 */
export interface Rule extends CitationFields, TimestampFields {
  /** Unique rule identifier (e.g., "RPP-15-4A") */
  rule_id: string
  /** Exact regulation text */
  text: string
  /** Reference to Facts Registry */
  fact_id: string
  /** Scope of rule (e.g., "general", "rental", "military") */
  scope: string
  /** Section/page number reference */
  source_section: string
  /** When this rule took effect (YYYY-MM-DD) */
  effective_date: string | null
}

/**
 * Template for accepted documents.
 * Example: "Utility bill ≤30 days"
 */
export interface DocumentType extends CitationFields, TimestampFields {
  /** Unique document type identifier (e.g., "proof.utility_bill") */
  doc_type_id: string
  /** Human-readable document type name */
  name: string
  /** Maximum age in days (e.g., 30) */
  freshness_days: number
  /** Whether document name must match applicant name */
  name_match_required: boolean
  /** Whether document address must match Boston address */
  address_match_required: boolean
  /** List of example issuers (e.g., ["National Grid", "Eversource"]) */
  examples: string[]
}

/**
 * User-provided document instance.
 * Note: No citation fields - this is user data, not regulatory data.
 * Documents are auto-deleted after 24 hours.
 */
export interface Document extends TimestampFields {
  /** Unique document ID (UUID) */
  doc_id: string
  /** Reference to DocumentType */
  doc_type_id: string
  /** Document issuer (from OCR) */
  issuer: string
  /** Issue date (from OCR, YYYY-MM-DD) */
  issue_date: string
  /** Name on document (from OCR) */
  name_on_doc: string
  /** Address on document (from OCR) */
  address_on_doc: string
  /** File path (S3/local, deleted after 24h) */
  file_ref: string
  /** Whether document passed validation */
  verified: boolean
  /** Validation errors if any */
  validation_errors: string[]
  /** When document will be/was deleted (created_at + 24h, ISO 8601) */
  deleted_at: string | null
}

/**
 * Physical location for in-person steps.
 * Example: "Office of the Parking Clerk"
 */
export interface Office extends CitationFields, TimestampFields {
  /** Unique office identifier (e.g., "parking_clerk") */
  office_id: string
  /** Office name */
  name: string
  /** Full street address */
  address: string
  /** Room number */
  room: string | null
  /** Operating hours (e.g., "Mon-Fri, 9:00-4:30") */
  hours: string
  /** Phone number */
  phone: string | null
  /** Email address */
  email: string | null
}

/**
 * Boston parking neighborhood (RPP-specific).
 */
export interface RPPNeighborhood extends CitationFields, TimestampFields {
  /** Unique neighborhood identifier (e.g., "back_bay") */
  nbrhd_id: string
  /** Neighborhood display name */
  name: string
  /** Next auto-renewal audit date (YYYY-MM-DD) */
  auto_renew_cycle: string | null
  /** Street names with RPP signage */
  posted_streets: string[]
  /** Special rules or notes */
  notes: string | null
}

/**
 * Official web resource (page, PDF, portal).
 * Note: No citation fields - this IS a source, not derived from one.
 */
export interface WebResource extends TimestampFields {
  /** Unique resource identifier (e.g., "howto") */
  res_id: string
  /** Page title */
  title: string
  /** Full URL (must be unique) */
  url: string
  /** Resource type */
  type: WebResourceType
  /** Owning office/department (e.g., "Parking Clerk", "BTD") */
  owner: string
  /** Last successful fetch date (YYYY-MM-DD) */
  last_seen: string
  /** SHA256 hash of content for change detection */
  hash: string
}

/**
 * User (optional, for tracking).
 * Note: Minimal PII - only for Phase 2+.
 */
export interface Person {
  /** Unique person ID (UUID) */
  person_id: string
  /** Hashed email address */
  email: string
  /** When user record was created (ISO 8601) */
  created_at: string
}

/**
 * User's process session (Phase 2+).
 */
export interface Application extends TimestampFields {
  /** Unique application ID (UUID) */
  app_id: string
  /** Process ID (e.g., "boston_rpp") */
  process_id: string
  /** Application category */
  category: ApplicationCategory
  /** When application was submitted (ISO 8601) */
  submitted_on: string | null
  /** Current application status */
  status: ApplicationStatus
  /** Reason for denial if status is DENIED */
  reason_if_denied: string | null
}
