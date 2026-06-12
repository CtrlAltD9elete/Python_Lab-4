import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "GeoIP API"
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "lab4_geoip")
    jwt_secret: str = os.getenv("JWT_SECRET", "replace-this-secret-in-production")
    jwt_expires_minutes: int = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
    geo_provider_timeout: float = float(os.getenv("GEO_PROVIDER_TIMEOUT", "6"))


settings = Settings()
