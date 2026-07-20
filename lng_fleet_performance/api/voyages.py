from fastapi import APIRouter
from .deps import get_db

router = APIRouter()


@router.get("/")
async def list_voyages(vessel_id: int = None):
    db = get_db()
    if vessel_id:
        voyages = db.fetchall(
            """SELECT vg.*, v.vessel_name FROM voyages vg
               JOIN vessels v ON vg.vessel_id = v.vessel_id
               WHERE vg.vessel_id=? ORDER BY vg.created_at DESC""",
            (vessel_id,))
    else:
        voyages = db.fetchall(
            """SELECT vg.*, v.vessel_name FROM voyages vg
               JOIN vessels v ON vg.vessel_id = v.vessel_id
               ORDER BY vg.created_at DESC LIMIT 50""")
    return {"voyages": voyages, "count": len(voyages)}


@router.get("/{voyage_id}")
async def get_voyage(voyage_id: int):
    db = get_db()
    voyage = db.fetchone("SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
    if not voyage:
        return {"error": "Voyage not found"}
    waypoints = db.fetchall(
        "SELECT * FROM voyage_waypoints WHERE voyage_id=? ORDER BY sequence_num",
        (voyage_id,))
    return {**dict(voyage), "waypoints": waypoints}
