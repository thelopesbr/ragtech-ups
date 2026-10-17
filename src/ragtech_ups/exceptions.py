class UPSError(Exception):
    """Erro base da biblioteca."""


class UPSConnectionError(UPSError):
    """Não foi possível abrir a porta (ex.: ocupada pelo Supervise) ou ela caiu."""


class UPSProtocolError(UPSError):
    """O nobreak não respondeu ou respondeu algo fora do formato esperado."""
