"""Monitor de Hardware - CPU/RAM/disco/GPU/temperatura.

Stats em tempo real via psutil + nvidia-ml-py + WMI.
"""

from __future__ import annotations

import psutil


def cpu_stats() -> dict:
    freq = psutil.cpu_freq()
    return {
        "percent": psutil.cpu_percent(interval=0.1),
        "per_core": psutil.cpu_percent(interval=None, percpu=True),
        "freq_mhz": round(freq.current) if freq else 0,
        "freq_max_mhz": round(freq.max) if freq else 0,
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
    }


def ram_stats() -> dict:
    m = psutil.virtual_memory()
    s = psutil.swap_memory()
    return {
        "total_gb": round(m.total / 1e9, 2),
        "used_gb": round(m.used / 1e9, 2),
        "available_gb": round(m.available / 1e9, 2),
        "percent": m.percent,
        "swap_used_gb": round(s.used / 1e9, 2),
        "swap_percent": s.percent,
    }


def disk_stats() -> list[dict]:
    out = []
    for d in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(d.mountpoint)
            out.append({
                "mount": d.mountpoint,
                "fstype": d.fstype,
                "total_gb": round(u.total / 1e9, 2),
                "used_gb": round(u.used / 1e9, 2),
                "free_gb": round(u.free / 1e9, 2),
                "percent": u.percent,
            })
        except Exception:
            pass
    return out


def net_stats() -> dict:
    n = psutil.net_io_counters()
    return {
        "sent_mb": round(n.bytes_sent / 1e6, 1),
        "recv_mb": round(n.bytes_recv / 1e6, 1),
    }


def gpu_stats() -> list[dict]:
    try:
        import pynvml
        pynvml.nvmlInit()
        out = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            try: temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            except Exception: temp = None
            try: power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000  # W
            except Exception: power = None
            name = pynvml.nvmlDeviceGetName(h)
            if isinstance(name, bytes): name = name.decode("utf-8", errors="ignore")
            out.append({
                "name": name,
                "util_percent": util.gpu,
                "mem_util_percent": util.memory,
                "mem_used_gb": round(mem.used / 1e9, 2),
                "mem_total_gb": round(mem.total / 1e9, 2),
                "temp_c": temp,
                "power_w": round(power, 1) if power else None,
            })
        pynvml.nvmlShutdown()
        return out
    except Exception:
        return []


def cpu_temp_celsius() -> float | None:
    """Tenta varios caminhos para temperatura de CPU no Windows."""
    # 1) psutil (Linux/macOS - improvavel no Windows)
    try:
        temps = psutil.sensors_temperatures()
        for label, entries in temps.items():
            if entries and entries[0].current:
                return round(entries[0].current, 1)
    except Exception:
        pass
    # 2) WMI MSAcpi_ThermalZoneTemperature (funciona em alguns sistemas)
    try:
        import wmi
        w = wmi.WMI(namespace="root\\wmi")
        for t in w.MSAcpi_ThermalZoneTemperature():
            return round((t.CurrentTemperature / 10) - 273.15, 1)
    except Exception:
        pass
    # 3) OpenHardwareMonitor / LibreHardwareMonitor (precisa estar rodando)
    try:
        import wmi
        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        cpu_temps = [s.Value for s in w.Sensor()
                     if s.SensorType == "Temperature" and "CPU" in (s.Name or "")]
        if cpu_temps:
            return round(sum(cpu_temps) / len(cpu_temps), 1)
    except Exception:
        pass
    return None


def top_processes(n: int = 5) -> list[dict]:
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            procs.append({
                "name": info["name"],
                "cpu": info["cpu_percent"] or 0,
                "ram_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / 1e6, 1),
            })
        except Exception:
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:n]


def all_stats() -> dict:
    return {
        "cpu": cpu_stats(),
        "ram": ram_stats(),
        "disk": disk_stats(),
        "net": net_stats(),
        "gpu": gpu_stats(),
        "cpu_temp_c": cpu_temp_celsius(),
        "top_processes": top_processes(5),
    }


def render_for_prompt() -> str:
    return (
        "\n\n### Hardware monitor\n"
        "Voce pode consultar stats em tempo real:\n"
        "```python\n"
        "from app.sys_monitor import all_stats, cpu_stats, gpu_stats, top_processes\n"
        "s = all_stats()\n"
        "# {cpu, ram, disk, gpu, cpu_temp_c, top_processes, net}\n"
        "```\n"
    )
