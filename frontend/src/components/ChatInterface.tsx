import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient, getApiErrorMessage } from '../lib/api'
import type { ChatRequest, ConversationResponse, Citation } from '../types/api'

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
 * Message in the chat interface.
 * Extends the conversation with user messages and agent responses.
 */
interface Message {
  /** Role of the message sender */
  role: 'user' | 'agent'
  /** Message content (may include citation markers like [1], [2]) */
  content: string
  /** Citations for agent messages */
  citations?: Citation[]
  /** Timestamp of the message */
  timestamp: Date
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
 * Props for CitationList component.
 */
interface CitationListProps {
  /** Array of citations to display */
  citations: Citation[]
}

/**
 * Renders a list of citations at the bottom of an agent message.
 */
const CitationList = ({ citations }: CitationListProps): JSX.Element => {
  if (citations.length === 0) {
    return <></>
  }

  return (
    <div
      style={{
        marginTop: '1rem',
        paddingTop: '0.75rem',
        borderTop: '1px solid #e0e0e0',
        fontSize: '0.85em',
        color: '#555',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Sources:</div>
      <ol style={{ margin: 0, paddingLeft: '1.5rem' }}>
        {citations.map((citation, index) => {
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
                <span style={{ color: '#777' }}> ({citation.source_section})</span>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/**
 * Props for MessageBubble component.
 */
interface MessageBubbleProps {
  /** Message to display */
  message: Message
}

/**
 * Renders a single message bubble (user or agent).
 */
const MessageBubble = ({ message }: MessageBubbleProps): JSX.Element => {
  const isUser = message.role === 'user'

  // Parse message content and insert citation links
  const renderContent = (): JSX.Element => {
    if (isUser || !message.citations || message.citations.length === 0) {
      return <>{message.content}</>
    }

    // Replace citation markers like [1], [2] with clickable links
    const MAX_CITATIONS = 100 // Prevent DoS from excessive citation markers
    const parts: (string | JSX.Element)[] = []
    let lastIndex = 0
    let matchCount = 0
    const regex = /\[(\d+)\]/g
    let match: RegExpExecArray | null

    while ((match = regex.exec(message.content)) !== null) {
      matchCount++
      if (matchCount > MAX_CITATIONS) {
        console.warn('Too many citation markers, stopping parsing')
        break
      }

      const citationIndex = parseInt(match[1] ?? '0', 10)

      // Validate citation index is reasonable
      if (citationIndex < 1 || citationIndex > 1000) {
        parts.push(match[0] ?? '')
        lastIndex = regex.lastIndex
        continue
      }

      const citation = message.citations[citationIndex - 1]

      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(message.content.substring(lastIndex, match.index))
      }

      // Add citation link
      if (citation) {
        parts.push(
          <CitationLink key={`cite-${citationIndex}`} index={citationIndex} citation={citation} />
        )
      } else {
        // Citation not found, keep original marker
        parts.push(match[0] ?? '')
      }

      lastIndex = regex.lastIndex
    }

    // Add remaining text
    if (lastIndex < message.content.length) {
      parts.push(message.content.substring(lastIndex))
    }

    return <>{parts}</>
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '1rem',
      }}
    >
      <div
        style={{
          maxWidth: '70%',
          padding: '0.75rem 1rem',
          borderRadius: '12px',
          backgroundColor: isUser ? '#007bff' : '#f0f0f0',
          color: isUser ? '#ffffff' : '#333333',
          wordWrap: 'break-word',
        }}
      >
        <div style={{ whiteSpace: 'pre-wrap' }}>{renderContent()}</div>
        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}
      </div>
    </div>
  )
}

/**
 * Loading indicator (typing dots animation).
 */
const LoadingIndicator = (): JSX.Element => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'flex-start',
        marginBottom: '1rem',
      }}
    >
      <div
        style={{
          padding: '0.75rem 1rem',
          borderRadius: '12px',
          backgroundColor: '#f0f0f0',
        }}
      >
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#999',
              animation: 'pulse 1.4s infinite ease-in-out',
              animationDelay: '0s',
            }}
          />
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#999',
              animation: 'pulse 1.4s infinite ease-in-out',
              animationDelay: '0.2s',
            }}
          />
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#999',
              animation: 'pulse 1.4s infinite ease-in-out',
              animationDelay: '0.4s',
            }}
          />
        </div>
      </div>
    </div>
  )
}

