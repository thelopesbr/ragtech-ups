# Changelog

## 0.1.1

- Broker MQTT configurável nas opções (`mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`)
  para quem não usa o app Mosquitto. O app Mosquitto continua sendo usado automaticamente quando estiver rodando.

## 0.1.0

- Primeira versão: leitura do nobreak via USB, publicação em MQTT e MQTT Discovery do Home Assistant.
- Sensor binário "Em bateria" (bit 6 do byte de eventos).
