import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { QuickActions } from './QuickActions'

describe('QuickActions', () => {
  it.each([
    ['Check service status', 'Is my vehicle due for service?'],
    ['Explain a warning light', 'What does a warning light mean?'],
    ['Plan my next service', 'What service should I get for my vehicle?'],
    ['Talk to human support', 'I want to speak to a human agent.'],
  ])('uses a canonical routable prompt for %s', (label, prompt) => {
    const onSelect = vi.fn()

    render(
      <QuickActions onSelect={onSelect} />,
    )
    fireEvent.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))

    expect(onSelect).toHaveBeenCalledWith(prompt)
  })

  it('keeps the technical experiment out of customer quick actions', () => {
    const onSelect = vi.fn()

    render(<QuickActions onSelect={onSelect} />)

    expect(screen.getAllByRole('button')).toHaveLength(4)
    expect(
      screen.queryByRole('button', { name: /predictive experiment/i }),
    ).not.toBeInTheDocument()
    expect(onSelect).not.toHaveBeenCalled()
  })
})
