import React from 'react'
import {
  IoTimeOutline,
  IoPlayOutline,
  IoPauseOutline,
  IoPlayBackOutline,
  IoPlayForwardOutline,
  IoRefreshOutline,
} from 'react-icons/io5'

interface TimelineSliderProps {
  arrivalHours: number
  maxHours: number
  offsetHours: number
  onChangeOffset: (hours: number) => void
  baseDepartureTime: string
  onApplyForecastTime: (hours: number) => void
  isLoading: boolean
}

const QUICK_HOURS = [0, 3, 6, 12, 18, 24, 36, 48]

export const TimelineSlider: React.FC<TimelineSliderProps> = ({
  arrivalHours,
  maxHours,
  offsetHours,
  onChangeOffset,
  baseDepartureTime,
  onApplyForecastTime,
  isLoading,
}) => {
  const [isPlaying, setIsPlaying] = React.useState(false)

  // Calculate projected date/time based on base time + offsetHours
  const projectedDate = React.useMemo(() => {
    const d = new Date(new Date(baseDepartureTime).getTime() + offsetHours * 3600000)
    return d.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    })
  }, [baseDepartureTime, offsetHours])

  // Smooth auto-play simulation
  React.useEffect(() => {
    if (!isPlaying || isLoading || offsetHours >= arrivalHours) return

    const interval = setInterval(() => {
      onChangeOffset(Math.min(arrivalHours, offsetHours + 1))
    }, 450)

    return () => clearInterval(interval)
  }, [isPlaying, offsetHours, onChangeOffset, arrivalHours, isLoading])

  const handleStepBack = () => {
    setIsPlaying(false)
    onChangeOffset(Math.max(0, offsetHours - 1))
  }

  const handleStepForward = () => {
    setIsPlaying(false)
    onChangeOffset(Math.min(maxHours, offsetHours + 1))
  }

  return (
    <div className="timeline-slider-panel">
      <div className="timeline-header-row">
        <div className="timeline-title-col">
          <IoTimeOutline size={18} className="timeline-icon" />
          <span className="timeline-title">Corridor Forecast & Trip Simulation (0 to {maxHours} Hours)</span>
        </div>
        <div className="timeline-current-val">
          <span className="timeline-offset-badge">+{Number(offsetHours.toFixed(2))}h Offset</span>
          <span className="timeline-projected-date">{projectedDate}</span>
        </div>
      </div>

      <div className="timeline-controls-row">
        <div className="timeline-playback-btn-group">
          <button
            type="button"
            className="timeline-step-btn"
            onClick={handleStepBack}
            disabled={offsetHours <= 0 || isLoading}
            title="Step -1 Hour"
          >
            <IoPlayBackOutline size={16} />
          </button>

          <button
            type="button"
            className="timeline-play-btn"
            onClick={() => {
              if (offsetHours >= arrivalHours) onChangeOffset(0)
              setIsPlaying(offsetHours >= arrivalHours || !isPlaying)
            }}
            title={isPlaying && offsetHours < arrivalHours ? 'Pause Simulation' : 'Play Simulation'}
            disabled={isLoading}
          >
            {isPlaying && offsetHours < arrivalHours ? <IoPauseOutline size={18} /> : <IoPlayOutline size={18} />}
            <span>{isPlaying && offsetHours < arrivalHours ? 'Pause' : 'Simulate'}</span>
          </button>

          <button
            type="button"
            className="timeline-step-btn"
            onClick={handleStepForward}
            disabled={offsetHours >= maxHours || isLoading}
            title="Step +1 Hour"
          >
            <IoPlayForwardOutline size={16} />
          </button>
        </div>

        <input
          type="range"
          min="0"
          max={maxHours}
          step="any"
          value={offsetHours}
          onChange={(e) => {
            setIsPlaying(false)
            onChangeOffset(Number(e.target.value))
          }}
          className="timeline-range-input"
          disabled={isLoading}
          aria-label="Forecast hour slider"
        />

        <button
          type="button"
          className="timeline-apply-btn"
          onClick={() => onApplyForecastTime(offsetHours)}
          disabled={isLoading}
          title="Re-plan routes departing at this simulated time"
        >
          <IoRefreshOutline size={16} />
          <span>Set Departure</span>
        </button>
      </div>

      {/* Quick Jump Buttons */}
      <div className="timeline-pills-row">
        {[...new Set([...QUICK_HOURS.filter((hour) => hour <= maxHours), maxHours])].map((hr) => (
          <button
            key={hr}
            type="button"
            className={`timeline-pill ${offsetHours === hr ? 'timeline-pill-active' : ''}`}
            onClick={() => {
              setIsPlaying(false)
              onChangeOffset(hr)
            }}
            disabled={isLoading}
          >
            {hr === 0 ? 'Departure (0h)' : `+${hr}h`}
          </button>
        ))}
      </div>
    </div>
  )
}
