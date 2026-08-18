import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { HumanHandoffResult } from '../../types/assistant'
import { HandoffResultCard } from './HandoffResultCard'

const handoffResult: HumanHandoffResult = {
  ticket_id: 'DEMO-OWNERSHIP-1042',
  reason: 'routed_human_handoff',
  request_summary: 'I would like to speak with human support about my vehicle.',
  status: 'created',
}

describe('HandoffResultCard', () => {
  it('renders the structured demo handoff fields', () => {
    render(<HandoffResultCard result={handoffResult} />)

    expect(screen.getByLabelText('Demo human handoff result')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Demo support handoff created' }),
    ).toBeInTheDocument()
    expect(screen.getByText('DEMO-OWNERSHIP-1042')).toBeInTheDocument()
    expect(screen.getByText('Created')).toBeInTheDocument()
    expect(screen.getByText('Human support requested')).toBeInTheDocument()
    expect(screen.getByText(handoffResult.request_summary)).toBeInTheDocument()
  })

  it('clearly discloses that no real support integration was contacted', () => {
    render(<HandoffResultCard result={handoffResult} />)

    expect(screen.getByText('Demo handoff')).toBeInTheDocument()
    expect(
      screen.getByText(
        'This is a local demo handoff. No external CRM, dealer, email, or messaging system was contacted.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(/dealer assigned/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/support agent/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
