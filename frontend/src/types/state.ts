/**
 * TypeScript types for application state management.
 *
 * These types define the shape of the global application state
 * managed by the AppContext provider.
 */

import type { Citation } from './api'

/**
 * Message in the chat interface.
 * Represents a single message from either the user or the agent.
 */
export interface Message {
  /** Unique identifier for the message */
  id: string
  /** Role of the message sender */
  role: 'user' | 'agent'
  /** Message content (may include citation markers like [1], [2] for agent messages) */
  content: string
  /** Citations for agent messages (references to regulatory sources) */
  citations?: Citation[]
  /** Timestamp when the message was created */
  timestamp: Date
}

/**
 * Application state shape.
 * This interface defines all state managed by the AppContext provider.
 */
export interface AppState {
  // ========== Chat State ==========

  /** Array of chat messages in chronological order */
  messages: Message[]

  /** Whether the chat is waiting for an agent response */
  isLoading: boolean

  /** Error message if the last API call failed, null otherwise */
  error: string | null

  /** Session ID for conversation continuity (optional, for future use) */
  sessionId: string | null

  // ========== Navigation State ==========

  /** Currently selected step ID (for StepDetail display), null if no step selected */
  selectedStepId: string | null

  /** Currently selected process ID (for context), null if no process selected */
  selectedProcessId: string | null

  // ========== Actions ==========

  /**
   * Adds a new message to the chat history.
   * Automatically generates ID and timestamp.
   *
   * @param message - Message data without id and timestamp
   */
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void

  /**
   * Clears all messages from the chat history.
   * Useful for starting a new conversation or resetting state.
   */
  clearMessages: () => void

  /**
   * Sets the loading state for the chat.
   * Should be true when waiting for agent response, false otherwise.
   *
   * @param loading - Whether the chat is loading
   */
  setLoading: (loading: boolean) => void

  /**
   * Sets or clears the error state.
   *
   * @param error - Error message string or null to clear error
   */
  setError: (error: string | null) => void

  /**
   * Sets or clears the session ID.
   *
   * @param id - Session ID string or null to clear session
   */
  setSessionId: (id: string | null) => void

  /**
   * Sets the currently selected step for detail view.
   * Passing null will deselect the current step.
   *
   * @param stepId - Step ID to select, or null to deselect
   * @param processId - Optional process ID for context
   */
  setSelectedStep: (stepId: string | null, processId?: string | null) => void
}

/**
 * Options for configuring the AppProvider.
 */
export interface AppProviderOptions {
  /**
   * Whether to persist state to sessionStorage.
   * If true, messages and selected step will be saved and restored on page reload.
   * Default: false (disabled for MVP)
   */
  enablePersistence?: boolean

  /**
   * Storage key for persisted state.
   * Default: 'boston-gov-app-state'
   */
  storageKey?: string
}
