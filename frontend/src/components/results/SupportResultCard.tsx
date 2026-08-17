import { BookOpenCheck, FileText, SearchX } from 'lucide-react'
import type { SupportResult } from '../../types/assistant'

interface SupportResultCardProps {
  result: SupportResult
}

export function SupportResultCard({ result }: SupportResultCardProps) {
  if (result.retrieval_status === 'unsupported') {
    return (
      <article
        aria-label="Support documentation result"
        className="support-result-card support-result-card--unsupported"
      >
        <header className="support-result-card__header">
          <span className="support-result-card__icon" aria-hidden="true">
            <SearchX size={21} strokeWidth={1.8} />
          </span>
          <div>
            <span className="support-result-card__eyebrow">Support guidance</span>
            <h3>Insufficient documentation</h3>
          </div>
        </header>
        <p className="support-result-card__answer">{result.answer}</p>
        <p className="support-result-card__notice">
          No sources are shown because the available support documentation did not
          provide sufficiently relevant context.
        </p>
      </article>
    )
  }

  return (
    <article
      aria-label="Grounded support answer"
      className="support-result-card support-result-card--grounded"
    >
      <header className="support-result-card__header">
        <span className="support-result-card__icon" aria-hidden="true">
          <BookOpenCheck size={21} strokeWidth={1.8} />
        </span>
        <div>
          <span className="support-result-card__eyebrow">Support guidance</span>
          <h3>Answer from support documentation</h3>
        </div>
        <span className="support-result-card__grounded-label">Grounded</span>
      </header>

      <p className="support-result-card__answer">{result.answer}</p>

      <section className="support-result-card__sources" aria-labelledby="support-sources">
        <div className="support-result-card__sources-heading">
          <h4 id="support-sources">Sources</h4>
          <span>
            {result.sources.length} {result.sources.length === 1 ? 'reference' : 'references'}
          </span>
        </div>
        <ul>
          {result.sources.map((source) => (
            <li key={source.chunk_id}>
              <FileText size={18} aria-hidden="true" />
              <div>
                <strong>{source.document_title}</strong>
                <span>{source.section_title}</span>
                <small>
                  Source {source.source_id} · Chunk {source.chunk_id}
                </small>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </article>
  )
}
