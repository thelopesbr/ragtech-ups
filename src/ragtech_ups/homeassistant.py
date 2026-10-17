"""
MQTT Discovery do Home Assistant.

Gera as mensagens de configuração que fazem o nobreak aparecer sozinho no HA
como um dispositivo com sensores. Cada sensor lê o JSON publicado em
<base_topic>/state e usa <base_topic>/availability para ficar indisponível
quando a ponte cai.

Referência: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
"""

from dataclasses import dataclass

from . import __version__
from .status import UPSStatus


@dataclass(frozen=True)
class SensorSpec:
    key: str
    name: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    icon: str | None = None
    diagnostic: bool = False


SENSORS = [
    SensorSpec("battery_charge_pct", "Carga da bateria", "%", "battery"),
    SensorSpec("battery_voltage_v", "Tensão da bateria", "V", "voltage"),
    SensorSpec("input_voltage_v", "Tensão de entrada", "V", "voltage"),
    SensorSpec("output_voltage_v", "Tensão de saída", "V", "voltage"),
    SensorSpec("output_current_a", "Corrente de saída", "A", "current"),
    SensorSpec("output_power_pct", "Carga de saída", "%", icon="mdi:gauge"),
    SensorSpec("output_power_w", "Potência de saída", "W", "power"),
    SensorSpec("temperature_c", "Temperatura", "°C", "temperature"),
    SensorSpec("shutdown_countdown", "Contador de shutdown", icon="mdi:timer-outline", diagnostic=True),
    SensorSpec("event_flags", "Flags de eventos", state_class=None, icon="mdi:flag", diagnostic=True),
    SensorSpec("fault_flags", "Flags de falhas", state_class=None, icon="mdi:alert", diagnostic=True),
    SensorSpec("firmware", "Firmware", state_class=None, icon="mdi:chip", diagnostic=True),
]


def build_discovery_messages(status: UPSStatus, base_topic: str, node_id: str,
                             discovery_prefix: str = "homeassistant") -> list[tuple[str, dict]]:
    """Devolve a lista (tópico, payload) de configuração de cada entidade."""
    device = {
        "identifiers": [node_id],
        "name": "Nobreak Ragtech",
        "manufacturer": "Ragtech",
        "model": status.model_name,
        "sw_version": str(status.firmware),
    }
    common = {
        "state_topic": f"{base_topic}/state",
        "availability_topic": f"{base_topic}/availability",
        "device": device,
        "origin": {"name": "ragtech-ups", "sw_version": __version__},
    }
    messages = [(
        f"{discovery_prefix}/binary_sensor/{node_id}/on_battery/config",
        {
            "name": "Em bateria",
            "unique_id": f"{node_id}_on_battery",
            "value_template": "{{ 'ON' if value_json.on_battery else 'OFF' }}",
            "icon": "mdi:battery-alert-variant-outline",
            **common,
        },
    )]
    for spec in SENSORS:
        # Sem potência nominal configurada não há como calcular os watts
        if spec.key == "output_power_w" and status.output_power_w is None:
            continue
        config = {
            "name": spec.name,
            "unique_id": f"{node_id}_{spec.key}",
            "value_template": f"{{{{ value_json.{spec.key} }}}}",
            **common,
        }
        if spec.unit:
            config["unit_of_measurement"] = spec.unit
        if spec.device_class:
            config["device_class"] = spec.device_class
        if spec.state_class:
            config["state_class"] = spec.state_class
        if spec.icon:
            config["icon"] = spec.icon
        if spec.diagnostic:
            config["entity_category"] = "diagnostic"
        messages.append((f"{discovery_prefix}/sensor/{node_id}/{spec.key}/config", config))
    return messages
