import { describe, expect, it } from 'vitest'
import {
  createEmptyPredictiveExperimentDraft,
  parsePredictiveExperimentDraft,
  type PredictiveExperimentDraft,
} from './predictiveExperiment'

const validDraft: PredictiveExperimentDraft = {
  vehicle_age_years: '6.5',
  current_odometer_km: '72000',
  distance_since_last_scheduled_service_km: '7500',
  months_since_last_scheduled_service: '8',
  service_interval_km: '10000',
  service_interval_months: '12',
  average_monthly_driving_km: '1100',
  usage_severity_score: '0.65',
}

describe('predictive experiment state', () => {
  it('starts with no hidden or prefilled values', () => {
    expect(Object.values(createEmptyPredictiveExperimentDraft())).toEqual(
      Array.from({ length: 8 }, () => ''),
    )
  })

  it('preserves all eight entered numeric values in API order and shape', () => {
    expect(parsePredictiveExperimentDraft(validDraft)).toEqual({
      vehicle_age_years: 6.5,
      current_odometer_km: 72_000,
      distance_since_last_scheduled_service_km: 7_500,
      months_since_last_scheduled_service: 8,
      service_interval_km: 10_000,
      service_interval_months: 12,
      average_monthly_driving_km: 1_100,
      usage_severity_score: 0.65,
    })
  })

  it('rejects incomplete, out-of-range, and inconsistent inputs', () => {
    expect(parsePredictiveExperimentDraft(createEmptyPredictiveExperimentDraft())).toBeNull()
    expect(
      parsePredictiveExperimentDraft({ ...validDraft, usage_severity_score: '1.1' }),
    ).toBeNull()
    expect(
      parsePredictiveExperimentDraft({
        ...validDraft,
        current_odometer_km: '5000',
        distance_since_last_scheduled_service_km: '7500',
      }),
    ).toBeNull()
  })
})
