import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  NodeTypes,
  ConnectionMode,
  Panel,
  Handle,
  Position,
} from 'reactflow'
import dagre from 'dagre'
import { apiClient, getApiErrorMessage } from '../lib/api'
import type { ProcessDag } from '../types/api'
import 'reactflow/dist/style.css'

/**
 * Props for ProcessDAG component.
 */
export interface ProcessDAGProps {
  /** Process ID to fetch DAG for (e.g., "boston_resident_parking_permit") */
  processId: string
  /** Callback when a node is clicked, receives the step ID */
  onNodeClick?: (stepId: string) => void
}

/**
 * Sanitizes user-provided labels to prevent XSS attacks.
 * Removes HTML tags, trims whitespace, and limits length.
 */
const sanitizeLabel = (label: string): string => {
  return String(label)
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .trim()
    .substring(0, 200) // Limit length to prevent DoS
}

/**
 * Validates node IDs to prevent injection attacks.
 * Only allows alphanumeric characters, underscores, hyphens, and dots.
 */
const isValidNodeId = (id: string): boolean => {
  return /^[a-zA-Z0-9_.-]{1,100}$/.test(id)
}

// Security limits to prevent DoS attacks
const MAX_NODES = 100
const MAX_EDGES = 500

/**
 * Custom node component for process steps.
 * Displays step label with styling.
 * SECURITY: Sanitizes labels to prevent XSS attacks.
 * Includes Handle components for React Flow edge connections.
 */
const StepNode = ({ data }: { data: { label: string; order: number } }): JSX.Element => {
  const safeLabel = sanitizeLabel(data.label)

  return (
    <>
      <Handle type="target" position={Position.Top} id="top" />
      <div
        style={{
          padding: '12px 20px',
          borderRadius: '8px',
          border: '2px solid #007bff',
          backgroundColor: '#ffffff',
          minWidth: '150px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#e7f3ff'
          e.currentTarget.style.borderColor = '#0056b3'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#ffffff'
          e.currentTarget.style.borderColor = '#007bff'
        }}
      >
        <div style={{ fontSize: '0.75rem', color: '#666666', marginBottom: '4px' }}>
          Step {data.order}
        </div>
        <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#333' }}>{safeLabel}</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" />
    </>
  )
}

// Node types for reactflow
const nodeTypes: NodeTypes = {
  stepNode: StepNode,
}

/**
 * Layout nodes using dagre for hierarchical positioning.
 * Uses dagre's rank algorithm to create a top-to-bottom flow.
 */
const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): { nodes: Node[]; edges: Edge[] } => {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 200
  const nodeHeight = 80

  // Configure graph layout
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 100,
    marginx: 20,
    marginy: 20,
  })

  // Add nodes to graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight })
  })

  // Add edges to graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  // Calculate layout
  dagre.layout(dagreGraph)

  // Apply layout positions to nodes
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

/**
 * ProcessDAG component - interactive visualization of process steps.
 *
 * Features:
 * - Fetches process DAG from backend API
 * - Renders interactive graph with reactflow
 * - Auto-layout using dagre (hierarchical top-to-bottom)
 * - Click handler on nodes
 * - Pan and zoom controls
 * - Mobile-friendly (touch gestures)
 * - Loading state
 * - Error state
 * - Accessible (ARIA labels, keyboard navigation)
 */
