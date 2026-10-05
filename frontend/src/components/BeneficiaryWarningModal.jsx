export default function BeneficiaryWarningModal({ warning, onCancel, onProceed }) {
  if (!warning) return null

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
        <div className="verify-icon high">⚠️</div>
        <h2 style={{ fontSize: 17, margin: '0 0 8px' }}>Recipient risk warning</h2>
        <p className="text-secondary" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {warning.warning_message}
        </p>

        {warning.tags && warning.tags.length > 0 && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '12px 0' }}>
            {warning.tags.map(tag => (
              <span key={tag} className="badge badge-new">{tag.replace(/_/g, ' ')}</span>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
          <button className="btn btn-secondary" onClick={onCancel}>Cancel Transfer</button>
          <button className="btn btn-danger" onClick={onProceed}>Proceed Anyway</button>
        </div>
      </div>
    </div>
  )
}
