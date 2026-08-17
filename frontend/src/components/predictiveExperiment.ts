import type { PredictiveMaintenanceInput } from '../types/assistant'

export type PredictiveExperimentDraft = {
  [Field in keyof PredictiveMaintenanceInput]: string
}

export type PredictiveField = keyof PredictiveMaintenanceInput

interface PredictiveFieldConfig {
  key: PredictiveField
  label: string
  min: number
  max?: number
  exclusiveMin?: boolean
}

export const predictiveFields: PredictiveFieldConfig[] = [
  { key: 'vehicle_age_years', label: 'Vehicle age (years)', min: 0, exclusiveMin: true },
  { key: 'current_odometer_km', label: 'Current odometer (km)', min: 0 },
  {
    key: 'distance_since_last_scheduled_service_km',
    label: 'Distance since last scheduled service (km)',
    min: 0,
  },
  {
    key: 'months_since_last_scheduled_service',
    label: 'Months since last scheduled service',
    min: 0,
  },
  { key: 'service_interval_km', label: 'Service interval (km)', min: 0, exclusiveMin: true },
  {
    key: 'service_interval_months',
    label: 'Service interval (months)',
    min: 0,
    exclusiveMin: true,
  },
  {
    key: 'average_monthly_driving_km',
    label: 'Average monthly driving (km)',
    min: 0,
    exclusiveMin: true,
  },
  { key: 'usage_severity_score', label: 'Usage severity score (0–1)', min: 0, max: 1 },
]

export function createEmptyPredictiveExperimentDraft(): PredictiveExperimentDraft {
  return {
    vehicle_age_years: '',
    current_odometer_km: '',
    distance_since_last_scheduled_service_km: '',
    months_since_last_scheduled_service: '',
    service_interval_km: '',
    service_interval_months: '',
    average_monthly_driving_km: '',
    usage_severity_score: '',
  }
}

export function parsePredictiveExperimentDraft(
  draft: PredictiveExperimentDraft,
): PredictiveMaintenanceInput | null {
  if (Object.keys(validatePredictiveExperimentDraft(draft)).length > 0) {
    return null
  }

  return {
    vehicle_age_years: Number(draft.vehicle_age_years),
    current_odometer_km: Number(draft.current_odometer_km),
    distance_since_last_scheduled_service_km: Number(
      draft.distance_since_last_scheduled_service_km,
    ),
    months_since_last_scheduled_service: Number(
      draft.months_since_last_scheduled_service,
    ),
    service_interval_km: Number(draft.service_interval_km),
    service_interval_months: Number(draft.service_interval_months),
    average_monthly_driving_km: Number(draft.average_monthly_driving_km),
    usage_severity_score: Number(draft.usage_severity_score),
  }
}

export function validatePredictiveExperimentDraft(
  draft: PredictiveExperimentDraft,
): Partial<Record<PredictiveField, string>> {
  const errors: Partial<Record<PredictiveField, string>> = {}

  for (const field of predictiveFields) {
    const rawValue = draft[field.key].trim()
    const value = Number(rawValue)
    if (!rawValue) {
      errors[field.key] = 'Required'
    } else if (!Number.isFinite(value)) {
      errors[field.key] = 'Enter a finite number'
    } else if (field.exclusiveMin && value <= field.min) {
      errors[field.key] = 'Enter a value greater than zero'
    } else if (value < field.min) {
      errors[field.key] = `Enter ${field.min} or greater`
    } else if (field.max !== undefined && value > field.max) {
      errors[field.key] = `Enter a value from ${field.min} to ${field.max}`
    }
  }

  const odometer = Number(draft.current_odometer_km)
  const distanceSinceService = Number(draft.distance_since_last_scheduled_service_km)
  if (
    !errors.current_odometer_km &&
    !errors.distance_since_last_scheduled_service_km &&
    distanceSinceService > odometer
  ) {
    errors.distance_since_last_scheduled_service_km =
      'Distance since service cannot exceed the current odometer'
  }

  return errors
}
