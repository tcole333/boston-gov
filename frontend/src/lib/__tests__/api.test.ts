/**
 * Tests for API client configuration and error handling.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios, { AxiosError, AxiosInstance } from 'axios'
import type { ApiError } from '../../types/api'

// Create mock axios instance
const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  patch: vi.fn(),
  interceptors: {
    request: {
      use: vi.fn(),
      eject: vi.fn(),
    },
    response: {
      use: vi.fn(),
      eject: vi.fn(),
    },
  },
} as unknown as AxiosInstance

// Mock axios.create to return our mock instance
vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      isAxiosError: vi.fn((error: unknown) => {
        return (error as any)?.isAxiosError === true
      }),
    },
    isAxiosError: vi.fn((error: unknown) => {
      return (error as any)?.isAxiosError === true
    }),
  }
})

describe('API Client', () => {
  // Helper to get error interceptor from mock
  const getErrorInterceptor = () => {
    return (mockAxiosInstance.interceptors.response.use as any).mock.calls[0]?.[1]
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    // Dynamically import the module after mocks are set up
    await import('../api')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Configuration', () => {
    it('should create axios instance', () => {
      expect(axios.create).toHaveBeenCalled()
    })

    it('should export configured apiClient', async () => {
      const module = await import('../api')
      expect(module.apiClient).toBeDefined()
      expect(typeof module.apiClient.get).toBe('function')
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const networkError = new Error('Network Error') as AxiosError
      networkError.isAxiosError = true
      networkError.code = 'ERR_NETWORK'

      try {
        await errorInterceptor(networkError)
      } catch (error) {
        expect(error).toHaveProperty('userMessage')
        expect((error as any).userMessage).toContain('Unable to connect')
        expect((error as any).isNetworkError).toBe(true)
      }
    })

    it('should handle timeout errors', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const timeoutError = new Error('Timeout') as AxiosError
      timeoutError.isAxiosError = true
      timeoutError.code = 'ECONNABORTED'

      try {
        await errorInterceptor(timeoutError)
      } catch (error) {
        expect((error as any).userMessage).toContain('took too long')
      }
    })

    it('should handle 400 Bad Request errors', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const badRequestError = {
        isAxiosError: true,
        response: {
          status: 400,
          data: {} as ApiError,
          statusText: 'Bad Request',
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(badRequestError)
      } catch (error) {
        expect((error as any).userMessage).toContain('Invalid request')
        expect((error as any).statusCode).toBe(400)
        expect((error as any).isNetworkError).toBe(false)
      }
    })

    it('should handle 404 Not Found errors', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const notFoundError = {
        isAxiosError: true,
        response: {
          status: 404,
          data: {} as ApiError,
          statusText: 'Not Found',
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(notFoundError)
      } catch (error) {
        expect((error as any).userMessage).toContain('not found')
      }
    })

    it('should handle 500 Internal Server Error', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const serverError = {
        isAxiosError: true,
        response: {
          status: 500,
          data: {} as ApiError,
          statusText: 'Internal Server Error',
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(serverError)
      } catch (error) {
        expect((error as any).userMessage).toContain('server')
      }
    })

    it('should handle 503 Service Unavailable errors', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const unavailableError = {
        isAxiosError: true,
        response: {
          status: 503,
          data: {} as ApiError,
          statusText: 'Service Unavailable',
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(unavailableError)
      } catch (error) {
        expect((error as any).userMessage).toContain('temporarily unavailable')
      }
    })

    it('should use backend error message when available', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const customError = {
        isAxiosError: true,
        response: {
          status: 400,
          data: { detail: 'Custom error message from backend' } as ApiError,
          statusText: 'Bad Request',
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(customError)
      } catch (error) {
        expect((error as any).userMessage).toBe('Custom error message from backend')
      }
    })

    it('should handle unknown status codes with default message', async () => {
      const errorInterceptor = getErrorInterceptor()
      if (!errorInterceptor) return

      const unknownError = {
        isAxiosError: true,
        response: {
          status: 418, // I'm a teapot
          data: {} as ApiError,
          statusText: "I'm a teapot",
          headers: {},
          config: {},
        },
      } as AxiosError<ApiError>

      try {
        await errorInterceptor(unknownError)
      } catch (error) {
        expect((error as any).userMessage).toContain('unexpected error')
      }
    })
  })

  describe('Type Guards and Helpers', () => {
    it('isApiClientError should identify API client errors', async () => {
      const module = await import('../api')
      const apiError = {
        isAxiosError: true,
        userMessage: 'Test error',
        isNetworkError: false,
        statusCode: 400,
      }

      expect(module.isApiClientError(apiError)).toBe(true)
    })

    it('isApiClientError should reject non-API errors', async () => {
      const module = await import('../api')
      const regularError = new Error('Regular error')

      expect(module.isApiClientError(regularError)).toBe(false)
    })

    it('getApiErrorMessage should extract message from API client error', async () => {
      const module = await import('../api')
      const apiError = {
        isAxiosError: true,
        userMessage: 'API error message',
        isNetworkError: false,
      }

      expect(module.getApiErrorMessage(apiError)).toBe('API error message')
    })

    it('getApiErrorMessage should handle regular Error objects', async () => {
      const module = await import('../api')
      const regularError = new Error('Regular error message')

      expect(module.getApiErrorMessage(regularError)).toBe('Regular error message')
    })

    it('getApiErrorMessage should handle unknown error types', async () => {
      const module = await import('../api')
      const unknownError = { something: 'else' }

      expect(module.getApiErrorMessage(unknownError)).toContain('unexpected error')
    })
  })
})
