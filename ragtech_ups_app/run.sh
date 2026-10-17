#!/command/with-contenv bashio
# Lê as opções do app e as credenciais do broker MQTT e inicia a ponte

# Broker: o informado nas opções tem prioridade; senão, o do app Mosquitto (via Supervisor)
if bashio::config.has_value "mqtt_host"; then
    mqtt_host="$(bashio::config 'mqtt_host')"
    mqtt_port=1883
    mqtt_username=""
    mqtt_password=""
    if bashio::config.has_value "mqtt_port"; then
        mqtt_port="$(bashio::config 'mqtt_port')"
    fi
    if bashio::config.has_value "mqtt_username"; then
        mqtt_username="$(bashio::config 'mqtt_username')"
    fi
    if bashio::config.has_value "mqtt_password"; then
        mqtt_password="$(bashio::config 'mqtt_password')"
    fi
    bashio::log.info "Usando o broker MQTT das opções: ${mqtt_host}:${mqtt_port}"
elif bashio::services.available "mqtt"; then
    mqtt_host="$(bashio::services mqtt 'host')"
    mqtt_port="$(bashio::services mqtt 'port')"
    mqtt_username="$(bashio::services mqtt 'username')"
    mqtt_password="$(bashio::services mqtt 'password')"
    bashio::log.info "Usando o broker MQTT do app Mosquitto: ${mqtt_host}:${mqtt_port}"
else
    bashio::exit.nok "Nenhum broker MQTT encontrado. Inicie o app Mosquitto broker ou preencha mqtt_host (e usuário/senha) na configuração deste app."
fi

args=()
if bashio::config.has_value "port"; then
    args+=(--port "$(bashio::config 'port')")
fi
if bashio::config.has_value "nominal_power"; then
    args+=(--nominal-power "$(bashio::config 'nominal_power')")
fi
if bashio::config.true "debug"; then
    args+=(--verbose)
fi

args+=(mqtt
    --host "${mqtt_host}"
    --mqtt-port "${mqtt_port}"
    --topic "$(bashio::config 'topic')"
    --interval "$(bashio::config 'interval')"
)
if bashio::config.true "ha_discovery"; then
    args+=(--ha-discovery)
fi
if bashio::config.true "publish_fields"; then
    args+=(--fields)
fi
if bashio::var.has_value "${mqtt_username}"; then
    args+=(--username "${mqtt_username}")
fi
# A senha vai por variável de ambiente para não aparecer na lista de processos
export MQTT_PASSWORD="${mqtt_password}"

bashio::log.info "Iniciando a ponte do nobreak (tópico $(bashio::config 'topic'))"
exec ragtech-ups "${args[@]}"
