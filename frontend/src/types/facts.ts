/**
 * TypeScript types for Facts Registry.
 *
 * These types mirror the Pydantic schemas from backend/src/schemas/facts.py.
 * The Facts Registry is the citation system that ensures all regulatory claims
 * are traceable to official sources.
 */

import { ConfidenceLevel } from './graph'

/**
 * Individual regulatory fact with citation metadata.
 *
 * Every fact in the registry must be traceable to an official source and include
 * verification information. Facts are the atomic units of regulatory knowledge.
 *
 * Example:
 * ```typescript
 * const fact: Fact = {
 *   id: "rpp.proof_of_residency.recency",
 *   text: "Proof of residency must be dated within 30 days",
 *   source_url: "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
 *   source_section: "Proof of Boston residency",
 *   last_verified: "2025-11-09",
 *   confidence: ConfidenceLevel.HIGH
 * }
 * ```
 */
export interface Fact {
  /** Unique hierarchical identifier (e.g., "rpp.eligibility.vehicle_class") */
  id: string
  /** Human-readable regulatory claim (the actual fact) */
  text: string
  /** URL to official source document (regulation, webpage, PDF) */
  source_url: string
  /** Section/page reference within the source (optional) */
  source_section: string | null
  /** Date when this fact was last verified against the source (YYYY-MM-DD) */
  last_verified: string
  /** Confidence level in this fact's accuracy */
  confidence: ConfidenceLevel
  /** Additional context or caveats (optional) */
  note: string | null
}

/**
 * Root container for all facts in a Facts Registry YAML file.
 *
 * The Facts Registry maintains a versioned, auditable collection of regulatory facts.
 * Each registry file typically corresponds to one government process (e.g., Boston RPP).
 *
 * Example:
 * ```typescript
 * const registry: FactsRegistry = {
 *   version: "1.0.0",
 *   last_updated: "2025-11-09",
 *   scope: "boston_resident_parking_permit",
 *   facts: [
 *     {
 *       id: "rpp.eligibility.vehicle_class",
 *       text: "Only Class 1 and Class 2 vehicles are eligible",
 *       source_url: "https://www.boston.gov/...",
 *       source_section: null,
 *       last_verified: "2025-11-09",
 *       confidence: ConfidenceLevel.HIGH,
 *       note: null
 *     }
 *   ]
 * }
 * ```
 */
export interface FactsRegistry {
  /** Semantic version of this registry (e.g., "1.0.0") */
  version: string
  /** Date when this registry was last updated (YYYY-MM-DD) */
  last_updated: string
  /** Scope identifier for this registry (e.g., "boston_resident_parking_permit") */
  scope: string
  /** List of regulatory facts */
  facts: Fact[]
}
