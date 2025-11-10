import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { AxiosResponse } from 'axios'
import { DocumentUpload } from '../src/components/DocumentUpload'
import type { DocumentUploadResponse } from '../src/types/api'
import * as api from '../src/lib/api'

/**
 * Test suite for DocumentUpload component.
 *
 * Tests:
 * - File selection via click
 * - Drag and drop
 * - Client-side validation (file type, size)
 * - Upload success with validation result
 * - Upload error handling
 * - Clear file functionality
 * - Citation display in validation results
 * - Accessibility (ARIA labels, keyboard navigation)
 * - Progress indicator during upload
 *
 * Note: This suite mocks axios directly instead of using MSW to avoid
 * axios/MSW/Vitest integration issues. The apiClient.post method is mocked
 * to return controlled responses for each test scenario.
 */

// Create test files
const createTestFile = (name: string, size: number, type: string): File => {
  const content = new Array(size).fill('a').join('')
  return new File([content], name, { type })
}

// Helper to upload file to input element
const uploadFile = (input: HTMLInputElement, file: File): void => {
  // Create a FileList-like object
  const fileList = {
    0: file,
    length: 1,
    item: () => file,
  }

  // Set the files property (use configurable: true to allow redefinition)
  Object.defineProperty(input, 'files', {
    value: fileList,
    writable: false,
    configurable: true,
  })

  // Trigger change event
  fireEvent.change(input)
}

// Mock responses
const mockSuccessResponse: DocumentUploadResponse = {
  document_id: 'doc-123',
  filename: 'test-document.pdf',
  status: 'verified',
  upload_timestamp: '2025-11-10T12:00:00Z',
  validation_result: {
    passed: true,
    message: 'Document meets all requirements [1]',
    citations: [
      {
        fact_id: 'fact-001',
        url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
        text: 'Proof of residency requirements',
        source_section: 'Required Documents',
      },
    ],
  },
}

const mockFailureResponse: DocumentUploadResponse = {
  document_id: 'doc-456',
  filename: 'invalid-document.jpg',
  status: 'rejected',
  upload_timestamp: '2025-11-10T12:00:00Z',
  validation_result: {
    passed: false,
    message: 'Document does not meet residency requirements [1]. Please ensure the document is dated within the last 30 days [2].',
    citations: [
      {
        fact_id: 'fact-001',
        url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
        text: 'Proof of residency requirements',
        source_section: 'Required Documents',
      },
      {
        fact_id: 'fact-002',
        url: 'https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit',
        text: 'Document freshness requirement',
        source_section: 'Document Date Requirements',
      },
    ],
  },
}

// Mock apiClient.post before each test
beforeEach(() => {
  // Clear all mocks before each test
  vi.clearAllMocks()
})

// Reset mocks after each test
afterEach(() => {
  vi.restoreAllMocks()
})