/**
 * ChatInterface component - conversational UI for asking RPP questions.
 *
 * Features:
 * - Message history with user and agent messages
 * - Input field with send button
 * - Typing indicator during API call
 * - Inline citation links (clickable)
 * - Auto-scroll to bottom on new messages
 * - Enter key sends message
 * - Error handling
 * - Disabled input while waiting for response
 */
export const ChatInterface = (): JSX.Element => {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Chat mutation for sending messages
  const mutation = useMutation({
    mutationFn: async (request: ChatRequest): Promise<ConversationResponse> => {
      const response = await apiClient.post<ConversationResponse>('/chat/message', request)
      return response.data
    },
    onSuccess: (data: ConversationResponse) => {
      // Add agent response to messages
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          content: data.answer,
          citations: data.citations,
          timestamp: new Date(),
        },
      ])
      setError(null)
    },
    onError: (err: unknown) => {
      const errorMessage = getApiErrorMessage(err)
      setError(errorMessage)

      // Only log safe info in dev mode (prevent information disclosure)
      if (import.meta.env.DEV) {
        console.error('Chat error:', { message: errorMessage })
      }
    },
  })

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, mutation.isPending])

  // Handle send message
  const handleSend = (): void => {
    const trimmedMessage = inputValue.trim()
    if (!trimmedMessage || mutation.isPending) {
      return
    }

    // Add user message to messages
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: trimmedMessage,
        timestamp: new Date(),
      },
    ])

    // Clear input
    setInputValue('')

    // Send message to API
    mutation.mutate({ message: trimmedMessage })
  }

  // Handle form submit
  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    handleSend()
  }

  // Handle Enter key
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '600px',
        width: '100%',
        maxWidth: '800px',
        border: '1px solid #ddd',
        borderRadius: '8px',
        overflow: 'hidden',
        backgroundColor: '#ffffff',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '1rem',
          borderBottom: '1px solid #ddd',
          backgroundColor: '#f8f9fa',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>
          Boston Parking Permit Assistant
        </h2>
        <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: '#666' }}>
          Ask questions about resident parking permits
        </p>
      </div>

      {/* Messages container */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 && !mutation.isPending && (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#999',
              textAlign: 'center',
              padding: '2rem',
            }}
          >
            <div>
              <p style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>
                Welcome! How can I help you today?
              </p>
              <p style={{ fontSize: '0.9rem' }}>
                Ask me anything about Boston resident parking permits.
              </p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}

        {mutation.isPending && <LoadingIndicator />}

        {/* Error message */}
        {error && (
          <div
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: '#fee',
              border: '1px solid #fcc',
              borderRadius: '8px',
              color: '#c00',
              marginBottom: '1rem',
            }}
            role="alert"
          >
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: '1rem',
          borderTop: '1px solid #ddd',
          backgroundColor: '#f8f9fa',
        }}
      >
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question here..."
            disabled={mutation.isPending}
            style={{
              flex: 1,
              padding: '0.75rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '1rem',
              fontFamily: 'inherit',
              resize: 'none',
              minHeight: '60px',
              maxHeight: '120px',
              backgroundColor: mutation.isPending ? '#f5f5f5' : '#ffffff',
              color: mutation.isPending ? '#999' : '#333',
            }}
            aria-label="Message input"
          />
          <button
            type="submit"
            disabled={mutation.isPending || !inputValue.trim()}
            style={{
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              fontWeight: 600,
              color: '#ffffff',
              backgroundColor: mutation.isPending || !inputValue.trim() ? '#ccc' : '#007bff',
              border: 'none',
              borderRadius: '4px',
              cursor: mutation.isPending || !inputValue.trim() ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
            aria-label="Send message"
          >
            {mutation.isPending ? 'Sending...' : 'Send'}
          </button>
        </div>
        <p
          style={{
            margin: '0.5rem 0 0 0',
            fontSize: '0.75rem',
            color: '#999',
          }}
        >
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>

      {/* CSS animation for loading dots */}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          40% {
            opacity: 1;
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  )
}

export default ChatInterface
