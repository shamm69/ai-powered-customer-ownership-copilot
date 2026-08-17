import { CalendarDays, CarFront, Gauge, History, Wrench } from 'lucide-react'

interface DemoVehicle {
  ownerName: string
  manufacturer: string
  model: string
  modelYear: number
  currentOdometerKm: number
  serviceIntervalKm: number
  serviceIntervalMonths: number
  latestScheduledServiceDate: string
  latestScheduledServiceOdometerKm: number
}

interface VehicleOverviewProps {
  vehicle: DemoVehicle
}

const numberFormatter = new Intl.NumberFormat('en-US')

export function VehicleOverview({ vehicle }: VehicleOverviewProps) {
  const kilometresSinceService =
    vehicle.currentOdometerKm - vehicle.latestScheduledServiceOdometerKm

  return (
    <section className="vehicle-panel" aria-labelledby="vehicle-name">
      <div className="vehicle-panel__header">
        <div>
          <p className="section-label">Selected vehicle</p>
          <h2 id="vehicle-name">
            {vehicle.manufacturer} <span>{vehicle.model}</span>
          </h2>
          <p className="vehicle-panel__year">
            {vehicle.modelYear} model · Owned by {vehicle.ownerName}
          </p>
        </div>
        <span className="availability-badge">Maintenance check available</span>
      </div>

      <div className="vehicle-visual" aria-hidden="true">
        <div className="vehicle-visual__halo" />
        <CarFront size={104} strokeWidth={1.25} />
        <span className="vehicle-visual__road" />
      </div>

      <div className="vehicle-primary-fact">
        <span className="fact-icon" aria-hidden="true">
          <Gauge size={21} />
        </span>
        <div>
          <span className="fact-label">Current odometer</span>
          <strong>{numberFormatter.format(vehicle.currentOdometerKm)} km</strong>
        </div>
        <span className="vehicle-primary-fact__note">
          {numberFormatter.format(kilometresSinceService)} km since latest scheduled service
        </span>
      </div>

      <div className="vehicle-facts" aria-label="Vehicle service information">
        <article className="vehicle-fact">
          <span className="fact-icon fact-icon--subtle" aria-hidden="true">
            <Wrench size={18} />
          </span>
          <div>
            <span className="fact-label">Service interval</span>
            <strong>{numberFormatter.format(vehicle.serviceIntervalKm)} km</strong>
          </div>
        </article>
        <article className="vehicle-fact">
          <span className="fact-icon fact-icon--subtle" aria-hidden="true">
            <CalendarDays size={18} />
          </span>
          <div>
            <span className="fact-label">Time interval</span>
            <strong>{vehicle.serviceIntervalMonths} months</strong>
          </div>
        </article>
        <article className="vehicle-fact vehicle-fact--wide">
          <span className="fact-icon fact-icon--subtle" aria-hidden="true">
            <History size={18} />
          </span>
          <div>
            <span className="fact-label">Latest scheduled service</span>
            <strong>{vehicle.latestScheduledServiceDate}</strong>
            <span className="fact-detail">
              at {numberFormatter.format(vehicle.latestScheduledServiceOdometerKm)} km
            </span>
          </div>
        </article>
      </div>
    </section>
  )
}
