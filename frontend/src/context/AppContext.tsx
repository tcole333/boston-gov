/**
 * Global application state management using React Context.
 *
 * This context provides state management for:
 * - Chat message history
 * - Loading and error states
 * - Session ID management
 * - Process/step navigation
 * - Optional persistence to sessionStorage
 *
 * Usage:
 * ```tsx
 * // Wrap your app with the provider
 * <AppProvider>
 *   <YourApp />
 * </AppProvider>
 *
 * // Use the hook in any component
 * const { messages, addMessage, selectedStepId, setSelectedStep } = useAppContext()
 * ```
 */

import { createContext, useContext, useState, useCallback, useEffect, ReactNode, useMemo } from 'react'
import type { AppState, AppProviderOptions, Message } from '../types/state'

/**
 * Default storage key for persisted state.
 */
const DEFAULT_STORAGE_KEY = 'boston-gov-app-state'

/**
 * Persisted state shape for sessionStorage.
 * Only includes state that should be persisted across page reloads.
 */
interface PersistedState {
  messages: Message[]
  selectedStepId: string | null
  selectedProcessId: string | null
  sessionId: string | null
}

/**
 * Generates a unique ID for a message.
 * Uses timestamp + random string for uniqueness.
 */
const generateMessageId = (): string => {
  return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

/**
 * Loads persisted state from sessionStorage.
 * Returns null if storage is disabled, key doesn't exist, or parsing fails.
 */
const loadPersistedState = (storageKey: string): PersistedState | null => {
  try {
    const stored = sessionStorage.getItem(storageKey)
    if (!stored) return null

    const parsed = JSON.parse(stored) as PersistedState

    // Convert timestamp strings back to Date objects
    if (parsed.messages) {
      parsed.messages = parsed.messages.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      }))
    }

    return parsed
  } catch (error) {
    console.warn('Failed to load persisted state:', error)
    return null
  }
}

/**
 * Saves state to sessionStorage.
 * Silently fails if storage is unavailable or quota exceeded.
 */
const savePersistedState = (storageKey: string, state: PersistedState): void => {
  try {
    sessionStorage.setItem(storageKey, JSON.stringify(state))
  } catch (error) {
    // Silently fail if storage quota exceeded or unavailable
    if (import.meta.env.DEV) {
      console.warn('Failed to save state to sessionStorage:', error)
    }
  }
}

/**
 * Context value type (AppState or undefined if not in provider).
 */
type AppContextValue = AppState | undefined

/**
 * React Context for application state.
 */
const AppContext = createContext<AppContextValue>(undefined)

/**
 * Props for AppProvider component.
 */
interface AppProviderProps {
  children: ReactNode
  options?: AppProviderOptions
}

/**
 * AppProvider - provides global application state to the component tree.
 *
 * @param children - Child components
 * @param options - Configuration options for persistence
 */
export const AppProvider = ({ children, options = {} }: AppProviderProps): JSX.Element => {
  const { enablePersistence = false, storageKey = DEFAULT_STORAGE_KEY } = options

  // Load persisted state on mount (if enabled)
  const initialState = useMemo(() => {
    if (enablePersistence) {
      return loadPersistedState(storageKey)
    }
    return null
  }, [enablePersistence, storageKey])

  // ========== State ==========

  const [messages, setMessages] = useState<Message[]>(initialState?.messages ?? [])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setErrorState] = useState<string | null>(null)
  const [sessionId, setSessionIdState] = useState<string | null>(initialState?.sessionId ?? null)
  const [selectedStepId, setSelectedStepId] = useState<string | null>(
    initialState?.selectedStepId ?? null
  )
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(
    initialState?.selectedProcessId ?? null
  )

  // ========== Actions ==========

  /**
   * Adds a new message to the chat history.
   * Automatically generates ID and timestamp.
   */
  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>): void => {
    const newMessage: Message = {
      ...message,
      id: generateMessageId(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, newMessage])
  }, [])

  /**
   * Clears all messages from the chat history.
   */
  const clearMessages = useCallback((): void => {
    setMessages([])
  }, [])

  /**
   * Sets the loading state for the chat.
   */
  const setLoading = useCallback((loading: boolean): void => {
    setIsLoading(loading)
  }, [])

  /**
   * Sets or clears the error state.
   */
  const setError = useCallback((err: string | null): void => {
    setErrorState(err)
  }, [])

  /**
   * Sets or clears the session ID.
   */
  const setSessionId = useCallback((id: string | null): void => {
    setSessionIdState(id)
  }, [])

  /**
   * Sets the currently selected step for detail view.
   */
  const setSelectedStep = useCallback(
    (stepId: string | null, processId: string | null = null): void => {
      setSelectedStepId(stepId)
      if (processId !== null) {
        setSelectedProcessId(processId)
      }
    },
    []
  )

  // ========== Persistence ==========

  /**
   * Persist state to sessionStorage whenever relevant state changes.
   */
  useEffect(() => {
    if (!enablePersistence) return

    const stateToSave: PersistedState = {
      messages,
      selectedStepId,
      selectedProcessId,
      sessionId,
    }

    savePersistedState(storageKey, stateToSave)
  }, [enablePersistence, storageKey, messages, selectedStepId, selectedProcessId, sessionId])

  // ========== Context Value ==========

  /**
   * Memoize context value to prevent unnecessary re-renders.
   * Only recreates when state or callbacks change.
   */
  const value: AppState = useMemo(
    () => ({
      // State
      messages,
      isLoading,
      error,
      sessionId,
      selectedStepId,
      selectedProcessId,
      // Actions
      addMessage,
      clearMessages,
      setLoading,
      setError,
      setSessionId,
      setSelectedStep,
    }),
    [
      messages,
      isLoading,
      error,
      sessionId,
      selectedStepId,
      selectedProcessId,
      addMessage,
      clearMessages,
      setLoading,
      setError,
      setSessionId,
      setSelectedStep,
    ]
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

/**
 * Custom hook to access application state.
 * Must be used within an AppProvider.
 *
 * @throws Error if used outside of AppProvider
 * @returns Application state and actions
 *
 * @example
 * ```tsx
 * const { messages, addMessage, selectedStepId, setSelectedStep } = useAppContext()
 * ```
 */
export const useAppContext = (): AppState => {
  const context = useContext(AppContext)

  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider')
  }

  return context
}
