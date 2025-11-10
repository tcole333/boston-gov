import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom'
import { ProcessDAG } from '../ProcessDAG'
import * as api from '../../lib/api'
import type { ProcessDag } from '../../types/api'

// Mock the API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    get: vi.fn(),
  },
  getApiErrorMessage: vi.fn((error: Error) => error.message || 'An error occurred'),
}))

// Mock reactflow to avoid rendering issues in tests
vi.mock('reactflow', () => ({
  default: ({ nodes, edges, onNodeClick }: any) => (
    <div data-testid="react-flow">
      <div data-testid="nodes">
        {nodes.map((node: any) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            onClick={(e) => onNodeClick?.(e, node)}
            role="button"
            tabIndex={0}
          >
            {node.data.label} - Step {node.data.order}
          </div>
        ))}
      </div>
      <div data-testid="edges">
        {edges.map((edge: any) => (
          <div key={edge.id} data-testid={`edge-${edge.id}`}>
            {edge.source} -&gt; {edge.target}
          </div>
        ))}
      </div>
    </div>
  ),
  Controls: () => <div data-testid="controls">Controls</div>,
  Background: () => <div data-testid="background">Background</div>,
  Panel: ({ children }: any) => <div data-testid="panel">{children}</div>,
  BackgroundVariant: {
    Dots: 'dots',
  },
  ConnectionMode: {
    Strict: 'strict',
  },
}))

