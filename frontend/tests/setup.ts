import { expect, afterEach, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

// Cleanup after each test case
afterEach(() => {
  cleanup()
})

// Mock scrollIntoView (not implemented in jsdom)
beforeAll(() => {
  Element.prototype.scrollIntoView = () => {}
})

// Extend Vitest's expect with jest-dom matchers
expect.extend({})
