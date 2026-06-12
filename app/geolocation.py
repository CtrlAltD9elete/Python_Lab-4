import asyncio
import ipaddress
import json
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.config import settings
from app.schemas import Coordinates, GeolocationResponse, IPAddress


async def get_ip_geolocation(ip_address: IPAddress) -> GeolocationResponse:
    parsed_ip = ipaddress.ip_address(str(ip_address))
    if not parsed_ip.is_global:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Локальні, приватні або службові IP-адреси не мають публічної геолокації.",
        )

    data = await asyncio.to_thread(_fetch_provider_data, str(parsed_ip))
    if not data.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=data.get("message") or "Інформацію про цю IP-адресу не знайдено.",
        )

    connection = data.get("connection") or {}
    timezone_data = data.get("timezone") or {}
    latitude = _to_float(data.get("latitude"))
    longitude = _to_float(data.get("longitude"))

    if not data.get("country") and latitude is None and longitude is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Провайдер не повернув геолокаційні дані для цієї IP-адреси.",
        )

    return GeolocationResponse(
        ip_address=data.get("ip") or str(parsed_ip),
        country=data.get("country"),
        country_code=data.get("country_code"),
        region=data.get("region"),
        region_code=data.get("region_code"),
        city=data.get("city"),
        postal_code=data.get("postal"),
        coordinates=Coordinates(latitude=latitude, longitude=longitude),
        timezone=timezone_data.get("id"),
        timezone_utc=timezone_data.get("utc"),
        isp=connection.get("isp"),
        organization=connection.get("org"),
        asn=str(connection["asn"]) if connection.get("asn") is not None else None,
        provider="ipwho.is",
        requested_at=datetime.now(timezone.utc),
    )


def _fetch_provider_data(ip_address: str) -> dict[str, Any]:
    fields = ",".join(
        [
            "success",
            "message",
            "ip",
            "country",
            "country_code",
            "region",
            "region_code",
            "city",
            "latitude",
            "longitude",
            "postal",
            "connection",
            "timezone",
        ]
    )
    url = f"https://ipwho.is/{quote(ip_address, safe='')}?fields={fields}"
    request = Request(url, headers={"User-Agent": "Lab4-GeoIP-FastAPI/1.0"})

    try:
        with urlopen(request, timeout=settings.geo_provider_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Геолокаційний сервіс повернув помилку HTTP {exc.code}.",
        ) from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Не вдалося отримати відповідь від геолокаційного сервісу.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Геолокаційний сервіс повернув некоректну відповідь.",
        ) from exc


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
