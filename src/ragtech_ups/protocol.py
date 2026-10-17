"""
Protocolo serial dos nobreaks Ragtech (família 10).

Pedido:   AA 04 <end_hi> <end_lo> <qtd> <checksum>   (checksum = soma de end_hi, end_lo e qtd)
Resposta: AA seguido diretamente dos <qtd> bytes de memória, sem checksum.
"""

from .exceptions import UPSProtocolError
from .models import get_model_info
from .status import UPSStatus

FRAME_HEADER = 0xAA

# Bits do byte de eventos (0x90), mapeados tirando o nobreak da tomada:
# o bit 6 acende na mesma leitura em que a rede cai e apaga ~2 s após ela voltar
EVENT_ON_BATTERY = 0x40

# Bloco principal de variáveis: 30 bytes a partir de 0x0080 (RANGE 01 do .cfg)
STATUS_ADDRESS = 0x0080
STATUS_SIZE = 30


def build_read_command(address: int, size: int) -> bytes:
    body = bytes([(address >> 8) & 0xFF, address & 0xFF, size])
    return bytes([FRAME_HEADER, 0x04]) + body + bytes([sum(body) & 0xFF])


def parse_response(response: bytes, size: int) -> bytes:
    """Extrai os `size` bytes de dados de uma resposta crua."""
    start = response.find(bytes([FRAME_HEADER]))
    if start < 0 or len(response) - start - 1 < size:
        raise UPSProtocolError(f"resposta inválida do nobreak: {response.hex(' ') or '(vazia)'}")
    return response[start + 1:start + 1 + size]


def decode_status(data: bytes, nominal_power_w: int | None = None) -> UPSStatus:
    """Converte o bloco de memória 0x80..0x9D em valores de engenharia."""
    if len(data) != STATUS_SIZE:
        raise UPSProtocolError(f"bloco de status com {len(data)} bytes, esperado {STATUS_SIZE}")

    def byte_at(address: int) -> int:
        return data[address - STATUS_ADDRESS]

    model = get_model_info(byte_at(0x9A))
    power_pct = byte_at(0x8D)
    events = byte_at(0x90)

    return UPSStatus(
        model_code=model.code,
        model_name=model.name,
        firmware=round(byte_at(0x9B) * 0.1, 1),
        on_battery=bool(events & EVENT_ON_BATTERY),
        battery_charge_pct=round(byte_at(0x87) * 0.393, 1),
        battery_voltage_v=round(byte_at(0x8A) * model.battery_voltage_scale, 2),
        input_voltage_v=round(byte_at(0x8B) * 1.060, 1),
        output_voltage_v=round(byte_at(0x9D) * model.output_voltage_scale, 1),
        # A divisão por 100 é uma suposição: o .cfg traz a escala, mas não a unidade
        output_current_a=round(byte_at(0x8C) * model.output_current_scale / 100, 2),
        output_power_pct=power_pct,
        output_power_w=round(power_pct * nominal_power_w / 100) if nominal_power_w else None,
        temperature_c=byte_at(0x8E),
        shutdown_countdown=byte_at(0x98),
        event_flags=events,
        fault_flags=byte_at(0x91),
        user_flags=byte_at(0x92),
        general_flags_2=byte_at(0x95),
    )
