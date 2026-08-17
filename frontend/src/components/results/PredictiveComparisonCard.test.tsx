import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PredictiveMaintenanceComparisonResult } from '../../types/assistant'
import { PredictiveComparisonCard } from './PredictiveComparisonCard'

const comparisonResult: PredictiveMaintenanceComparisonResult = {
  deterministic: {
    status: 'due_soon',
    kilometres_travelled_since_last_service: 8_100,
    kilometres_remaining: 1_900,
    months_remaining: 2,
    reasons: ['Distance interval is approaching its service threshold.'],
  },
  experimental_ml: {
    maintenance_needed_within_90_days_prediction: 1,
    positive_class_probability: 0.742,
    threshold: 0.19,
    experimental: true,
    artifact_schema_version: 1,
  },
  comparison: {
    deterministic_binary_signal: 1,
    experimental_ml_binary_signal: 1,
    relationship: 'agree_positive',
  },
}

describe('PredictiveComparisonCard', () => {
  it('keeps authoritative maintenance and the experiment visibly separate', () => {
    render(<PredictiveComparisonCard result={comparisonResult} />)

    expect(
      screen.getByLabelText('Experimental predictive maintenance comparison'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Experimental model output')).toHaveTextContent(
      'Experimental',
    )
    expect(screen.getByRole('heading', { name: 'Scheduled maintenance' })).toBeInTheDocument()
    expect(
      screen.getByLabelText('Authoritative scheduled maintenance result'),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Due Soon' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '90-day ML signal' })).toBeInTheDocument()
  })

  it('renders the exact experimental probability, threshold, signals, and metadata', () => {
    render(<PredictiveComparisonCard result={comparisonResult} />)

    expect(screen.getByText('Positive (1)')).toBeInTheDocument()
    expect(screen.getByText('74.2%')).toBeInTheDocument()
    expect(screen.getByText('19%')).toBeInTheDocument()
    expect(screen.getByText('Artifact schema v1')).toBeInTheDocument()
    expect(screen.getByText('Both comparison signals are positive')).toBeInTheDocument()
    expect(screen.getByText('Deterministic signal 1 · ML signal 1')).toBeInTheDocument()
  })

  it('states the failed gate, synthetic limitation, and non-override rule', () => {
    render(<PredictiveComparisonCard result={comparisonResult} />)

    expect(
      screen.getByText(/synthetic-data model did not meet the predefined/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/does not override the authoritative deterministic service status/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/final prediction/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/combined status/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/recommended status/i)).not.toBeInTheDocument()
  })
})
