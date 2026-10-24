import type { LocationGeo, RoutePlanRequest, RoutePlanResponse } from '../types/routing'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function planRoutes(payload: RoutePlanRequest): Promise<RoutePlanResponse> {
  const response = await fetch(`${API_BASE_URL}/routes/plan/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json()

  if (!response.ok) {
    if (data && typeof data === 'object') {
      if (typeof data.error === 'string') {
        throw new Error(data.error)
      }
      // Handle Django REST Framework field validation errors
      const fieldErrors = Object.entries(data)
        .map(([field, errors]) => {
          const msg = Array.isArray(errors) ? errors.join(' ') : String(errors)
          return `${field}: ${msg}`
        })
        .join(' | ')
      if (fieldErrors) {
        throw new Error(fieldErrors)
      }
    }
    throw new Error(`Failed to plan route (HTTP ${response.status})`)
  }

  return data as RoutePlanResponse
}


export async function searchCities(query: string, signal: AbortSignal): Promise<LocationGeo[]> {
  const response = await fetch(`${API_BASE_URL}/cities/?q=${encodeURIComponent(query)}`, { signal })
  if (!response.ok) throw new Error('City suggestions are unavailable. Enter a city, address, or coordinates.')
  const data = await response.json()
  return data.results
}
