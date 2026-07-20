from datetime import datetime, timedelta


class CertificateManager:

    CERT_TYPES = {
        "IAPP": {"name": "International Air Pollution Prevention", "validity_years": 5, "required": True},
        "EIAPP": {"name": "International Energy Efficiency Certificate", "validity_years": None, "required": True},
        "IEE": {"name": "International Energy Efficiency Existing Ship", "validity_years": None, "required": True},
        "ISGOTT": {"name": "International Safety Guide for Oil Tankers and Terminals", "validity_years": 5, "required": False},
        "IGC": {"name": "International Gas Carrier Code Certificate", "validity_years": 5, "required": True},
        "ISM": {"name": "International Safety Management Certificate", "validity_years": 5, "required": True},
        "ISPS": {"name": "International Ship Security Certificate", "validity_years": 5, "required": True},
        "MLC": {"name": "Maritime Labour Convention Certificate", "validity_years": 5, "required": True},
        "CLASS": {"name": "Classification Society Certificate", "validity_years": 5, "required": True},
        "P&I": {"name": "Protection & Indemnity Insurance", "validity_years": 1, "required": True},
    }

    def __init__(self, db):
        self.db = db

    def add_certificate(self, vessel_id: int, cert_type: str, cert_number: str,
                        expiry_date: str, issue_date: str = None,
                        issuing_authority: str = "") -> dict:
        if cert_type not in self.CERT_TYPES:
            return {"error": f"Invalid cert type. Valid: {list(self.CERT_TYPES.keys())}"}
        cert_id = self.db.insert_returning_id(
            """INSERT INTO certificates
               (vessel_id, cert_type, cert_number, issue_date, expiry_date,
                issuing_authority, status)
               VALUES (?,?,?,?,?,?,?)""",
            (vessel_id, cert_type, cert_number,
             issue_date or datetime.utcnow().isoformat(),
             expiry_date, issuing_authority, "active"))
        try:
            exp = datetime.fromisoformat(expiry_date)
            days_left = (exp - datetime.utcnow()).days
        except (ValueError, TypeError):
            days_left = 999
        self.db.execute(
            """INSERT INTO certificate_expiry_log
               (vessel_id, cert_id, cert_type, cert_number, expiry_date,
                days_remaining, alert_90_sent, alert_30_sent)
               VALUES (?,?,?,?,?,?,?,?)""",
            (vessel_id, cert_id, cert_type, cert_number, expiry_date,
             days_left, int(days_left <= 90), int(days_left <= 30)))
        return {
            "vessel_id": vessel_id,
            "cert_type": cert_type,
            "cert_number": cert_number,
            "expiry_date": expiry_date,
            "days_remaining": days_left,
            "status": "added",
        }

    def list_certificates(self, vessel_id: int) -> dict:
        certs = self.db.fetchall(
            """SELECT * FROM certificates WHERE vessel_id=?
               ORDER BY expiry_date""",
            (vessel_id,))
        cert_list = []
        now = datetime.utcnow()
        for c in certs:
            try:
                exp = datetime.fromisoformat(c["expiry_date"])
                days_left = (exp - now).days
            except (ValueError, TypeError):
                days_left = 999
            if days_left < 0:
                status = "expired"
            elif days_left <= 30:
                status = "critical"
            elif days_left <= 90:
                status = "expiring_soon"
            else:
                status = "valid"
            cert_list.append({
                "cert_id": c["cert_id"],
                "cert_type": c["cert_type"],
                "cert_number": c["cert_number"],
                "issue_date": c["issue_date"],
                "expiry_date": c["expiry_date"],
                "issuing_authority": c["issuing_authority"],
                "days_remaining": days_left,
                "status": status,
            })
        expired = [c for c in cert_list if c["status"] == "expired"]
        critical = [c for c in cert_list if c["status"] == "critical"]
        expiring = [c for c in cert_list if c["status"] == "expiring_soon"]
        return {
            "vessel_id": vessel_id,
            "total_certificates": len(cert_list),
            "valid": len([c for c in cert_list if c["status"] == "valid"]),
            "expiring_soon": len(expiring),
            "critical": len(critical),
            "expired": len(expired),
            "certificates": cert_list,
            "alerts": [
                {"severity": "critical", "cert": c["cert_type"],
                 "days": c["days_remaining"],
                 "message": f"{self.CERT_TYPES.get(c['cert_type'], {}).get('name', c['cert_type'])} "
                            f"expires in {c['days_remaining']} days"}
                for c in critical + expired
            ],
        }

    def check_expiry_alerts(self, vessel_id: int, days_threshold: int = 90) -> dict:
        certs = self.db.fetchall(
            "SELECT * FROM certificates WHERE vessel_id=? AND status='active'",
            (vessel_id,))
        alerts = []
        now = datetime.utcnow()
        for c in certs:
            try:
                exp = datetime.fromisoformat(c["expiry_date"])
                days_left = (exp - now).days
            except (ValueError, TypeError):
                continue
            cert_name = self.CERT_TYPES.get(c["cert_type"], {}).get("name", c["cert_type"])
            if days_left <= 0:
                alerts.append({
                    "cert_type": c["cert_type"],
                    "cert_name": cert_name,
                    "days_remaining": days_left,
                    "severity": "expired",
                    "message": f"{cert_name} has expired {abs(days_left)} days ago!",
                })
            elif days_left <= 30:
                alerts.append({
                    "cert_type": c["cert_type"],
                    "cert_name": cert_name,
                    "days_remaining": days_left,
                    "severity": "critical",
                    "message": f"{cert_name} expires in {days_left} days",
                })
            elif days_left <= days_threshold:
                alerts.append({
                    "cert_type": c["cert_type"],
                    "cert_name": cert_name,
                    "days_remaining": days_left,
                    "severity": "warning",
                    "message": f"{cert_name} expires in {days_left} days",
                })
        return {
            "vessel_id": vessel_id,
            "threshold_days": days_threshold,
            "total_alerts": len(alerts),
            "expired_count": sum(1 for a in alerts if a["severity"] == "expired"),
            "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
            "alerts": sorted(alerts, key=lambda x: x["days_remaining"]),
        }

    def validate_voyage_certs(self, vessel_id: int,
                              destination_zone: str = None) -> dict:
        required = [ct for ct, info in self.CERT_TYPES.items() if info["required"]]
        certs = self.db.fetchall(
            "SELECT * FROM certificates WHERE vessel_id=? AND status='active'",
            (vessel_id,))
        cert_map = {}
        for c in certs:
            cert_map[c["cert_type"]] = c
        now = datetime.utcnow()
        validation = []
        all_valid = True
        for ct in required:
            cert = cert_map.get(ct)
            if not cert:
                validation.append({
                    "cert_type": ct,
                    "name": self.CERT_TYPES[ct]["name"],
                    "status": "missing",
                    "valid": False,
                })
                all_valid = False
                continue
            try:
                exp = datetime.fromisoformat(cert["expiry_date"])
                days_left = (exp - now).days
            except (ValueError, TypeError):
                days_left = 0
            if days_left <= 0:
                validation.append({
                    "cert_type": ct,
                    "name": self.CERT_TYPES[ct]["name"],
                    "status": "expired",
                    "days_remaining": days_left,
                    "valid": False,
                })
                all_valid = False
            elif days_left <= 30:
                validation.append({
                    "cert_type": ct,
                    "name": self.CERT_TYPES[ct]["name"],
                    "status": "expiring_soon",
                    "days_remaining": days_left,
                    "valid": True,
                })
            else:
                validation.append({
                    "cert_type": ct,
                    "name": self.CERT_TYPES[ct]["name"],
                    "status": "valid",
                    "days_remaining": days_left,
                    "valid": True,
                })
        return {
            "vessel_id": vessel_id,
            "destination_zone": destination_zone,
            "all_certificates_valid": all_valid,
            "certificate_count": len(required),
            "valid_count": sum(1 for v in validation if v["valid"]),
            "invalid_count": sum(1 for v in validation if not v["valid"]),
            "certificates": validation,
            "voyage_clearance": all_valid,
        }
