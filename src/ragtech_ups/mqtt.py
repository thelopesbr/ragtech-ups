"""
Ponte nobreak -> MQTT.

Tópicos publicados (com <base> = base_topic, ex.: "ragtech_ups/nobreak"):
    <base>/availability   "online" / "offline" (retido; "offline" também é o LWT)
    <base>/state          JSON com a leitura completa (retido)
    <base>/<campo>        um tópico por campo, se publish_fields=True (retido)

Com ha_discovery=True, publica também a configuração do MQTT Discovery do
Home Assistant em <discovery_prefix>/sensor/<node_id>/<campo>/config.
"""

import json
import logging
import re
import threading

from .device import RagtechUPS
from .exceptions import UPSError
from .homeassistant import build_discovery_messages

try:
    import paho.mqtt.client as mqtt
except ImportError as e:  # pragma: no cover
    raise ImportError("a ponte MQTT precisa do paho-mqtt: pip install ragtech-ups[mqtt]") from e

log = logging.getLogger(__name__)

ONLINE = "online"
OFFLINE = "offline"


def _field_payload(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class MQTTBridge:
    def __init__(self, ups: RagtechUPS, host: str, port: int = 1883,
                 base_topic: str = "ragtech_ups/nobreak",
                 username: str | None = None, password: str | None = None,
                 client_id: str | None = None, interval: float = 5.0,
                 publish_fields: bool = False, qos: int = 1,
                 ha_discovery: bool = False, discovery_prefix: str = "homeassistant",
                 node_id: str | None = None):
        self.ups = ups
        # Espaços sobrando (comuns ao colar o endereço) quebram a resolução do nome
        self.host = host.strip()
        self.port = port
        self.base_topic = base_topic.rstrip("/")
        self.interval = interval
        self.publish_fields = publish_fields
        self.qos = qos
        self.ha_discovery = ha_discovery
        self.discovery_prefix = discovery_prefix.rstrip("/")
        # O node_id identifica o dispositivo no HA; por padrão vem do tópico base
        self.node_id = node_id or re.sub(r"[^a-zA-Z0-9_-]", "_", self.base_topic)
        self._discovery_sent = False
        self._available = False
        self._stop = threading.Event()

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id or "")
        if username:
            self.client.username_pw_set(username, password)
        # Se a ponte cair sem avisar, o broker publica "offline" por ela
        self.client.will_set(self._topic("availability"), OFFLINE, qos=qos, retain=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_connect_fail = self._on_connect_fail

    def run(self) -> None:
        """Lê o nobreak e publica até stop() ser chamado (ou Ctrl+C)."""
        # connect_async + loop_start: o paho reconecta sozinho se o broker cair
        self.client.connect_async(self.host, self.port)
        self.client.loop_start()
        try:
            while not self._stop.is_set():
                self._poll_once()
                self._stop.wait(self.interval)
        finally:
            self._set_available(False)
            self.ups.close()
            self.client.disconnect()
            self.client.loop_stop()

    def stop(self) -> None:
        self._stop.set()

    def _poll_once(self) -> None:
        try:
            self.ups.open()
            status = self.ups.read()
        except UPSError as e:
            log.warning("falha ao ler o nobreak: %s", e)
            # Fecha para que a próxima volta tente reabrir a porta do zero
            self.ups.close()
            self._set_available(False)
            return

        if self.ha_discovery and not self._discovery_sent:
            # Enviado após a primeira leitura para já levar o modelo e o firmware
            self._publish_discovery(status)
        payload = status.to_dict()
        self._publish("state", json.dumps(payload, ensure_ascii=False))
        if self.publish_fields:
            for key, value in payload.items():
                self._publish(key, _field_payload(value))
        self._set_available(True)
        log.debug("publicado: %s", payload)

    def _publish_discovery(self, status) -> None:
        for topic, config in build_discovery_messages(status, self.base_topic, self.node_id,
                                                      self.discovery_prefix):
            self.client.publish(topic, json.dumps(config, ensure_ascii=False), qos=self.qos, retain=True)
        self._discovery_sent = True
        log.info("discovery do Home Assistant publicado (node_id=%s)", self.node_id)

    def _set_available(self, available: bool) -> None:
        if available != self._available:
            self._available = available
            self._publish("availability", ONLINE if available else OFFLINE)

    def _publish(self, subtopic: str, payload: str) -> None:
        self.client.publish(self._topic(subtopic), payload, qos=self.qos, retain=True)

    def _topic(self, subtopic: str) -> str:
        return f"{self.base_topic}/{subtopic}"

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            log.error("broker recusou a conexão: %s", reason_code)
            return
        log.info("conectado ao broker %s:%s", self.host, self.port)
        # Após reconectar, o LWT pode ter marcado "offline"; republica o estado atual
        self._publish("availability", ONLINE if self._available else OFFLINE)

    def _on_connect_fail(self, client, userdata) -> None:
        # Falhas de rede/DNS não passam pelo on_connect; sem isto ficariam silenciosas
        log.warning("não foi possível conectar ao broker %s:%s; tentando de novo", self.host, self.port)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            log.warning("desconectado do broker (%s); tentando reconectar", reason_code)
