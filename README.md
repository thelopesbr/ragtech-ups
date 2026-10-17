# ragtech-ups

Leitura de nobreaks Ragtech da família NEP/Toro/Innergie/One Up via USB-serial, com ponte MQTT
e integração automática com o Home Assistant (MQTT Discovery).

Testado com o **One Up Nitro 2000 (modelo 4590)**, que aparece como dispositivo serial USB
(VID `04D8` / PID `000A`): `COMx` no Windows, `/dev/ttyACMx` no Linux. A porta é detectada sozinha.

> Só um programa pode usar a porta por vez. No Windows, pare o Supervise antes (PowerShell como admin):
> `Stop-Service SupSrv; Set-Service SupSrv -StartupType Manual`

## Home Assistant (app)

Se o Home Assistant roda em uma Raspberry Pi (ou outro hardware com HA OS), ligue o nobreak
direto nele e instale o app deste repositório:

1. Configurações → Apps → Instalar app → menu (⋮) → Repositórios
2. Adicione `https://github.com/thelopesbr/ragtech-ups`
3. Instale **Nobreak Ragtech**, informe `nominal_power` (ex.: 1400) e inicie.

O app usa o broker MQTT do próprio Home Assistant (app Mosquitto) e cria o dispositivo automaticamente.
Detalhes em [ragtech_ups_app/DOCS.md](ragtech_ups_app/DOCS.md).

## Instalação da lib

```bash
pip install "ragtech-ups[mqtt] @ git+https://github.com/thelopesbr/ragtech-ups.git"

# desenvolvimento, a partir do repositório
pip install -e ".[mqtt,dev]"
```

## Uso como biblioteca

```python
from ragtech_ups import RagtechUPS, UPSError

with RagtechUPS(nominal_power_w=1400) as ups:      # porta detectada pelo USB
    status = ups.read()
    print(status.battery_charge_pct, status.input_voltage_v, status.output_power_w)
    print(status.to_dict())                          # pronto para json.dumps
```

- `port`: opcional (`"COM4"`, `"/dev/ttyACM0"`); sem ele, a porta é detectada a cada abertura.
- `nominal_power_w`: potência ativa nominal do nobreak (ex.: 1400 no One Up Nitro 2000). Sem ela, `output_power_w` fica `None`.
- Erros: `UPSConnectionError` (porta ausente/ocupada/perdida) e `UPSProtocolError` (resposta inválida), ambos derivados de `UPSError`. Respostas inválidas são repetidas automaticamente (`retries=3`).

## Terminal

```bash
ragtech-ups read                          # lê a cada 2 s (Ctrl+C para sair)
ragtech-ups --nominal-power 1400 read --once --json
ragtech-ups --port /dev/ttyACM0 read --raw
```

## MQTT e Home Assistant

```bash
export MQTT_PASSWORD="segredo"            # PowerShell: $env:MQTT_PASSWORD = "segredo"
ragtech-ups --nominal-power 1400 mqtt --host 192.168.0.10 --username nobreak \
    --topic casa/nobreak --ha-discovery
```

Com `--ha-discovery`, o nobreak aparece sozinho no Home Assistant (Configurações → Dispositivos → MQTT)
como "Nobreak Ragtech", com o sensor binário **Em bateria** e sensores de carga e tensão da bateria, tensões de entrada/saída, corrente,
potência e temperatura.

| Tópico | Conteúdo |
|---|---|
| `<topic>/availability` | `online` / `offline` (retido; `offline` também é o LWT) |
| `<topic>/state` | JSON com a leitura completa (retido) |
| `<topic>/<campo>` | um valor por tópico, com `--fields` |
| `homeassistant/sensor/<node_id>/<campo>/config` | configuração do Discovery, com `--ha-discovery` |

Variáveis de ambiente aceitas: `UPS_PORT`, `UPS_NOMINAL_POWER`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`,
`MQTT_PASSWORD`, `MQTT_TOPIC`.

Dentro do seu código:

```python
from ragtech_ups import RagtechUPS
from ragtech_ups.mqtt import MQTTBridge

MQTTBridge(RagtechUPS(nominal_power_w=1400), host="192.168.0.10", ha_discovery=True).run()
```

## Linux

O conversor USB usa o driver padrão `cdc_acm`, então não há nada para instalar. Dois cuidados:

1. **Permissão**: o usuário precisa estar no grupo da porta (`dialout` no Debian/Ubuntu/Raspberry Pi OS,
   `uucp` no Arch): `sudo usermod -aG dialout $USER` e faça login de novo.
2. **ModemManager**: ele costuma "testar" portas `ttyACM` como se fossem modems, o que atrapalha a
   comunicação. Para ignorar o nobreak, crie `/etc/udev/rules.d/99-ragtech-ups.rules`:

   ```
   ATTRS{idVendor}=="04d8", ATTRS{idProduct}=="000a", ENV{ID_MM_DEVICE_IGNORE}="1", MODE="0660", GROUP="dialout"
   ```

   e rode `sudo udevadm control --reload-rules && sudo udevadm trigger`.

## Licença

MIT. Veja [LICENSE](LICENSE).

## Limitações conhecidas

- Dos flags, só o bit 6 de `event_flags` (0x40, "em bateria", exposto como `on_battery`) foi mapeado até agora; os demais bits seguem em hexa.
- A unidade da corrente de saída é uma suposição (escala do Supervise ÷ 100).
