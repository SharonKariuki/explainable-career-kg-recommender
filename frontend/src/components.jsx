// Small pieces shared by the recommendation screens.

export function Meter({ label, value, weight }) {
  const percent = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div className="meter">
      <div className="meter-label">
        <span>{label}{weight !== undefined && <span className="muted"> · weight {Math.round(weight * 100)}%</span>}</span>
        <span>{value.toFixed(2)}</span>
      </div>
      <div className="meter-track" role="img" aria-label={`${label} ${value.toFixed(2)} out of 1`}>
        <div className="meter-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

export function Status({ loading, error }) {
  if (loading) return <p className="muted">Loading…</p>
  if (error) return <p className="error" role="alert">{error}</p>
  return null
}
