/**
 * Tests for AppContext state management.
 *
 * Test categories:
 * - Initialization
 * - Message operations
 * - Loading/Error state
 * - Session management
 * - Step navigation
 * - Multiple consumers
 * - Persistence
 * - Error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, renderHook, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { AppProvider, useAppContext } from '../AppContext'
import type { Message, AppState } from '../../types/state'
import type { ReactNode } from 'react'

// Test component that uses the context
const TestConsumer = ({ testId = 'test-consumer' }: { testId?: string }): JSX.Element => {
  const {
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
  } = useAppContext()

  return (
    <div>
      <div data-testid={`${testId}-message-count`}>{messages.length}</div>
      <div data-testid={`${testId}-loading`}>{isLoading.toString()}</div>
      <div data-testid={`${testId}-error`}>{error || 'null'}</div>
      <div data-testid={`${testId}-session-id`}>{sessionId || 'null'}</div>
      <div data-testid={`${testId}-selected-step`}>{selectedStepId || 'null'}</div>
      <div data-testid={`${testId}-selected-process`}>{selectedProcessId || 'null'}</div>

      <button
        onClick={() =>
          addMessage({
            role: 'user',
            content: 'Test message',
          })
        }
        data-testid={`${testId}-add-message`}
      >
        Add Message
      </button>
      <button onClick={() => clearMessages()} data-testid={`${testId}-clear-messages`}>
        Clear Messages
      </button>
      <button onClick={() => setLoading(true)} data-testid={`${testId}-set-loading`}>
        Set Loading
      </button>
      <button onClick={() => setError('Test error')} data-testid={`${testId}-set-error`}>
        Set Error
      </button>
      <button onClick={() => setSessionId('test-session')} data-testid={`${testId}-set-session`}>
        Set Session
      </button>
      <button
        onClick={() => setSelectedStep('step-1', 'process-1')}
        data-testid={`${testId}-set-step`}
      >
        Set Step
      </button>

      {messages.map((msg) => (
        <div key={msg.id} data-testid={`message-${msg.id}`}>
          {msg.content}
        </div>
      ))}
    </div>
  )
}

describe('AppContext', () => {
  beforeEach(() => {
    // Clear sessionStorage before each test
    sessionStorage.clear()
    // Reset any mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  describe('Initialization', () => {
    it('provides default state values', () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      )

      expect(screen.getByTestId('test-consumer-message-count')).toHaveTextContent('0')
      expect(screen.getByTestId('test-consumer-loading')).toHaveTextContent('false')
      expect(screen.getByTestId('test-consumer-error')).toHaveTextContent('null')
      expect(screen.getByTestId('test-consumer-session-id')).toHaveTextContent('null')
      expect(screen.getByTestId('test-consumer-selected-step')).toHaveTextContent('null')
      expect(screen.getByTestId('test-consumer-selected-process')).toHaveTextContent('null')
    })

    it('provides all required state and actions', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      // Check state properties
      expect(result.current.messages).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.sessionId).toBeNull()
      expect(result.current.selectedStepId).toBeNull()
      expect(result.current.selectedProcessId).toBeNull()

      // Check actions exist
      expect(typeof result.current.addMessage).toBe('function')
      expect(typeof result.current.clearMessages).toBe('function')
      expect(typeof result.current.setLoading).toBe('function')
      expect(typeof result.current.setError).toBe('function')
      expect(typeof result.current.setSessionId).toBe('function')
      expect(typeof result.current.setSelectedStep).toBe('function')
    })
  })

  describe('Message Operations', () => {
    it('adds a message with generated ID and timestamp', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({
          role: 'user',
          content: 'Hello world',
        })
      })

      expect(result.current.messages).toHaveLength(1)
      expect(result.current.messages[0]).toMatchObject({
        role: 'user',
        content: 'Hello world',
      })
      expect(result.current.messages[0]?.id).toBeTruthy()
      expect(result.current.messages[0]?.timestamp).toBeInstanceOf(Date)
    })

    it('adds multiple messages in order', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'First' })
        result.current.addMessage({ role: 'agent', content: 'Second' })
        result.current.addMessage({ role: 'user', content: 'Third' })
      })

      expect(result.current.messages).toHaveLength(3)
      expect(result.current.messages[0]?.content).toBe('First')
      expect(result.current.messages[1]?.content).toBe('Second')
      expect(result.current.messages[2]?.content).toBe('Third')
    })

    it('adds agent message with citations', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({
          role: 'agent',
          content: 'You need proof of residency [1].',
          citations: [
            {
              fact_id: 'fact-1',
              url: 'https://example.com/source',
              text: 'Proof of residency requirement',
              source_section: 'Section 2.1',
            },
          ],
        })
      })

      expect(result.current.messages).toHaveLength(1)
      expect(result.current.messages[0]?.citations).toHaveLength(1)
      expect(result.current.messages[0]?.citations?.[0]?.url).toBe('https://example.com/source')
    })

    it('clears all messages', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'Message 1' })
        result.current.addMessage({ role: 'user', content: 'Message 2' })
      })

      expect(result.current.messages).toHaveLength(2)

      act(() => {
        result.current.clearMessages()
      })

      expect(result.current.messages).toHaveLength(0)
    })

    it('generates unique message IDs', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'Message 1' })
        result.current.addMessage({ role: 'user', content: 'Message 2' })
        result.current.addMessage({ role: 'user', content: 'Message 3' })
      })

      const ids = result.current.messages.map((m) => m.id)
      const uniqueIds = new Set(ids)

      expect(uniqueIds.size).toBe(3)
    })
  })

  describe('Loading State', () => {
    it('sets loading state to true', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      expect(result.current.isLoading).toBe(false)

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.isLoading).toBe(true)
    })

    it('sets loading state to false', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.isLoading).toBe(true)

      act(() => {
        result.current.setLoading(false)
      })

      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('Error State', () => {
    it('sets error message', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      expect(result.current.error).toBeNull()

      act(() => {
        result.current.setError('Network error')
      })

      expect(result.current.error).toBe('Network error')
    })

    it('clears error message', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setError('Network error')
      })

      expect(result.current.error).toBe('Network error')

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('Session Management', () => {
    it('sets session ID', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      expect(result.current.sessionId).toBeNull()

      act(() => {
        result.current.setSessionId('session-123')
      })

      expect(result.current.sessionId).toBe('session-123')
    })

    it('clears session ID', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setSessionId('session-123')
      })

      expect(result.current.sessionId).toBe('session-123')

      act(() => {
        result.current.setSessionId(null)
      })

      expect(result.current.sessionId).toBeNull()
    })
  })

  describe('Step Navigation', () => {
    it('sets selected step and process', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setSelectedStep('step-1', 'process-1')
      })

      expect(result.current.selectedStepId).toBe('step-1')
      expect(result.current.selectedProcessId).toBe('process-1')
    })

    it('sets selected step without changing process', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setSelectedStep('step-1', 'process-1')
      })

      expect(result.current.selectedStepId).toBe('step-1')
      expect(result.current.selectedProcessId).toBe('process-1')

      act(() => {
        result.current.setSelectedStep('step-2')
      })

      expect(result.current.selectedStepId).toBe('step-2')
      expect(result.current.selectedProcessId).toBe('process-1') // Unchanged
    })

    it('deselects step', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.setSelectedStep('step-1', 'process-1')
      })

      expect(result.current.selectedStepId).toBe('step-1')

      act(() => {
        result.current.setSelectedStep(null)
      })

      expect(result.current.selectedStepId).toBeNull()
    })
  })

  describe('Multiple Consumers', () => {
    it('shares state between multiple consumers', async () => {
      const user = userEvent.setup()

      render(
        <AppProvider>
          <TestConsumer testId="consumer-1" />
          <TestConsumer testId="consumer-2" />
        </AppProvider>
      )

      // Both consumers should see the same initial state
      expect(screen.getByTestId('consumer-1-message-count')).toHaveTextContent('0')
      expect(screen.getByTestId('consumer-2-message-count')).toHaveTextContent('0')

      // Add message from consumer 1
      const addButton1 = screen.getByTestId('consumer-1-add-message')
      await user.click(addButton1)

      // Both consumers should see the updated state
      expect(screen.getByTestId('consumer-1-message-count')).toHaveTextContent('1')
      expect(screen.getByTestId('consumer-2-message-count')).toHaveTextContent('1')
    })

    it('synchronizes loading state across consumers', async () => {
      const user = userEvent.setup()

      render(
        <AppProvider>
          <TestConsumer testId="consumer-1" />
          <TestConsumer testId="consumer-2" />
        </AppProvider>
      )

      expect(screen.getByTestId('consumer-1-loading')).toHaveTextContent('false')
      expect(screen.getByTestId('consumer-2-loading')).toHaveTextContent('false')

      // Set loading from consumer 1
      const loadingButton1 = screen.getByTestId('consumer-1-set-loading')
      await user.click(loadingButton1)

      // Both consumers should see the updated state
      expect(screen.getByTestId('consumer-1-loading')).toHaveTextContent('true')
      expect(screen.getByTestId('consumer-2-loading')).toHaveTextContent('true')
    })

    it('synchronizes step selection across consumers', async () => {
      const user = userEvent.setup()

      render(
        <AppProvider>
          <TestConsumer testId="consumer-1" />
          <TestConsumer testId="consumer-2" />
        </AppProvider>
      )

      expect(screen.getByTestId('consumer-1-selected-step')).toHaveTextContent('null')
      expect(screen.getByTestId('consumer-2-selected-step')).toHaveTextContent('null')

      // Select step from consumer 1
      const stepButton1 = screen.getByTestId('consumer-1-set-step')
      await user.click(stepButton1)

      // Both consumers should see the updated state
      expect(screen.getByTestId('consumer-1-selected-step')).toHaveTextContent('step-1')
      expect(screen.getByTestId('consumer-2-selected-step')).toHaveTextContent('step-1')
      expect(screen.getByTestId('consumer-1-selected-process')).toHaveTextContent('process-1')
      expect(screen.getByTestId('consumer-2-selected-process')).toHaveTextContent('process-1')
    })
  })

  describe('Persistence', () => {
    it('saves state to sessionStorage when enabled', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider options={{ enablePersistence: true }}>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'Test message' })
        result.current.setSelectedStep('step-1', 'process-1')
        result.current.setSessionId('session-123')
      })

      // Wait for persistence effect to run
      await waitFor(() => {
        const stored = sessionStorage.getItem('boston-gov-app-state')
        expect(stored).toBeTruthy()

        const parsed = JSON.parse(stored!)
        expect(parsed.messages).toHaveLength(1)
        expect(parsed.messages[0].content).toBe('Test message')
        expect(parsed.selectedStepId).toBe('step-1')
        expect(parsed.selectedProcessId).toBe('process-1')
        expect(parsed.sessionId).toBe('session-123')
      })
    })

    it('restores state from sessionStorage on mount', () => {
      // Pre-populate sessionStorage
      const persistedState = {
        messages: [
          {
            id: 'msg-1',
            role: 'user' as const,
            content: 'Restored message',
            timestamp: new Date().toISOString(),
          },
        ],
        selectedStepId: 'step-restored',
        selectedProcessId: 'process-restored',
        sessionId: 'session-restored',
      }

      sessionStorage.setItem('boston-gov-app-state', JSON.stringify(persistedState))

      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider options={{ enablePersistence: true }}>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      expect(result.current.messages).toHaveLength(1)
      expect(result.current.messages[0]?.content).toBe('Restored message')
      expect(result.current.messages[0]?.timestamp).toBeInstanceOf(Date)
      expect(result.current.selectedStepId).toBe('step-restored')
      expect(result.current.selectedProcessId).toBe('process-restored')
      expect(result.current.sessionId).toBe('session-restored')
    })

    it('does not persist when disabled', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider options={{ enablePersistence: false }}>{children}</AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'Test message' })
      })

      // Wait a bit to ensure effect would have run if enabled
      await new Promise((resolve) => setTimeout(resolve, 100))

      const stored = sessionStorage.getItem('boston-gov-app-state')
      expect(stored).toBeNull()
    })

    it('uses custom storage key when provided', async () => {
      const customKey = 'custom-app-state'

      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider options={{ enablePersistence: true, storageKey: customKey }}>
          {children}
        </AppProvider>
      )

      const { result } = renderHook(() => useAppContext(), { wrapper })

      act(() => {
        result.current.addMessage({ role: 'user', content: 'Test message' })
      })

      await waitFor(() => {
        const stored = sessionStorage.getItem(customKey)
        expect(stored).toBeTruthy()

        const defaultStored = sessionStorage.getItem('boston-gov-app-state')
        expect(defaultStored).toBeNull()
      })
    })

    it('handles corrupted storage data gracefully', () => {
      // Pre-populate with invalid JSON
      sessionStorage.setItem('boston-gov-app-state', 'invalid-json{')

      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider options={{ enablePersistence: true }}>{children}</AppProvider>
      )

      // Should not throw error
      const { result } = renderHook(() => useAppContext(), { wrapper })

      // Should start with default state
      expect(result.current.messages).toEqual([])
      expect(result.current.selectedStepId).toBeNull()
    })
  })

  describe('Error Handling', () => {
    it('throws error when used outside provider', () => {
      // Suppress console.error for this test
      const originalError = console.error
      console.error = vi.fn()

      expect(() => {
        renderHook(() => useAppContext())
      }).toThrow('useAppContext must be used within an AppProvider')

      console.error = originalError
    })
  })

  describe('Performance', () => {
    it('memoizes action callbacks', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result, rerender } = renderHook(() => useAppContext(), { wrapper })

      const firstAddMessage = result.current.addMessage
      const firstClearMessages = result.current.clearMessages
      const firstSetLoading = result.current.setLoading
      const firstSetError = result.current.setError
      const firstSetSessionId = result.current.setSessionId
      const firstSetSelectedStep = result.current.setSelectedStep

      // Trigger a state change
      act(() => {
        result.current.addMessage({ role: 'user', content: 'Test' })
      })

      rerender()

      // Callbacks should be the same references
      expect(result.current.addMessage).toBe(firstAddMessage)
      expect(result.current.clearMessages).toBe(firstClearMessages)
      expect(result.current.setLoading).toBe(firstSetLoading)
      expect(result.current.setError).toBe(firstSetError)
      expect(result.current.setSessionId).toBe(firstSetSessionId)
      expect(result.current.setSelectedStep).toBe(firstSetSelectedStep)
    })
  })
})
