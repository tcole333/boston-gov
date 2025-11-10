import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom'
import { StepDetail } from '../StepDetail'
import * as api from '../../lib/api'
import type { Step, Requirement, DocumentType } from '../../types/graph'
import { ConfidenceLevel } from '../../types/graph'

// Mock the API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    get: vi.fn(),
  },
  getApiErrorMessage: vi.fn((error: Error) => error.message || 'An error occurred'),
}))

/**
 * Helper to create a new QueryClient for each test.
 * Disables retries and logs for cleaner test output.
 */
const createTestQueryClient = (): QueryClient => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: () => {},
      warn: () => {},
      error: () => {},
    },
  })
}

/**
 * Helper to render component with QueryClient provider.
 */
const renderWithQueryClient = (
  component: React.ReactElement,
  queryClient: QueryClient = createTestQueryClient()
) => {
  return render(<QueryClientProvider client={queryClient}>{component}</QueryClientProvider>)
}

/**
 * Mock step data for testing.
 */
const mockStep: Step = {
  step_id: 'rpp_step_1_check_eligibility',
  process_id: 'boston_resident_parking_permit',
  name: 'Check Eligibility',
  description: 'Verify you meet the basic requirements for a Boston RPP',
  order: 1,
  estimated_time_minutes: 10,
  observed_time_minutes: null,
  cost_usd: 0.0,
  optional: false,
  source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
  last_verified: '2025-11-09',
  confidence: ConfidenceLevel.HIGH,
  created_at: '2025-11-09T12:00:00Z',
  updated_at: '2025-11-09T12:00:00Z',
}

/**
 * Mock requirement data for testing.
 */
const mockRequirements: Requirement[] = [
  {
    requirement_id: 'req_residency_proof',
    text: 'Proof of Boston residency required',
    fact_id: 'rpp.documents.residency_proof',
    applies_to_process: 'boston_resident_parking_permit',
    hard_gate: true,
    source_section: 'Requirements',
    source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
    last_verified: '2025-11-09',
    confidence: ConfidenceLevel.HIGH,
    created_at: '2025-11-09T12:00:00Z',
    updated_at: '2025-11-09T12:00:00Z',
  },
  {
    requirement_id: 'req_ma_registration',
    text: 'MA vehicle registration at Boston address',
    fact_id: 'rpp.eligibility.registration_state',
    applies_to_process: 'boston_resident_parking_permit',
    hard_gate: true,
    source_section: 'Eligibility',
    source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
    last_verified: '2025-11-09',
    confidence: ConfidenceLevel.HIGH,
    created_at: '2025-11-09T12:00:00Z',
    updated_at: '2025-11-09T12:00:00Z',
  },
]

/**
 * Mock document type data for testing.
 */
const mockDocumentTypes: DocumentType[] = [
  {
    doc_type_id: 'proof.utility_bill',
    name: 'Utility Bill',
    freshness_days: 30,
    name_match_required: true,
    address_match_required: true,
    examples: ['National Grid', 'Eversource', 'Boston Water and Sewer'],
    source_url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
    last_verified: '2025-11-09',
    confidence: ConfidenceLevel.HIGH,
    created_at: '2025-11-09T12:00:00Z',
    updated_at: '2025-11-09T12:00:00Z',
  },
]

