from ..database.connection import DatabaseManager
from ..modules.voyage_optimization import VoyageOptimization
from ..modules.cargo_monitoring import CargoMonitoring
from ..modules.hull_machinery import HullMachinery
from ..modules.cii_compliance import CIICompliance
from ..modules.digital_twin import DigitalTwin
from ..modules.charter_party import CharterPartyVerification
from ..modules.eca_optimization import ECAOptimization
from ..modules.eexi_compliance import EEXICompliance
from ..modules.seemp_compliance import SEEMPCompliance
from ..modules.certificate_manager import CertificateManager
import os

_db = None
_analytics_db = None
_voyage_opt = None
_cargo = None
_hull = None
_cii = None
_twin = None
_charter = None
_eca = None
_eexi = None
_seemp = None
_certs = None


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lng_fleet.db")
        _db = DatabaseManager(db_path)
    return _db


def get_analytics_db() -> DatabaseManager:
    global _analytics_db
    if _analytics_db is None:
        project_root = os.path.dirname(os.path.dirname(__file__))
        candidates = [
            os.path.join(project_root, "output", "lng_fleet_analytics.db"),
            os.path.join(project_root, "..", "lng-data-generator", "output", "lng_fleet_analytics.db"),
        ]
        for c in candidates:
            if os.path.exists(c):
                _analytics_db = DatabaseManager(c)
                break
    return _analytics_db


def init_modules():
    global _voyage_opt, _cargo, _hull, _cii, _twin, _charter, _eca, _eexi, _seemp, _certs
    db = get_db()
    _voyage_opt = VoyageOptimization(db)
    _cargo = CargoMonitoring(db)
    _hull = HullMachinery(db)
    _cii = CIICompliance(db)
    _twin = DigitalTwin(db)
    _charter = CharterPartyVerification(db)
    _eca = ECAOptimization(db)
    _eexi = EEXICompliance(db)
    _seemp = SEEMPCompliance(db)
    _certs = CertificateManager(db)


def get_voyage_opt() -> VoyageOptimization:
    if _voyage_opt is None:
        init_modules()
    return _voyage_opt


def get_cargo() -> CargoMonitoring:
    if _cargo is None:
        init_modules()
    return _cargo


def get_hull() -> HullMachinery:
    if _hull is None:
        init_modules()
    return _hull


def get_cii() -> CIICompliance:
    if _cii is None:
        init_modules()
    return _cii


def get_twin() -> DigitalTwin:
    if _twin is None:
        init_modules()
    return _twin


def get_charter() -> CharterPartyVerification:
    if _charter is None:
        init_modules()
    return _charter


def get_eca() -> ECAOptimization:
    if _eca is None:
        init_modules()
    return _eca


def get_eexi() -> EEXICompliance:
    if _eexi is None:
        init_modules()
    return _eexi


def get_seemp() -> SEEMPCompliance:
    if _seemp is None:
        init_modules()
    return _seemp


def get_certs() -> CertificateManager:
    if _certs is None:
        init_modules()
    return _certs
