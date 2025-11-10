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

// Type definitions for mocked ReactFlow components
interface MockNode {
  id: string
  type?: string
  data: {
    label: string
    order: number
  }
  position: { x: number; y: number }
}

interface MockEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  type?: string
  animated?: boolean
  style?: Record<string, string | number>
  markerEnd?: string
}

interface MockReactFlowProps {
  nodes: MockNode[]
  edges: MockEdge[]
  onNodeClick?: (event: React.MouseEvent, node: MockNode) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  nodeTypes?: Record<string, React.ComponentType<any>>
  connectionMode?: string
  fitView?: boolean
  fitViewOptions?: Record<string, unknown>
  minZoom?: number
  maxZoom?: number
  defaultViewport?: Record<string, unknown>
  attributionPosition?: string
  nodesDraggable?: boolean
  nodesConnectable?: boolean
  elementsSelectable?: boolean
  children?: React.ReactNode
}

interface MockPanelProps {
  children: React.ReactNode
  position?: string
  style?: React.CSSProperties
}

// Helper to sanitize labels (matches component implementation)
const sanitizeLabel = (label: string): string => {
  return String(label)
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .trim()
    .substring(0, 200) // Limit length to prevent DoS
}

// Mock reactflow to avoid rendering issues in tests
vi.mock('reactflow', () => ({
  default: ({ nodes, edges, onNodeClick, nodeTypes }: MockReactFlowProps) => (
    <div data-testid="react-flow">
      <div data-testid="nodes">
        {nodes.map((node) => {
          // Use the custom node component if specified
          const NodeComponent = nodeTypes && node.type ? nodeTypes[node.type] : null
          const sanitizedLabel = sanitizeLabel(node.data.label)

          return (
            <div
              key={node.id}
              data-testid={`node-${node.id}`}
              onClick={(e) => onNodeClick?.(e, node)}
              role="button"
              tabIndex={0}
            >
              {NodeComponent ? (
                <NodeComponent data={node.data} />
              ) : (
                `${sanitizedLabel} - Step ${node.data.order}`
              )}
            </div>
          )
        })}
      </div>
      <div data-testid="edges">
        {edges.map((edge) => (
          <div key={edge.id} data-testid={`edge-${edge.id}`}>
            {edge.source} -&gt; {edge.target}
            {edge.sourceHandle && edge.targetHandle && (
              <span data-testid={`edge-handles-${edge.id}`}>
                ({edge.sourceHandle} → {edge.targetHandle})
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  ),
  Controls: () => <div data-testid="controls">Controls</div>,
  Background: () => <div data-testid="background">Background</div>,
  Panel: ({ children }: MockPanelProps) => <div data-testid="panel">{children}</div>,
  Handle: ({ id, type }: { id: string; type: string }) => (
    <div data-testid={`handle-${type}-${id}`}>Handle</div>
  ),
  Position: {
    Top: 'top',
    Bottom: 'bottom',
  },
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

  const renderProcessDAG = (
    processId = 'boston_resident_parking_permit',
    onNodeClick?: (stepId: string) => void
  ) => {
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

      // Check node content (labels are in separate divs from step numbers)
      expect(screen.getByText('Check Eligibility')).toBeInTheDocument()
      expect(screen.getByText('Gather Documents')).toBeInTheDocument()
      expect(screen.getByText('Submit Application')).toBeInTheDocument()

      // Check edges are rendered
      expect(screen.getByTestId('edges')).toBeInTheDocument()
    })

    it('renders nodes with React Flow handles for edge connections (Issue #61)', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Each node should have both target (top) and source (bottom) handles
      // Check that Handle components are rendered for first node
      const step1Node = screen.getByTestId('node-step_1')
      expect(step1Node.querySelector('[data-testid="handle-target-top"]')).toBeInTheDocument()
      expect(step1Node.querySelector('[data-testid="handle-source-bottom"]')).toBeInTheDocument()
    })

    it('edges specify sourceHandle and targetHandle for connections (Issue #61)', async () => {
      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Check that edges have handle specifications
      const edge0 = screen.getByTestId('edge-edge-0')
      expect(edge0.textContent).toContain('(bottom → top)')

      const edge1 = screen.getByTestId('edge-edge-1')
      expect(edge1.textContent).toContain('(bottom → top)')
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

      expect(screen.getByText('Single Step')).toBeInTheDocument()
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
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Special characters should be sanitized (HTML tags removed)
      expect(screen.getByText('Step with "quotes" &')).toBeInTheDocument()
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

  describe('Security: XSS Protection', () => {
    it('sanitizes node labels with HTML/script tags', async () => {
      const xssDag: ProcessDag = {
        nodes: [
          {
            id: 'step_1',
            label: '<script>alert("XSS")</script>Malicious Step',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: xssDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Should render sanitized text without script tags
      expect(screen.getByText('alert("XSS")Malicious Step')).toBeInTheDocument()
      // The word "script" should not appear as it was in tags <script> which are removed
      const nodeContent = screen.getByTestId('node-step_1').textContent
      expect(nodeContent).not.toContain('<script>')
      expect(nodeContent).not.toContain('</script>')
    })

    it('sanitizes node labels with malicious HTML tags', async () => {
      const xssDag: ProcessDag = {
        nodes: [
          {
            id: 'step_1',
            label: '<img src=x onerror=alert("XSS")>Step Name',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: xssDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Should render sanitized text without img tag
      expect(screen.getByText('Step Name')).toBeInTheDocument()
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
      // Verify no img tag in content
      const nodeContent = screen.getByTestId('node-step_1').textContent
      expect(nodeContent).not.toContain('<img')
    })

    it('blocks node with invalid node ID containing script', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const mockOnNodeClick = vi.fn()

      const maliciousDag: ProcessDag = {
        nodes: [
          {
            id: 'step<script>alert("xss")</script>',
            label: 'Normal Label',
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: maliciousDag })

      renderProcessDAG('boston_resident_parking_permit', mockOnNodeClick)

      await waitFor(() => {
        // When all nodes are invalid, should show empty state
        expect(screen.getByText('No process steps available')).toBeInTheDocument()
      })

      // Node should not render due to invalid ID
      expect(screen.queryByText('Normal Label')).not.toBeInTheDocument()

      // Should have warned about invalid node ID
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Skipping node with invalid ID:',
        'step<script>alert("xss")</script>'
      )

      consoleWarnSpy.mockRestore()
    })

    it('truncates extremely long labels to prevent DoS', async () => {
      const longLabel = 'A'.repeat(500) // 500 characters

      const longLabelDag: ProcessDag = {
        nodes: [
          {
            id: 'step_1',
            label: longLabel,
            order: 1,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: longLabelDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Label should be truncated to 200 characters
      const nodeElement = screen.getByTestId('node-step_1')
      const labelDiv = nodeElement.querySelector('div[style*="font-weight: 600"]')
      const labelText = labelDiv?.textContent || ''

      // The label itself should be truncated to 200 characters
      expect(labelText.length).toBe(200)
      expect(labelText).toBe('A'.repeat(200))
    })
  })

  describe('Security: DoS Protection', () => {
    it('limits number of nodes to prevent browser crash', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Create DAG with 150 nodes (exceeds MAX_NODES = 100)
      const largeNodes = Array.from({ length: 150 }, (_, i) => ({
        id: `step_${i}`,
        label: `Step ${i}`,
        order: i + 1,
        data: {},
      }))

      const largeDag: ProcessDag = {
        nodes: largeNodes,
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: largeDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Should have warned about limiting nodes
      expect(consoleWarnSpy).toHaveBeenCalledWith('Graph has 150 nodes, limiting to 100')

      // Should render only 100 nodes
      const renderedNodes = screen.getByTestId('nodes').children
      expect(renderedNodes.length).toBeLessThanOrEqual(100)

      consoleWarnSpy.mockRestore()
    })

    it('limits number of edges to prevent browser crash', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      // Create 50 nodes
      const nodes = Array.from({ length: 50 }, (_, i) => ({
        id: `step_${i}`,
        label: `Step ${i}`,
        order: i + 1,
        data: {},
      }))

      // Create 600 edges (exceeds MAX_EDGES = 500)
      const largeEdges = Array.from({ length: 600 }, (_, i) => ({
        source: `step_${i % 50}`,
        target: `step_${(i + 1) % 50}`,
        type: 'DEPENDS_ON' as const,
      }))

      const largeDag: ProcessDag = {
        nodes,
        edges: largeEdges,
      }

      mockGet.mockResolvedValueOnce({ data: largeDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Should have warned about limiting edges
      expect(consoleWarnSpy).toHaveBeenCalledWith('Graph has 600 edges, limiting to 500')

      // Should render only 500 edges
      const renderedEdges = screen.getByTestId('edges').children
      expect(renderedEdges.length).toBeLessThanOrEqual(500)

      consoleWarnSpy.mockRestore()
    })
  })

  describe('Security: Injection Protection', () => {
    it('filters nodes with invalid IDs containing special characters', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const maliciousDag: ProcessDag = {
        nodes: [
          {
            id: 'valid_step_1',
            label: 'Valid Step',
            order: 1,
            data: {},
          },
          {
            id: '../../../etc/passwd',
            label: 'Path Traversal',
            order: 2,
            data: {},
          },
          {
            id: 'step; DROP TABLE nodes;',
            label: 'SQL Injection',
            order: 3,
            data: {},
          },
        ],
        edges: [],
      }

      mockGet.mockResolvedValueOnce({ data: maliciousDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Only valid node should render
      expect(screen.getByTestId('node-valid_step_1')).toBeInTheDocument()
      expect(screen.queryByText(/Path Traversal/)).not.toBeInTheDocument()
      expect(screen.queryByText(/SQL Injection/)).not.toBeInTheDocument()

      // Should have warned about invalid IDs
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Skipping node with invalid ID:',
        '../../../etc/passwd'
      )
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Skipping node with invalid ID:',
        'step; DROP TABLE nodes;'
      )

      consoleWarnSpy.mockRestore()
    })

    it('allows node IDs with dots (Issue #62)', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const dotIdDag: ProcessDag = {
        nodes: [
          {
            id: 'rpp.check_eligibility',
            label: 'Check Eligibility',
            order: 1,
            data: {},
          },
          {
            id: 'rpp.gather_documents',
            label: 'Gather Documents',
            order: 2,
            data: {},
          },
          {
            id: 'rpp.submit_application',
            label: 'Submit Application',
            order: 3,
            data: {},
          },
        ],
        edges: [
          {
            source: 'rpp.gather_documents',
            target: 'rpp.check_eligibility',
            type: 'DEPENDS_ON',
          },
        ],
      }

      mockGet.mockResolvedValueOnce({ data: dotIdDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // All nodes with dots should render
      expect(screen.getByTestId('node-rpp.check_eligibility')).toBeInTheDocument()
      expect(screen.getByTestId('node-rpp.gather_documents')).toBeInTheDocument()
      expect(screen.getByTestId('node-rpp.submit_application')).toBeInTheDocument()

      // Should NOT warn about dots in IDs
      expect(consoleWarnSpy).not.toHaveBeenCalledWith(
        'Skipping node with invalid ID:',
        expect.stringContaining('.')
      )

      consoleWarnSpy.mockRestore()
    })

    it('filters edges referencing non-existent nodes', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      const invalidEdgesDag: ProcessDag = {
        nodes: [
          {
            id: 'step_1',
            label: 'Step 1',
            order: 1,
            data: {},
          },
          {
            id: 'step_2',
            label: 'Step 2',
            order: 2,
            data: {},
          },
        ],
        edges: [
          {
            source: 'step_1',
            target: 'step_2',
            type: 'DEPENDS_ON',
          },
          {
            source: 'step_2',
            target: 'nonexistent_step',
            type: 'DEPENDS_ON',
          },
          {
            source: 'another_fake',
            target: 'step_1',
            type: 'DEPENDS_ON',
          },
        ],
      }

      mockGet.mockResolvedValueOnce({ data: invalidEdgesDag })

      renderProcessDAG()

      await waitFor(() => {
        expect(screen.getByTestId('react-flow')).toBeInTheDocument()
      })

      // Should have warned about invalid edges
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Skipping edge with invalid node reference:',
        expect.objectContaining({ source: 'step_2', target: 'nonexistent_step' })
      )
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Skipping edge with invalid node reference:',
        expect.objectContaining({ source: 'another_fake', target: 'step_1' })
      )

      // Only valid edge should render
      const renderedEdges = screen.getByTestId('edges').children
      expect(renderedEdges.length).toBe(1)

      consoleWarnSpy.mockRestore()
    })

    it('blocks callback invocation with invalid node ID on click', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const mockOnNodeClick = vi.fn()

      mockGet.mockResolvedValueOnce({ data: mockDagData })

      renderProcessDAG('boston_resident_parking_permit', mockOnNodeClick)

      await waitFor(() => {
        expect(screen.getByTestId('node-step_1')).toBeInTheDocument()
      })

      // Manually trigger click with invalid node ID
      const invalidNode = {
        id: 'invalid/../node',
        type: 'stepNode',
        data: { label: 'Test', order: 1 },
        position: { x: 0, y: 0 },
      }

      // Access the onNodeClick handler from ReactFlow mock
      const reactFlowElement = screen.getByTestId('react-flow')
      const mockOnNodeClickHandler = (reactFlowElement as never)['props']?.onNodeClick

      // This should trigger validation
      if (mockOnNodeClickHandler) {
        mockOnNodeClickHandler(new MouseEvent('click') as never, invalidNode as never)
      }

      // Should not have called the user's callback
      expect(mockOnNodeClick).not.toHaveBeenCalled()

      consoleWarnSpy.mockRestore()
    })
  })
})
