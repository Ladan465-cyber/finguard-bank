export default function RiskBadge({ level }) {
  if (!level) return <span className="badge">—</span>
  return <span className={`risk-badge risk-${level}`}>{level}</span>
}
