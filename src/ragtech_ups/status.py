from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class UPSStatus:
    """Uma leitura do nobreak."""

    model_code: int
    model_name: str
    firmware: float
    on_battery: bool                  # sem rede elétrica, alimentando pela bateria
    battery_charge_pct: float
    battery_voltage_v: float
    input_voltage_v: float
    output_voltage_v: float
    output_current_a: float
    output_power_pct: int
    output_power_w: int | None        # None quando a potência nominal não é informada
    temperature_c: int
    shutdown_countdown: int
    # Flags crus: o significado de cada bit ainda não foi mapeado
    event_flags: int
    fault_flags: int
    user_flags: int
    general_flags_2: int
    # Horário local com fuso (ex.: 2026-10-16T22:13:03-03:00)
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def to_dict(self) -> dict:
        """Dicionário serializável em JSON (timestamp em ISO 8601)."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat(timespec="seconds")
        return data
