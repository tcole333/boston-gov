import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChatInterface from './components/ChatInterface'

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

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          padding: '2rem',
          backgroundColor: '#f5f5f5',
        }}
      >
        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
          Boston Government Navigation Assistant
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem' }}>
          Helping citizens navigate government services
        </p>

        <ChatInterface />

        <p style={{ marginTop: '2rem', color: '#999', fontSize: '0.9rem' }}>
          Phase 1: Boston Resident Parking Permits (RPP)
        </p>
      </div>
    </QueryClientProvider>
  )
}

export default App