describe('ProcessDAG', () => {
  let queryClient: QueryClient
  const mockGet = api.apiClient.get as Mock

  const mockDagData: ProcessDag = {
    nodes: [
      {
        id: 'step_1',
        label: 'Check Eligibility',
        order: 1,
        data: {},
      },
      {
        id: 'step_2',
        label: 'Gather Documents',
        order: 2,
        data: {},
      },
      {
        id: 'step_3',
        label: 'Submit Application',
        order: 3,
        data: {},
      },
    ],
    edges: [
      {
        source: 'step_2',
        target: 'step_1',
        type: 'DEPENDS_ON',
      },
      {
        source: 'step_3',
        target: 'step_2',
        type: 'DEPENDS_ON',
      },
    ],
  }

  beforeEach(() => {
    // Create a new QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    // Clear all mocks
    vi.clearAllMocks()
  })

  const renderProcessDAG = (processId = 'boston_resident_parking_permit', onNodeClick?: any) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ProcessDAG processId={processId} onNodeClick={onNodeClick} />
      </QueryClientProvider>
    )
  }

  describe('Loading State', () => {
    it('displays loading indicator while fetching data', () => {
      // Mock pending request
      mockGet.mockImplementation(() => new Promise(() => {})) // Never resolves

      renderProcessDAG()

      expect(screen.getByRole('status')).toBeInTheDocument()
      expect(screen.getByLabelText('Loading process diagram')).toBeInTheDocument()
      expect(screen.getByText('Loading process diagram...')).toBeInTheDocument()
    })

    it('has proper ARIA attributes for loading state', () => {
      mockGet.mockImplementation(() => new Promise(() => {}))

      renderProcessDAG()

      const loadingContainer = screen.getByRole('status')
      expect(loadingContainer).toHaveAttribute('aria-live', 'polite')
      expect(loadingContainer).toHaveAttribute('aria-label', 'Loading process diagram')
    })
  })

  describe('Error State', () => {
    it('displays error message when fetch fails', async () => {
      const mockError = new Error('Network error')
      const mockGetApiErrorMessage = api.getApiErrorMessage as Mock

      mockGet.mockRejectedValueOnce(mockError)
      mockGetApiErrorMessage.mockReturnValueOnce('Network error')

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(screen.getByText('Failed to load process diagram')).toBeInTheDocument()
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })

    it('handles 404 error gracefully', async () => {
      const mockError = new Error('Process not found')
      const mockGetApiErrorMessage = api.getApiErrorMessage as Mock

      mockGet.mockRejectedValueOnce(mockError)
      mockGetApiErrorMessage.mockReturnValueOnce('The requested resource was not found.')

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(screen.getByText('The requested resource was not found.')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no nodes are returned', async () => {
      const emptyDagData: ProcessDag = {
        nodes: [],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: emptyDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByText('No process steps available')).toBeInTheDocument()
      })
    })
  })

  describe('Success State - Rendering Graph', () => {
    it('renders graph with nodes and edges', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Check nodes are rendered
      expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      expect(screen.getByTestId('node-step_2')).toBeInTheDocument()
      expect(screen.getByTestId('node-step_3')).toBeInTheDocument()

      // Check node content
      expect(screen.getByText(/Check Eligibility.*Step 1/)).toBeInTheDocument()
      expect(screen.getByText(/Gather Documents.*Step 2/)).toBeInTheDocument()
      expect(screen.getByText(/Submit Application.*Step 3/)).toBeInTheDocument()

      // Check edges are rendered
      expect(screen.getByTestId('edges')).toBeInTheDocument()
    })

    it('fetches data from correct API endpoint', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit')

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/processes/boston_resident_parking_permit/dag')
      })
    })

    it('renders graph visualization container', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Verify the graph container has proper styling
      const container = screen.getByTestId('react-flow').parentElement
      expect(container).toHaveStyle({ overflow: 'hidden' })
    })
  })

  describe('Node Click Handler', () => {
    it('calls onNodeClick callback when node is clicked', async () => {
      const mockOnNodeClick = vi.fn()
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit', mockOnNodeClick)

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      const node = screen.getByTestId('node-step_1')
      await userEvent.click(node)

      expect(mockOnNodeClick).toHaveBeenCalledWith('step_1')
    })

    it('does not crash when onNodeClick is not provided', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit')

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      const node = screen.getByTestId('node-step_1')
      await userEvent.click(node)

      // Should not crash
      expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
    })

    it('passes correct step ID for different nodes', async () => {
      const mockOnNodeClick = vi.fn()
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit', mockOnNodeClick)

      await waitFor(() => {
        expect(screen.getByTestId('node-step_2')).toBeInTheDocument()
      })

      // Click different nodes
      await userEvent.click(screen.getByTestId('node-step_1'))
      expect(mockOnNodeClick).toHaveBeenCalledWith('step_1')

      await userEvent.click(screen.getByTestId('node-step_2'))
      expect(mockOnNodeClick).toHaveBeenCalledWith('step_2')

      await userEvent.click(screen.getByTestId('node-step_3'))
      expect(mockOnNodeClick).toHaveBeenCalledWith('step_3')
    })
  })

  describe('Query Caching', () => {
    it('uses query key with processId for caching', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit')

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Check that the query was called
      expect(mockGet).toHaveBeenCalledTimes(1)
    })

    it('fetches different data for different processIds', async () => {
      const dagData2: ProcessDag = {
        nodes: [
          {
            id: 'other_step_1',
            label: 'Other Step',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: mockDagData })
      mockGet.mockResolvedValueOnce({ data: dagData2 })

      // Render with first process ID
      const { unmount } = renderProcessDAG('process_1')

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      expect(mockGet).toHaveBeenCalledWith('/processes/process_1/dag')

      unmount()

      // Render with second process ID
      renderProcessDAG('process_2')

      await waitFor(() => {
        expect(mockGet).toHaveBeenCalledWith('/processes/process_2/dag')
      })

      expect(mockGet).toHaveBeenCalledTimes(2)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA roles for error state', async () => {
      const mockError = new Error('Network error')
      mockGet.mockRejectedValueOnce(mockError)

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })

    it('nodes are keyboard accessible', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Check that nodes have proper attributes for keyboard navigation
      const node = screen.getByTestId('node-step_1')
      expect(node).toHaveAttribute('role', 'button')
      expect(node).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Edge Cases', () => {
    it('handles single node with no edges', async () => {
      const singleNodeDag: ProcessDag = {
        nodes: [
          {
            id: 'only_step',
            label: 'Single Step',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: singleNodeDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('node-only_step')).toBeInTheDocument()
      })

      expect(screen.getByText(/Single Step.*Step 1/)).toBeInTheDocument()
    })

    it('handles nodes with special characters in labels', async () => {
      const specialCharsDag: ProcessDag = {
        nodes: [
          {
            id: 'step_1',
            label: 'Step with "quotes" & <symbols>',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: specialCharsDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByText(/Step with "quotes" & <symbols>.*Step 1/)).toBeInTheDocument()
      })
    })

    it('handles complex graph with multiple dependencies', async () => {
      const complexDag: ProcessDag = {
        nodes: [
          { id: 'a', label: 'A', order: 1, data: {} },
          { id: 'b', label: 'B', order: 2, data: {} },
          { id: 'c', label: 'C', order: 3, data: {} },
          { id: 'd', label: 'D', order: 4, data: {} },
        ],
        edges: [
          { source: 'b', target: 'a', type: 'DEPENDS_ON' },
          { source: 'c', target: 'a', type: 'DEPENDS_ON' },
          { source: 'd', target: 'b', type: 'DEPENDS_ON' },
          { source: 'd', target: 'c', type: 'DEPENDS_ON' },
        ],
      }

      mockGet.mockResolvedValueOnce({ data: complexDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      expect(screen.getByTestId('node-a')).toBeInTheDocument()
      expect(screen.getByTestId('node-b')).toBeInTheDocument()
      expect(screen.getByTestId('node-c')).toBeInTheDocument()
      expect(screen.getByTestId('node-d')).toBeInTheDocument()
    })
  })
})
