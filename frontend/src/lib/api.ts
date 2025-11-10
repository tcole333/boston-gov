/**
 * API client configuration with axios and interceptors.
 *
 * This module provides:
 * - Configured axios instance with base URL from environment
 * - Request interceptors for headers and logging
 * - Response interceptors for error handling
 * - User-friendly error messages
 *
 * Usage:
 * ```typescript
 * import { apiClient } from '@/lib/api'
 *
 * const response = await apiClient.get<Process[]>('/processes')
 * ```
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import type { ApiError } from '../types/api'

/**
 * Get the API base URL from environment variables with fallback.
 */
const getApiBaseUrl = (): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  if (!baseUrl) {
    console.warn(
      'VITE_API_BASE_URL not set in environment. Using default: http://localhost:8000/api'
    )
    return 'http://localhost:8000/api'
  }
  return baseUrl
}

/**
 * User-friendly error messages for common API errors.
 */
const ERROR_MESSAGES: Record<string, string> = {
  NETWORK_ERROR: 'Unable to connect to the server. Please check your internet connection.',
  TIMEOUT_ERROR: 'The request took too long. Please try again.',
  BAD_REQUEST: 'Invalid request. Please check your input and try again.',
  UNAUTHORIZED: 'Authentication required. Please log in.',
  FORBIDDEN: 'You do not have permission to access this resource.',
  NOT_FOUND: 'The requested resource was not found.',
  CONFLICT: 'A conflict occurred. The resource may have been modified.',
  UNPROCESSABLE_ENTITY: 'The request could not be processed. Please check your input.',
  INTERNAL_SERVER_ERROR: 'An error occurred on the server. Please try again later.',
  SERVICE_UNAVAILABLE: 'The service is temporarily unavailable. Please try again later.',
  DEFAULT: 'An unexpected error occurred. Please try again.',
}

/**
 * Extract user-friendly error message from API error.
 */
const getErrorMessage = (error: AxiosError<ApiError>): string => {
  // Network or timeout errors
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return ERROR_MESSAGES.TIMEOUT_ERROR as string
    }
    return ERROR_MESSAGES.NETWORK_ERROR as string
  }

  // Use backend error message if available
  if (error.response.data?.detail) {
    return error.response.data.detail
  }

  // Fallback to status code messages
  const { status } = error.response
  switch (status) {
    case 400:
      return ERROR_MESSAGES.BAD_REQUEST as string
    case 401:
      return ERROR_MESSAGES.UNAUTHORIZED as string
    case 403:
      return ERROR_MESSAGES.FORBIDDEN as string
    case 404:
      return ERROR_MESSAGES.NOT_FOUND as string
    case 409:
      return ERROR_MESSAGES.CONFLICT as string
    case 422:
      return ERROR_MESSAGES.UNPROCESSABLE_ENTITY as string
    case 500:
      return ERROR_MESSAGES.INTERNAL_SERVER_ERROR as string
    case 503:
      return ERROR_MESSAGES.SERVICE_UNAVAILABLE as string
    default:
      return ERROR_MESSAGES.DEFAULT as string
  }
}

/**
 * Create and configure axios instance.
 */
const createApiClient = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: getApiBaseUrl(),
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
    },
  })

  /**
   * Request interceptor - Add headers and log requests in development.
   */
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Log request in development
      if (import.meta.env.DEV) {
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`)
      }

      // Add any additional headers here (e.g., auth tokens)
      // config.headers['Authorization'] = `Bearer ${token}`

      return config
    },
    (error: AxiosError) => {
      console.error('[API Request Error]', error)
      return Promise.reject(error)
    }
  )

  /**
   * Response interceptor - Extract data and handle errors.
   */
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log response in development
      if (import.meta.env.DEV) {
        console.log(
          `[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`,
          {
            status: response.status,
            data: response.data,
          }
        )
      }

      return response
    },
    (error: AxiosError<ApiError>) => {
      // Log error in development
      if (import.meta.env.DEV) {
        console.error('[API Response Error]', {
          url: error.config?.url,
          status: error.response?.status,
          message: getErrorMessage(error),
        })
      }

      // Transform error to include user-friendly message
      const userMessage = getErrorMessage(error)

      // Create enhanced error object
      const enhancedError = Object.assign(error, {
        userMessage,
        isNetworkError: !error.response,
        statusCode: error.response?.status,
      })

      return Promise.reject(enhancedError)
    }
  )

  return instance
}

/**
 * Configured axios instance for API requests.
 *
 * Use this instance for all API calls. It includes:
 * - Base URL from environment
 * - Request/response interceptors
 * - Error handling with user-friendly messages
 * - Logging in development mode
 */
export const apiClient = createApiClient()

/**
 * Enhanced Axios error with user-friendly message.
 */
export interface ApiClientError extends AxiosError<ApiError> {
  userMessage: string
  isNetworkError: boolean
  statusCode?: number
}

/**
 * Type guard to check if error is an API client error.
 */
export const isApiClientError = (error: unknown): error is ApiClientError => {
  return axios.isAxiosError(error) && 'userMessage' in error && 'isNetworkError' in error
}

/**
 * Helper to get error message from any error type.
 */
export const getApiErrorMessage = (error: unknown): string => {
  if (isApiClientError(error)) {
    return error.userMessage
  }
  if (error instanceof Error) {
    return error.message
  }
  return ERROR_MESSAGES.DEFAULT as string
}
