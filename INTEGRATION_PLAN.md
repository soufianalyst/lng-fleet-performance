=== ANALYTICS DB INTEGRATION WORK PLAN ===

Phase 1: Fix Critical Issues (Immediate - 5 minutes)
-----------------------------------

1. Fix vessel mapping in api/vessels.py
   - Add vessel_id to mapping to prevent duplicates
   - Ensure proper vessel matching between analytics and main DB
   - Test /api/vessels/ for 50 unique vessels

2. Add analytics vessel lookup in api/hull.py
   - Modify hull overview endpoint
   - Import hull data from analytics DB for missing vessels
   - Test hull modules for 50 vessels

Phase 2: Module Integration (1-2 hours)
---------------------------------

3. Integrate analytics engine data into machinery.py
   - Add engine performance data for vessels 6-50
   - Map analytics metrics to main engine_performance format

4. Enhance charterer analytics in api/charterer.py
   - Import analytics-based performance metrics
   - Add analytics BOG, fuel, emission data

5. Update frontend components
   - Ensure all modules show data for 50 vessels
   - Fix TrimAnalysis, SpeedPower, HullOverview data display

Phase 3: Testing & Documentation (30 minutes)
--------------------------------------------

6. Run integration tests
   - curl /api/vessels/ - expect 50 vessels
   - curl /api/map/fleet-positions - expect 50 vessels
   - curl /api/charterer/voyage-pnl - expect data for 50 vessels
   - Test hull modules for all vessel IDs

7. Update integration guide
   - Document successful fixes
   - Note remaining issues/known limitations
