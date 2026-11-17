"""European Portuguese entity wording; no Home Assistant imports or network."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Reviewed wording, not protocol keys. Keep measurements and proprietary modes
# distinct: e.g. coil != room air, and Health is not a verified health benefit.
REVIEWED_LABELS = {
    "sensor.indoor_coil_temperature.name": "Temperatura do permutador interior",
    "sensor.outdoor_coil_temperature.name": "Temperatura do permutador exterior",
    "sensor.outdoor_in_temperature.name": "Temperatura de entrada da unidade exterior",
    "sensor.outdoor_out_temperature.name": "Temperatura de saída da unidade exterior",
    "sensor.compressor_current.name": "Corrente elétrica do compressor",
    "sensor.power.name": "Potência elétrica",
    "sensor.expansion_valve.name": "Válvula de expansão (valor bruto)",
    "sensor.operation_source.state.remote": "Comando à distância",
    "sensor.operation_source.state.panel": "Painel do aparelho",
    "binary_sensor.indoor_fan.name": "Ventilador interior em funcionamento",
    "binary_sensor.outdoor_fan.name": "Ventilador exterior em funcionamento",
    "binary_sensor.four_way_valve.name": "Válvula de quatro vias",
    "switch.health.name": "Função Health",
    "switch.display.name": "Iluminação do painel",
    "switch.self_clean.name": "Autolimpeza",
    "switch.lock_remote.name": "Bloqueio do comando à distância",
    "select.vertical_swing.name": "Direção vertical do fluxo de ar",
    "select.vertical_swing.state.auto": "Oscilação automática",
    "select.vertical_swing.state.health_up": "Posição Health para cima",
    "select.vertical_swing.state.health_down": "Posição Health para baixo",
    "climate.ac.state_attributes.fan_mode.state.quiet": "Silencioso",
    "climate.ac.state_attributes.preset_mode.state.none": "Sem predefinição",
    "climate.ac.state_attributes.preset_mode.state.boost": "Turbo",
    "climate.ac.state_attributes.preset_mode.state.sleep": "Modo noturno",
}


def leaves(value, prefix=""):
    if isinstance(value, dict):
        return {
            path: text
            for key, child in value.items()
            for path, text in leaves(child, f"{prefix}.{key}" if prefix else key).items()
        }
    return {prefix: value}


class PortugueseEntityTranslationTests(unittest.TestCase):
    def load_entities(self, language):
        path = ROOT / "custom_components/haier_smartair2/translations" / f"{language}.json"
        return leaves(json.loads(path.read_text())["entity"])

    def test_reviewed_pt_pt_labels(self):
        actual = self.load_entities("pt")
        for path, expected in REVIEWED_LABELS.items():
            with self.subTest(path=path):
                self.assertEqual(actual[path], expected)

    def test_existing_english_entity_translation_keys_are_preserved(self):
        english = self.load_entities("en")
        portuguese = self.load_entities("pt")
        self.assertEqual(set(portuguese), set(english))
        self.assertTrue(all(isinstance(value, str) and value.strip() for value in portuguese.values()))


if __name__ == "__main__":
    unittest.main()
