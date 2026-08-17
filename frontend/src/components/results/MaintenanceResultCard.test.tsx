import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { MaintenanceResult, MaintenanceStatus } from '../../types/assistant'
import { MaintenanceResultCard } from './MaintenanceResultCard'

const baseResult: MaintenanceResult = {
  status: 'not_due',
  kilometres_travelled_since_last_service: 2_500,
  kilometres_remaining: 7_500,
  months_remaining: 8,
  reasons: ['Distance and time intervals remain below their service thresholds.'],
}

describe('MaintenanceResultCard', () => {
  it.each([
    ['not_due', 'Not Due', 'positive'],
    ['due_soon', 'Due Soon', 'attention'],
    ['overdue', 'Overdue', 'critical'],
  ] satisfies [MaintenanceStatus, string, string][]) (
    'renders %s with its human-readable status and semantic tone',
    (status, label, tone) => {
      render(<MaintenanceResultCard result={{ ...baseResult, status }} />)

      expect(screen.getByRole('heading', { name: label })).toBeInTheDocument()
      expect(
        screen.getByLabelText('Authoritative scheduled maintenance result'),
      ).toHaveClass(`maintenance-result-card--${tone}`)
    },
  )

  it('renders the exact backend reasons and service metrics', () => {
    render(
      <MaintenanceResultCard
        result={{
          ...baseResult,
          kilometres_travelled_since_last_service: 8_250.5,
          kilometres_remaining: 1_749.5,
          months_remaining: 1,
          reasons: [
            'Distance interval is approaching its service threshold.',
            'Time interval remains below its service threshold.',
          ],
        }}
      />,
    )

    expect(screen.getByText('8,250.5 km')).toBeInTheDocument()
    expect(screen.getByText('1,749.5 km')).toBeInTheDocument()
    expect(screen.getByText('1 month')).toBeInTheDocument()
    expect(
      screen.getByText('Distance interval is approaching its service threshold.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Time interval remains below its service threshold.'),
    ).toBeInTheDocument()
  })
})
