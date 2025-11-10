import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { DocumentUpload } from '../src/components/DocumentUpload'
import type { DocumentUploadResponse } from '../src/types/api'

/**
 * Basic test suite for DocumentUpload component.
 * Tests core functionality and rendering.
 */

const API_BASE_URL = 'http://localhost:8000/api'

const mockSuccessResponse: DocumentUploadResponse = {
  document_id: 'doc-123',
  filename: 'test-document.pdf',
  status: 'verified',
  upload_timestamp: '2025-11-10T12:00:00Z',
  validation_result: {
    passed: true,
    message: 'Document meets all requirements',
    citations: [],
  },
}

const server = setupServer(
  http.post(`${API_BASE_URL}/documents/upload`, async () => {
    return HttpResponse.json(mockSuccessResponse)
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const renderWithQueryClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('DocumentUpload - Basic Tests', () => {
  describe('Rendering', () => {
    it('should render with correct document type label', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      expect(screen.getByText('Upload Proof Of Residency')).toBeInTheDocument()
    })

    it('should render drop zone', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      expect(screen.getByRole('button', { name: /Click or drag file to upload/i })).toBeInTheDocument()
    })

    it('should render upload button (disabled initially)', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      expect(uploadButton).toBeDisabled()
    })

    it('should show supported formats message', () => {
      renderWithQueryClient(<DocumentUpload documentType="vehicle_registration" />)
      expect(screen.getByText(/Supported formats: PDF, JPG, PNG \(max 10MB\)/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels on form controls', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      expect(screen.getByLabelText('Click or drag file to upload')).toBeInTheDocument()
      expect(screen.getByLabelText('File input')).toBeInTheDocument()
      expect(screen.getByLabelText('Upload document')).toBeInTheDocument()
    })

    it('should support keyboard navigation for drop zone', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      const dropZone = screen.getByRole('button', { name: /Click or drag file to upload/i })
      expect(dropZone).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Component Structure', () => {
    it('should render file input with correct accept attribute', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      const input = screen.getByLabelText('File input') as HTMLInputElement
      expect(input).toHaveAttribute('accept', 'application/pdf,image/jpeg,image/png')
      expect(input).toHaveAttribute('type', 'file')
    })

    it('should render form element', () => {
      const { container } = renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      const form = container.querySelector('form')
      expect(form).toBeInTheDocument()
    })
  })

  describe('Props', () => {
    it('should accept documentType prop', () => {
      renderWithQueryClient(<DocumentUpload documentType="license" />)
      expect(screen.getByText('Upload License')).toBeInTheDocument()
    })

    it('should handle different document types', () => {
      const { rerender } = renderWithQueryClient(
        <QueryClientProvider client={new QueryClient()}>
          <DocumentUpload documentType="proof_of_residency" />
        </QueryClientProvider>
      )
      expect(screen.getByText('Upload Proof Of Residency')).toBeInTheDocument()

      rerender(
        <QueryClientProvider client={new QueryClient()}>
          <DocumentUpload documentType="vehicle_registration" />
        </QueryClientProvider>
      )
      expect(screen.getByText('Upload Vehicle Registration')).toBeInTheDocument()
    })
  })
})
