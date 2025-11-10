import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppProvider, useAppContext } from './context/AppContext'
import ProcessDAG from './components/ProcessDAG'
import StepDetail from './components/StepDetail'
import ChatInterface from './components/ChatInterface'
import DocumentUpload from './components/DocumentUpload'

/**
 * React Query client configuration.
 *
 * Sensible defaults for government data:
 * - Longer staleTime: Government data doesn't change frequently
 * - Conservative retry: Avoid hammering backend on errors
 * - No refetch on window focus: Prevent unnecessary requests
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Cache data for 10 minutes
      gcTime: 10 * 60 * 1000,
      // Retry failed requests once after 1 second
      retry: 1,
      retryDelay: 1000,
      // Don't refetch on window focus (prevents unnecessary requests)
      refetchOnWindowFocus: false,
      // Don't refetch on reconnect (will use cached data)
      refetchOnReconnect: false,
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      retryDelay: 1000,
    },
  },
})

/**
 * Default process ID for Phase 1 MVP.
 */
const DEFAULT_PROCESS_ID = 'boston_resident_parking_permit'

/**
 * MainPage component - integrates all components with responsive layout.
 *
 * Layout:
 * - Desktop (≥1024px): 2-column grid (DAG left, Chat right), StepDetail below
 * - Mobile/Tablet (<1024px): Stacked vertical layout
 *
 * State flow:
 * 1. User clicks node in ProcessDAG
 * 2. ProcessDAG calls setSelectedStep from AppContext
 * 3. StepDetail reads selectedStepId from AppContext and displays
 * 4. DocumentUpload conditionally shows if step requires documents
 */
const MainPage = (): JSX.Element => {
  const { selectedStepId, selectedProcessId, setSelectedStep } = useAppContext()

  // Use selected process or default
  const processId = selectedProcessId || DEFAULT_PROCESS_ID

  // Handler for DAG node clicks
  const handleNodeClick = (stepId: string): void => {
    setSelectedStep(stepId, processId)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f5f5f5',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Header */}
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '2px solid #007bff',
          padding: '1.5rem 2rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: '1.75rem',
            fontWeight: 600,
            color: '#333',
          }}
        >
          Boston Government Navigation Assistant
        </h1>
        <p
          style={{
            margin: '0.5rem 0 0 0',
            fontSize: '1rem',
            color: '#666',
          }}
        >
          Helping citizens navigate government services - Phase 1: Resident Parking Permits
        </p>
      </header>

      {/* Main content area */}
      <main
        style={{
          padding: '2rem',
          maxWidth: '1600px',
          margin: '0 auto',
        }}
      >
        {/* Two-column layout for DAG and Chat (responsive) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '1.5rem',
            marginBottom: '1.5rem',
          }}
        >
          {/* ProcessDAG - Left column on desktop */}
          <section aria-label="Process flow diagram">
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: '#333',
                marginBottom: '1rem',
              }}
            >
              Process Flow
            </h2>
            <ProcessDAG processId={processId} onNodeClick={handleNodeClick} />
          </section>

          {/* ChatInterface - Right column on desktop */}
          <section aria-label="Chat assistant">
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: '#333',
                marginBottom: '1rem',
              }}
            >
              Ask Questions
            </h2>
            <ChatInterface />
          </section>
        </div>

        {/* StepDetail - Full width, conditional */}
        {selectedStepId && (
          <section
            aria-label="Step details"
            style={{
              marginBottom: '1.5rem',
            }}
          >
            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: '#333',
                marginBottom: '1rem',
              }}
            >
              Step Details
            </h2>
            <StepDetail stepId={selectedStepId} processId={processId} />
          </section>
        )}

        {/* DocumentUpload - Full width, conditional (shows when step requires documents) */}
        {selectedStepId && (
          <section
            aria-label="Document upload"
            style={{
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <div style={{ width: '100%', maxWidth: '600px' }}>
              <h2
                style={{
                  fontSize: '1.25rem',
                  fontWeight: 600,
                  color: '#333',
                  marginBottom: '1rem',
                  textAlign: 'center',
                }}
              >
                Upload Documents
              </h2>
              <DocumentUpload
                documentType="proof_of_residency"
                onUploadSuccess={(response) => {
                  console.log('Upload successful:', response)
                }}
                onUploadError={(error) => {
                  console.error('Upload failed:', error)
                }}
              />
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          padding: '1.5rem 2rem',
          textAlign: 'center',
          color: '#999',
          fontSize: '0.875rem',
          borderTop: '1px solid #ddd',
          marginTop: '2rem',
        }}
      >
        <p style={{ margin: 0 }}>
          Boston Government Navigation Assistant - Phase 1 MVP
        </p>
        <p style={{ margin: '0.5rem 0 0 0' }}>
          Providing guidance on resident parking permits and government processes
        </p>
      </footer>

      {/* Responsive CSS adjustments */}
      <style>{`
        /* Ensure responsive grid works on smaller screens */
        @media (max-width: 768px) {
          main > div {
            grid-template-columns: 1fr !important;
          }
        }

        /* Keyboard navigation support */
        *:focus-visible {
          outline: 2px solid #007bff;
          outline-offset: 2px;
        }
      `}</style>
    </div>
  )
}

/**
 * App component - root component with providers.
 */
const App = (): JSX.Element => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <MainPage />
      </AppProvider>
    </QueryClientProvider>
  )
}

export default App
