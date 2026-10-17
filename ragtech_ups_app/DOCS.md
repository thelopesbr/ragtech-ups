# Nobreak Ragtech

Lê o nobreak Ragtech ligado em uma porta USB do Home Assistant e cria o dispositivo
**Nobreak Ragtech** com o sensor binário **Em bateria** (falta de energia) e sensores de carga e tensão da bateria, tensões de entrada e saída,
corrente, potência e temperatura.

Testado com o **One Up Nitro 2000 (modelo 4590)**. Outros modelos da família NEP/Toro/Innergie/One Up
usam o mesmo protocolo.

## Antes de instalar

1. Tenha um broker MQTT e a integração **MQTT** configurados. Com o app **Mosquitto broker**
   rodando, as credenciais são obtidas automaticamente; com outro broker, preencha as opções `mqtt_*`.
2. Ligue o cabo USB do nobreak no Home Assistant (ex.: na Raspberry Pi). Ele aparece como `/dev/ttyACM0`.

## Configuração

| Opção | Descrição |
|---|---|
| `port` | Porta serial. Deixe vazio para detectar o nobreak pelo USB. |
| `nominal_power` | Potência ativa nominal em watts (ex.: `1400` no One Up Nitro 2000). Sem ela, o sensor de potência em W não é criado. |
| `topic` | Tópico MQTT base (padrão `ragtech_ups/nobreak`). Use um tópico diferente para cada nobreak. |
| `interval` | Intervalo entre leituras, em segundos. |
| `ha_discovery` | Cria o dispositivo e os sensores automaticamente no Home Assistant. |
| `publish_fields` | Publica também um tópico MQTT por campo (útil para Node-RED). |
| `debug` | Logs detalhados. |
| `mqtt_host` | Broker MQTT manual (ex.: `192.168.0.10`). Vazio = usa o app Mosquitto. |
| `mqtt_port` | Porta do broker manual (padrão `1883`). |
| `mqtt_username` / `mqtt_password` | Credenciais do broker manual. |

## Tópicos MQTT

- `<topic>/state`: JSON com a leitura completa.
- `<topic>/availability`: `online` / `offline`.

## Exemplo de automação

Avisar no celular quando faltar energia:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.nobreak_ragtech_em_bateria
    to: "on"
actions:
  - action: notify.notify
    data:
      message: "Falta de energia! Nobreak em bateria ({{ states('sensor.nobreak_ragtech_carga_da_bateria') }}%)."
```

Confira os ids reais das entidades em Configurações → Dispositivos → Nobreak Ragtech.

## Limitações

- Dos flags de eventos e falhas, só o "em bateria" foi mapeado; os demais aparecem como sensores de diagnóstico.
