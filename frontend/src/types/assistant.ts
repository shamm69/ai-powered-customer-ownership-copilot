export type RoutingIntent =
  | 'stored_vehicle_maintenance'
  | 'service_recommendation'
  | 'support_knowledge'
  | 'experimental_predictive_maintenance'
  | 'human_handoff'
  | 'unsupported'
  | 'clarification_required'

export type OrchestrationOutcome =
  | 'executed'
  | 'context_required'
  | 'not_yet_integrated'
  | 'unsupported'
  | 'clarification_required'

export type OrchestratedCapability =
  | 'stored_vehicle_maintenance'
  | 'service_recommendation'
  | 'support_knowledge'
  | 'human_handoff'
  | 'experimental_predictive_maintenance_comparison'

export type OrchestrationContextField =
  | 'vehicle_id'
  | 'evaluation_date'
  | 'database_session'
  | 'rag_service'
  | 'escalation_service'
  | 'predictive_maintenance_input'
  | 'predictive_comparison_service'

export type MaintenanceStatus = 'not_due' | 'due_soon' | 'overdue'
export type RetrievalSupportStatus = 'supported' | 'unsupported'
export type EscalationReason = 'routed_human_handoff'
export type HandoffStatus = 'created'
export type BinarySignal = 0 | 1
export type ServiceType =
  | 'periodic_maintenance_service'
  | 'pre_trip_inspection'
  | 'tyre_inspection_rotation'
  | 'battery_health_check'
  | 'no_service_required'
export type RecommendationPriority =
  | 'none'
  | 'routine'
  | 'recommended'
  | 'due_soon'
  | 'urgent'

export type MaintenanceSignalRelationship =
  | 'agree_negative'
  | 'agree_positive'
  | 'deterministic_only_positive'
  | 'ml_only_positive'

export interface PredictiveMaintenanceInput {
  vehicle_age_years: number
  current_odometer_km: number
  distance_since_last_scheduled_service_km: number
  months_since_last_scheduled_service: number
  service_interval_km: number
  service_interval_months: number
  average_monthly_driving_km: number
  usage_severity_score: number
}

export interface AssistantQueryRequest {
  message: string
  vehicle_id?: number | null
  /** ISO calendar date in YYYY-MM-DD format. */
  evaluation_date?: string | null
  predictive_maintenance_input?: PredictiveMaintenanceInput | null
}

export interface RoutingDecision {
  intent: RoutingIntent
  normalized_request: string
  matched_intents: RoutingIntent[]
  reason: string
}

/** The authoritative deterministic maintenance result. */
export interface MaintenanceResult {
  status: MaintenanceStatus
  kilometres_travelled_since_last_service: number
  kilometres_remaining: number
  months_remaining: number
  reasons: string[]
}

export interface SupportSource {
  source_id: string
  document_title: string
  section_title: string
  chunk_id: string
}

export interface SupportResult {
  answer: string
  retrieval_status: RetrievalSupportStatus
  sources: SupportSource[]
}

/** A local mock handoff result; it does not represent an external CRM ticket. */
export interface HumanHandoffResult {
  ticket_id: string
  reason: EscalationReason
  request_summary: string
  status: HandoffStatus
}

/** Non-authoritative output from the controlled synthetic-data experiment. */
export interface ExperimentalMaintenanceResult {
  maintenance_needed_within_90_days_prediction: BinarySignal
  positive_class_probability: number
  threshold: number
  experimental: true
  artifact_schema_version: number
}

export interface MaintenanceComparisonSignals {
  deterministic_binary_signal: BinarySignal
  experimental_ml_binary_signal: BinarySignal
  relationship: MaintenanceSignalRelationship
}

/** Side-by-side signals only. There is deliberately no combined/final status. */
export interface PredictiveMaintenanceComparisonResult {
  deterministic: MaintenanceResult
  experimental_ml: ExperimentalMaintenanceResult
  comparison: MaintenanceComparisonSignals
}

export interface ServiceRecommendation {
  service_type: ServiceType
  priority: RecommendationPriority
  reason: string
  supporting_factors: string[]
}

/** Deterministic next-service guidance kept separate from maintenance status. */
export interface ServiceRecommendationResult {
  authoritative_maintenance: MaintenanceResult
  recommendations: ServiceRecommendation[]
}

interface AssistantResponseBase {
  routing_decision: RoutingDecision
  missing_context: OrchestrationContextField[]
  message: string
}

export interface MaintenanceAssistantResponse extends AssistantResponseBase {
  outcome: 'executed'
  invoked_capability: 'stored_vehicle_maintenance'
  maintenance_result: MaintenanceResult
  support_result: null
  escalation_result: null
  experimental_comparison_result: null
  recommendation_result: null
}

export interface RecommendationAssistantResponse extends AssistantResponseBase {
  outcome: 'executed'
  invoked_capability: 'service_recommendation'
  maintenance_result: null
  support_result: null
  escalation_result: null
  experimental_comparison_result: null
  recommendation_result: ServiceRecommendationResult
}

export interface SupportAssistantResponse extends AssistantResponseBase {
  outcome: 'executed'
  invoked_capability: 'support_knowledge'
  maintenance_result: null
  support_result: SupportResult
  escalation_result: null
  experimental_comparison_result: null
  recommendation_result: null
}

export interface HandoffAssistantResponse extends AssistantResponseBase {
  outcome: 'executed'
  invoked_capability: 'human_handoff'
  maintenance_result: null
  support_result: null
  escalation_result: HumanHandoffResult
  experimental_comparison_result: null
  recommendation_result: null
}

export interface ExperimentalComparisonAssistantResponse
  extends AssistantResponseBase {
  outcome: 'executed'
  invoked_capability: 'experimental_predictive_maintenance_comparison'
  maintenance_result: null
  support_result: null
  escalation_result: null
  experimental_comparison_result: PredictiveMaintenanceComparisonResult
  recommendation_result: null
}

export interface UnexecutedAssistantResponse extends AssistantResponseBase {
  outcome: Exclude<OrchestrationOutcome, 'executed'>
  invoked_capability: null
  maintenance_result: null
  support_result: null
  escalation_result: null
  experimental_comparison_result: null
  recommendation_result: null
}

export type AssistantQueryResponse =
  | MaintenanceAssistantResponse
  | RecommendationAssistantResponse
  | SupportAssistantResponse
  | HandoffAssistantResponse
  | ExperimentalComparisonAssistantResponse
  | UnexecutedAssistantResponse
