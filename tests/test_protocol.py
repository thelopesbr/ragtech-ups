import pytest

from ragtech_ups.exceptions import UPSProtocolError
from ragtech_ups.protocol import STATUS_ADDRESS, STATUS_SIZE, build_read_command, decode_status, parse_response

# Resposta real capturada do One Up Nitro 2000 em 16/10/2026
RAW_RESPONSE = bytes.fromhex(
    "aa 09 00 0c 38 ff ff ff ef d3 ee ca c9 0f 0b 2c f7 00 00 03 82 86 03 a7 2e 00 c9 10 0a 31 ca"
)


def test_build_read_command():
    assert build_read_command(STATUS_ADDRESS, STATUS_SIZE) == bytes.fromhex("aa 04 00 80 1e 9e")


def test_parse_response_strips_header():
    data = parse_response(RAW_RESPONSE, STATUS_SIZE)
    assert len(data) == STATUS_SIZE
    assert data[0] == 0x09


def test_parse_response_rejects_short_frame():
    with pytest.raises(UPSProtocolError):
        parse_response(RAW_RESPONSE[:10], STATUS_SIZE)


def test_parse_response_rejects_empty():
    with pytest.raises(UPSProtocolError):
        parse_response(b"", STATUS_SIZE)


def test_decode_status_one_up_nitro_2000():
    status = decode_status(parse_response(RAW_RESPONSE, STATUS_SIZE), nominal_power_w=1400)
    assert status.model_code == 16
    assert status.model_name == "NEP/Toro/Innergie 2000 TI"
    assert status.firmware == 1.0
    assert status.battery_charge_pct == 93.9
    assert status.battery_voltage_v == 27.07
    assert status.input_voltage_v == 213.1
    assert status.output_voltage_v == 112.1
    assert status.output_current_a == 2.39
    assert status.output_power_pct == 11
    assert status.output_power_w == 154
    assert status.temperature_c == 44
    assert status.event_flags == 0x00
    assert status.fault_flags == 0x00


def test_decode_status_without_nominal_power():
    status = decode_status(parse_response(RAW_RESPONSE, STATUS_SIZE))
    assert status.output_power_w is None


def test_to_dict_is_json_friendly():
    import json

    data = decode_status(parse_response(RAW_RESPONSE, STATUS_SIZE)).to_dict()
    assert isinstance(data["timestamp"], str)
    json.dumps(data)


# Resposta capturada com o nobreak fora da tomada (EVENTOS = 0x48)
RAW_RESPONSE_ON_BATTERY = bytes.fromhex(
    "aa 09 00 0c 38 ff ff ff f1 25 e1 b9 04 0b 0a 2c 00 48 00 02 82 c0 02 a7 2c 00 05 10 0a 31 cf"
)


def test_decode_status_on_mains():
    status = decode_status(parse_response(RAW_RESPONSE, STATUS_SIZE))
    assert status.on_battery is False


def test_decode_status_on_battery():
    status = decode_status(parse_response(RAW_RESPONSE_ON_BATTERY, STATUS_SIZE))
    assert status.on_battery is True
    assert status.input_voltage_v < 10
    assert status.event_flags == 0x48
