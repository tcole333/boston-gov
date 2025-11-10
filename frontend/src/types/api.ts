/**
 * TypeScript types for API client and backend responses.
 *
 * These types mirror the Pydantic schemas from backend/src/schemas/agent.py
 * and provide frontend-specific types for API communication.
 *
 * For graph entity types, import from './graph'
 * For Facts Registry types, import from './facts'
 */

/**
 * Citation for a fact or regulatory claim.
 *
 * Citations ensure all regulatory claims are traceable to official sources.
 * They can reference either Facts Registry entries (with fact_id) or graph nodes.
 *
 * Backend schema: backend/src/schemas/agent.py:Citation
 */
export interface Citation {
  /** Unique fact identifier from Facts Registry (optional for graph citations) */
  fact_id: string | null
  /** URL to the official source document */
  url: string
  /** The cited text or claim being referenced */
  text: string
  /** Section/page reference within the source (optional) */
  source_section: string | null
}

/**
 * Chat message request.
 */
export interface ChatRequest {
  /** User's chat message */
  message: string
  /** Optional session ID for conversation continuity */
  session_id?: string | null
}

/**
 * Response from a conversation agent.
 *
 * This schema ensures that conversation agents return properly formatted responses
 * with inline citations and structured citation metadata.
 *
 * Backend schema: backend/src/schemas/agent.py:ConversationResponse
 */
export interface ConversationResponse {
  /** Natural language response with inline citation links */
  answer: string
  /** List of citations for all sources referenced in the answer */
  citations: Citation[]
  /** List of tool names called during response generation (for debugging) */
  tool_calls_made: string[]
}

/**
 * DAG node for frontend visualization.
 * This is a frontend-specific type for rendering process graphs.
 */
export interface DagNode {
  id: string
  label: string
  order: number
  data: Record<string, unknown>
}

/**
 * DAG edge for frontend visualization.
 * This is a frontend-specific type for rendering process graphs.
 */
export interface DagEdge {
  source: string
  target: string
  type: string
}

/**
 * Process DAG for frontend visualization.
 * This is a frontend-specific type for rendering process graphs.
 */
export interface ProcessDag {
  nodes: DagNode[]
  edges: DagEdge[]
}

/**
 * Registry metadata for Facts Registry API responses.
 * This is a frontend-specific type for API communication.
 */
export interface RegistryMetadata {
  registry_name: string
  version: string
  scope: string
  last_updated: string
  fact_count: number
}

/**
 * Document validation response from backend.
 * Used when validating user-uploaded documents against requirements.
 */
export interface DocumentValidationResponse {
  /** Whether the document passed validation */
  valid: boolean
  /** List of validation errors if any */
  errors: string[]
  /** Document ID if validation passed */
  doc_id: string | null
}

/**
 * Document type for upload and validation.
 */
export type DocumentType = 'proof_of_residency' | 'vehicle_registration' | 'license'

/**
 * Document upload status.
 */
export type DocumentUploadStatus = 'uploaded' | 'processing' | 'verified' | 'rejected'

/**
 * Document upload response from backend.
 *
 * Backend endpoint: POST /api/documents/upload
 * Content-Type: multipart/form-data
 */
export interface DocumentUploadResponse {
  /** Unique document identifier */
  document_id: string
  /** Original filename (sanitized) */
  filename: string
  /** Current status of the document */
  status: DocumentUploadStatus
  /** Timestamp when the document was uploaded */
  upload_timestamp: string
  /** Validation result (if processing complete) */
  validation_result?: {
    /** Whether validation passed */
    passed: boolean
    /** Validation message or explanation */
    message: string
    /** Citations for validation rules if available */
    citations?: Citation[]
  }
}

/**
 * API error response (FastAPI standard format).
 */
export interface ApiError {
  detail: string
}

/**
 * Generic API response wrapper.
 * This is a frontend-specific type for handling API responses with errors.
 */
export interface ApiResponse<T> {
  data?: T
  error?: ApiError
}
