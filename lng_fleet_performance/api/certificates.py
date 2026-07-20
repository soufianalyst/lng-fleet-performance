from fastapi import APIRouter, Query
from .deps import get_certs

router = APIRouter()


@router.get("/{vessel_id}")
async def list_certificates(vessel_id: int):
    return get_certs().list_certificates(vessel_id)


@router.get("/{vessel_id}/alerts")
async def cert_alerts(vessel_id: int, threshold: int = Query(90)):
    return get_certs().check_expiry_alerts(vessel_id, threshold)


@router.get("/{vessel_id}/validate")
async def validate_certs(vessel_id: int, zone: str = Query(None)):
    return get_certs().validate_voyage_certs(vessel_id, zone)


@router.post("/{vessel_id}")
async def add_certificate(vessel_id: int, cert_type: str = Query(...),
                          cert_number: str = Query(...), expiry_date: str = Query(...),
                          issue_date: str = Query(None),
                          authority: str = Query("")):
    return get_certs().add_certificate(
        vessel_id, cert_type, cert_number, expiry_date, issue_date, authority)
