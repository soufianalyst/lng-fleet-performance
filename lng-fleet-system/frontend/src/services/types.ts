export interface Vessel {
  id: string;
  name: string;
  imo: string;
  flag: string;
  built: number;
  capacity: number;
  engineType: string;
  boilOffRate: number;
  status: 'in-port' | 'at-sea' | 'dry-dock' | 'idle';
  position: [number, number];
  heading: number;
  speed: number;
  destination: string | null;
  eta: string | null;
  ciiRating: CIIRating;
  currentCII: number;
  requiredCII: number;
  charterParty: string | null;
}

export type CIIRating = 'A' | 'B' | 'C' | 'D' | 'E';

export interface Voyage {
  id: string;
  vesselId: string;
  vesselName: string;
  departurePort: string;
  arrivalPort: string;
  departureTime: string;
  arrivalTime: string | null;
  status: 'planned' | 'in-progress' | 'completed' | 'cancelled';
  distance: number;
  cargoQuantity: number;
  avgSpeed: number;
  fuelConsumption: number;
  boilOff: number;
  emissions: number;
  route: [number, number][];
}

export interface TelemetryPoint {
  timestamp: string;
  speed: number;
  shaftPower: number;
  sfoc: number;
  boilOffRate: number;
  engineLoad: number;
  rpm: number;
  fuelConsumption: number;
  lngTemperature: number;
  tankPressure: number;
}

export interface CIIRecord {
  year: number;
  vesselId: string;
  vesselName: string;
  attainedCII: number;
  requiredCII: number;
  rating: CIIRating;
  trend: 'improving' | 'stable' | 'declining';
  operationalCarbonIntensity: number;
}

export interface EtsRecord {
  year: number;
  vesselId: string;
  vesselName: string;
  totalEmissions: number;
  allowanceAllocated: number;
  allowanceSurrendered: number;
  surplusDeficit: number;
  estimatedLiability: number;
}

export interface Alert {
  id: string;
  vesselId: string;
  vesselName: string;
  type: 'cii' | 'ets' | 'maintenance' | 'navigation' | 'cargo' | 'engine' | 'compliance';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  acknowledgedBy: string | null;
  acknowledgedAt: string | null;
}

export interface FuelEURecord {
  year: number;
  vesselId: string;
  vesselName: string;
  co2Intensity: number;
  referenceIntensity: number;
  surplus: number;
  complianceBalance: number;
  penalty: number;
}

export interface CharterParty {
  id: string;
  vesselId: string;
  vesselName: string;
  charterer: string;
  type: 'time' | 'voyage' | 'bareboat';
  startDate: string;
  endDate: string;
  rate: number;
  currency: string;
  terms: string;
  status: 'active' | 'completed' | 'pending';
}

export interface CharterVerification {
  id: string;
  charterPartyId: string;
  vesselId: string;
  periodStart: string;
  periodEnd: string;
  avgSpeed: number;
  totalDistance: number;
  fuelConsumed: number;
  co2Emissions: number;
  ciiRating: CIIRating;
  verified: boolean;
}

export interface ECAEvent {
  id: string;
  vesselId: string;
  vesselName: string;
  zone: string;
  entryTime: string;
  exitTime: string | null;
  fuelSwitch: boolean;
  complianceStatus: 'compliant' | 'non-compliant' | 'pending';
}

export interface BogRecord {
  id: string;
  vesselId: string;
  vesselName: string;
  timestamp: string;
  boilOffRate: number;
  temperature: number;
  tankPressure: number;
  lngComposition: string;
  reliquefactionActive: boolean;
}

export interface MaintenancePrediction {
  id: string;
  vesselId: string;
  component: string;
  predictedFailure: string;
  remainingLife: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  recommendedAction: string;
  estimatedCost: number;
}

export interface DashboardSummary {
  total_vessels: number;
  active_voyages: number;
  fleet_avg_cii: number;
  fleet_cii_coverage_pct: number;
  open_alerts: number;
  critical_alerts: number;
  fleet_fuel_consumption_tonne: number;
  fleet_distance_nm: number;
  fleet_co2_tonne: number;
  eu_ets_exposure_eur: number;
}

export interface FleetOverviewData {
  total_vessels: number;
  active_voyages: number;
  fleet_avg_cii: number;
  fleet_cii_coverage_pct: number;
  open_alerts: number;
  critical_alerts: number;
  fleet_fuel_consumption_tonne: number;
  fleet_distance_nm: number;
  fleet_co2_tonne: number;
  eu_ets_exposure_eur: number;
}
