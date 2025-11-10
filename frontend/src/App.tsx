import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

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
  const [count, setCount] = useState(0)

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
        }}
      >
        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
          Boston Government Navigation Assistant
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem' }}>
          Helping citizens navigate government services
        </p>

        <div
          style={{
            padding: '2rem',
            border: '1px solid #ddd',
            borderRadius: '8px',
            textAlign: 'center',
          }}
        >
          <p style={{ marginBottom: '1rem' }}>Development server is running!</p>
          <button
            onClick={() => setCount((count) => count + 1)}
            style={{
              padding: '0.5rem 1rem',
              fontSize: '1rem',
              cursor: 'pointer',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
            }}
          >
            count is {count}
          </button>
        </div>

        <p style={{ marginTop: '2rem', color: '#999', fontSize: '0.9rem' }}>
          Phase 1: Boston Resident Parking Permits (RPP)
        </p>
      </div>
    </QueryClientProvider>
  )
}

export default App
