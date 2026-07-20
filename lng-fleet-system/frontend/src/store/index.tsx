import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type { Vessel, Alert, DashboardSummary } from '../services/types';

interface AppState {
  vessels: Vessel[];
  alerts: Alert[];
  summary: DashboardSummary | null;
  selectedVesselId: string | null;
  sidebarOpen: boolean;
}

type Action =
  | { type: 'SET_VESSELS'; payload: Vessel[] }
  | { type: 'SET_ALERTS'; payload: Alert[] }
  | { type: 'SET_SUMMARY'; payload: DashboardSummary }
  | { type: 'SELECT_VESSEL'; payload: string | null }
  | { type: 'ACKNOWLEDGE_ALERT'; payload: string }
  | { type: 'TOGGLE_SIDEBAR' };

const initialState: AppState = {
  vessels: [],
  alerts: [],
  summary: null,
  selectedVesselId: null,
  sidebarOpen: true,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_VESSELS':
      return { ...state, vessels: action.payload };
    case 'SET_ALERTS':
      return { ...state, alerts: action.payload };
    case 'SET_SUMMARY':
      return { ...state, summary: action.payload };
    case 'SELECT_VESSEL':
      return { ...state, selectedVesselId: action.payload };
    case 'ACKNOWLEDGE_ALERT':
      return {
        ...state,
        alerts: state.alerts.map((a) =>
          a.id === action.payload ? { ...a, acknowledged: true } : a
        ),
      };
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<Action>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx;
}

export function useVessels() {
  const { state, dispatch } = useAppState();
  const setVessels = useCallback(
    (v: Vessel[]) => dispatch({ type: 'SET_VESSELS', payload: v }),
    [dispatch]
  );
  return { vessels: state.vessels, setVessels };
}

export function useAlerts() {
  const { state, dispatch } = useAppState();
  const acknowledge = useCallback(
    (id: string) => dispatch({ type: 'ACKNOWLEDGE_ALERT', payload: id }),
    [dispatch]
  );
  return { alerts: state.alerts, acknowledge };
}
