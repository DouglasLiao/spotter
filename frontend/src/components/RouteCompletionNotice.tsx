import { IoCheckmarkCircleOutline, IoCloseOutline } from 'react-icons/io5'

interface RouteCompletionNoticeProps {
  routeName: string
  destinationName: string
  onDismiss: () => void
}

export function RouteCompletionNotice({
  routeName,
  destinationName,
  onDismiss,
}: RouteCompletionNoticeProps) {
  return (
    <div className="route-completion-notice" role="status" aria-live="polite" aria-atomic="true">
      <IoCheckmarkCircleOutline size={24} className="route-completion-icon" aria-hidden="true" />
      <div className="route-completion-content">
        <strong>Route completed</strong>
        <p>Simulation finished: {routeName} has reached {destinationName}.</p>
      </div>
      <button
        type="button"
        className="overlay-close-btn"
        onClick={onDismiss}
        aria-label="Dismiss route completion"
      >
        <IoCloseOutline size={20} aria-hidden="true" />
      </button>
    </div>
  )
}
