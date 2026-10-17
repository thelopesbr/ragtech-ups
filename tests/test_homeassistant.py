from ragtech_ups.homeassistant import build_discovery_messages
from ragtech_ups.protocol import STATUS_SIZE, decode_status, parse_response

from test_protocol import RAW_RESPONSE


def _status(nominal_power_w=1400):
    return decode_status(parse_response(RAW_RESPONSE, STATUS_SIZE), nominal_power_w)


def test_discovery_topics_and_device():
    messages = dict(build_discovery_messages(_status(), "casa/nobreak", "nobreak_sala"))

    topic = "homeassistant/sensor/nobreak_sala/battery_charge_pct/config"
    assert topic in messages
    config = messages[topic]
    assert config["unique_id"] == "nobreak_sala_battery_charge_pct"
    assert config["state_topic"] == "casa/nobreak/state"
    assert config["availability_topic"] == "casa/nobreak/availability"
    assert config["value_template"] == "{{ value_json.battery_charge_pct }}"
    assert config["device_class"] == "battery"
    assert config["unit_of_measurement"] == "%"
    assert config["device"]["model"] == "NEP/Toro/Innergie 2000 TI"


def test_discovery_skips_power_without_nominal_power():
    with_power = [t for t, _ in build_discovery_messages(_status(1400), "b", "n")]
    without_power = [t for t, _ in build_discovery_messages(_status(None), "b", "n")]
    assert any(t.endswith("/output_power_w/config") for t in with_power)
    assert not any(t.endswith("/output_power_w/config") for t in without_power)


def test_discovery_marks_flags_as_diagnostic():
    messages = dict(build_discovery_messages(_status(), "b", "n"))
    assert messages["homeassistant/sensor/n/fault_flags/config"]["entity_category"] == "diagnostic"
    assert "entity_category" not in messages["homeassistant/sensor/n/input_voltage_v/config"]


def test_discovery_has_on_battery_binary_sensor():
    messages = dict(build_discovery_messages(_status(), "casa/nobreak", "n"))
    config = messages["homeassistant/binary_sensor/n/on_battery/config"]
    assert config["unique_id"] == "n_on_battery"
    assert config["state_topic"] == "casa/nobreak/state"
    assert "on_battery" in config["value_template"]