export const ProcessDAG = ({ processId, onNodeClick }: ProcessDAGProps): JSX.Element => {
  // Fetch DAG data from backend
  const {
    data: dagData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['process-dag', processId],
    queryFn: async (): Promise<ProcessDag> => {
      const response = await apiClient.get<ProcessDag>(`/processes/${processId}/dag`)
      return response.data
    },
  })

  // Transform backend nodes to reactflow format and apply layout
  // SECURITY: Limits nodes/edges to prevent DoS, validates node IDs, sanitizes labels
  const { nodes, edges } = useMemo(() => {
    if (!dagData) {
      return { nodes: [], edges: [] }
    }

    // Limit and warn if graph is too large (DoS protection)
    if (dagData.nodes.length > MAX_NODES) {
      console.warn(`Graph has ${dagData.nodes.length} nodes, limiting to ${MAX_NODES}`)
    }
    if (dagData.edges.length > MAX_EDGES) {
      console.warn(`Graph has ${dagData.edges.length} edges, limiting to ${MAX_EDGES}`)
    }

    const limitedNodes = dagData.nodes.slice(0, MAX_NODES)
    const limitedEdges = dagData.edges.slice(0, MAX_EDGES)

    // Validate node IDs before processing (injection protection)
    const validNodes = limitedNodes.filter((node) => {
      if (!isValidNodeId(node.id)) {
        console.warn('Skipping node with invalid ID:', node.id)
        return false
      }
      return true
    })

    // Convert backend nodes to reactflow nodes
    const reactFlowNodes: Node[] = validNodes.map((node) => ({
      id: node.id,
      type: 'stepNode',
      data: {
        label: node.label, // Will be sanitized by StepNode component
        order: node.order,
      },
      position: { x: 0, y: 0 }, // Will be set by layout
    }))

    // Create set of valid node IDs for edge validation
    const validNodeIds = new Set(validNodes.map((n) => n.id))

    // Convert backend edges to reactflow edges, filtering invalid references
    const reactFlowEdges: Edge[] = limitedEdges
      .filter((edge) => {
        if (!validNodeIds.has(edge.source) || !validNodeIds.has(edge.target)) {
          console.warn('Skipping edge with invalid node reference:', edge)
          return false
        }
        return true
      })
      .map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        sourceHandle: 'bottom',
        targetHandle: 'top',
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#007bff', strokeWidth: 2 },
        markerEnd: 'arrowclosed',
      }))

    // Apply dagre layout
    return getLayoutedElements(reactFlowNodes, reactFlowEdges)
  }, [dagData])

  // Handle node click with security validation
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        if (!isValidNodeId(node.id)) {
          console.warn('Blocked invalid node ID:', node.id)
          return
        }
        onNodeClick(node.id)
      }
    },
    [onNodeClick]
  )

  // Loading state
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #ddd',
        }}
        role="status"
        aria-live="polite"
        aria-label="Loading process diagram"
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              border: '4px solid #e0e0e0',
              borderTop: '4px solid #007bff',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 1rem',
            }}
          />
          <p style={{ color: '#666666', fontSize: '0.95rem' }}>Loading process diagram...</p>
        </div>

        {/* CSS animation for spinner */}
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  // Error state
  if (isError) {
    const errorMessage = getApiErrorMessage(error)
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          backgroundColor: '#fff5f5',
          borderRadius: '8px',
          border: '1px solid #fcc',
        }}
        role="alert"
      >
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#c00', marginBottom: '0.5rem' }}>
            Failed to load process diagram
          </h3>
          <p style={{ color: '#666666', fontSize: '0.9rem' }}>{errorMessage}</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (!dagData || nodes.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '400px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #ddd',
        }}
      >
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ color: '#666666', fontSize: '0.95rem' }}>No process steps available</p>
        </div>
      </div>
    )
  }

  // Success state - render graph
  return (
    <div
      role="region"
      aria-label={`Process flow diagram for ${processId} with ${nodes.length} steps`}
      style={{
        height: '600px',
        width: '100%',
        border: '1px solid #ddd',
        borderRadius: '8px',
        overflow: 'hidden',
        backgroundColor: '#ffffff',
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        connectionMode={ConnectionMode.Strict}
        fitView
        fitViewOptions={{
          padding: 0.2,
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        attributionPosition="bottom-right"
        // Accessibility
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e0e0e0" />
        <Controls
          showZoom={true}
          showFitView={true}
          showInteractive={false}
          position="top-right"
        />
        <Panel position="top-left" style={{ fontSize: '0.9rem', color: '#666666' }}>
          <div
            style={{
              backgroundColor: '#ffffff',
              padding: '0.5rem 0.75rem',
              borderRadius: '4px',
              border: '1px solid #ddd',
              fontWeight: 500,
            }}
          >
            Process Flow Diagram
          </div>
        </Panel>
      </ReactFlow>
    </div>
  )
}

export default ProcessDAG
