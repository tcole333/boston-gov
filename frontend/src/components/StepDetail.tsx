import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, getApiErrorMessage } from '../lib/api'
import type { Step, Requirement, DocumentType } from '../types/graph'

/**
 * Props for StepDetail component.
 */
export interface StepDetailProps {
  /** Step ID to display details for */
  stepId: string
  /** Process ID that contains this step */
  processId: string
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
 * Sanitizes user-provided text to prevent XSS attacks.
 * Removes HTML tags, trims whitespace, and limits length.
 */
const sanitizeText = (text: string): string => {
  return String(text)
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .trim()
    .substring(0, 5000) // Limit length to prevent DoS
}

/**
 * Props for CitationLink component.
 */
interface CitationLinkProps {
  /** Citation URL */
  url: string
  /** Citation text (e.g., "Boston.gov Parking Permit Requirements") */
  text?: string
  /** Source section (e.g., "Requirements") */
  sourceSection?: string | null
  /** Confidence level */
  confidence?: string
}

/**
 * Renders a citation as a clickable link with metadata.
 * SECURITY: Validates URLs before rendering, uses rel="noopener noreferrer".
 */
const CitationLink = ({ url, text, sourceSection, confidence }: CitationLinkProps): JSX.Element => {
  const safeUrl = isSafeUrl(url) ? url : '#'
  const displayText = text || 'Source'

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
        marginLeft: '0.2em',
        fontWeight: 'bold',
      }}
      title={`${displayText}${sourceSection ? ` (${sourceSection})` : ''}${confidence ? ` - ${confidence} confidence` : ''}`}
      aria-label={`Citation: ${displayText}`}
      onClick={(e) => {
        if (!isSafeUrl(url)) {
          e.preventDefault()
          console.warn('Blocked unsafe URL:', url)
        }
      }}
    >
      [source]
    </a>
  )
}

/**
 * Loading skeleton component.
 */
const LoadingSkeleton = (): JSX.Element => {
  return (
    <div
      style={{
        padding: '2rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #ddd',
      }}
      role="status"
      aria-live="polite"
      aria-label="Loading step details"
    >
      <div style={{ marginBottom: '1rem' }}>
        <div
          style={{
            height: '2rem',
            width: '60%',
            backgroundColor: '#e0e0e0',
            borderRadius: '4px',
            marginBottom: '0.5rem',
          }}
        />
        <div
          style={{
            height: '1rem',
            width: '40%',
            backgroundColor: '#e0e0e0',
            borderRadius: '4px',
          }}
        />
      </div>
      <div style={{ marginTop: '1.5rem' }}>
        <div
          style={{
            height: '1rem',
            width: '100%',
            backgroundColor: '#e0e0e0',
            borderRadius: '4px',
            marginBottom: '0.5rem',
          }}
        />
        <div
          style={{
            height: '1rem',
            width: '90%',
            backgroundColor: '#e0e0e0',
            borderRadius: '4px',
          }}
        />
      </div>
    </div>
  )
}

/**
 * StepDetail component - displays detailed information about a process step.
 *
 * Features:
 * - Fetches step details from backend API
 * - Displays step name, description, cost, time estimates
 * - Shows list of requirements with inline citations
 * - Shows list of required documents with inline citations
 * - Clickable citations that open in new tabs with security measures
 * - Loading state while fetching
 * - Error state if step not found or network error
 * - WCAG 2.1 AA compliance (semantic HTML, ARIA labels, keyboard navigation)
 * - XSS prevention (URL validation, text sanitization)
 *
 * Security:
 * - Validates all URLs before rendering as links
 * - Sanitizes all text content to prevent XSS
 * - Uses rel="noopener noreferrer" on external links
 * - Limits text length to prevent DoS attacks
 */
