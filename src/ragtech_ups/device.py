import logging
import time

import serial
from serial.tools import list_ports

from .exceptions import UPSConnectionError, UPSProtocolError
from .protocol import STATUS_ADDRESS, STATUS_SIZE, build_read_command, decode_status, parse_response
from .status import UPSStatus

log = logging.getLogger(__name__)

BAUD_RATE = 2560

# Conversor USB-serial (Microchip CDC) usado pelos nobreaks Ragtech
USB_VID = 0x04D8
USB_PID = 0x000A


def find_port() -> str:
    """Procura o nobreak pelo VID/PID USB (COMx no Windows, /dev/ttyACMx no Linux)."""
    for info in list_ports.comports():
        if info.vid == USB_VID and info.pid == USB_PID:
            return info.device
    raise UPSConnectionError(f"nenhum nobreak Ragtech encontrado (USB {USB_VID:04X}:{USB_PID:04X})")


class RagtechUPS:
    """
    Conexão com um nobreak Ragtech.

    Só um processo pode abrir a porta por vez; se o Supervise (serviço SupSrv)
    estiver rodando, `open()` levanta UPSConnectionError.

    Se `port` não for informado, a porta é detectada pelo VID/PID USB ao abrir.

    Exemplo:
        with RagtechUPS(nominal_power_w=1400) as ups:
            status = ups.read()
    """

    def __init__(self, port: str | None = None, nominal_power_w: int | None = None,
                 response_timeout: float = 2.0, retries: int = 3):
        self._requested_port = port
        self.port = port
        self.nominal_power_w = nominal_power_w
        self.response_timeout = response_timeout
        self.retries = retries
        self._serial: serial.Serial | None = None
        self.last_raw: bytes = b""

    def open(self) -> None:
        if self._serial is not None:
            return
        # Sem porta fixa, detecta de novo a cada abertura: ao reconectar o cabo
        # o nome pode mudar (ex.: /dev/ttyACM0 -> /dev/ttyACM1)
        self.port = self._requested_port or find_port()
        try:
            self._serial = serial.Serial(self.port, BAUD_RATE, timeout=0.5)
        except serial.SerialException as e:
            raise UPSConnectionError(f"não foi possível abrir {self.port}: {e}") from e
        # Dá tempo ao conversor USB-serial de estabilizar antes do primeiro pedido
        time.sleep(0.5)

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def __enter__(self) -> "RagtechUPS":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def read_memory(self, address: int, size: int) -> bytes:
        """Lê `size` bytes da memória do nobreak a partir de `address`."""
        # O nobreak às vezes perde um byte da resposta; nesse caso basta pedir de novo
        last_error: UPSProtocolError | None = None
        for attempt in range(1, max(1, self.retries) + 1):
            try:
                return self._read_memory_once(address, size)
            except UPSProtocolError as e:
                last_error = e
                log.debug("tentativa %d falhou: %s", attempt, e)
        raise last_error

    def _read_memory_once(self, address: int, size: int) -> bytes:
        if self._serial is None:
            raise UPSConnectionError("porta não está aberta; use open() ou 'with'")
        try:
            self._serial.reset_input_buffer()
            self._serial.write(build_read_command(address, size))
            response = self._receive(size + 1)
        except serial.SerialException as e:
            # Cabo desconectado ou porta perdida: fecha para permitir reabrir depois
            self.close()
            raise UPSConnectionError(f"falha de comunicação em {self.port}: {e}") from e
        self.last_raw = response
        return parse_response(response, size)

    def read(self) -> UPSStatus:
        """Faz uma leitura completa do status."""
        return decode_status(self.read_memory(STATUS_ADDRESS, STATUS_SIZE), self.nominal_power_w)

    def _receive(self, expected: int) -> bytes:
        response = b""
        deadline = time.monotonic() + self.response_timeout
        while time.monotonic() < deadline:
            chunk = self._serial.read(self._serial.in_waiting or 1)
            if chunk:
                response += chunk
            if len(response) >= expected and not self._serial.in_waiting:
                # Pequena espera para garantir que não há mais bytes a caminho
                time.sleep(0.05)
                if not self._serial.in_waiting:
                    break
        if not response:
            raise UPSProtocolError("o nobreak não respondeu")
        return response
