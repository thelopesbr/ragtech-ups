"""
Comando de terminal `ragtech-ups`.

    ragtech-ups read                    # lê continuamente a cada 2 s (Ctrl+C para sair)
    ragtech-ups read --once --json      # uma leitura em JSON
    ragtech-ups mqtt --host 192.168.0.10 --topic casa/nobreak --ha-discovery
"""

import argparse
import json
import logging
import os
import sys
import time

from .device import RagtechUPS
from .exceptions import UPSConnectionError, UPSError

# Rótulos exibidos na saída em texto
LABELS = {
    "model_name": "Modelo (família)",
    "model_code": "Código de modelo",
    "firmware": "Firmware",
    "on_battery": "Em bateria",
    "battery_charge_pct": "Carga da bateria (%)",
    "battery_voltage_v": "Tensão da bateria (V)",
    "input_voltage_v": "Tensão de entrada (V)",
    "output_voltage_v": "Tensão de saída (V)",
    "output_current_a": "Corrente de saída (A)",
    "output_power_pct": "Potência de saída (%)",
    "output_power_w": "Potência de saída (W)",
    "temperature_c": "Temperatura (°C)",
    "shutdown_countdown": "Contador de shutdown",
    "event_flags": "Flags de eventos",
    "fault_flags": "Flags de falhas",
    "user_flags": "Flags de usuário",
    "general_flags_2": "Flags gerais 2",
}
FLAG_FIELDS = {"event_flags", "fault_flags", "user_flags", "general_flags_2"}


def print_status(data: dict) -> None:
    print(data["timestamp"])
    width = max(len(label) for label in LABELS.values())
    for key, label in LABELS.items():
        value = data[key]
        if key in FLAG_FIELDS:
            value = f"0x{value:02X}"
        elif isinstance(value, bool):
            value = "sim" if value else "não"
        print(f"  {label:<{width}}  {value}")
    if "_raw" in data:
        print(f"  {'Bytes crus':<{width}}  {data['_raw']}")


def cmd_read(ups: RagtechUPS, args: argparse.Namespace) -> int:
    # A primeira abertura falha direto (ex.: Supervise rodando); depois disso, quedas
    # da porta são tratadas abaixo, reabrindo na próxima volta
    ups.open()
    with ups:
        while True:
            try:
                ups.open()
                status = ups.read()
                data = status.to_dict()
                if args.raw:
                    data["_raw"] = ups.last_raw.hex(" ")
                if args.json:
                    print(json.dumps(data, ensure_ascii=False))
                else:
                    print_status(data)
                # Garante que cada leitura apareça na hora, mesmo redirecionando a saída
                sys.stdout.flush()
            except UPSError as e:
                print(f"Erro: {e}", file=sys.stderr)
                if args.once:
                    return 1
            if args.once:
                return 0
            time.sleep(args.interval)


def cmd_mqtt(ups: RagtechUPS, args: argparse.Namespace) -> int:
    from .mqtt import MQTTBridge

    bridge = MQTTBridge(
        ups,
        host=args.host,
        port=args.mqtt_port,
        base_topic=args.topic,
        username=args.username,
        password=os.environ.get("MQTT_PASSWORD"),
        client_id=args.client_id,
        interval=args.interval,
        publish_fields=args.fields,
        ha_discovery=args.ha_discovery,
        discovery_prefix=args.discovery_prefix,
        node_id=args.node_id,
    )
    bridge.run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ragtech-ups", description="Lê dados de nobreaks Ragtech.")
    parser.add_argument("--port", default=os.environ.get("UPS_PORT"),
                        help="porta serial, ex.: COM4 ou /dev/ttyACM0 (padrão: detecta pelo USB)")
    nominal_power = os.environ.get("UPS_NOMINAL_POWER")
    parser.add_argument("--nominal-power", type=int, default=int(nominal_power) if nominal_power else None,
                        metavar="W", help="potência ativa nominal em watts, para calcular a potência de saída "
                                          "(ex.: 1400 no One Up Nitro 2000)")
    parser.add_argument("-v", "--verbose", action="store_true", help="logs detalhados")
    sub = parser.add_subparsers(dest="command", required=True)

    read = sub.add_parser("read", help="mostra as leituras no terminal")
    read.add_argument("--interval", type=float, default=2.0, metavar="SEC", help="intervalo entre leituras (padrão: 2s)")
    read.add_argument("--once", action="store_true", help="faz uma única leitura e sai")
    read.add_argument("--json", action="store_true", help="saída em JSON")
    read.add_argument("--raw", action="store_true", help="mostra os bytes crus recebidos")
    read.set_defaults(handler=cmd_read)

    pub = sub.add_parser("mqtt", help="publica as leituras em um broker MQTT",
                         description="A senha do broker é lida da variável de ambiente MQTT_PASSWORD.")
    pub.add_argument("--host", default=os.environ.get("MQTT_HOST", "localhost"), help="broker (padrão: localhost)")
    pub.add_argument("--mqtt-port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    pub.add_argument("--username", default=os.environ.get("MQTT_USERNAME"))
    pub.add_argument("--client-id", default=None)
    pub.add_argument("--topic", default=os.environ.get("MQTT_TOPIC", "ragtech_ups/nobreak"),
                     help="tópico base (padrão: ragtech_ups/nobreak)")
    pub.add_argument("--interval", type=float, default=5.0, metavar="SEC", help="intervalo entre publicações (padrão: 5s)")
    pub.add_argument("--fields", action="store_true", help="publica também um tópico por campo")
    pub.add_argument("--ha-discovery", action="store_true", help="publica o MQTT Discovery do Home Assistant")
    pub.add_argument("--discovery-prefix", default="homeassistant", help="prefixo do discovery (padrão: homeassistant)")
    pub.add_argument("--node-id", default=None, help="id do dispositivo no Home Assistant (padrão: derivado do tópico)")
    pub.set_defaults(handler=cmd_mqtt)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ups = RagtechUPS(args.port, nominal_power_w=args.nominal_power)
    try:
        return args.handler(ups, args)
    except UPSConnectionError as e:
        print(f"Erro: {e}", file=sys.stderr)
        print("Se o Supervise (serviço SupSrv) estiver rodando, pare-o antes.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        # Ctrl+C encerra sem mostrar traceback
        return 0


if __name__ == "__main__":
    sys.exit(main())
