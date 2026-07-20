import axios from 'axios';
import type {
  Vessel, Voyage, TelemetryPoint, CIIRecord, EtsRecord, Alert,
  FuelEURecord, DashboardSummary, FleetOverviewData, CharterParty,
  CharterVerification, ECAEvent, BogRecord, MaintenancePrediction,
} from './types';

const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.response.use(
  (response) => {
    if (response.data && response.data.status === 'success' && response.data.data !== undefined) {
      response.data = response.data.data;
    }
    return response;
  },
  (error) => Promise.reject(error)
);

export async function getVessels(): Promise<Vessel[]> {
  const { data } = await client.get('/v1/vessels');
  return data;
}

export async function getVessel(id: string): Promise<Vessel> {
  const { data } = await client.get(`/v1/vessels/${id}`);
  return data;
}

export async function getVesselTelemetry(
  id: string,
  params?: { from?: string; to?: string }
): Promise<TelemetryPoint[]> {
  const { data } = await client.get(`/v1/telemetry/${id}`, { params });
  return data;
}

export async function getLatestTelemetry(id: string): Promise<TelemetryPoint> {
  const { data } = await client.get(`/v1/telemetry/${id}/latest`);
  return data;
}

export async function getVesselCII(id: string): Promise<CIIRecord[]> {
  const { data } = await client.get(`/v1/cii/${id}`);
  return data;
}

export async function getVoyages(params?: {
  vesselId?: string;
  status?: string;
  from?: string;
  to?: string;
}): Promise<Voyage[]> {
  const { data } = await client.get('/v1/voyages', { params });
  return data;
}

export async function getVoyage(id: string): Promise<Voyage> {
  const { data } = await client.get(`/v1/voyages/${id}`);
  return data;
}

export async function getAlerts(params?: {
  vesselId?: string;
  severity?: string;
  acknowledged?: boolean;
}): Promise<Alert[]> {
  const { data } = await client.get('/v1/dashboard/alerts', { params });
  return data;
}

export async function acknowledgeAlert(id: string, acknowledgedBy?: string): Promise<Alert> {
  const { data } = await client.post(`/v1/alerts/${id}/acknowledge`, { acknowledgedBy });
  return data;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await client.get('/v1/dashboard/fleet-overview');
  return data;
}

export async function getVesselDashboard(vesselId: string): Promise<any> {
  const { data } = await client.get(`/v1/dashboard/vessel/${vesselId}`);
  return data;
}

export async function getCIISummary(): Promise<any> {
  const { data } = await client.get('/v1/dashboard/cii-summary');
  return data;
}

export async function getFleetCII(year?: number): Promise<CIIRecord[]> {
  const { data } = await client.get('/v1/cii/fleet', { params: { year } });
  return data;
}

export async function getEtsStatus(
  vesselId?: string,
  year?: number
): Promise<EtsRecord[]> {
  const { data } = await client.get('/v1/ets/status', {
    params: { vesselId, year },
  });
  return data;
}

export async function getFleetOverview(): Promise<FleetOverviewData> {
  const { data } = await client.get('/v1/dashboard/fleet-overview');
  return data;
}

export async function getCharterParties(vesselId?: string): Promise<CharterParty[]> {
  const { data } = await client.get('/v1/charters', { params: { vesselId } });
  return data;
}

export async function getCharterVerifications(
  charterPartyId: string
): Promise<CharterVerification[]> {
  const { data } = await client.get(`/v1/charters/${charterPartyId}/verifications`);
  return data;
}

export async function getECAEvents(vesselId?: string): Promise<ECAEvent[]> {
  const { data } = await client.get('/v1/eca-events', { params: { vesselId } });
  return data;
}

export async function getBogRecords(
  vesselId: string,
  params?: { from?: string; to?: string }
): Promise<BogRecord[]> {
  const { data } = await client.get(`/v1/bog/${vesselId}`, { params });
  return data;
}

export async function getMaintenancePredictions(
  vesselId?: string
): Promise<MaintenancePrediction[]> {
  const { data } = await client.get('/v1/maintenance/predictions', {
    params: { vesselId },
  });
  return data;
}

export async function getFuelEUBalance(
  vesselId?: string,
  year?: number
): Promise<FuelEURecord[]> {
  const { data } = await client.get('/v1/fueleu/balance', {
    params: { vesselId, year },
  });
  return data;
}
