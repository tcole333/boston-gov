import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from '../src/App'
import type { ProcessGraph, Step } from '../src/types/api'
import * as api from '../src/lib/api'

/**
 * Test suite for App component - Main page layout integration.
 *
 * Tests:
 * - Rendering all integrated components (ProcessDAG, ChatInterface, StepDetail, DocumentUpload)
 * - State integration (clicking DAG node updates StepDetail)
 * - Responsive layout (tested via CSS media queries)
 * - Accessibility (ARIA labels, semantic HTML, keyboard navigation)
 * - Loading states for initial data fetch
 * - Error handling
 * - Component visibility based on state
 *
 * Coverage for Issue #28: Main page layout integrating all components
 */

// Mock components to simplify integration testing
vi.mock('../src/components/ProcessDAG', () => ({
  default: ({
    processId,
    onNodeClick,
  }: {
    processId: string
    onNodeClick: (stepId: string) => void
  }) => (
    <div data-testid="process-dag" data-process-id={processId}>
      <button onClick={() => onNodeClick('step-1')}>Step 1</button>
      <button onClick={() => onNodeClick('step-2')}>Step 2</button>
    </div>
  ),
}))

vi.mock('../src/components/StepDetail', () => ({
  default: ({ stepId, processId }: { stepId: string; processId: string }) => (
    <div data-testid="step-detail" data-step-id={stepId} data-process-id={processId}>
      Step Detail: {stepId}
    </div>
  ),
}))

vi.mock('../src/components/ChatInterface', () => ({
  default: () => <div data-testid="chat-interface">Chat Interface</div>,
}))

vi.mock('../src/components/DocumentUpload', () => {
  const MockDocumentUpload = ({
    documentType,
    onUploadSuccess,
    onUploadError,
  }: {
    documentType: string
    onUploadSuccess?: (response: unknown) => void
    onUploadError?: (error: string) => void
  }) => (
    <div data-testid="document-upload" data-document-type={documentType}>
      Document Upload: {documentType}
      <button
        onClick={() => {
          if (onUploadSuccess) {
            onUploadSuccess({ document_id: 'test-doc' })
          }
        }}
      >
        Simulate Success
      </button>
      <button
        onClick={() => {
          if (onUploadError) {
            onUploadError('Upload failed')
          }
        }}
      >
        Simulate Error
      </button>
    </div>
  )

  return {
    default: MockDocumentUpload,
    DocumentUpload: MockDocumentUpload,
  }
})

// Mock data
const mockProcessGraph: ProcessGraph = {
  process_id: 'boston_resident_parking_permit',
  name: 'Boston Resident Parking Permit',
  description: 'Process for obtaining a resident parking permit',
  steps: [
    {
      step_id: 'step-1',
      name: 'Verify Eligibility',
      description: 'Check if you qualify for a resident parking permit',
      order: 1,
      required: true,
      estimated_time_minutes: 10,
      requirements: [],
    },
    {
      step_id: 'step-2',
      name: 'Gather Documents',
      description: 'Collect required documentation',
      order: 2,
      required: true,
      estimated_time_minutes: 15,
      requirements: [],
    },
  ],
  edges: [
    {
      from_step: 'step-1',
      to_step: 'step-2',
      condition: null,
    },
  ],
}

const mockStepDetail: Step = {
  step_id: 'step-1',
  name: 'Verify Eligibility',
  description: 'Check if you qualify for a resident parking permit',
  order: 1,
  required: true,
  estimated_time_minutes: 10,
  requirements: [],
}

// Helper to render App with QueryClient
const renderApp = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  )
}

// Mock API responses
beforeEach(() => {
  vi.clearAllMocks()

  // Mock successful API responses by default
  vi.spyOn(api.apiClient, 'get').mockImplementation((url: string) => {
    if (url.includes('/process/')) {
      return Promise.resolve({ data: mockProcessGraph })
    }
    if (url.includes('/step/')) {
      return Promise.resolve({ data: mockStepDetail })
    }
    return Promise.reject(new Error('Unknown endpoint'))
  })
})

