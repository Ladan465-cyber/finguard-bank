const LABELS = {
  pending: 'Pending',
  awaiting_otp: 'Awaiting OTP',
  awaiting_verification: 'Awaiting Verification',
  approved: 'Approved',
  completed: 'Completed',
  rejected: 'Rejected',
  blocked: 'Blocked',
}

export default function StatusPill({ status }) {
  return (
    <span className={`status-pill status-${status}`}>
      {LABELS[status] || status}
    </span>
  )
}
