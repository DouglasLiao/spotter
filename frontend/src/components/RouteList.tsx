import React from 'react'
import { IoListOutline, IoInformationCircleOutline } from 'react-icons/io5'
import type { RouteOption, RoutePlanResponse } from '../types/routing'
import { RouteCard } from './RouteCard'

interface RouteListProps {
  planData: RoutePlanResponse
  selectedRouteId: string | number
  onSelectRoute: (routeId: string | number) => void
}

export const RouteList: React.FC<RouteListProps> = ({
  planData,
  selectedRouteId,
  onSelectRoute,
}) => {
  const { routes, origin, destination, load_weight, departure_time } = planData

  const originAddress = origin.formatted_address || origin.address || origin.name || 'Origin'
  const destAddress = destination.formatted_address || destination.address || destination.name || 'Destination'

  const departureFormatted = new Date(departure_time).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  })

  return (
    <div className="route-list-container">
      <div className="route-list-header">
        <div className="route-list-title-row">
          <IoListOutline size={18} className="section-icon" />
          <h2>Route Comparison & Safety Ranking</h2>
        </div>
        <div className="route-list-corridor-row">
          <span className="corridor-text">
            {originAddress} &rarr; {destAddress}
          </span>
        </div>
        <div className="route-list-meta-bar">
          <span className="meta-item">
            <strong>Payload:</strong> {load_weight.toLocaleString()} lbs
          </span>
          <span className="meta-separator">|</span>
          <span className="meta-item">
            <strong>Departure:</strong> {departureFormatted}
          </span>
        </div>
      </div>

      <div className="route-cards-stack">
        {routes.map((route: RouteOption) => (
          <RouteCard
            key={route.id}
            route={route}
            isSelected={route.id === selectedRouteId}
            onSelect={onSelectRoute}
          />
        ))}
      </div>

      <div className="route-list-footer-tip">
        <IoInformationCircleOutline size={16} className="tip-icon" />
        <p>
          {routes.length} available route option(s) are compared. Click any route card to inspect its
          path and weather checkpoints on the map.
        </p>
      </div>
    </div>
  )
}
