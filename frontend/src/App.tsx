import { useState } from 'react'

const App = () => {
  const [count, setCount] = useState(0)

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      padding: '2rem'
    }}>
      <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
        Boston Government Navigation Assistant
      </h1>
      <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem' }}>
        Helping citizens navigate government services
      </p>

      <div style={{
        padding: '2rem',
        border: '1px solid #ddd',
        borderRadius: '8px',
        textAlign: 'center'
      }}>
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
            borderRadius: '4px'
          }}
        >
          count is {count}
        </button>
      </div>

      <p style={{ marginTop: '2rem', color: '#999', fontSize: '0.9rem' }}>
        Phase 1: Boston Resident Parking Permits (RPP)
      </p>
    </div>
  )
}

export default App
