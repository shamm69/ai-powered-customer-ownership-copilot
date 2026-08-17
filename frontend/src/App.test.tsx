import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders truthful seeded vehicle context and the assistant workspace', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Aster Motors Comet' }),
    ).toBeInTheDocument()
    expect(screen.getByText('12,500 km')).toBeInTheDocument()
    expect(screen.getByText('15 Jul 2026')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', {
        name: 'How can I help with your vehicle today?',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Preview interface · Live responses are not connected yet'),
    ).toBeInTheDocument()
  })

  it('places a selected quick action into the local assistant composer', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /check service status/i }))

    expect(screen.getByLabelText('Ask the ownership assistant')).toHaveValue(
      'Is my vehicle due for service?',
    )
  })
})