// Helper to render component with QueryClient
const renderWithQueryClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('DocumentUpload', () => {
  describe('Rendering', () => {
    it('should render with correct document type label', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      expect(screen.getByText('Upload Proof Of Residency')).toBeInTheDocument()
    })

    it('should show supported formats message', () => {
      renderWithQueryClient(<DocumentUpload documentType="vehicle_registration" />)
      expect(screen.getByText(/Supported formats: PDF, JPG, PNG \(max 10MB\)/i)).toBeInTheDocument()
    })

    it('should render drop zone with proper ARIA labels', () => {
      renderWithQueryClient(<DocumentUpload documentType="license" />)
      const dropZone = screen.getByRole('button', { name: /Click or drag file to upload/i })
      expect(dropZone).toBeInTheDocument()
      expect(dropZone).toHaveAttribute('tabIndex', '0')
    })

    it('should render upload button (disabled initially)', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)
      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      expect(uploadButton).toBeInTheDocument()
      expect(uploadButton).toBeDisabled()
    })
  })

  describe('File Selection', () => {
    it('should allow selecting a valid PDF file', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText('test.pdf')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Upload button should now be enabled
      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      expect(uploadButton).not.toBeDisabled()
    })

    it('should allow selecting a valid JPG file', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('photo.jpg', 2048, 'image/jpeg')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText('photo.jpg')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })

    it('should allow selecting a valid PNG file', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('scan.png', 3072, 'image/png')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText('scan.png')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })

    it('should show file size in preview', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024 * 1024, 'application/pdf') // 1MB
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText(/1 MB/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Client-side Validation', () => {
    it('should reject invalid file type', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('document.txt', 1024, 'text/plain')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      // Use fireEvent for file input to ensure change event fires
      uploadFile(input, file)

      // Validation error should appear immediately (synchronous validation)
      await waitFor(
        () => {
          expect(screen.getByText(/Invalid file type/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // File preview should not be shown
      expect(screen.queryByText('document.txt')).not.toBeInTheDocument()

      // Upload button should remain disabled
      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      expect(uploadButton).toBeDisabled()
    })

    it('should reject file exceeding size limit', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('large.pdf', 11 * 1024 * 1024, 'application/pdf') // 11MB
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText(/File size exceeds 10 MB limit/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      expect(screen.queryByText('large.pdf')).not.toBeInTheDocument()
    })

    it('should reject empty file', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('empty.pdf', 0, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText(/File is empty/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Drag and Drop', () => {
    it('should handle file drop', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('dropped.pdf', 1024, 'application/pdf')
      const dropZone = screen.getByRole('button', { name: /Click or drag file to upload/i })

      // Simulate drop with fireEvent
      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
          types: ['Files'],
        },
      })

      await waitFor(
        () => {
          expect(screen.getByText('dropped.pdf')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Upload Functionality', () => {
    it('should upload file successfully and show validation result', async () => {
      // Mock apiClient.post with a small delay to allow checking upload state
      vi.spyOn(api.apiClient, 'post').mockImplementation(
        () =>
          new Promise<AxiosResponse<DocumentUploadResponse>>((resolve) => {
            setTimeout(() => {
              resolve({ data: mockSuccessResponse } as AxiosResponse<DocumentUploadResponse>)
            }, 100)
          })
      )

      const user = userEvent.setup()
      const onSuccess = vi.fn()
      renderWithQueryClient(
        <DocumentUpload documentType="proof_of_residency" onUploadSuccess={onSuccess} />
      )

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Should show uploading state in progress indicator
      await waitFor(
        () => {
          expect(screen.getByRole('status', { name: /Upload in progress/i })).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Should show success result
      await waitFor(
        () => {
          expect(screen.getByText('Validation Passed')).toBeInTheDocument()
          expect(screen.getByText(/Document meets all requirements/i)).toBeInTheDocument()
        },
        { timeout: 5000 }
      )

      // Should call success callback
      expect(onSuccess).toHaveBeenCalledWith(mockSuccessResponse)
    })

    it('should show validation failure with citations', async () => {
      // Mock apiClient.post to return failure response
      vi.spyOn(api.apiClient, 'post').mockResolvedValue({
        data: mockFailureResponse,
      } as AxiosResponse<DocumentUploadResponse>)

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.jpg', 1024, 'image/jpeg')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Should show failure result
      await waitFor(
        () => {
          expect(screen.getByText('Validation Failed')).toBeInTheDocument()
          expect(screen.getByText(/Document does not meet residency requirements/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Should show citations
      expect(screen.getByText('Sources:')).toBeInTheDocument()
      expect(screen.getByText('Proof of residency requirements')).toBeInTheDocument()
      expect(screen.getByText('Document freshness requirement')).toBeInTheDocument()

      // Should have clickable citation links
      const citationLinks = screen.getAllByText(/\[\d+\]/)
      expect(citationLinks.length).toBeGreaterThan(0)
    })

    it('should handle upload error', async () => {
      // Mock apiClient.post to reject with properly structured error
      // The error needs to pass through the API client's error interceptor
      const mockError = Object.assign(new Error('Request failed with status code 500'), {
        response: {
          status: 500,
          data: { detail: 'Upload failed: Server error' },
          config: {},
        },
        config: {},
        isAxiosError: true,
        toJSON: () => ({}),
        userMessage: 'Upload failed: Server error',
        isNetworkError: false,
        statusCode: 500,
      })
      vi.spyOn(api.apiClient, 'post').mockRejectedValue(mockError)

      const user = userEvent.setup()
      const onError = vi.fn()
      renderWithQueryClient(
        <DocumentUpload documentType="proof_of_residency" onUploadError={onError} />
      )

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Should show error message
      await waitFor(
        () => {
          expect(screen.getByText(/Upload failed: Server error/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Should call error callback
      expect(onError).toHaveBeenCalledWith('Upload failed: Server error')
    })

    it('should prevent upload while request is pending', async () => {
      // Mock apiClient.post with delayed response
      vi.spyOn(api.apiClient, 'post').mockImplementation(
        () =>
          new Promise<AxiosResponse<DocumentUploadResponse>>((resolve) => {
            setTimeout(() => {
              resolve({ data: mockSuccessResponse } as AxiosResponse<DocumentUploadResponse>)
            }, 1000)
          })
      )

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Upload button should be disabled during upload
      await waitFor(
        () => {
          expect(uploadButton).toBeDisabled()
          expect(screen.getByRole('status', { name: /Upload in progress/i })).toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Clear Functionality', () => {
    it('should clear selected file', async () => {
      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          expect(screen.getByText('test.pdf')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      const clearButton = screen.getByRole('button', { name: /Clear selected file/i })
      await user.click(clearButton)

      // File preview should be removed
      await waitFor(
        () => {
          expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Upload button should be disabled again
      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      expect(uploadButton).toBeDisabled()
    })

    it('should clear validation error when clearing file', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('document.txt', 1024, 'text/plain')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      // Error should appear
      await waitFor(
        () => {
          expect(screen.getByText(/Invalid file type/i)).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Select valid file
      const validFile = createTestFile('test.pdf', 1024, 'application/pdf')
      uploadFile(input, validFile)

      // Error should be cleared
      await waitFor(
        () => {
          expect(screen.queryByText(/Invalid file type/i)).not.toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })

    it('should clear upload result when selecting new file', async () => {
      // Mock apiClient.post to return success response
      vi.spyOn(api.apiClient, 'post').mockResolvedValue({
        data: mockSuccessResponse,
      } as AxiosResponse<DocumentUploadResponse>)

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Wait for success
      await waitFor(
        () => {
          expect(screen.getByText('Validation Passed')).toBeInTheDocument()
        },
        { timeout: 3000 }
      )

      // Select new file
      const newFile = createTestFile('test2.pdf', 2048, 'application/pdf')
      uploadFile(input, newFile)

      // Previous result should be cleared
      await waitFor(
        () => {
          expect(screen.queryByText('Validation Passed')).not.toBeInTheDocument()
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      expect(screen.getByLabelText('Click or drag file to upload')).toBeInTheDocument()
      expect(screen.getByLabelText('File input')).toBeInTheDocument()
      expect(screen.getByLabelText('Upload document')).toBeInTheDocument()
    })

    it('should support keyboard navigation for drop zone', async () => {
      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const dropZone = screen.getByRole('button', { name: /Click or drag file to upload/i })

      // Focus drop zone
      await user.tab()
      expect(dropZone).toHaveFocus()

      // Should be keyboard accessible
      expect(dropZone).toHaveAttribute('tabIndex', '0')
    })

    it('should announce upload status to screen readers', async () => {
      // Mock apiClient.post with delayed response
      vi.spyOn(api.apiClient, 'post').mockImplementation(
        () =>
          new Promise<AxiosResponse<DocumentUploadResponse>>((resolve) => {
            setTimeout(() => {
              resolve({ data: mockSuccessResponse } as AxiosResponse<DocumentUploadResponse>)
            }, 100)
          })
      )

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      // Should have aria-live region for status
      await waitFor(
        () => {
          const status = screen.getByRole('status')
          expect(status).toHaveAttribute('aria-live', 'polite')
        },
        { timeout: 3000 }
      )
    })

    it('should announce validation errors with aria-live', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('document.txt', 1024, 'text/plain')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          const alert = screen.getByRole('alert')
          expect(alert).toHaveAttribute('aria-live', 'assertive')
          expect(alert).toHaveTextContent(/Invalid file type/i)
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Citation Links', () => {
    it('should render citation links with proper attributes', async () => {
      // Mock apiClient.post to return success response
      vi.spyOn(api.apiClient, 'post').mockResolvedValue({
        data: mockSuccessResponse,
      } as AxiosResponse<DocumentUploadResponse>)

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      await waitFor(
        () => {
          const citationLink = screen.getByLabelText(/Citation 1:/i)
          expect(citationLink).toHaveAttribute('href')
          expect(citationLink).toHaveAttribute('target', '_blank')
          expect(citationLink).toHaveAttribute('rel', 'noopener noreferrer')
        },
        { timeout: 3000 }
      )
    })

    it('should display citation sources list', async () => {
      // Mock apiClient.post to return failure response with citations
      vi.spyOn(api.apiClient, 'post').mockResolvedValue({
        data: mockFailureResponse,
      } as AxiosResponse<DocumentUploadResponse>)

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      await waitFor(
        () => {
          expect(screen.getByText('Sources:')).toBeInTheDocument()

          // Check that all citation texts are present
          mockFailureResponse.validation_result!.citations!.forEach((citation) => {
            expect(screen.getByText(citation.text)).toBeInTheDocument()
          })
        },
        { timeout: 3000 }
      )
    })
  })

  describe('Security', () => {
    it('should sanitize filename display', async () => {
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('../../../malicious.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      await waitFor(
        () => {
          // Should sanitize path traversal characters
          const displayedName = screen.getByText(/malicious\.pdf/i)
          expect(displayedName.textContent).not.toContain('../')
        },
        { timeout: 3000 }
      )
    })

    it('should prevent XSS in validation messages', async () => {
      // Mock apiClient.post with potential XSS in message
      vi.spyOn(api.apiClient, 'post').mockResolvedValue({
        data: {
          ...mockFailureResponse,
          validation_result: {
            passed: false,
            message: '<script>alert("xss")</script>Invalid document',
            citations: [],
          },
        },
      } as AxiosResponse<DocumentUploadResponse>)

      const user = userEvent.setup()
      renderWithQueryClient(<DocumentUpload documentType="proof_of_residency" />)

      const file = createTestFile('test.pdf', 1024, 'application/pdf')
      const input = screen.getByLabelText('File input') as HTMLInputElement

      uploadFile(input, file)

      const uploadButton = screen.getByRole('button', { name: /Upload document/i })
      await user.click(uploadButton)

      await waitFor(
        () => {
          // Should render as text, not execute script
          const message = screen.getByText(/Invalid document/i)
          expect(message.innerHTML).not.toContain('<script>')
        },
        { timeout: 3000 }
      )
    })
  })
})
