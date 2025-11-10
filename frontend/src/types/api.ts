/**
 * TypeScript types for API client and backend responses.
 *
 * These types mirror the Pydantic schemas from the backend.
 */

/**
 * Citation for a fact or regulatory claim.
 */
export interface Citation {
  fact_id: string
  url: string
  text: string
  source_section?: string
}

/**
 * Chat message request.
 */
export interface ChatRequest {
  message: string
  session_id?: string | null
}

/**
 * Chat conversation response with citations.
 */
export interface ConversationResponse {
  answer: string
  citations: Citation[]
  tool_calls_made: string[]
}

/**
 * Fact from the Facts Registry.
 */
export interface Fact {
  id: string
  content: string
  source_url: string
  source_section?: string | null
  last_verified: string
  confidence: 'high' | 'medium' | 'low'
  tags?: string[]
  metadata?: Record<string, unknown>
}

/**
 * Process details.
 */
export interface Process {
  id: string
  name: string
  description: string
  jurisdiction: string
  category: string
  created_at: string
  updated_at: string
}

/**
 * Step in a process.
 */
export interface Step {
  id: string
  name: string
  description: string
  order: number
  estimated_time?: string | null
  required: boolean
  notes?: string | null
}

/**
 * Requirement for a process or step.
 */
export interface Requirement {
  id: string
  name: string
  description: string
  required: boolean
  type: string
  notes?: string | null
}

/**
 * DAG node for visualization.
 */
export interface DagNode {
  id: string
  label: string
  order: number
  data: Record<string, unknown>
}

/**
 * DAG edge for visualization.
 */
export interface DagEdge {
  source: string
  target: string
  type: string
}

/**
 * Process DAG for visualization.
 */
export interface ProcessDag {
  nodes: DagNode[]
  edges: DagEdge[]
}

/**
 * Registry metadata.
 */
export interface RegistryMetadata {
  registry_name: string
  version: string
  scope: string
  last_updated: string
  fact_count: number
}

/**
 * API error response.
 */
export interface ApiError {
  detail: string
}

/**
 * Generic API response wrapper for errors.
 */
export interface ApiResponse<T> {
  data?: T
  error?: ApiError
}
