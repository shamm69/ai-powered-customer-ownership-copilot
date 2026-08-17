import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SupportResult } from '../../types/assistant'
import { SupportResultCard } from './SupportResultCard'

const supportedResult: SupportResult = {
  answer: 'Inspect the indicator and consult the support guidance before driving.',
  retrieval_status: 'supported',
  sources: [
    {
      source_id: 'warning-indicators',
      document_title: 'Warning Indicator Guide',
      section_title: 'Responding to dashboard warnings',
      chunk_id: 'warning-indicators-responding-01',
    },
    {
      source_id: 'roadside-safety',
      document_title: 'Roadside Safety Basics',
      section_title: 'Stopping safely',
      chunk_id: 'roadside-safety-stopping-01',
    },
  ],
}

describe('SupportResultCard', () => {
  it('renders the grounded answer and human-readable source metadata', () => {
    render(<SupportResultCard result={supportedResult} />)

    expect(screen.getByLabelText('Grounded support answer')).toBeInTheDocument()
    expect(screen.getByText(supportedResult.answer)).toBeInTheDocument()
    expect(screen.getByText('Warning Indicator Guide')).toBeInTheDocument()
    expect(screen.getByText('Responding to dashboard warnings')).toBeInTheDocument()
    expect(
      screen.getByText(
        'Source warning-indicators · Chunk warning-indicators-responding-01',
      ),
    ).toBeInTheDocument()
  })

  it('renders multiple retrieved sources', () => {
    render(<SupportResultCard result={supportedResult} />)

    expect(screen.getByText('2 references')).toBeInTheDocument()
    expect(screen.getByText('Warning Indicator Guide')).toBeInTheDocument()
    expect(screen.getByText('Roadside Safety Basics')).toBeInTheDocument()
    expect(screen.getByText('Stopping safely')).toBeInTheDocument()
  })

  it('renders an unsupported fallback without source claims', () => {
    render(
      <SupportResultCard
        result={{
          answer: 'Insufficient information in the available support documentation.',
          retrieval_status: 'unsupported',
          sources: supportedResult.sources,
        }}
      />,
    )

    expect(screen.getByText('Insufficient documentation')).toBeInTheDocument()
    expect(
      screen.getByText('Insufficient information in the available support documentation.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Sources' })).not.toBeInTheDocument()
    expect(screen.queryByText('Warning Indicator Guide')).not.toBeInTheDocument()
    expect(screen.queryByText('Grounded')).not.toBeInTheDocument()
  })
})
