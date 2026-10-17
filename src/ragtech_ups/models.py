"""
Tabela de modelos da família 10 (NEP/Toro/Innergie) e escalas por modelo.

Extraída de C:\\Program Files (x86)\\Supervise\\000\\upscfg10.cfg. O One Up Nitro
2000 (modelo 4590) se identifica como índice 16 ("2000 TI").
"""

from dataclasses import dataclass

MODEL_NAMES = [
    "NEP/Toro/Innergie 600 TI", "NEP/Toro/Innergie 600 M2",
    "NEP/Toro/Innergie 700 TI", "NEP/Toro/Innergie 700 M2",
    "NEP/Toro/Innergie 900 TI", "NEP/Toro/Innergie 900 M2",
    "NEP/Toro/Innergie 1200 TI", "NEP/Toro/Innergie 1200 M2",
    "NEP/Toro/Innergie 1300 TI", "NEP/Toro/Innergie 1300 M2",
    "NEP/Toro/Innergie 1400 TI", "NEP/Toro/Innergie 1400 M2",
    "NEP/Toro/Innergie 1600 TI", "NEP/Toro/Innergie 1600 M2",
    "NEP/Toro/Innergie 1800 TI", "NEP/Toro/Innergie 1800 M2",
    "NEP/Toro/Innergie 2000 TI", "NEP/Toro/Innergie 2000 M2",
    "NEP/Toro/Innergie 2200 TI", "NEP/Toro/Innergie 2200 M2",
]

# Escala da corrente de saída por modelo (seções [VARn] do .cfg)
OUTPUT_CURRENT_SCALES = [3.20, 1.70, 4.30, 2.30, 4.94, 2.64, 6.37, 3.41, 9.56, 5.11,
                         11.15, 5.96, 12.80, 6.80, 14.40, 7.65, 15.93, 8.52, 17.52, 9.37]

# Valor usado pelo .cfg na seção [VAR] padrão, quando o modelo é desconhecido
DEFAULT_OUTPUT_CURRENT_SCALE = 4.30


@dataclass(frozen=True)
class ModelInfo:
    code: int
    name: str
    battery_voltage_scale: float
    output_voltage_scale: float
    output_current_scale: float


def get_model_info(code: int) -> ModelInfo:
    known = code < len(MODEL_NAMES)
    is_m2 = code % 2 == 1                     # modelos ímpares são M2
    return ModelInfo(
        code=code,
        name=MODEL_NAMES[code] if known else "desconhecido",
        # A partir do índice 8 (1300 VA) o banco de baterias é de 24 V
        battery_voltage_scale=0.134 if code >= 8 else 0.067,
        output_voltage_scale=1.030 if is_m2 else 0.555,
        output_current_scale=OUTPUT_CURRENT_SCALES[code] if known else DEFAULT_OUTPUT_CURRENT_SCALE,
    )
