import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ServiceRecommendationCard } from './ServiceRecommendationCard'

describe('ServiceRecommendationCard', () => {
  it('keeps authoritative status separate from ordered service guidance', () => {
    render(
      <ServiceRecommendationCard
        result={{
          authoritative_maintenance: {
            status: 'due_soon',
            kilometres_travelled_since_last_service: 8_500,
            kilometres_remaining: 1_500,
            months_remaining: 2,
            reasons: ['Scheduled maintenance is due soon.'],
          },
          recommendations: [
            {
              service_type: 'periodic_maintenance_service',
              priority: 'due_soon',
              reason: 'The authoritative maintenance evaluation is due soon.',
              supporting_factors: ['Distance threshold was reached.'],
            },
            {
              service_type: 'tyre_inspection_rotation',
              priority: 'routine',
              reason: 'A routine tyre inspection can be considered.',
              supporting_factors: ['8,500 km since scheduled service.'],
            },
          ],
        }}
      />,
    )

    const card = screen.getByLabelText('Deterministic service recommendations')
    expect(within(card).getByText('Authoritative scheduled status')).toBeInTheDocument()
    expect(within(card).getByText('Due Soon')).toBeInTheDocument()
    expect(within(card).getByRole('heading', { name: 'Periodic Maintenance Service' })).toBeInTheDocument()
    expect(within(card).getByRole('heading', { name: 'Tyre Inspection / Rotation' })).toBeInTheDocument()
    expect(within(card).getByText('Distance threshold was reached.')).toBeInTheDocument()
    expect(within(card).getByText(/do not diagnose a fault/i)).toBeInTheDocument()
    expect(within(card).getByText(/not manufacturer-authoritative schedules/i)).toBeInTheDocument()
    expect(within(card).queryByText(/prediction/i)).not.toBeInTheDocument()
  })
})
