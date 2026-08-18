import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { QuickActions } from './QuickActions'

describe('QuickActions', () => {
  it.each([
    ['Check service status', 'Is my vehicle due for service?'],
    ['Explain a warning light', 'What does a warning light mean?'],
    ['Prepare for a long trip', 'What should I check before a long trip?'],
    ['Talk to human support', 'I want to speak to a human agent.'],
  ])('uses a canonical routable prompt for %s', (label, prompt) => {
    const onSelect = vi.fn()

    render(
      <QuickActions onSelect={onSelect} onSelectExperiment={vi.fn()} />,
    )
    fireEvent.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))

    expect(onSelect).toHaveBeenCalledWith(prompt)
  })

  it('keeps the predictive shortcut explicit and separately handled', () => {
    const onSelect = vi.fn()
    const onSelectExperiment = vi.fn()

    render(
      <QuickActions
        onSelect={onSelect}
        onSelectExperiment={onSelectExperiment}
      />,
    )
    fireEvent.click(
      screen.getByRole('button', { name: /explore predictive experiment/i }),
    )

    expect(onSelectExperiment).toHaveBeenCalledOnce()
    expect(onSelect).not.toHaveBeenCalled()
    expect(screen.getByText('Experimental')).toBeInTheDocument()
  })
})
