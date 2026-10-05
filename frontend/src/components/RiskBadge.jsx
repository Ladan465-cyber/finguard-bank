const LABELS = {
  SAFE: 'Safe',
  CAUTION: 'Caution',
  VERIFY: 'Verify',
  HIGH_RISK: 'High Risk',
  CRITICAL: 'Critical',
}

export default function RiskBadge({ level }) {
  if (!level) return <span className="badge">—</span>
  return <span className={`risk-badge risk-${level}`}>{LABELS[level] || level}</span>
}
