import { postJson } from './client'
import type {
  AssistantQueryRequest,
  AssistantQueryResponse,
  BinarySignal,
  EscalationReason,
  HandoffStatus,
  HumanHandoffResult,
  MaintenanceSignalRelationship,
  MaintenanceStatus,
  MaintenanceResult,
  OrchestratedCapability,
  OrchestrationContextField,
  OrchestrationOutcome,
  PredictiveMaintenanceComparisonResult,
  RecommendationPriority,
  RetrievalSupportStatus,
  RoutingDecision,
  RoutingIntent,
  SupportResult,
  ServiceRecommendationResult,
  ServiceType,
} from '../types/assistant'

const routingIntents = [
  'stored_vehicle_maintenance',
  'service_recommendation',
  'support_knowledge',
  'experimental_predictive_maintenance',
  'human_handoff',
  'unsupported',
  'clarification_required',
] as const satisfies readonly RoutingIntent[]

const orchestrationOutcomes = [
  'executed',
  'context_required',
  'not_yet_integrated',
  'unsupported',
  'clarification_required',
] as const satisfies readonly OrchestrationOutcome[]

const capabilities = [
  'stored_vehicle_maintenance',
  'service_recommendation',
  'support_knowledge',
  'human_handoff',
  'experimental_predictive_maintenance_comparison',
] as const satisfies readonly OrchestratedCapability[]

const contextFields = [
  'vehicle_id',
  'evaluation_date',
  'database_session',
  'rag_service',
  'escalation_service',
  'predictive_maintenance_input',
  'predictive_comparison_service',
] as const satisfies readonly OrchestrationContextField[]

const maintenanceStatuses = [
  'not_due',
  'due_soon',
  'overdue',
] as const satisfies readonly MaintenanceStatus[]

const retrievalStatuses = [
  'supported',
  'unsupported',
] as const satisfies readonly RetrievalSupportStatus[]

const escalationReasons = [
  'routed_human_handoff',
] as const satisfies readonly EscalationReason[]

const handoffStatuses = ['created'] as const satisfies readonly HandoffStatus[]

const signalRelationships = [
  'agree_negative',
  'agree_positive',
  'deterministic_only_positive',
  'ml_only_positive',
] as const satisfies readonly MaintenanceSignalRelationship[]

const serviceTypes = [
  'periodic_maintenance_service',
  'pre_trip_inspection',
  'tyre_inspection_rotation',
  'battery_health_check',
  'no_service_required',
] as const satisfies readonly ServiceType[]

const recommendationPriorities = [
  'none',
  'routine',
  'recommended',
  'due_soon',
  'urgent',
] as const satisfies readonly RecommendationPriority[]

export function queryAssistant(
  request: AssistantQueryRequest,
): Promise<AssistantQueryResponse> {
  return postJson('/assistant/query', request, parseAssistantQueryResponse)
}

export function parseAssistantQueryResponse(
  payload: unknown,
): AssistantQueryResponse {
  if (!isRecord(payload) || !hasValidBaseFields(payload)) {
    throw new TypeError('Assistant response base fields are invalid')
  }

  const capability = payload.invoked_capability
  if (payload.outcome !== 'executed') {
    if (
      capability !== null ||
      payload.maintenance_result !== null ||
      payload.support_result !== null ||
      payload.escalation_result !== null ||
      payload.experimental_comparison_result !== null ||
      payload.recommendation_result !== null
    ) {
      throw new TypeError('Unexecuted response must not contain a capability result')
    }
    return {
      routing_decision: payload.routing_decision,
      outcome: payload.outcome,
      invoked_capability: null,
      missing_context: payload.missing_context,
      message: payload.message,
      maintenance_result: null,
      support_result: null,
      escalation_result: null,
      experimental_comparison_result: null,
      recommendation_result: null,
    }
  }

  if (!isOneOf(capability, capabilities)) {
    throw new TypeError('Executed response capability is invalid')
  }
  const base = {
    routing_decision: payload.routing_decision,
    outcome: 'executed' as const,
    missing_context: payload.missing_context,
    message: payload.message,
  }
  if (
    capability === 'stored_vehicle_maintenance' &&
    isMaintenanceResult(payload.maintenance_result) &&
    payload.support_result === null &&
    payload.escalation_result === null &&
    payload.experimental_comparison_result === null &&
    payload.recommendation_result === null
  ) {
    return {
      ...base,
      invoked_capability: capability,
      maintenance_result: payload.maintenance_result,
      support_result: null,
      escalation_result: null,
      experimental_comparison_result: null,
      recommendation_result: null,
    }
  }
  if (
    capability === 'service_recommendation' &&
    payload.maintenance_result === null &&
    payload.support_result === null &&
    payload.escalation_result === null &&
    payload.experimental_comparison_result === null &&
    isServiceRecommendationResult(payload.recommendation_result)
  ) {
    return {
      ...base,
      invoked_capability: capability,
      maintenance_result: null,
      support_result: null,
      escalation_result: null,
      experimental_comparison_result: null,
      recommendation_result: payload.recommendation_result,
    }
  }
  if (
    capability === 'support_knowledge' &&
    payload.maintenance_result === null &&
    isSupportResult(payload.support_result) &&
    payload.escalation_result === null &&
    payload.experimental_comparison_result === null &&
    payload.recommendation_result === null
  ) {
    return {
      ...base,
      invoked_capability: capability,
      maintenance_result: null,
      support_result: payload.support_result,
      escalation_result: null,
      experimental_comparison_result: null,
      recommendation_result: null,
    }
  }
  if (
    capability === 'human_handoff' &&
    payload.maintenance_result === null &&
    payload.support_result === null &&
    isHandoffResult(payload.escalation_result) &&
    payload.experimental_comparison_result === null &&
    payload.recommendation_result === null
  ) {
    return {
      ...base,
      invoked_capability: capability,
      maintenance_result: null,
      support_result: null,
      escalation_result: payload.escalation_result,
      experimental_comparison_result: null,
      recommendation_result: null,
    }
  }
  if (
    capability === 'experimental_predictive_maintenance_comparison' &&
    payload.maintenance_result === null &&
    payload.support_result === null &&
    payload.escalation_result === null &&
    isPredictiveComparisonResult(payload.experimental_comparison_result) &&
    payload.recommendation_result === null
  ) {
    return {
      ...base,
      invoked_capability: capability,
      maintenance_result: null,
      support_result: null,
      escalation_result: null,
      experimental_comparison_result: payload.experimental_comparison_result,
      recommendation_result: null,
    }
  }
  throw new TypeError('Executed response capability result is inconsistent')
}

