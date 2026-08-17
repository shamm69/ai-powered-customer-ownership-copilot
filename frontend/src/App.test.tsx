import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the frontend design foundation', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', {
        name: 'A confident home for every ownership moment.',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('Design foundation ready')).toBeInTheDocument()
    expect(screen.getByText('Dashboard experience comes next')).toBeInTheDocument()
  })
})
