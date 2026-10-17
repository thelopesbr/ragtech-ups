#!/command/with-contenv bashio
# Lê as opções do app e as credenciais do broker MQTT e inicia a ponte

if ! bashio::services.available "mqtt"; then
    bashio::exit.nok "Nenhum broker MQTT encontrado. Instale e inicie o app Mosquitto broker."
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
    --host "$(bashio::services mqtt 'host')"
    --mqtt-port "$(bashio::services mqtt 'port')"
    --topic "$(bashio::config 'topic')"
    --interval "$(bashio::config 'interval')"
)
if bashio::config.true "ha_discovery"; then
    args+=(--ha-discovery)
fi
if bashio::config.true "publish_fields"; then
    args+=(--fields)
fi

mqtt_username="$(bashio::services mqtt 'username')"
if bashio::var.has_value "${mqtt_username}"; then
    args+=(--username "${mqtt_username}")
fi
# A senha vai por variável de ambiente para não aparecer na lista de processos
export MQTT_PASSWORD="$(bashio::services mqtt 'password')"

bashio::log.info "Iniciando a ponte do nobreak (tópico $(bashio::config 'topic'))"
exec ragtech-ups "${args[@]}"
