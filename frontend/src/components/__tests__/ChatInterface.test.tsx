import { describe, it, expect, vi, beforeEach, Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom'
import { ChatInterface } from '../ChatInterface'
import * as api from '../../lib/api'
import type { ConversationResponse } from '../../types/api'

// Mock the API client
vi.mock('../../lib/api', () => ({
  apiClient: {
    post: vi.fn(),
  },
  getApiErrorMessage: vi.fn((error: Error) => error.message || 'An error occurred'),
}))

describe('ChatInterface', () => {
  let queryClient: QueryClient
  const mockPost = api.apiClient.post as Mock

  beforeEach(() => {
    // Create a new QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    // Clear all mocks
    vi.clearAllMocks()
  })

  const renderChatInterface = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ChatInterface />
      </QueryClientProvider>
    )
  }

  it('renders the chat interface', () => {
    renderChatInterface()

    expect(screen.getByText('Boston Parking Permit Assistant')).toBeInTheDocument()
    expect(screen.getByText('Ask questions about resident parking permits')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Type your question here...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
  })

  it('displays welcome message when no messages', () => {
    renderChatInterface()

    expect(screen.getByText(/Welcome! How can I help you today\?/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Ask me anything about Boston resident parking permits/i)
    ).toBeInTheDocument()
  })

  it('allows user to type in input field', async () => {
    const user = userEvent.setup()
    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')
    await user.type(input, 'How do I get a parking permit?')

    expect(input).toHaveValue('How do I get a parking permit?')
  })

  it('send button is disabled when input is empty', () => {
    renderChatInterface()

    const sendButton = screen.getByRole('button', { name: /send message/i })
    expect(sendButton).toBeDisabled()
  })

  it('send button is enabled when input has text', async () => {
    const user = userEvent.setup()
    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')
    const sendButton = screen.getByRole('button', { name: /send message/i })

    await user.type(input, 'Test question')

    expect(sendButton).not.toBeDisabled()
  })

  it('sends message when send button is clicked', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'You need to provide proof of residency.',
      citations: [],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')
    const sendButton = screen.getByRole('button', { name: /send message/i })

    await user.type(input, 'How do I get a parking permit?')
    await user.click(sendButton)

    // User message should appear
    expect(screen.getByText('How do I get a parking permit?')).toBeInTheDocument()

    // API should be called
    expect(mockPost).toHaveBeenCalledWith('/chat/message', {
      message: 'How do I get a parking permit?',
    })

    // Agent response should appear
    await waitFor(() => {
      expect(screen.getByText('You need to provide proof of residency.')).toBeInTheDocument()
    })
  })

  it('sends message when Enter key is pressed', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'You need to provide proof of residency.',
      citations: [],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'Test question{Enter}')

    // User message should appear
    expect(screen.getByText('Test question')).toBeInTheDocument()

    // API should be called
    expect(mockPost).toHaveBeenCalledWith('/chat/message', {
      message: 'Test question',
    })
  })

  it('does not send message when Shift+Enter is pressed', async () => {
    const user = userEvent.setup()
    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2')

    // API should not be called
    expect(mockPost).not.toHaveBeenCalled()

    // Input should still have text (with newline)
    expect(input).toHaveValue('Line 1\nLine 2')
  })

  it('clears input after sending message', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'Response',
      citations: [],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'Test question')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    // Input should be cleared
    expect(input).toHaveValue('')
  })

  it('disables input during API call', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'Response',
      citations: [],
      tool_calls_made: [],
    }

    // Delay the response
    mockPost.mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: mockResponse }), 100))
    )

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')
    const sendButton = screen.getByRole('button', { name: /send message/i })

    await user.type(input, 'Test question')
    await user.click(sendButton)

    // Input and button should be disabled during API call
    expect(input).toBeDisabled()
    expect(sendButton).toBeDisabled()
    expect(sendButton).toHaveTextContent('Sending...')

    // Wait for response
    await waitFor(() => {
      expect(input).not.toBeDisabled()
      expect(sendButton).toHaveTextContent('Send')
    })
  })

  it('displays loading indicator during API call', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'Response',
      citations: [],
      tool_calls_made: [],
    }

    // Delay the response
    mockPost.mockImplementationOnce(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: mockResponse }), 100))
    )

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'Test question')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    // Loading indicator should appear (typing dots container)
    const loadingContainer = document.querySelector('[style*="animation"]')
    expect(loadingContainer).toBeInTheDocument()

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText('Response')).toBeInTheDocument()
    })
  })

  it('displays agent response with citations', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'You need proof of residency [1] and a valid ID [2].',
      citations: [
        {
          fact_id: 'fact-1',
          url: 'https://example.com/source1',
          text: 'Proof of residency requirement',
          source_section: 'Section 2.1',
        },
        {
          fact_id: 'fact-2',
          url: 'https://example.com/source2',
          text: 'Valid ID requirement',
          source_section: null,
        },
      ],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'What do I need?')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    // Agent response should appear
    await waitFor(() => {
      expect(screen.getByText(/You need proof of residency/i)).toBeInTheDocument()
    })

    // Citations should be rendered as links
    const citationLinks = screen.getAllByRole('link')
    expect(citationLinks.length).toBeGreaterThan(0)

    // Check if citation URLs are correct
    const sourcesSection = screen.getByText('Sources:')
    expect(sourcesSection).toBeInTheDocument()

    expect(screen.getByText('Proof of residency requirement')).toBeInTheDocument()
    expect(screen.getByText('Valid ID requirement')).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup()
    const mockError = new Error('Network error')
    const mockGetApiErrorMessage = api.getApiErrorMessage as Mock

    mockPost.mockRejectedValueOnce(mockError)
    mockGetApiErrorMessage.mockReturnValueOnce('Network error')

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, 'Test question')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    // Error message should appear
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('preserves message history', async () => {
    const user = userEvent.setup()
    const mockResponse1: ConversationResponse = {
      answer: 'First response',
      citations: [],
      tool_calls_made: [],
    }
    const mockResponse2: ConversationResponse = {
      answer: 'Second response',
      citations: [],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse1 })
    mockPost.mockResolvedValueOnce({ data: mockResponse2 })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    // Send first message
    await user.type(input, 'First question')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    await waitFor(() => {
      expect(screen.getByText('First question')).toBeInTheDocument()
      expect(screen.getByText('First response')).toBeInTheDocument()
    })

    // Send second message
    await user.type(input, 'Second question')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    await waitFor(() => {
      expect(screen.getByText('Second question')).toBeInTheDocument()
      expect(screen.getByText('Second response')).toBeInTheDocument()
    })

    // Both messages should still be visible
    expect(screen.getByText('First question')).toBeInTheDocument()
    expect(screen.getByText('First response')).toBeInTheDocument()
    expect(screen.getByText('Second question')).toBeInTheDocument()
    expect(screen.getByText('Second response')).toBeInTheDocument()
  })

  it('does not send empty messages', async () => {
    const user = userEvent.setup()
    renderChatInterface()

    const sendButton = screen.getByRole('button', { name: /send message/i })

    // Try to send with empty input
    await user.click(sendButton)

    // API should not be called
    expect(mockPost).not.toHaveBeenCalled()
  })

  it('trims whitespace from messages', async () => {
    const user = userEvent.setup()
    const mockResponse: ConversationResponse = {
      answer: 'Response',
      citations: [],
      tool_calls_made: [],
    }

    mockPost.mockResolvedValueOnce({ data: mockResponse })

    renderChatInterface()

    const input = screen.getByPlaceholderText('Type your question here...')

    await user.type(input, '   Test question   ')
    await user.click(screen.getByRole('button', { name: /send message/i }))

    // API should be called with trimmed message
    expect(mockPost).toHaveBeenCalledWith('/chat/message', {
      message: 'Test question',
    })
  })

  it('has accessible labels', () => {
    renderChatInterface()

    expect(screen.getByLabelText('Message input')).toBeInTheDocument()
    expect(screen.getByLabelText('Send message')).toBeInTheDocument()
  })

  it('displays hint about Enter key usage', () => {
    renderChatInterface()

    expect(screen.getByText('Press Enter to send, Shift+Enter for new line')).toBeInTheDocument()
  })

  // SECURITY TESTS

  describe('Security: XSS Protection', () => {
    it('blocks javascript: protocol URLs in citation links', async () => {
      const user = userEvent.setup()
      const mockResponse: ConversationResponse = {
        answer: 'Check this source [1].',
        citations: [
          {
            fact_id: 'fact-1',
            url: 'javascript:alert("XSS")',
            text: 'Malicious source',
            source_section: null,
          },
        ],
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText(/Check this source/i)).toBeInTheDocument()
      })

      // Find the citation link
      const citationLinks = screen.getAllByRole('link')
      const citationLink = citationLinks.find((link) => link.textContent === '[1]')
      expect(citationLink).toBeInTheDocument()

      // URL should be sanitized to '#'
      expect(citationLink).toHaveAttribute('href', '#')
    })

    it('blocks data: protocol URLs in citation links', async () => {
      const user = userEvent.setup()
      const mockResponse: ConversationResponse = {
        answer: 'Check this source [1].',
        citations: [
          {
            fact_id: 'fact-1',
            url: 'data:text/html,<script>alert("XSS")</script>',
            text: 'Malicious source',
            source_section: null,
          },
        ],
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText(/Check this source/i)).toBeInTheDocument()
      })

      // Find the citation link
      const citationLinks = screen.getAllByRole('link')
      const citationLink = citationLinks.find((link) => link.textContent === '[1]')
      expect(citationLink).toBeInTheDocument()

      // URL should be sanitized to '#'
      expect(citationLink).toHaveAttribute('href', '#')
    })

    it('allows https: URLs in citation links', async () => {
      const user = userEvent.setup()
      const mockResponse: ConversationResponse = {
        answer: 'Check this source [1].',
        citations: [
          {
            fact_id: 'fact-1',
            url: 'https://example.com/safe',
            text: 'Safe source',
            source_section: null,
          },
        ],
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText(/Check this source/i)).toBeInTheDocument()
      })

      // Find the citation link
      const citationLinks = screen.getAllByRole('link')
      const citationLink = citationLinks.find((link) => link.textContent === '[1]')
      expect(citationLink).toBeInTheDocument()

      // URL should be preserved
      expect(citationLink).toHaveAttribute('href', 'https://example.com/safe')
    })

    it('blocks unsafe URLs in citation list', async () => {
      const user = userEvent.setup()
      const mockResponse: ConversationResponse = {
        answer: 'Check sources [1] and [2].',
        citations: [
          {
            fact_id: 'fact-1',
            url: 'javascript:alert("XSS")',
            text: 'Malicious source',
            source_section: null,
          },
          {
            fact_id: 'fact-2',
            url: 'https://example.com/safe',
            text: 'Safe source',
            source_section: null,
          },
        ],
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      await waitFor(() => {
        expect(screen.getByText(/Check sources/i)).toBeInTheDocument()
      })

      // Find citation list links
      const sourcesHeading = screen.getByText('Sources:')
      expect(sourcesHeading).toBeInTheDocument()

      const allLinks = screen.getAllByRole('link')
      const maliciousLink = allLinks.find((link) => link.textContent === 'Malicious source')
      const safeLink = allLinks.find((link) => link.textContent === 'Safe source')

      expect(maliciousLink).toHaveAttribute('href', '#')
      expect(safeLink).toHaveAttribute('href', 'https://example.com/safe')
    })
  })

  describe('Security: DoS Protection', () => {
    it('handles excessive citation markers without crashing', async () => {
      const user = userEvent.setup()
      // Generate message with 150 citation markers (exceeds MAX_CITATIONS of 100)
      const excessiveMarkers = Array(150)
        .fill(0)
        .map((_, i) => `[${i + 1}]`)
        .join('')
      const mockResponse: ConversationResponse = {
        answer: `Text with excessive citations ${excessiveMarkers}`,
        citations: Array(150)
          .fill(0)
          .map((_, i) => ({
            fact_id: `fact-${i + 1}`,
            url: `https://example.com/${i + 1}`,
            text: `Source ${i + 1}`,
            source_section: null,
          })),
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      // Should render without crashing
      await waitFor(() => {
        expect(screen.getByText(/Text with excessive citations/i)).toBeInTheDocument()
      })

      // Component should still be functional
      expect(input).toBeInTheDocument()
    })

    it('validates citation index range', async () => {
      const user = userEvent.setup()
      const mockResponse: ConversationResponse = {
        answer: 'Text with invalid citation [9999] and valid citation [1].',
        citations: [
          {
            fact_id: 'fact-1',
            url: 'https://example.com/valid',
            text: 'Valid source',
            source_section: null,
          },
        ],
        tool_calls_made: [],
      }

      mockPost.mockResolvedValueOnce({ data: mockResponse })

      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Test question')
      await user.click(screen.getByRole('button', { name: /send message/i }))

      // Wait for response to appear
      await waitFor(() => {
        expect(screen.getByText('Test question')).toBeInTheDocument()
      })

      // Check that the invalid marker [9999] is present as text (not a link)
      const messageContent = screen.getByText(/\[9999\]/)
      expect(messageContent).toBeInTheDocument()

      // Valid citation should be a link
      const citationLinks = screen.getAllByRole('link')
      const validLink = citationLinks.find((link) => link.textContent === '[1]')
      expect(validLink).toBeInTheDocument()
      expect(validLink).toHaveAttribute('href', 'https://example.com/valid')
    })
  })

  describe('UX: Message Length Limit', () => {
    it('displays character counter', () => {
      renderChatInterface()

      expect(screen.getByText('0 / 2000')).toBeInTheDocument()
    })

    it('updates character counter as user types', async () => {
      const user = userEvent.setup()
      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      await user.type(input, 'Hello world')

      expect(screen.getByText('11 / 2000')).toBeInTheDocument()
    })

    it('prevents input beyond max length', async () => {
      const user = userEvent.setup()
      renderChatInterface()

      const input = screen.getByPlaceholderText('Type your question here...')
      const longText = 'a'.repeat(2100) // Exceeds 2000 limit

      await user.type(input, longText)

      // Input should be capped at 2000 characters
      expect(input).toHaveValue('a'.repeat(2000))
      expect(screen.getByText('2000 / 2000')).toBeInTheDocument()
    })
  })
})