type AssistantResponseWire = Record<string, unknown> & {
  routing_decision: RoutingDecision
  outcome: OrchestrationOutcome
  invoked_capability: OrchestratedCapability | null
  missing_context: OrchestrationContextField[]
  message: string
  maintenance_result: unknown
  support_result: unknown
  escalation_result: unknown
  experimental_comparison_result: unknown
  recommendation_result: unknown
}

function hasValidBaseFields(
  value: Record<string, unknown>,
): value is AssistantResponseWire {
  return (
    isRoutingDecision(value.routing_decision) &&
    isOneOf(value.outcome, orchestrationOutcomes) &&
    (value.invoked_capability === null ||
      isOneOf(value.invoked_capability, capabilities)) &&
    isArrayOf(value.missing_context, (item) => isOneOf(item, contextFields)) &&
    typeof value.message === 'string' &&
    'maintenance_result' in value &&
    'support_result' in value &&
    'escalation_result' in value &&
    'experimental_comparison_result' in value &&
    'recommendation_result' in value
  )
}

function isRoutingDecision(value: unknown): value is RoutingDecision {
  return (
    isRecord(value) &&
    isOneOf(value.intent, routingIntents) &&
    typeof value.normalized_request === 'string' &&
    isArrayOf(value.matched_intents, (item) => isOneOf(item, routingIntents)) &&
    typeof value.reason === 'string'
  )
}

function isMaintenanceResult(value: unknown): value is MaintenanceResult {
  return (
    isRecord(value) &&
    isOneOf(value.status, maintenanceStatuses) &&
    isFiniteNumber(value.kilometres_travelled_since_last_service) &&
    isFiniteNumber(value.kilometres_remaining) &&
    isFiniteNumber(value.months_remaining) &&
    isArrayOf(value.reasons, isString)
  )
}

function isSupportResult(value: unknown): value is SupportResult {
  return (
    isRecord(value) &&
    typeof value.answer === 'string' &&
    isOneOf(value.retrieval_status, retrievalStatuses) &&
    isArrayOf(value.sources, isSupportSource)
  )
}

function isSupportSource(
  value: unknown,
): value is SupportResult['sources'][number] {
  return (
    isRecord(value) &&
    typeof value.source_id === 'string' &&
    typeof value.document_title === 'string' &&
    typeof value.section_title === 'string' &&
    typeof value.chunk_id === 'string'
  )
}

function isHandoffResult(value: unknown): value is HumanHandoffResult {
  return (
    isRecord(value) &&
    typeof value.ticket_id === 'string' &&
    isOneOf(value.reason, escalationReasons) &&
    typeof value.request_summary === 'string' &&
    isOneOf(value.status, handoffStatuses)
  )
}

function isPredictiveComparisonResult(
  value: unknown,
): value is PredictiveMaintenanceComparisonResult {
  if (!isRecord(value)) {
    return false
  }
  const experimental = value.experimental_ml
  const comparison = value.comparison
  return (
    isMaintenanceResult(value.deterministic) &&
    isRecord(experimental) &&
    isBinarySignal(experimental.maintenance_needed_within_90_days_prediction) &&
    isFiniteNumber(experimental.positive_class_probability) &&
    isFiniteNumber(experimental.threshold) &&
    experimental.experimental === true &&
    Number.isInteger(experimental.artifact_schema_version) &&
    isRecord(comparison) &&
    isBinarySignal(comparison.deterministic_binary_signal) &&
    isBinarySignal(comparison.experimental_ml_binary_signal) &&
    isOneOf(comparison.relationship, signalRelationships)
  )
}

function isServiceRecommendationResult(
  value: unknown,
): value is ServiceRecommendationResult {
  return (
    isRecord(value) &&
    isMaintenanceResult(value.authoritative_maintenance) &&
    isArrayOf(
      value.recommendations,
      (
        recommendation,
      ): recommendation is ServiceRecommendationResult['recommendations'][number] =>
        isRecord(recommendation) &&
        isOneOf(recommendation.service_type, serviceTypes) &&
        isOneOf(recommendation.priority, recommendationPriorities) &&
        typeof recommendation.reason === 'string' &&
        isArrayOf(recommendation.supporting_factors, isString),
    )
  )
}

function isBinarySignal(value: unknown): value is BinarySignal {
  return value === 0 || value === 1
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isArrayOf<T>(
  value: unknown,
  predicate: (item: unknown) => item is T,
): value is T[] {
  return Array.isArray(value) && value.every(predicate)
}

function isString(value: unknown): value is string {
  return typeof value === 'string'
}

function isOneOf<T extends string>(
  value: unknown,
  allowedValues: readonly T[],
): value is T {
  return typeof value === 'string' && allowedValues.includes(value as T)
}
