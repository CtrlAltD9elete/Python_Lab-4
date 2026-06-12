import re
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Вкажіть коректну email-адресу.")
        return value

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class UserLogin(BaseModel):
    login: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class IPLookupRequest(BaseModel):
    ip_address: IPvAnyAddress = Field(description="IPv4 або IPv6 адреса")


class Coordinates(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


class GeolocationResponse(BaseModel):
    ip_address: str
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    region_code: str | None = None
    city: str | None = None
    postal_code: str | None = None
    coordinates: Coordinates
    timezone: str | None = None
    timezone_utc: str | None = None
    isp: str | None = None
    organization: str | None = None
    asn: str | None = None
    provider: str
    requested_at: datetime

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ip_address": "8.8.8.8",
            "country": "United States",
            "country_code": "US",
            "region": "California",
            "region_code": "CA",
            "city": "Mountain View",
            "postal_code": "94043",
            "coordinates": {"latitude": 37.386, "longitude": -122.0838},
            "timezone": "America/Los_Angeles",
            "timezone_utc": "-07:00",
            "isp": "Google LLC",
            "organization": "Google Public DNS",
            "asn": "15169",
            "provider": "ipwho.is",
            "requested_at": "2026-06-11T12:00:00Z",
        }
    })


class HistoryItem(BaseModel):
    id: str
    ip_address: str
    requested_at: datetime
    geolocation: GeolocationResponse


IPAddress = IPv4Address | IPv6Address