export const StepDetail = ({ stepId, processId }: StepDetailProps): JSX.Element => {
  // Fetch step details
  const {
    data: step,
    isLoading: isStepLoading,
    isError: isStepError,
    error: stepError,
  } = useQuery({
    queryKey: ['step', processId, stepId],
    queryFn: async (): Promise<Step> => {
      const response = await apiClient.get<Step>(`/processes/${processId}/steps/${stepId}`)
      return response.data
    },
    enabled: Boolean(stepId && processId),
  })

  // Fetch process requirements (we'll filter for this step if needed)
  const {
    data: allRequirements,
    isLoading: isRequirementsLoading,
    isError: isRequirementsError,
  } = useQuery({
    queryKey: ['requirements', processId],
    queryFn: async (): Promise<Requirement[]> => {
      const response = await apiClient.get<Requirement[]>(`/processes/${processId}/requirements`)
      return response.data
    },
    enabled: Boolean(processId),
  })

  // Fetch document types (placeholder - in Phase 1, we'll show a simplified view)
  const {
    data: documentTypes,
    isLoading: isDocumentsLoading,
  } = useQuery({
    queryKey: ['document-types', processId],
    queryFn: async (): Promise<DocumentType[]> => {
      // For Phase 1, we'll return empty array since there's no dedicated endpoint yet
      // In Phase 2, this would fetch from /processes/{processId}/documents
      return []
    },
    enabled: Boolean(processId),
  })

  // Sanitize step data
  const sanitizedStep = useMemo(() => {
    if (!step) return null
    return {
      ...step,
      name: sanitizeText(step.name),
      description: sanitizeText(step.description),
    }
  }, [step])

  // Loading state
  if (isStepLoading || isRequirementsLoading || isDocumentsLoading) {
    return <LoadingSkeleton />
  }

  // Error state
  if (isStepError || isRequirementsError) {
    const errorMessage = getApiErrorMessage(stepError || new Error('Failed to load step details'))
    return (
      <div
        style={{
          padding: '2rem',
          backgroundColor: '#fff5f5',
          borderRadius: '8px',
          border: '1px solid #fcc',
          textAlign: 'center',
        }}
        role="alert"
      >
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
        <h3
          style={{
            fontSize: '1.1rem',
            fontWeight: 600,
            color: '#c00',
            marginBottom: '0.5rem',
          }}
        >
          Failed to load step details
        </h3>
        <p style={{ color: '#666666', fontSize: '0.9rem' }}>{errorMessage}</p>
      </div>
    )
  }

  // No step data
  if (!sanitizedStep) {
    return (
      <div
        style={{
          padding: '2rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #ddd',
          textAlign: 'center',
        }}
      >
        <p style={{ color: '#666666', fontSize: '0.95rem' }}>No step details available</p>
      </div>
    )
  }

  return (
    <article
      style={{
        padding: '2rem',
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        border: '1px solid #ddd',
      }}
      aria-label={`Details for step: ${sanitizedStep.name}`}
    >
      {/* Step Header */}
      <header style={{ marginBottom: '1.5rem', borderBottom: '2px solid #007bff', paddingBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '0.25rem 0.75rem',
              backgroundColor: '#007bff',
              color: '#ffffff',
              borderRadius: '12px',
              fontSize: '0.75rem',
              fontWeight: 600,
              marginRight: '0.75rem',
            }}
            aria-label={`Step ${sanitizedStep.order}`}
          >
            Step {sanitizedStep.order}
          </span>
          {sanitizedStep.optional && (
            <span
              style={{
                display: 'inline-block',
                padding: '0.25rem 0.75rem',
                backgroundColor: '#f0f0f0',
                color: '#666',
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
              aria-label="Optional step"
            >
              Optional
            </span>
          )}
        </div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#333', margin: 0 }}>
          {sanitizedStep.name}
          <CitationLink
            url={sanitizedStep.source_url}
            text="Official Source"
            confidence={sanitizedStep.confidence}
          />
        </h2>
      </header>

      {/* Step Description */}
      <section style={{ marginBottom: '1.5rem' }}>
        <p
          style={{
            fontSize: '1rem',
            lineHeight: '1.6',
            color: '#333',
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}
        >
          {sanitizedStep.description}
        </p>
      </section>

      {/* Step Metadata */}
      <section
        style={{
          marginBottom: '1.5rem',
          padding: '1rem',
          backgroundColor: '#f8f9fa',
          borderRadius: '6px',
        }}
        aria-label="Step metadata"
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem' }}>
          {sanitizedStep.estimated_time_minutes !== null && (
            <div>
              <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>
                Estimated Time
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#333' }}>
                {sanitizedStep.estimated_time_minutes} minutes
              </div>
            </div>
          )}
          {sanitizedStep.cost_usd > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>
                Cost
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#333' }}>
                ${sanitizedStep.cost_usd.toFixed(2)}
              </div>
            </div>
          )}
          <div>
            <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>
              Last Verified
            </div>
            <div style={{ fontSize: '0.9rem', color: '#333' }}>
              {sanitizedStep.last_verified}
            </div>
          </div>
        </div>
      </section>

      {/* Requirements Section */}
      {allRequirements && allRequirements.length > 0 && (
        <section style={{ marginBottom: '1.5rem' }} aria-labelledby="requirements-heading">
          <h3
            id="requirements-heading"
            style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              color: '#333',
              marginBottom: '0.75rem',
            }}
          >
            Requirements
          </h3>
          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              margin: 0,
            }}
          >
            {allRequirements.map((req) => {
              const sanitizedReqText = sanitizeText(req.text)
              return (
                <li
                  key={req.requirement_id}
                  style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    backgroundColor: req.hard_gate ? '#fff3cd' : '#f8f9fa',
                    border: `1px solid ${req.hard_gate ? '#ffc107' : '#ddd'}`,
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'flex-start',
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      width: '1.5rem',
                      height: '1.5rem',
                      borderRadius: '50%',
                      backgroundColor: req.hard_gate ? '#ffc107' : '#6c757d',
                      color: '#fff',
                      textAlign: 'center',
                      lineHeight: '1.5rem',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      marginRight: '0.75rem',
                      flexShrink: 0,
                    }}
                    aria-label={req.hard_gate ? 'Required' : 'Optional'}
                  >
                    {req.hard_gate ? '!' : 'i'}
                  </span>
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: '0.95rem', color: '#333' }}>
                      {sanitizedReqText}
                      <CitationLink
                        url={req.source_url}
                        text="Source"
                        sourceSection={req.source_section}
                        confidence={req.confidence}
                      />
                    </span>
                    {req.hard_gate && (
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: '#856404',
                          marginTop: '0.25rem',
                        }}
                      >
                        Required - blocks progress if not met
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {/* Documents Section */}
      {documentTypes && documentTypes.length > 0 && (
        <section style={{ marginBottom: '1.5rem' }} aria-labelledby="documents-heading">
          <h3
            id="documents-heading"
            style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              color: '#333',
              marginBottom: '0.75rem',
            }}
          >
            Required Documents
          </h3>
          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              margin: 0,
            }}
          >
            {documentTypes.map((docType) => {
              const sanitizedDocName = sanitizeText(docType.name)
              return (
                <li
                  key={docType.doc_type_id}
                  style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    backgroundColor: '#f8f9fa',
                    border: '1px solid #ddd',
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#333', marginBottom: '0.25rem' }}>
                    {sanitizedDocName}
                    <CitationLink
                      url={docType.source_url}
                      text="Source"
                      confidence={docType.confidence}
                    />
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#666' }}>
                    {docType.freshness_days > 0 && (
                      <div>Must be issued within {docType.freshness_days} days</div>
                    )}
                    {docType.name_match_required && (
                      <div>Name must match applicant</div>
                    )}
                    {docType.address_match_required && (
                      <div>Address must match Boston address</div>
                    )}
                    {docType.examples.length > 0 && (
                      <div style={{ marginTop: '0.25rem' }}>
                        Examples: {docType.examples.join(', ')}
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {/* Source Attribution */}
      <footer
        style={{
          marginTop: '2rem',
          paddingTop: '1rem',
          borderTop: '1px solid #e0e0e0',
          fontSize: '0.85rem',
          color: '#666',
        }}
      >
        <div style={{ marginBottom: '0.5rem' }}>
          <strong>Source Confidence:</strong>{' '}
          <span
            style={{
              textTransform: 'capitalize',
              color: sanitizedStep.confidence === 'high' ? '#28a745' : sanitizedStep.confidence === 'medium' ? '#ffc107' : '#dc3545',
              fontWeight: 600,
            }}
          >
            {sanitizedStep.confidence}
          </span>
        </div>
        <div>
          Information last verified on {sanitizedStep.last_verified}
        </div>
      </footer>
    </article>
  )
}

export default StepDetail
