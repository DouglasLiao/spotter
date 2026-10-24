import { expect, test } from '@playwright/test'
import type { RoutePlanResponse, RiskLevel } from '../src/types/routing'

function plan(unknown = false, count = 3): RoutePlanResponse {
  const start = new Date('2026-10-24T12:30:00Z')
  const weather = { available: !unknown, wind_mph: unknown ? null : 44.5,
    rain_in_hr: unknown ? null : 0.05, snow_in_hr: unknown ? null : 0 }
  const riskLabel: RiskLevel = unknown ? 'Unknown' : 'Severe'
  const hourly = Array.from({ length: 49 }, (_, hour) => ({
    ...weather, hour, time: new Date(start.getTime() + hour * 3600000).toISOString(),
    // The final hour deliberately has no forecast: the UI must not reuse ETA weather.
    ...(hour === 48 ? { available: false, wind_mph: null, rain_in_hr: null, snow_in_hr: null } : {}),
    risk_level: unknown ? null : 4, risk_label: riskLabel,
  }))
  return {
    origin: { lat: 40, lon: -90, name: 'Origin' }, destination: { lat: 41, lon: -89, name: 'Destination' },
    departure_time: start.toISOString(), load_weight: 42000, sample_interval_miles: 25,
    recommended_route_id: unknown ? null : 'route_1',
    warnings: [...(unknown ? ['No recommendation is available because checkpoint weather is incomplete for every route.'] : []),
      ...(count < 3 ? [`Only ${count} distinct route option(s) are available from the routing provider.`] : [])],
    routes: Array.from({ length: count }, (_, index) => ({
      id: `route_${index + 1}`, name: `Route ${index + 1}`, distance_miles: 100,
      duration_seconds: 7200, duration_hours: 2,
      coordinates: [[40, -90], [40.5 + index * 0.2, -89.5], [41, -89]],
      is_recommended: !unknown && index === 0, recommendation_reason: unknown ? 'Weather incomplete.' : 'Lowest weather exposure.',
      risk_summary: { severe_miles: unknown ? 0 : 100, high_miles: 0, moderate_miles: 0,
        low_miles: 0, no_travel_miles: 0, unknown_miles: unknown ? 100 : 0,
        average_risk_score: unknown ? null : 4, max_risk_level: riskLabel, weather_complete: !unknown },
      checkpoints: [0, 1, 2].map((cp) => ({ index: cp, lat: 40 + cp * 0.5,
        lon: -90 + cp * 0.5, distance_from_start_miles: cp * 50,
        eta_iso: new Date(start.getTime() + cp * 3600000).toISOString(), weather,
        risk: { overall_risk_label: riskLabel, overall_risk_level: unknown ? null : 4, load_penalty_applied: !unknown },
        hourly_forecast: hourly,
      })),
    })),
    corridor: { half_width_miles: 15, grid_spacing_miles: 25,
      points: [0, 1, 2, 3].map((index) => ({ lat: 40 + index / 4, lon: -89.8 + index / 4, hourly_forecast: hourly })) },
  }
}

test.beforeEach(async ({ page }) => {
  // Deterministic offline tiles; external routing/weather are covered by backend tests.
  await page.route('https://*.tile.openstreetmap.org/**', (route) => route.fulfill({
    contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e2e8f0"/></svg>',
  }))
})

test('map selection, checkpoint ETA, 0–48h slider and missing forecast', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  let calls = 0
  await page.route('**/api/routes/plan/', (route) => { calls++; return route.fulfill({ json: plan() }) })
  await page.goto('/')
  await page.locator('.submit-button').click()
  await expect(page.locator('.route-card')).toHaveCount(3)
  await expect(page.locator('.route-card-recommended')).toHaveCount(1)
  await expect(page.locator('.corridor-coverage')).toContainText('4/4 grid points available')
  await expect(page.locator('canvas.leaflet-layer')).toHaveCount(1)
  await page.locator('.route-card').nth(1).click()
  await expect(page.locator('.route-card').nth(1)).toHaveClass(/route-card-selected/)
  await page.locator('path.checkpoint-marker').nth(1).click()
  await expect(page.locator('.checkpoint-popup')).toContainText('ETA:')
  await page.locator('.leaflet-popup-close-button').click()
  const slider = page.getByRole('slider', { name: 'Forecast hour slider' })
  const durations = await slider.evaluate(async (element) => {
    const values = []
    for (let hour = 0; hour < 49; hour++) {
      const start = performance.now()
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(element, String(hour))
      element.dispatchEvent(new Event('input', { bubbles: true }))
      await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      values.push(performance.now() - start)
    }
    return values
  })
  expect(Math.max(...durations)).toBeLessThan(250)
  await info.attach('slider-paint-times-ms', { body: JSON.stringify(durations), contentType: 'application/json' })
  expect(calls).toBe(1)
  await slider.fill('48')
  await expect(page.locator('.timeline-offset-badge')).toHaveText('+48h Offset')
  await expect(page.locator('.corridor-coverage')).toContainText('0/4 grid points available')
  await expect(page.locator('canvas.leaflet-layer')).toHaveCount(0)
  await page.getByRole('button', { name: 'Departure (0h)', exact: true }).click()
  await page.getByRole('button', { name: 'Wind Speed', exact: true }).click()
  await expect(page.locator('canvas.leaflet-layer')).toHaveCount(1)
  const request = page.waitForRequest('**/api/routes/plan/')
  await slider.fill('12')
  await page.getByRole('button', { name: 'Set Departure', exact: true }).click()
  expect((await request).postDataJSON().departure_time).toBe('2026-10-25T00:30:00.000Z')
  await expect(page.locator('.route-card')).toHaveCount(3)
  expect(errors).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('map.png'), fullPage: true })
})

test('unknown weather has no green exposure or recommendation', async ({ page }) => {
  await page.route('**/api/routes/plan/', (route) => route.fulfill({ json: plan(true) }))
  await page.goto('/')
  await page.locator('.submit-button').click()
  await expect(page.locator('.route-card-recommended')).toHaveCount(0)
  await expect(page.locator('.route-card .metric-value').filter({ hasText: 'Unknown' })).toHaveCount(3)
  await expect(page.locator('.segment-low').first()).toHaveAttribute('style', 'width: 0%;')
  await expect(page.locator('.segment-unknown').first()).toHaveAttribute('style', 'width: 100%;')
  await expect(page.locator('.corridor-coverage')).toContainText('0/4 grid points available')
  await expect(page.locator('canvas.leaflet-layer')).toHaveCount(0)
})

test('one available route and provider error are explicit', async ({ page }) => {
  let fail = false
  await page.route('**/api/routes/plan/', (route) => route.fulfill(fail
    ? { status: 502, json: { error: 'Routing provider unavailable.' } } : { json: plan(false, 1) }))
  await page.goto('/')
  await page.locator('.submit-button').click()
  await expect(page.locator('.route-card')).toHaveCount(1)
  await expect(page.getByText('Only 1 distinct route option(s)', { exact: false })).toBeVisible()
  fail = true
  await page.locator('.submit-button').click()
  await expect(page.locator('.error-banner')).toContainText('Routing provider unavailable.')
})
