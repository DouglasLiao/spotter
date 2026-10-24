import { useEffect, useState } from 'react'
import type { LocationGeo } from '../types/routing'
import { searchCities } from '../services/api'

interface CityAutocompleteProps {
  id: string
  value: string
  disabled: boolean
  placeholder: string
  onChange: (value: string, location?: LocationGeo) => void
}

export function CityAutocomplete({ id, value, disabled, placeholder, onChange }: CityAutocompleteProps) {
  const [query, setQuery] = useState<string | null>(null)
  const [result, setResult] = useState<{ query: string; cities: LocationGeo[]; error?: string } | null>(null)
  const [active, setActive] = useState(-1)
  const searching = !disabled && query !== null && query === value && query.trim().length >= 3
  const current = searching && result?.query === query ? result : null
  const cities = current?.cities ?? []
  const listId = `${id}-suggestions`

  useEffect(() => {
    if (!searching || query === null) return
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      try {
        const cities = await searchCities(query.trim(), controller.signal)
        if (!controller.signal.aborted) setResult({ query, cities })
      } catch (error) {
        if (!controller.signal.aborted) setResult({ query, cities: [], error: error instanceof Error ? error.message : 'City suggestions are unavailable.' })
      }
    }, 350)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query, searching])

  const choose = (city: LocationGeo) => {
    onChange(city.formatted_address || city.name || '', city)
    setQuery(null)
    setActive(-1)
  }

  return (
    <div className="city-autocomplete">
      <input id={id} className="form-input" type="text" role="combobox"
        value={value} disabled={disabled} required placeholder={placeholder} autoComplete="off"
        aria-autocomplete="list" aria-expanded={searching} aria-controls={searching ? listId : undefined}
        aria-activedescendant={cities[active] ? `${id}-option-${active}` : undefined}
        onChange={(event) => {
          onChange(event.target.value)
          setQuery(event.target.value)
          setResult(null)
          setActive(-1)
        }}
        onFocus={() => { setQuery(value); setActive(-1) }}
        onBlur={() => { setQuery(null); setActive(-1) }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') { setQuery(null); setActive(-1) }
          if (searching && cities.length && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
            event.preventDefault()
            setActive((index) => event.key === 'ArrowDown'
              ? (index + 1) % cities.length : index <= 0 ? cities.length - 1 : index - 1)
          }
          if (searching && event.key === 'Enter' && cities[active]) {
            event.preventDefault()
            choose(cities[active])
          }
        }} />
      {searching && (
        <div className="city-suggestions">
          <ul id={listId} role="listbox" aria-label="City suggestions">
            {cities.map((city, index) => (
              <li key={`${city.lat},${city.lon}`} id={`${id}-option-${index}`} role="option"
                aria-selected={active === index} onPointerDown={(event) => event.preventDefault()}
                onClick={() => choose(city)}>{city.formatted_address}</li>
            ))}
          </ul>
          {!cities.length && <p role="status">{!current ? 'Searching cities…' : current.error || 'No cities found. Try adding a state or country, or enter coordinates.'}</p>}
        </div>
      )}
    </div>
  )
}
