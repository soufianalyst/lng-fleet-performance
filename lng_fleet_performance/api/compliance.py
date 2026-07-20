from fastapi import APIRouter, Query
from .deps import get_cii, get_eexi, get_seemp

router = APIRouter()


@router.get("/cii/boundaries")
async def cii_boundaries(year: int = Query(2024)):
    return get_cii().get_boundaries(year)


@router.get("/cii/drift-alert/{vessel_id}")
async def cii_drift_alert(vessel_id: int, year: int = Query(None)):
    return get_cii().cii_drift_alert(vessel_id, year)


@router.get("/cii/what-if/{vessel_id}")
async def cii_what_if(vessel_id: int, speed_reduction: float = Query(5)):
    return get_cii().cii_what_if(vessel_id, speed_reduction)


@router.get("/cii/fleet")
async def cii_fleet(year: int = Query(None), eua_price: float = Query(85)):
    """Fleet-wide CII summary — average rating, distribution, top/bottom performers."""
    cii = get_cii()
    vessels = cii.db.fetchall("SELECT vessel_id, vessel_name FROM vessels ORDER BY vessel_id")
    ratings = []
    for v in vessels:
        try:
            r = cii.calculate_cii(v["vessel_id"], year)
            if 'cii_calculated' in r and r['cii_calculated'] is not None:
                ratings.append({
                    'vessel_id': v["vessel_id"],
                    'vessel_name': v["vessel_name"],
                    'cii_value': r['cii_calculated'],
                    'rating': r.get('cii_rating', 'N/A'),
                    'target': r.get('cii_required', 0),
                    'distance_nm': r.get('distance_sailed_nm', 0),
                    'fuel_mt': r.get('total_fuel_mt', 0),
                    'cargo_mt': r.get('cargo_carried_mt', 0),
                })
        except Exception:
            pass
    if not ratings:
        return {'error': 'No CII data available', 'vessels': []}
    avg_cii = sum(r['cii_value'] for r in ratings) / len(ratings)
    dist = {}
    for r in ratings:
        rt = r['rating']
        dist[rt] = dist.get(rt, 0) + 1
    best = min(ratings, key=lambda x: x['cii_value'])
    worst = max(ratings, key=lambda x: x['cii_value'])
    return {
        'year': year,
        'fleet_size': len(ratings),
        'avg_cii': round(avg_cii, 3),
        'rating_distribution': dist,
        'best_performer': {'vessel_id': best['vessel_id'], 'vessel_name': best['vessel_name'],
                           'cii_value': best['cii_value'], 'rating': best['rating']},
        'worst_performer': {'vessel_id': worst['vessel_id'], 'vessel_name': worst['vessel_name'],
                            'cii_value': worst['cii_value'], 'rating': worst['rating']},
        'vessels': ratings,
    }


@router.get("/cii/{vessel_id}")
async def cii(vessel_id: int, year: int = Query(None)):
    return get_cii().calculate_cii(vessel_id, year)


@router.get("/eu-ets/summary/{vessel_id}")
async def eu_ets_summary(vessel_id: int, year: int = Query(None), eua_price: float = Query(80)):
    return get_cii().eu_ets_annual_summary(vessel_id, year, eua_price)


@router.get("/eu-ets/{voyage_id}")
async def eu_ets(voyage_id: int, eua_price: float = Query(80)):
    return get_cii().calculate_eu_ets(voyage_id, eua_price)


@router.get("/fueleu/trajectory")
async def fueleu_trajectory(year: int = Query(2025)):
    return get_cii().fueleu_trajectory_limit(year)


@router.get("/fueleu/annual/{vessel_id}")
async def fueleu_annual(vessel_id: int, year: int = Query(2025)):
    return get_cii().fueleu_annual_aggregation(vessel_id, year)


@router.get("/fueleu/{voyage_id}")
async def fueleu(voyage_id: int, reference: float = Query(91.16)):
    return get_cii().calculate_fueleu(voyage_id, reference)


@router.get("/epl/verify/{vessel_id}")
async def verify_epl(vessel_id: int, lat: float = Query(0), lon: float = Query(0),
                     power_pct: float = Query(100)):
    return get_eexi().verify_epl_compliance(vessel_id, lat, lon, power_pct)


@router.get("/epl/{vessel_id}")
async def epl_status(vessel_id: int):
    return get_eexi().get_epl_status(vessel_id)


@router.post("/epl/{vessel_id}")
async def configure_epl(vessel_id: int, power_limit_pct: float = Query(80),
                        eca_zone: str = Query(None), reason: str = Query("")):
    return get_eexi().configure_epl(vessel_id, power_limit_pct, eca_zone, reason)


@router.get("/eexi/{vessel_id}")
async def eexi(vessel_id: int):
    return get_eexi().calculate_eexi(vessel_id)
