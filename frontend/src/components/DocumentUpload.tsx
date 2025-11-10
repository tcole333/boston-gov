import { useState, useRef, ChangeEvent, DragEvent, FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient, getApiErrorMessage } from '../lib/api'
import type { DocumentType, DocumentUploadResponse, Citation } from '../types/api'

/**
 * Maximum file size in bytes (10MB).
 */
const MAX_FILE_SIZE = 10 * 1024 * 1024

/**
 * Allowed MIME types for document upload.
 */
const ALLOWED_MIME_TYPES = ['application/pdf', 'image/jpeg', 'image/png']

/**
 * File extensions mapped to MIME types.
 */
const MIME_TYPE_EXTENSIONS: Record<string, string> = {
  'application/pdf': '.pdf',
  'image/jpeg': '.jpg, .jpeg',
  'image/png': '.png',
}

/**
 * Props for DocumentUpload component.
 */
export interface DocumentUploadProps {
  /** Type of document being uploaded */
  documentType: DocumentType
  /** Callback when upload succeeds */
  onUploadSuccess?: (response: DocumentUploadResponse) => void
  /** Callback when upload fails */
  onUploadError?: (error: string) => void
}

/**
 * Validates that a URL uses a safe protocol (http or https).
 * Prevents XSS attacks via javascript:, data:, vbscript: protocols.
 *
 * @param url - The URL to validate
 * @returns true if the URL is safe, false otherwise
 */
const isSafeUrl = (url: string): boolean => {
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}

/**
 * Sanitizes filename by removing potentially dangerous characters.
 * Prevents path traversal and XSS attacks.
 *
 * @param filename - The filename to sanitize
 * @returns Sanitized filename
 */
const sanitizeFilename = (filename: string): string => {
  return filename
    .replace(/[^a-zA-Z0-9._-]/g, '_') // Replace special chars with underscore
    .replace(/\.+/g, '.') // Replace multiple dots with single dot
    .substring(0, 255) // Limit length
    .trim()
}

/**
 * Formats file size in human-readable format.
 *
 * @param bytes - File size in bytes
 * @returns Formatted file size string
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Validates a file against allowed types and size limits.
 *
 * @param file - The file to validate
 * @returns Error message if invalid, null if valid
 */
const validateFile = (file: File): string | null => {
  // Check file type
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    const allowedExtensions = Object.values(MIME_TYPE_EXTENSIONS).join(', ')
    return `Invalid file type. Please upload a PDF, JPG, or PNG file. Allowed: ${allowedExtensions}`
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return `File size exceeds ${formatFileSize(MAX_FILE_SIZE)} limit. Your file is ${formatFileSize(file.size)}.`
  }

  // Check file size is not 0
  if (file.size === 0) {
    return 'File is empty. Please select a valid file.'
  }

  return null
}

/**
 * Props for CitationLink component.
 */
interface CitationLinkProps {
  /** Citation index (1-based) */
  index: number
  /** Citation data */
  citation: Citation
}

/**
 * Renders a citation as a clickable superscript link.
 */
const CitationLink = ({ index, citation }: CitationLinkProps): JSX.Element => {
  const safeUrl = isSafeUrl(citation.url) ? citation.url : '#'

  return (
    <a
      href={safeUrl}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        color: '#0066cc',
        textDecoration: 'none',
        fontSize: '0.75em',
        verticalAlign: 'super',
        marginLeft: '0.1em',
        fontWeight: 'bold',
      }}
      title={`${citation.text}${citation.source_section ? ` (${citation.source_section})` : ''}`}
      aria-label={`Citation ${index}: ${citation.text}`}
      onClick={(e) => {
        if (!isSafeUrl(citation.url)) {
          e.preventDefault()
          console.warn('Blocked unsafe URL:', citation.url)
        }
      }}
    >
      [{index}]
    </a>
  )
}

/**
 * Props for ValidationResult component.
 */
interface ValidationResultProps {
  /** Upload response data */
  response: DocumentUploadResponse
}

/**
 * Displays validation results with citations.
 */
