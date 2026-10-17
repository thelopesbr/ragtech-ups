from types import SimpleNamespace

import pytest

from ragtech_ups import device
from ragtech_ups.exceptions import UPSConnectionError, UPSProtocolError


def _fake_ports(monkeypatch, ports):
    monkeypatch.setattr(device.list_ports, "comports", lambda: ports)


def test_find_port_by_usb_id(monkeypatch):
    _fake_ports(monkeypatch, [
        SimpleNamespace(device="/dev/ttyS0", vid=None, pid=None),
        SimpleNamespace(device="/dev/ttyACM0", vid=0x04D8, pid=0x000A),
    ])
    assert device.find_port() == "/dev/ttyACM0"


def test_find_port_not_found(monkeypatch):
    _fake_ports(monkeypatch, [SimpleNamespace(device="COM1", vid=None, pid=None)])
    with pytest.raises(UPSConnectionError):
        device.find_port()


def test_read_memory_retries_on_protocol_error(monkeypatch):
    ups = device.RagtechUPS("COM_TESTE", retries=3)
    calls = []

    def flaky(address, size):
        calls.append(address)
        if len(calls) < 3:
            raise UPSProtocolError("byte perdido")
        return b"\x00" * size

    monkeypatch.setattr(ups, "_read_memory_once", flaky)
    assert ups.read_memory(0x80, 4) == b"\x00" * 4
    assert len(calls) == 3


def test_read_memory_gives_up_after_retries(monkeypatch):
    ups = device.RagtechUPS("COM_TESTE", retries=2)

    def always_fails(address, size):
        raise UPSProtocolError("sempre falha")

    monkeypatch.setattr(ups, "_read_memory_once", always_fails)
    with pytest.raises(UPSProtocolError):
        ups.read_memory(0x80, 4)