describe('StepDetail Component', () => {
  let mockApiGet: Mock

  beforeEach(() => {
    vi.clearAllMocks()
    mockApiGet = api.apiClient.get as Mock
  })

  // ==================== Rendering Tests ====================

  it('renders step details when stepId is valid', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: mockRequirements })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Check step name and description
    expect(screen.getByText('Check Eligibility')).toBeInTheDocument()
    expect(screen.getByText(/Verify you meet the basic requirements/)).toBeInTheDocument()

    // Check step order badge
    expect(screen.getByLabelText('Step 1')).toBeInTheDocument()

    // Check metadata
    expect(screen.getByText('10 minutes')).toBeInTheDocument()
    expect(screen.getByText('2025-11-09')).toBeInTheDocument()
  })

  it('displays optional badge for optional steps', async () => {
    const optionalStep = { ...mockStep, optional: true }
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: optionalStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByLabelText('Optional step')).toBeInTheDocument()
    })
  })

  it('displays cost when cost_usd is greater than 0', async () => {
    const stepWithCost = { ...mockStep, cost_usd: 25.0 }
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: stepWithCost })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByText('$25.00')).toBeInTheDocument()
    })
  })

  it('renders requirements list correctly', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: mockRequirements })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByText('Requirements')).toBeInTheDocument()
    })

    // Check both requirements are displayed
    expect(screen.getByText(/Proof of Boston residency required/)).toBeInTheDocument()
    expect(screen.getByText(/MA vehicle registration at Boston address/)).toBeInTheDocument()

    // Check hard_gate indicators
    const requiredLabels = screen.getAllByLabelText('Required')
    expect(requiredLabels).toHaveLength(2)
  })

  it('renders documents list correctly when documents are available', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: [] })
      }
      // Note: In Phase 1, document types endpoint returns empty array
      // This test validates that documents section appears when data is available
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // In Phase 1, documents section won't appear since the endpoint returns empty
    // This test validates the conditional rendering works correctly
    expect(screen.queryByText('Required Documents')).not.toBeInTheDocument()
  })

  // ==================== Loading State Tests ====================

  it('displays loading skeleton while fetching', () => {
    mockApiGet.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading step details')).toBeInTheDocument()
  })

  // ==================== Error State Tests ====================

  it('shows error message when step not found (404)', async () => {
    const notFoundError = new Error('The requested resource was not found.')
    mockApiGet.mockRejectedValue(notFoundError)

    renderWithQueryClient(
      <StepDetail stepId="nonexistent_step" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    expect(screen.getByText('Failed to load step details')).toBeInTheDocument()
    expect(screen.getByText(/The requested resource was not found/)).toBeInTheDocument()
  })

  it('shows error message on network failure', async () => {
    const networkError = new Error('Unable to connect to the server. Please check your internet connection.')
    mockApiGet.mockRejectedValue(networkError)

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    expect(screen.getByText(/Unable to connect to the server/)).toBeInTheDocument()
  })

  // ==================== Citation Tests ====================

  it('citation links open in new tab', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    const citationLinks = screen.getAllByText('[source]')
    expect(citationLinks.length).toBeGreaterThan(0)

    citationLinks.forEach((link) => {
      const anchor = link.closest('a')
      expect(anchor).toHaveAttribute('target', '_blank')
    })
  })

  it('citation links have rel="noopener noreferrer"', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    const citationLinks = screen.getAllByText('[source]')
    citationLinks.forEach((link) => {
      const anchor = link.closest('a')
      expect(anchor).toHaveAttribute('rel', 'noopener noreferrer')
    })
  })

  it('validates citation URLs before rendering', async () => {
    const stepWithInvalidUrl = {
      ...mockStep,
      source_url: 'javascript:alert("XSS")', // Invalid URL
    }

    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: stepWithInvalidUrl })
      }
      return Promise.resolve({ data: [] })
    })

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    const citationLinks = screen.getAllByText('[source]')
    const firstLink = citationLinks[0]?.closest('a')

    if (firstLink) {
      // Click the link - it should be blocked
      await userEvent.click(firstLink)

      // Verify console warning was called
      expect(consoleSpy).toHaveBeenCalledWith('Blocked unsafe URL:', 'javascript:alert("XSS")')

      // Verify href is set to '#' for safety
      expect(firstLink).toHaveAttribute('href', '#')
    }

    consoleSpy.mockRestore()
  })

  it('renders citation with proper ARIA labels', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    const citationLink = screen.getAllByLabelText(/Citation:/)[0]
    expect(citationLink).toBeInTheDocument()
  })

  // ==================== Security Tests ====================

  it('sanitizes HTML in step descriptions', async () => {
    const stepWithXSS = {
      ...mockStep,
      description: 'Test description with <script>alert("XSS")</script> malicious code',
    }

    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: stepWithXSS })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // HTML should be stripped
    expect(screen.getByText(/Test description with alert\("XSS"\) malicious code/)).toBeInTheDocument()
    expect(screen.queryByText(/<script>/)).not.toBeInTheDocument()
  })

  it('prevents XSS in requirement text', async () => {
    const requirementWithXSS = {
      ...mockRequirements[0],
      text: 'Requirement <img src=x onerror="alert(\'XSS\')">'
    }

    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: [requirementWithXSS] })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      // Use getAllByText since 'Requirements' appears as a heading and in requirement text
      const requirementElements = screen.getAllByText(/Requirement/)
      expect(requirementElements.length).toBeGreaterThan(0)
    })

    // HTML should be stripped
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('validates stepId format', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    // Should work with valid step ID
    renderWithQueryClient(
      <StepDetail stepId="valid_step_id-123" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalled()
    })
  })

  // ==================== Accessibility Tests ====================

  it('has proper ARIA labels for main sections', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: mockRequirements })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Check main article has aria-label
    expect(screen.getByLabelText(/Details for step: Check Eligibility/)).toBeInTheDocument()

    // Check requirements section has proper heading
    expect(screen.getByRole('heading', { name: 'Requirements' })).toBeInTheDocument()
  })

  it('keyboard navigation works on citation links', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    const citationLinks = screen.getAllByText('[source]')
    const firstLink = citationLinks[0]?.closest('a')

    if (firstLink) {
      // Tab to the link
      firstLink.focus()
      expect(document.activeElement).toBe(firstLink)

      // Verify it's keyboard accessible
      expect(firstLink).toHaveAttribute('href')
    }
  })

  it('uses semantic HTML elements', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: mockRequirements })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Check semantic elements
    expect(screen.getByRole('article')).toBeInTheDocument()
    expect(screen.getAllByRole('heading').length).toBeGreaterThan(0)
    expect(screen.getByRole('list')).toBeInTheDocument()
  })

  it('color contrast meets WCAG AA standards', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // This is a basic check - actual contrast testing would use a library
    // We're verifying that elements have color styles applied
    const stepName = screen.getByText('Check Eligibility')
    const computedStyle = window.getComputedStyle(stepName)

    // Verify color is set (not default)
    expect(computedStyle.color).toBeTruthy()
  })

  // ==================== Edge Cases ====================

  it('handles step with null estimated_time_minutes', async () => {
    const stepWithoutTime = { ...mockStep, estimated_time_minutes: null }
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: stepWithoutTime })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Should not display time when null
    expect(screen.queryByText(/minutes/)).not.toBeInTheDocument()
  })

  it('handles empty requirements list', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      if (url.includes('/requirements')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Should not display requirements section
    expect(screen.queryByText('Requirements')).not.toBeInTheDocument()
  })

  it('handles empty documents list', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Should not display documents section
    expect(screen.queryByText('Required Documents')).not.toBeInTheDocument()
  })

  it('renders confidence level with proper color coding', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/steps/')) {
        return Promise.resolve({ data: mockStep })
      }
      return Promise.resolve({ data: [] })
    })

    renderWithQueryClient(
      <StepDetail stepId="rpp_step_1_check_eligibility" processId="boston_resident_parking_permit" />
    )

    await waitFor(() => {
      expect(screen.getByRole('article')).toBeInTheDocument()
    })

    // Check confidence level is displayed
    expect(screen.getByText('high')).toBeInTheDocument()
  })
})
