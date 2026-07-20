import { useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, PathLayer, PolygonLayer, TextLayer } from '@deck.gl/layers';
import type { Vessel, Voyage } from '../services/types';
import { ciiColor } from '../utils/formatters';
import { Box } from '@mui/material';

interface FleetMapProps {
  vessels: Vessel[];
  voyages?: Voyage[];
  onVesselClick?: (vesselId: string) => void;
}

const ECA_ZONES = [
  {
    name: 'North Sea',
    coordinates: [
      [2.0, 51.0], [8.0, 56.0], [10.0, 58.0], [8.0, 62.0],
      [5.0, 62.0], [2.0, 58.0], [-2.0, 56.0], [2.0, 51.0],
    ],
  },
  {
    name: 'Baltic Sea',
    coordinates: [
      [14.0, 55.0], [20.0, 56.0], [28.0, 58.0], [30.0, 60.0],
      [28.0, 62.0], [24.0, 63.0], [18.0, 61.0], [14.0, 57.0],
      [12.0, 56.0], [14.0, 55.0],
    ],
  },
  {
    name: 'Mediterranean',
    coordinates: [
      [5.0, 36.0], [15.0, 35.0], [25.0, 34.0], [30.0, 35.0],
      [30.0, 38.0], [25.0, 40.0], [15.0, 42.0], [5.0, 44.0],
      [0.0, 42.0], [-5.0, 40.0], [5.0, 36.0],
    ],
  },
  {
    name: 'North America ECA',
    coordinates: [
      [-80.0, 28.0], [-75.0, 30.0], [-70.0, 35.0], [-68.0, 42.0],
      [-70.0, 45.0], [-72.0, 48.0], [-68.0, 52.0], [-66.0, 55.0],
      [-70.0, 58.0], [-80.0, 60.0], [-90.0, 55.0], [-95.0, 48.0],
      [-97.0, 42.0], [-95.0, 35.0], [-90.0, 30.0], [-85.0, 28.0],
    ],
  },
  {
    name: 'US Caribbean ECA',
    coordinates: [
      [-68.0, 18.0], [-65.0, 18.0], [-64.0, 19.0], [-65.0, 22.0],
      [-67.0, 23.0], [-70.0, 24.0], [-72.0, 22.0], [-70.0, 19.0],
    ],
  },
];

const INITIAL_VIEW = {
  longitude: 10,
  latitude: 40,
  zoom: 2.5,
  pitch: 0,
  bearing: 0,
};

export default function FleetMap({ vessels, voyages, onVesselClick }: FleetMapProps) {
  const vesselLayer = useMemo(
    () =>
      new ScatterplotLayer({
        id: 'vessels',
        data: vessels,
        getPosition: (d: Vessel) => d.position,
        getRadius: 60000,
        getFillColor: (d: Vessel) => hexToRgba(ciiColor(d.ciiRating)),
        getLineColor: [255, 255, 255, 180],
        getLineWidth: 2000,
        stroked: true,
        radiusMinPixels: 6,
        radiusMaxPixels: 16,
        pickable: true,
        onClick: (info: any) => {
          if (info.object && onVesselClick) {
            onVesselClick((info.object as Vessel).id);
          }
        },
      }),
    [vessels, onVesselClick]
  );

  const vesselLabelLayer = useMemo(
    () =>
      new TextLayer({
        id: 'vessel-labels',
        data: vessels,
        getPosition: (d: Vessel) => [d.position[0], d.position[1] + 0.8],
        getText: (d: Vessel) => d.name,
        getSize: 11,
        getColor: [200, 216, 240, 220],
        getPixelOffset: [0, -8],
        sizeUnits: 'pixels',
      }),
    [vessels]
  );

  const routeLayers = useMemo(() => {
    if (!voyages) return [];
    const activeVoyages = voyages.filter((v) => v.status === 'in-progress');
    return activeVoyages.map(
      (voyage) =>
        new PathLayer({
          id: `route-${voyage.id}`,
          data: [{ path: voyage.route }],
          getPath: (d: { path: [number, number][] }) => d.path,
          getColor: [64, 196, 255, 120],
          getWidth: 8000,
          widthMinPixels: 1.5,
          widthMaxPixels: 4,
          dashJustified: true,
          dashSize: [10, 15],
          dashGap: true,
        })
    );
  }, [voyages]);

  const ecaLayers = useMemo(
    () =>
      new PolygonLayer({
        id: 'eca-zones',
        data: ECA_ZONES,
        getPolygon: (d: { coordinates: [number, number][] }) => d.coordinates,
        getFillColor: [0, 200, 255, 12],
        getLineColor: [0, 200, 255, 60],
        getLineWidth: 2,
        stroked: true,
        extruded: false,
        lineWidthMinPixels: 1,
      }),
    []
  );

  const ecaLabelLayer = useMemo(
    () =>
      new TextLayer({
        id: 'eca-labels',
        data: ECA_ZONES,
        getPosition: (d: { name: string; coordinates: [number, number][] }) => {
          const coords = d.coordinates;
          const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length;
          const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length;
          return [cx, cy];
        },
        getText: (d: { name: string }) => d.name,
        getSize: 10,
        getColor: [0, 200, 255, 80],
        sizeUnits: 'pixels',
      }),
    []
  );

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller={{ dragRotate: false, inertia: true }}
        layers={[ecaLayers, ecaLabelLayer, ...routeLayers, vesselLayer, vesselLabelLayer]}
        getTooltip={({ object }: { object?: Vessel }) =>
          object
            ? {
                html: `<div style="font-family:Inter;font-size:13px">
                  <b>${object.name}</b><br/>
                  IMO: ${object.imo}<br/>
                  Speed: ${object.speed.toFixed(1)} kn<br/>
                  CII Rating: ${object.ciiRating}<br/>
                  Status: ${object.status}
                </div>`,
                style: {
                  background: '#111827',
                  border: '1px solid rgba(64,196,255,0.3)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#e0e6f0',
                },
              }
            : null
        }
        style={{ background: 'transparent' }}
      />
    </Box>
  );
}

function hexToRgba(hex: string, alpha = 200): [number, number, number, number] {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return [r, g, b, alpha];
}
