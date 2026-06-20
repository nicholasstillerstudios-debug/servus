"""Integracao Bluetooth (BLE) via bleak."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class BLEDevice:
    address: str
    name: str
    rssi: int = 0

    def to_dict(self) -> dict:
        return self.__dict__


async def _scan_async(timeout: float = 6.0) -> list[BLEDevice]:
    try:
        from bleak import BleakScanner
    except Exception:
        return []
    items: list[BLEDevice] = []
    try:
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    except Exception:
        return []
    # bleak retorna dict {address: (BLEDevice, AdvertisementData)}
    if isinstance(devices, dict):
        for addr, (dev, adv) in devices.items():
            name = (adv.local_name or dev.name or "(sem nome)") if adv else (dev.name or "(sem nome)")
            rssi = getattr(adv, "rssi", 0) or 0
            items.append(BLEDevice(address=addr, name=name, rssi=rssi))
    else:
        for d in devices:
            items.append(BLEDevice(address=d.address, name=d.name or "(sem nome)", rssi=getattr(d, "rssi", 0) or 0))
    items.sort(key=lambda x: x.rssi, reverse=True)
    return items


def scan(timeout: float = 6.0) -> list[BLEDevice]:
    return asyncio.run(_scan_async(timeout))


def render_for_prompt(cfg: dict) -> str:
    known = (cfg.get("bluetooth") or {}).get("known") or []
    if not known:
        return ""
    lines = [
        "",
        "### Bluetooth (BLE)",
        "Voce pode escanear e interagir com dispositivos BLE proximos via bleak.",
        "",
        "```python",
        "import asyncio",
        "from bleak import BleakScanner, BleakClient",
        "async def ble_scan(timeout=6):",
        "    devs = await BleakScanner.discover(timeout=timeout)",
        "    return [(d.address, d.name) for d in devs]",
        "async def ble_read(address, char_uuid):",
        "    async with BleakClient(address) as c:",
        "        return await c.read_gatt_char(char_uuid)",
        "async def ble_write(address, char_uuid, data: bytes):",
        "    async with BleakClient(address) as c:",
        "        await c.write_gatt_char(char_uuid, data, response=True)",
        "# exemplo:",
        "# devs = asyncio.run(ble_scan())",
        "```",
        "",
        "Dispositivos conhecidos (pareados pelo usuario):",
    ]
    for d in known:
        lines.append(f"- `{d.get('address', '?')}` - {d.get('name', '?')}{(' [' + d.get('alias') + ']') if d.get('alias') else ''}")
    return "\n".join(lines)


__all__ = ["BLEDevice", "scan", "render_for_prompt"]