const ValidationResult = ({ response }: ValidationResultProps): JSX.Element => {
  const result = response.validation_result

  if (!result) {
    return (
      <div
        style={{
          padding: '0.75rem 1rem',
          backgroundColor: '#e7f3ff',
          border: '1px solid #b3d9ff',
          borderRadius: '4px',
          color: '#004085',
        }}
        role="status"
        aria-live="polite"
      >
        <strong>Status:</strong> {response.status === 'processing' ? 'Processing...' : 'Uploaded'}
      </div>
    )
  }

  const isPassed = result.passed
  const backgroundColor = isPassed ? '#d4edda' : '#f8d7da'
  const borderColor = isPassed ? '#c3e6cb' : '#f5c6cb'
  const textColor = isPassed ? '#155724' : '#721c24'

  // Parse message and insert citation links
  const renderMessage = (): JSX.Element => {
    if (!result.citations || result.citations.length === 0) {
      return <>{result.message}</>
    }

    const MAX_CITATIONS = 50
    const parts: (string | JSX.Element)[] = []
    let lastIndex = 0
    let matchCount = 0
    const regex = /\[(\d+)\]/g
    let match: RegExpExecArray | null

    while ((match = regex.exec(result.message)) !== null) {
      matchCount++
      if (matchCount > MAX_CITATIONS) {
        console.warn('Too many citation markers, stopping parsing')
        break
      }

      const citationIndex = parseInt(match[1] ?? '0', 10)

      if (citationIndex < 1 || citationIndex > 1000) {
        parts.push(match[0] ?? '')
        lastIndex = regex.lastIndex
        continue
      }

      const citation = result.citations[citationIndex - 1]

      if (match.index > lastIndex) {
        parts.push(result.message.substring(lastIndex, match.index))
      }

      if (citation) {
        parts.push(
          <CitationLink key={`cite-${citationIndex}`} index={citationIndex} citation={citation} />
        )
      } else {
        parts.push(match[0] ?? '')
      }

      lastIndex = regex.lastIndex
    }

    if (lastIndex < result.message.length) {
      parts.push(result.message.substring(lastIndex))
    }

    return <>{parts}</>
  }

  return (
    <div
      style={{
        padding: '0.75rem 1rem',
        backgroundColor,
        border: `1px solid ${borderColor}`,
        borderRadius: '4px',
        color: textColor,
      }}
      role="alert"
      aria-live="assertive"
    >
      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
        {isPassed ? 'Validation Passed' : 'Validation Failed'}
      </div>
      <div style={{ whiteSpace: 'pre-wrap' }}>{renderMessage()}</div>

      {result.citations && result.citations.length > 0 && (
        <div
          style={{
            marginTop: '0.75rem',
            paddingTop: '0.75rem',
            borderTop: `1px solid ${borderColor}`,
            fontSize: '0.85em',
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Sources:</div>
          <ol style={{ margin: 0, paddingLeft: '1.5rem' }}>
            {result.citations.map((citation, index) => {
              const safeUrl = isSafeUrl(citation.url) ? citation.url : '#'
              return (
                <li key={index} style={{ marginBottom: '0.25rem' }}>
                  <a
                    href={safeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#0066cc', textDecoration: 'none' }}
                    onClick={(e) => {
                      if (!isSafeUrl(citation.url)) {
                        e.preventDefault()
                        console.warn('Blocked unsafe URL:', citation.url)
                      }
                    }}
                  >
                    {citation.text}
                  </a>
                  {citation.source_section && (
                    <span style={{ color: textColor, opacity: 0.8 }}>
                      {' '}
                      ({citation.source_section})
                    </span>
                  )}
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}

/**
 * DocumentUpload component - file upload with drag-and-drop support.
 *
 * Features:
 * - File input with drag-and-drop support
 * - Client-side validation (file type: PDF/JPG/PNG, size: <= 10MB)
 * - Upload progress indicator
 * - Displays validation result: pass/fail with explanation
 * - Shows inline citation links in validation messages
 * - Uses React Query useMutation for POST /api/documents/upload
 * - Error handling (upload failed, validation failed)
 * - Clear file button to reset
 * - Accessibility: keyboard navigation, ARIA labels, screen reader support
 *
 * @param props - Component props
 * @returns DocumentUpload component
 */
export const DocumentUpload = ({
  documentType,
  onUploadSuccess,
  onUploadError,
}: DocumentUploadProps): JSX.Element => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadResponse, setUploadResponse] = useState<DocumentUploadResponse | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Upload mutation
  const mutation = useMutation({
    mutationFn: async (file: File): Promise<DocumentUploadResponse> => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)

      const response = await apiClient.post<DocumentUploadResponse>(
        '/documents/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      return response.data
    },
    onSuccess: (data: DocumentUploadResponse) => {
      setUploadResponse(data)
      setValidationError(null)
      onUploadSuccess?.(data)
    },
    onError: (err: unknown) => {
      const errorMessage = getApiErrorMessage(err)
      setValidationError(errorMessage)
      setUploadResponse(null)
      onUploadError?.(errorMessage)

      if (import.meta.env.DEV) {
        console.error('Upload error:', { message: errorMessage })
      }
    },
  })

  // Handle file selection
  const handleFileSelect = (file: File | null): void => {
    if (!file) {
      setSelectedFile(null)
      setValidationError(null)
      setUploadResponse(null)
      return
    }

    // Validate file
    const error = validateFile(file)
    if (error) {
      setValidationError(error)
      setSelectedFile(null)
      setUploadResponse(null)
      return
    }

    // File is valid
    setSelectedFile(file)
    setValidationError(null)
    setUploadResponse(null)
  }

  // Handle file input change
  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const file = e.target.files?.[0] ?? null
    handleFileSelect(file)
  }

  // Handle drag events
  const handleDragEnter = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>): void => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const file = e.dataTransfer.files?.[0] ?? null
    handleFileSelect(file)
  }

  // Handle form submit (upload)
  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (selectedFile && !mutation.isPending) {
      mutation.mutate(selectedFile)
    }
  }

  // Handle clear file
  const handleClear = (): void => {
    setSelectedFile(null)
    setValidationError(null)
    setUploadResponse(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Handle click on drop zone
  const handleDropZoneClick = (): void => {
    fileInputRef.current?.click()
  }

  // Handle keyboard navigation for drop zone
  const handleDropZoneKeyDown = (e: React.KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      fileInputRef.current?.click()
    }
  }

  const documentTypeLabel = documentType.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '600px',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '1.5rem',
        backgroundColor: '#ffffff',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
          Upload {documentTypeLabel}
        </h3>
        <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.875rem', color: '#595959' }}>
          Supported formats: PDF, JPG, PNG (max 10MB)
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Drop zone */}
        <div
          onClick={handleDropZoneClick}
          onKeyDown={handleDropZoneKeyDown}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          tabIndex={0}
          role="button"
          aria-label="Click or drag file to upload"
          style={{
            border: `2px dashed ${isDragging ? '#007bff' : '#ddd'}`,
            borderRadius: '8px',
            padding: '2rem',
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: isDragging ? '#f0f8ff' : '#fafafa',
            transition: 'all 0.2s ease',
            marginBottom: '1rem',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png"
            onChange={handleFileInputChange}
            disabled={mutation.isPending}
            style={{ display: 'none' }}
            aria-label="File input"
          />

          <div style={{ color: '#595959' }}>
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ margin: '0 auto 1rem' }}
              aria-hidden="true"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', fontWeight: 500 }}>
              {isDragging ? 'Drop file here' : 'Click to select file or drag and drop'}
            </p>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>PDF, JPG, or PNG up to 10MB</p>
          </div>
        </div>

        {/* Selected file preview */}
        {selectedFile && (
          <div
            style={{
              padding: '1rem',
              backgroundColor: '#f8f9fa',
              border: '1px solid #dee2e6',
              borderRadius: '4px',
              marginBottom: '1rem',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ flex: 1, marginRight: '1rem' }}>
                <div style={{ fontWeight: 500, marginBottom: '0.25rem', wordBreak: 'break-all' }}>
                  {sanitizeFilename(selectedFile.name)}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#595959' }}>
                  {formatFileSize(selectedFile.size)}
                </div>
              </div>
              <button
                type="button"
                onClick={handleClear}
                disabled={mutation.isPending}
                style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.875rem',
                  color: '#dc3545',
                  backgroundColor: 'transparent',
                  border: '1px solid #dc3545',
                  borderRadius: '4px',
                  cursor: mutation.isPending ? 'not-allowed' : 'pointer',
                  opacity: mutation.isPending ? 0.5 : 1,
                }}
                aria-label="Clear selected file"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Validation error */}
        {validationError && (
          <div
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: '4px',
              color: '#721c24',
              marginBottom: '1rem',
            }}
            role="alert"
            aria-live="assertive"
          >
            <strong>Validation Error:</strong> {validationError}
          </div>
        )}

        {/* Upload progress */}
        {mutation.isPending && (
          <div
            style={{
              padding: '1rem',
              backgroundColor: '#e7f3ff',
              border: '1px solid #b3d9ff',
              borderRadius: '4px',
              marginBottom: '1rem',
            }}
            role="status"
            aria-live="polite"
            aria-label="Upload in progress"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  border: '3px solid #b3d9ff',
                  borderTop: '3px solid #007bff',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
                aria-hidden="true"
              />
              <span style={{ color: '#004085', fontWeight: 500 }}>Uploading...</span>
            </div>
          </div>
        )}

        {/* Upload response */}
        {uploadResponse && !mutation.isPending && (
          <div style={{ marginBottom: '1rem' }}>
            <ValidationResult response={uploadResponse} />
          </div>
        )}

        {/* Upload button */}
        <button
          type="submit"
          disabled={!selectedFile || mutation.isPending}
          style={{
            width: '100%',
            padding: '0.75rem 1.5rem',
            fontSize: '1rem',
            fontWeight: 600,
            color: '#ffffff',
            backgroundColor:
              !selectedFile || mutation.isPending ? '#ccc' : '#007bff',
            border: 'none',
            borderRadius: '4px',
            cursor: !selectedFile || mutation.isPending ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s',
          }}
          aria-label="Upload document"
        >
          {mutation.isPending ? 'Uploading...' : 'Upload Document'}
        </button>
      </form>

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

export default DocumentUpload