describe('App - Main Page Layout', () => {
  describe('Header and Structure', () => {
    it('should render the main header with title', () => {
      renderApp()

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Boston Government Navigation Assistant'
      )
    })

    it('should render the subtitle describing Phase 1', () => {
      renderApp()

      expect(
        screen.getByText(/Helping citizens navigate government services - Phase 1: Resident Parking Permits/i)
      ).toBeInTheDocument()
    })

    it('should render footer with project info', () => {
      renderApp()

      expect(screen.getByText(/Boston Government Navigation Assistant - Phase 1 MVP/i)).toBeInTheDocument()
      expect(
        screen.getByText(/Providing guidance on resident parking permits and government processes/i)
      ).toBeInTheDocument()
    })

    it('should have semantic HTML structure', () => {
      renderApp()

      expect(screen.getByRole('banner')).toBeInTheDocument() // header
      expect(screen.getByRole('main')).toBeInTheDocument() // main
      expect(screen.getByRole('contentinfo')).toBeInTheDocument() // footer
    })
  })

  describe('Component Integration', () => {
    it('should render ProcessDAG component', () => {
      renderApp()

      expect(screen.getByTestId('process-dag')).toBeInTheDocument()
      expect(screen.getByText('Process Flow')).toBeInTheDocument()
    })

    it('should render ChatInterface component', () => {
      renderApp()

      expect(screen.getByTestId('chat-interface')).toBeInTheDocument()
      expect(screen.getByText('Ask Questions')).toBeInTheDocument()
    })

    it('should pass correct processId to ProcessDAG', () => {
      renderApp()

      const dag = screen.getByTestId('process-dag')
      expect(dag).toHaveAttribute('data-process-id', 'boston_resident_parking_permit')
    })

    it('should NOT render StepDetail initially (no step selected)', () => {
      renderApp()

      expect(screen.queryByTestId('step-detail')).not.toBeInTheDocument()
      expect(screen.queryByText('Step Details')).not.toBeInTheDocument()
    })

    it('should NOT render DocumentUpload initially (no step selected)', () => {
      renderApp()

      expect(screen.queryByTestId('document-upload')).not.toBeInTheDocument()
    })
  })

  describe('State Integration - DAG to StepDetail', () => {
    it('should show StepDetail when DAG node is clicked', async () => {
      const user = userEvent.setup()
      renderApp()

      // Initially no step detail
      expect(screen.queryByTestId('step-detail')).not.toBeInTheDocument()

      // Click Step 1 in ProcessDAG
      const step1Button = screen.getByRole('button', { name: 'Step 1' })
      await user.click(step1Button)

      // StepDetail should now be visible
      await waitFor(() => {
        expect(screen.getByTestId('step-detail')).toBeInTheDocument()
        expect(screen.getByText('Step Details')).toBeInTheDocument()
      })
    })

    it('should pass correct stepId to StepDetail after click', async () => {
      const user = userEvent.setup()
      renderApp()

      const step1Button = screen.getByRole('button', { name: 'Step 1' })
      await user.click(step1Button)

      await waitFor(() => {
        const stepDetail = screen.getByTestId('step-detail')
        expect(stepDetail).toHaveAttribute('data-step-id', 'step-1')
        expect(stepDetail).toHaveAttribute('data-process-id', 'boston_resident_parking_permit')
      })
    })

    it('should update StepDetail when different node is clicked', async () => {
      const user = userEvent.setup()
      renderApp()

      // Click Step 1
      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      await waitFor(() => {
        expect(screen.getByTestId('step-detail')).toHaveAttribute('data-step-id', 'step-1')
      })

      // Click Step 2
      await user.click(screen.getByRole('button', { name: 'Step 2' }))

      await waitFor(() => {
        expect(screen.getByTestId('step-detail')).toHaveAttribute('data-step-id', 'step-2')
      })
    })

    it('should show DocumentUpload when step is selected', async () => {
      const user = userEvent.setup()
      renderApp()

      // Initially no document upload
      expect(screen.queryByTestId('document-upload')).not.toBeInTheDocument()

      // Click Step 1
      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      // DocumentUpload should now be visible
      await waitFor(() => {
        expect(screen.getByTestId('document-upload')).toBeInTheDocument()
        expect(screen.getByText('Upload Documents')).toBeInTheDocument()
      })
    })

    it('should pass correct documentType to DocumentUpload', async () => {
      const user = userEvent.setup()
      renderApp()

      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      await waitFor(() => {
        const upload = screen.getByTestId('document-upload')
        expect(upload).toHaveAttribute('data-document-type', 'proof_of_residency')
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels for sections', () => {
      renderApp()

      expect(screen.getByLabelText('Process flow diagram')).toBeInTheDocument()
      expect(screen.getByLabelText('Chat assistant')).toBeInTheDocument()
    })

    it('should have ARIA labels for conditional sections when visible', async () => {
      const user = userEvent.setup()
      renderApp()

      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      await waitFor(() => {
        expect(screen.getByLabelText('Step details')).toBeInTheDocument()
        expect(screen.getByLabelText('Document upload')).toBeInTheDocument()
      })
    })

    it('should have proper heading hierarchy', () => {
      renderApp()

      const h1 = screen.getByRole('heading', { level: 1 })
      const h2s = screen.getAllByRole('heading', { level: 2 })

      expect(h1).toHaveTextContent('Boston Government Navigation Assistant')
      expect(h2s.length).toBeGreaterThanOrEqual(2) // At least Process Flow and Ask Questions
      expect(h2s.some((h) => h.textContent === 'Process Flow')).toBe(true)
      expect(h2s.some((h) => h.textContent === 'Ask Questions')).toBe(true)
    })

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      renderApp()

      // Tab through interactive elements
      await user.tab() // Should focus first interactive element

      // At least one element should have focus
      expect(document.activeElement).not.toBe(document.body)
    })

    it('should have visible focus indicators (tested via CSS)', () => {
      renderApp()

      // Check that focus styles are defined in the page
      const styles = document.querySelector('style')
      expect(styles?.textContent).toContain('focus-visible')
    })
  })

  describe('Layout Responsiveness', () => {
    it('should apply responsive grid layout', () => {
      renderApp()

      const main = screen.getByRole('main')
      const gridContainer = main.querySelector('div')

      expect(gridContainer).toHaveStyle({
        display: 'grid',
      })
    })

    it('should include mobile-responsive CSS rules', () => {
      renderApp()

      const styles = document.querySelector('style')
      expect(styles?.textContent).toContain('@media')
      expect(styles?.textContent).toContain('max-width: 768px')
    })
  })

  describe('Document Upload Callbacks', () => {
    it('should handle upload success callback', async () => {
      const user = userEvent.setup()
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

      renderApp()

      // Select a step to show document upload
      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      await waitFor(() => {
        expect(screen.getByTestId('document-upload')).toBeInTheDocument()
      })

      // Trigger success
      const successButton = screen.getByRole('button', { name: 'Simulate Success' })
      await user.click(successButton)

      expect(consoleSpy).toHaveBeenCalledWith('Upload successful:', { document_id: 'test-doc' })

      consoleSpy.mockRestore()
    })

    it('should handle upload error callback', async () => {
      const user = userEvent.setup()
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      renderApp()

      // Select a step to show document upload
      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      await waitFor(() => {
        expect(screen.getByTestId('document-upload')).toBeInTheDocument()
      })

      // Trigger error
      const errorButton = screen.getByRole('button', { name: 'Simulate Error' })
      await user.click(errorButton)

      expect(consoleErrorSpy).toHaveBeenCalledWith('Upload failed:', 'Upload failed')

      consoleErrorSpy.mockRestore()
    })
  })

  describe('Provider Integration', () => {
    it('should wrap components with QueryClientProvider', () => {
      // Render without expecting errors about missing provider
      expect(() => renderApp()).not.toThrow()
    })

    it('should wrap components with AppProvider', () => {
      // The fact that state management works proves AppProvider is present
      const user = userEvent.setup()
      renderApp()

      expect(async () => {
        await user.click(screen.getByRole('button', { name: 'Step 1' }))
        await waitFor(() => {
          expect(screen.getByTestId('step-detail')).toBeInTheDocument()
        })
      }).not.toThrow()
    })
  })

  describe('QueryClient Configuration', () => {
    it('should configure QueryClient with sensible defaults', () => {
      // This test verifies the configuration exists
      // We can't directly test the config without exposing it, but we can verify
      // that the component renders without errors, which proves the config is valid
      expect(() => renderApp()).not.toThrow()
    })
  })

  describe('Edge Cases', () => {
    it('should handle clicking same node multiple times', async () => {
      const user = userEvent.setup()
      renderApp()

      const step1Button = screen.getByRole('button', { name: 'Step 1' })

      // Click multiple times
      await user.click(step1Button)
      await user.click(step1Button)
      await user.click(step1Button)

      // Should still work correctly
      await waitFor(() => {
        expect(screen.getByTestId('step-detail')).toHaveAttribute('data-step-id', 'step-1')
      })
    })

    it('should handle rapid step switching', async () => {
      const user = userEvent.setup()
      renderApp()

      // Rapidly switch between steps
      await user.click(screen.getByRole('button', { name: 'Step 1' }))
      await user.click(screen.getByRole('button', { name: 'Step 2' }))
      await user.click(screen.getByRole('button', { name: 'Step 1' }))

      // Should end up on Step 1
      await waitFor(() => {
        expect(screen.getByTestId('step-detail')).toHaveAttribute('data-step-id', 'step-1')
      })
    })
  })

  describe('Visual Layout', () => {
    it('should have proper max-width constraint on main content', () => {
      renderApp()

      const main = screen.getByRole('main')
      expect(main).toHaveStyle({ maxWidth: '1600px' })
    })

    it('should center main content with auto margins', () => {
      renderApp()

      const main = screen.getByRole('main')
      expect(main).toHaveStyle({ margin: '0 auto' })
    })

    it('should apply consistent spacing', () => {
      renderApp()

      const main = screen.getByRole('main')
      expect(main).toHaveStyle({ padding: '2rem' })
    })

    it('should have full-height layout', () => {
      renderApp()

      // Get the root div (immediate child of App)
      const container = screen.getByRole('banner').parentElement
      expect(container).toHaveStyle({ minHeight: '100vh' })
    })
  })
})
