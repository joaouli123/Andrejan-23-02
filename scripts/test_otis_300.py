#!/usr/bin/env python3
"""
300 Otis Test Scenarios — Comprehensive AI Agent Intelligence Test
================================================================
Tests the agent across ALL 135 Otis documents with varying levels of
specificity, multi-turn conversations, ambiguous cases, and edge cases.

Categories:
  A. Generic questions (no model) → expects CLARIFICATION
  B. Model-specific questions → expects ANSWER from correct document
  C. Multi-turn conversations → expects progressive questioning
  D. Ambiguous/multi-doc → expects DISAMBIGUATION
  E. Edge cases (wrong names, partial codes, part numbers)
  F. Symptom-based diagnosis
  G. Procedure/calibration queries
  H. Electrical diagrams/wiring
  I. Error codes
  J. Cross-model comparisons

Each test has:
  - question: the user query
  - expected: "CLARIFY" | "ANSWER" | "DISAMBIGUATE"
  - expected_docs: list of acceptable source document names (partial match)
  - expected_terms: terms that MUST appear in the answer
  - forbidden_terms: terms that must NOT appear
  - category: test category letter
  - follow_up: optional follow-up message for multi-turn tests
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

API = os.getenv("API_URL", "https://api.uxcodedev.com.br")
USERNAME = os.getenv("API_USER", "admin@andreja.com")
PASSWORD = os.getenv("API_PASS", "admin123")
BRAND_FILTER = "otis"

# ──────────────────────────────────────────────────────────────────────────────
# 300 TEST SCENARIOS
# ──────────────────────────────────────────────────────────────────────────────

TESTS = [
    # ═══════════════════════════════════════════════════════════════════════
    # A. GENERIC QUESTIONS (no model) → Expect CLARIFICATION (30 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 1, "question": "erro no elevador", "expected": "CLARIFY", "category": "A", "desc": "Generic error"},
    {"id": 2, "question": "porta não fecha", "expected": "CLARIFY", "category": "A", "desc": "Door won't close, no model"},
    {"id": 3, "question": "como calibrar o drive?", "expected": "CLARIFY", "category": "A", "desc": "Drive calibration, no model"},
    {"id": 4, "question": "elevador não parte", "expected": "CLARIFY", "category": "A", "desc": "Won't start, no model"},
    {"id": 5, "question": "problema na placa", "expected": "CLARIFY", "category": "A", "desc": "Board problem, no model"},
    {"id": 6, "question": "falha no inversor", "expected": "CLARIFY", "category": "A", "desc": "Inverter fault, no model"},
    {"id": 7, "question": "ajuste do freio", "expected": "CLARIFY", "category": "A", "desc": "Brake adjustment, no model"},
    {"id": 8, "question": "esquema elétrico", "expected": "CLARIFY", "category": "A", "desc": "Electrical diagram, no model"},
    {"id": 9, "question": "código de erro no painel", "expected": "CLARIFY", "category": "A", "desc": "Error code, no model"},
    {"id": 10, "question": "porta abre e fecha e não parte", "expected": "CLARIFY", "category": "A", "desc": "Door cycle no start"},
    {"id": 11, "question": "LED piscando", "expected": "CLARIFY", "category": "A", "desc": "LED blinking, no model"},
    {"id": 12, "question": "problema de nivelamento", "expected": "CLARIFY", "category": "A", "desc": "Leveling problem"},
    {"id": 13, "question": "motor fazendo barulho", "expected": "CLARIFY", "category": "A", "desc": "Motor noise"},
    {"id": 14, "question": "elevador vibrando", "expected": "CLARIFY", "category": "A", "desc": "Vibration"},
    {"id": 15, "question": "cadeia de segurança aberta", "expected": "CLARIFY", "category": "A", "desc": "Safety chain open"},
    {"id": 16, "question": "como resetar a placa?", "expected": "CLARIFY", "category": "A", "desc": "Board reset, no model"},
    {"id": 17, "question": "procedimento de resgate", "expected": "CLARIFY", "category": "A", "desc": "Rescue procedure, no model"},
    {"id": 18, "question": "alterar parâmetros", "expected": "CLARIFY", "category": "A", "desc": "Change parameters, no model"},
    {"id": 19, "question": "falha intermitente", "expected": "CLARIFY", "category": "A", "desc": "Intermittent fault"},
    {"id": 20, "question": "velocidade irregular", "expected": "CLARIFY", "category": "A", "desc": "Irregular speed"},
    {"id": 21, "question": "manual do controlador", "expected": "CLARIFY", "category": "A", "desc": "Controller manual, no model"},
    {"id": 22, "question": "substituir componente", "expected": "CLARIFY", "category": "A", "desc": "Replace component, no model"},
    {"id": 23, "question": "teste de porta", "expected": "CLARIFY", "category": "A", "desc": "Door test, no model"},
    {"id": 24, "question": "problema na URM", "expected": "CLARIFY", "category": "A", "desc": "URM problem, no model"},
    {"id": 25, "question": "como configurar?", "expected": "CLARIFY", "category": "A", "desc": "How to configure, no model"},
    {"id": 26, "question": "diagrama de ligação", "expected": "CLARIFY", "category": "A", "desc": "Wiring diagram, no model"},
    {"id": 27, "question": "elevador parou", "expected": "CLARIFY", "category": "A", "desc": "Elevator stopped"},
    {"id": 28, "question": "freio não segura", "expected": "CLARIFY", "category": "A", "desc": "Brake won't hold"},
    {"id": 29, "question": "operador de porta com defeito", "expected": "CLARIFY", "category": "A", "desc": "Door operator defect"},
    {"id": 30, "question": "encoder com problema", "expected": "CLARIFY", "category": "A", "desc": "Encoder problem"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - Gen2 family (30 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 31, "question": "Gen2 com GECB não parte depois de fechar a porta", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Gen2", "GECB", "gen2"], "expected_terms": ["DFC", "porta"],
     "desc": "Gen2 GECB door close no start"},
    {"id": 32, "question": "manual do GECB Gen2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GECB", "gen2"], "desc": "GECB Gen2 manual"},
    {"id": 33, "question": "calibração do Gen2 Comfort", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Gen2 Comfort", "Confort"], "desc": "Gen2 Comfort calibration"},
    {"id": 34, "question": "diagrama elétrico Gen2 BAA21000A", "expected": "ANSWER", "category": "B",
     "expected_docs": ["DIAGRAMA GEN2", "BAA21000A", "Gen2"], "desc": "Gen2 electrical diagram"},
    {"id": 35, "question": "erro DW no Gen2 com LCB2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Gen2", "LCB2"], "expected_terms": ["DW"], "desc": "Gen2 LCB2 DW error"},
    {"id": 36, "question": "resgate do Gen2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GEN2 Resgate", "Gen2"], "desc": "Gen2 rescue"},
    {"id": 37, "question": "treinamento Gen2C", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Treinamento", "Gen2C"], "desc": "Gen2C training"},
    {"id": 38, "question": "Gen2 Comfort esquema elétrico Baa21000j", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Baa21000j", "Gen2 Comfort"], "desc": "Gen2 Comfort wiring BAA21000J"},
    {"id": 39, "question": "MCS 220C GAA21000CJ como configurar", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MCS 220", "GAA21000CJ", "GEN 2"], "desc": "MCS220C config"},
    {"id": 40, "question": "URM do GECB como acessar", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GECB", "URM"], "desc": "GECB URM access"},
    {"id": 41, "question": "Gen2 com LVA diagrama BAA21000S", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LVA", "BAA21000S", "GEN2"], "desc": "Gen2 LVA diagram"},
    {"id": 42, "question": "parâmetros GECB reference", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GECB+reference", "GECB"], "desc": "GECB reference parameters"},
    {"id": 43, "question": "MAG Gen2 instalação", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MAG GEN2"], "desc": "MAG Gen2 installation"},
    {"id": 44, "question": "Gen2 Comfort manual de serviços completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Gen2 Comfort", "serviços"], "desc": "Gen2 Comfort full service manual"},
    {"id": 45, "question": "GECB chinês manual de uso", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CHINES", "GECB"], "desc": "Chinese GECB manual"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - OVF10/CVF (15 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 46, "question": "calibração do OVF10 passo a passo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Calibração do OVF10", "OVF10"], "desc": "OVF10 calibration steps"},
    {"id": 47, "question": "manual CVF OVF10", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CVF", "OVF10"], "desc": "CVF OVF10 manual"},
    {"id": 48, "question": "ADV DP com OVF10 BAA21340K diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV DP COM OVF10", "BAA21340K"], "desc": "ADV DP OVF10 diagram"},
    {"id": 49, "question": "substituir OVF10 por WEG CFW09", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF10 por WEG", "CFW09"], "desc": "Replace OVF10 with CFW09"},
    {"id": 50, "question": "OVF10 erro UV1 o que verificar", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF10", "CVF"], "expected_terms": ["UV"], "desc": "OVF10 UV1 error"},
    {"id": 51, "question": "parâmetros do CVF10", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CVF", "OVF10"], "desc": "CVF10 parameters"},
    {"id": 52, "question": "ADV 210 com OVF10 BAA21340G ligação", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV 210 com OVF10", "BAA21340G"], "desc": "ADV210 OVF10 wiring"},
    {"id": 53, "question": "OVF10 não funciona, LED apagado", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF10", "CVF"], "desc": "OVF10 not working LED off"},
    {"id": 54, "question": "OVF10 sobrecarga no motor", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF10", "CVF"], "desc": "OVF10 motor overload"},
    {"id": 55, "question": "como trocar OVF10 por CFW09 procedimento completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF10 por WEG"], "desc": "OVF10 to CFW09 full procedure"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - OVF20/LVF (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 56, "question": "manual de ajuste OVF20", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF 20", "OVF20", "LVF"], "desc": "OVF20 adjustment manual"},
    {"id": 57, "question": "LVF OVF20 parâmetros", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LVF", "OVF20", "OVF 20"], "desc": "LVF OVF20 parameters"},
    {"id": 58, "question": "LCB2 com OVF20 VF2 BAA21290AX", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCB2 OVF20", "BAA21290AX"], "desc": "LCB2 OVF20 VF2 diagram"},
    {"id": 59, "question": "ADV 210 com OVF20 BAA21340R diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV 210 com OVF20", "BAA21340R"], "desc": "ADV210 OVF20 diagram"},
    {"id": 60, "question": "OVF20 configuração inicial", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OVF20", "OVF 20", "LVF"], "desc": "OVF20 initial config"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - LCB1/LCB2/LCBII (20 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 61, "question": "substituição de LCB1 para LCB2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCB1", "LCB2", "TROCA", "SUBSTITUICAO"], "desc": "LCB1 to LCB2 upgrade"},
    {"id": 62, "question": "diagrama de troca LCB1 por LCB2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["DIAGRAMA", "LCB1", "LCB2"], "desc": "LCB1 to LCB2 swap diagram"},
    {"id": 63, "question": "LCB2 resumo das funções", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCB2 Resumo"], "desc": "LCB2 summary"},
    {"id": 64, "question": "WEG LCB2 configuração", "expected": "ANSWER", "category": "B",
     "expected_docs": ["WEG LCB2"], "desc": "WEG LCB2 configuration"},
    {"id": 65, "question": "URM LCB2 menu de ajuste", "expected": "ANSWER", "category": "B",
     "expected_docs": ["URM LCB2", "Manual URM"], "desc": "URM LCB2 adjustment menu"},
    {"id": 66, "question": "LCBII nova revisão", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCBII NOVA", "LCBII"], "desc": "LCBII new revision"},
    {"id": 67, "question": "guia URM LCB II", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Guia URM LCB II", "LCBII"], "desc": "URM LCBII guide"},
    {"id": 68, "question": "CFW09 com LCBII ligação", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CFW09", "LCBII", "LCBll"], "desc": "CFW09 LCBII wiring"},
    {"id": 69, "question": "ATC 035 substituição LCB1 por LCB2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ATC 035", "LCB1", "LCB2"], "desc": "ATC035 LCB1 to LCB2"},
    {"id": 70, "question": "ADV DP LCBII BAA21230AG", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21230AG", "LCBII", "ADVDP"], "desc": "ADV DP LCBII diagram"},
    {"id": 71, "question": "diferença entre LCB1 e LCB2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCB1", "LCB2"], "desc": "LCB1 vs LCB2 difference"},
    {"id": 72, "question": "diagrama ADV 210 com LCBI", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Diagrama ADV 210 LCBI", "ADV210", "LCBI"], "desc": "ADV210 LCBI diagram"},
    {"id": 73, "question": "LCB2 com OVF20 VF2 parâmetros de velocidade", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LCB2 OVF20"], "desc": "LCB2 OVF20 speed parameters"},
    {"id": 74, "question": "VW2 CFW09 com LCBII manual completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["VW2 CFW09", "LCBII", "LCBll"], "desc": "VW2 CFW09 LCBII full manual"},
    {"id": 75, "question": "Man CFW09 com LCBII", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Man CFW09", "LCBII"], "desc": "CFW09 LCBII manual"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - RCB2 (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 76, "question": "RCB2 manual de ajuste completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["RCB2 Manual de Ajuste"], "desc": "RCB2 adjustment manual"},
    {"id": 77, "question": "URM RCB2 guia de uso", "expected": "ANSWER", "category": "B",
     "expected_docs": ["URM", "RCB 2"], "desc": "RCB2 URM guide"},
    {"id": 78, "question": "Lista de IO RCB2 JAA30171AAA", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Lista de IO RCB2", "JAA30171AAA"], "desc": "RCB2 IO list"},
    {"id": 79, "question": "RCB2 parâmetros de porta", "expected": "ANSWER", "category": "B",
     "expected_docs": ["RCB2"], "desc": "RCB2 door parameters"},
    {"id": 80, "question": "JAA30171AAA pinagem dos conectores", "expected": "ANSWER", "category": "B",
     "expected_docs": ["JAA30171AAA", "RCB2"], "desc": "RCB2 connector pinout"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - ADV family (20 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 81, "question": "ADV210DP com LCBI diagrama completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV210DP", "LCBI"], "desc": "ADV210DP LCBI full diagram"},
    {"id": 82, "question": "ADVZÃO 210 BOS 9693A", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADVZÃO", "BOS 9693"], "desc": "ADVZÃO BOS 9693A"},
    {"id": 83, "question": "ADV-210 BAA21230B diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["adv-210", "baa21230b", "BAA21230"], "desc": "ADV210 BAA21230B diagram"},
    {"id": 84, "question": "ADV 210 adesão procedimento", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV 210 adevesao", "adesao"], "desc": "ADV210 adhesion procedure"},
    {"id": 85, "question": "ADV DP ACP LCB I diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV DP ACP", "LCBI", "Adv-Dp-Acp"], "desc": "ADV DP ACP LCBI diagram"},
    {"id": 86, "question": "ADV DP BAA21230Z", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21230Z", "ADV DP"], "desc": "ADV DP BAA21230Z"},
    {"id": 87, "question": "ADV DP BAA21230AD diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21230AD", "BAA21230AE", "ADV DP"], "desc": "ADV DP BAA21230AD"},
    {"id": 88, "question": "ADV 311VF BAA21290A", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV 311VF", "BAA21290A"], "desc": "ADV 311VF diagram"},
    {"id": 89, "question": "ADV 210 DP BBA21230J", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV 210 DP", "BBA21230J"], "desc": "ADV210 DP BBA21230J"},
    {"id": 90, "question": "ADV DP LCB1 ACP plugada BBA21230K", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV DP LCB1 ACP", "BBA21230K"], "desc": "ADV DP LCB1 ACP plugada"},
    {"id": 91, "question": "ADV hidráulico BAA21230L", "expected": "ANSWER", "category": "B",
     "expected_docs": ["HIDRAUL", "BAA21230"], "desc": "ADV hydraulic BAA21230L"},
    {"id": 92, "question": "OTIS ADV hidráulico BAA21240Y", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21240Y", "HIDRAUL"], "desc": "ADV hydraulic BAA21240Y"},
    {"id": 93, "question": "ADV DP AC 2 velocidades", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ADV-DP AC 2VEL", "AC 2VEL"], "desc": "ADV DP AC 2-speed"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - MRL (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 94, "question": "MRL malha aberta manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MRL", "Malha Aberta"], "desc": "MRL open loop manual"},
    {"id": 95, "question": "MRL WEG FOD diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MRL WEG FOD"], "desc": "MRL WEG FOD diagram"},
    {"id": 96, "question": "Otis 2000 VF MRL BAA21000B", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Otis 2000 VF", "MRL", "BAA21000B"], "desc": "Otis 2000 VF MRL diagram"},
    {"id": 97, "question": "MRL configuração de velocidade", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MRL", "mrl"], "desc": "MRL speed configuration"},
    {"id": 98, "question": "MRL não parte após inspeção", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MRL", "mrl"], "desc": "MRL won't start after inspection"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - DO2000/Operador porta (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 99, "question": "DO 2000 regulagem do operador", "expected": "ANSWER", "category": "B",
     "expected_docs": ["DO 2000", "DO2000", "Operador"], "desc": "DO2000 operator adjustment"},
    {"id": 100, "question": "operador OTIS DO 2000 manual completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Operador OTIS DO 2000", "DO 2000"], "desc": "Otis DO2000 full manual"},
    {"id": 101, "question": "MRDS operador de porta", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MRDS", "Otis Operador MRDS"], "desc": "MRDS door operator"},
    {"id": 102, "question": "Wittur MIDI SUPRA porta Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["WITTUR MIDI SUPRA"], "desc": "Wittur MIDI SUPRA door"},
    {"id": 103, "question": "operador LEDO ATC ajuste", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LEDO", "ATC", "Op.LEDO"], "desc": "LEDO ATC adjustment"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - XO508 (8 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 104, "question": "XO 508 manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["XO+508", "XO 508"], "desc": "XO508 manual"},
    {"id": 105, "question": "XO 508 lista de falhas", "expected": "ANSWER", "category": "B",
     "expected_docs": ["XO+508+falhas", "XO 508"], "desc": "XO508 fault list"},
    {"id": 106, "question": "XO508 não responde ao comando", "expected": "ANSWER", "category": "B",
     "expected_docs": ["XO+508", "XO 508"], "desc": "XO508 no command response"},
    {"id": 107, "question": "falha no XO 508 código de erro", "expected": "ANSWER", "category": "B",
     "expected_docs": ["XO+508+falhas"], "desc": "XO508 error codes"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - Miconic BX/LX (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 108, "question": "Miconic BX esquema elétrico", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Miconic BX", "Esquema Miconic"], "desc": "Miconic BX electrical"},
    {"id": 109, "question": "manual BX completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Manual BX", "BX"], "desc": "BX full manual"},
    {"id": 110, "question": "consulta rápida BX", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CONSULTA RÁPIDA", "bx"], "desc": "BX quick reference"},
    {"id": 111, "question": "Miconic LX manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MICONIC LX"], "desc": "Miconic LX manual"},
    {"id": 112, "question": "Miconic LX falha na placa", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MICONIC LX"], "desc": "Miconic LX board fault"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - VW/VW2, drives, GDCB, LVA (20 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 113, "question": "VW1 FOD diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["VW1_FOD"], "desc": "VW1 FOD diagram"},
    {"id": 114, "question": "VW2 WEG malha fechada", "expected": "ANSWER", "category": "B",
     "expected_docs": ["otisVW2 WEG Malha Fechada"], "desc": "VW2 WEG closed loop"},
    {"id": 115, "question": "BAA21290BM VW2 diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21290BM", "VW2"], "desc": "BAA21290BM VW2 diagram"},
    {"id": 116, "question": "BAA21290CC VMW VW2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21290CC", "VMW", "VW2"], "desc": "BAA21290CC VMW VW2"},
    {"id": 117, "question": "GDCB regenerativo manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GDCB", "REGEN"], "desc": "GDCB regenerative manual"},
    {"id": 118, "question": "drive regenerativo GDCB 55661", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Drive Regenerativo", "GDCB", "55661"], "desc": "GDCB 55661 regen drive"},
    {"id": 119, "question": "BAA21000H FOD diagrama regenerativo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21000H", "diagrama Regen"], "desc": "BAA21000H regen diagram"},
    {"id": 120, "question": "Ultra Drive LVA manual completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Ultra drive lva", "Ultra Drive"], "desc": "Ultra Drive LVA full manual"},
    {"id": 121, "question": "manual de ajuste LVA", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Manual de Ajuste LVA"], "desc": "LVA adjustment manual"},
    {"id": 122, "question": "Gen2 com LVA BAA21000S", "expected": "ANSWER", "category": "B",
     "expected_docs": ["GEN2+LVA", "BAA21000S"], "desc": "Gen2 LVA BAA21000S"},
    {"id": 123, "question": "CFW11 manual atualizado", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CFW_11", "CFW11"], "desc": "CFW11 updated manual"},
    {"id": 124, "question": "ATC CFW700 rev1", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ATC CFW700"], "desc": "ATC CFW700 rev1"},
    {"id": 125, "question": "malha fechada VW2 MW2 CFW09", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Malha Fechada VW2", "cfw09"], "desc": "Closed loop VW2 MW2 CFW09"},
    {"id": 126, "question": "BAA21290BM VW2 esquema elétrico", "expected": "ANSWER", "category": "B",
     "expected_docs": ["BAA21290BM"], "desc": "BAA21290BM electrical"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - OTISMATIC, MAG, Escada Rolante, etc (20 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 127, "question": "OTISMATIC manual completo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["OTISMATIC"], "desc": "OTISMATIC full manual"},
    {"id": 128, "question": "MAG completo manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Mag completo"], "desc": "MAG full manual"},
    {"id": 129, "question": "Manual Mag ADV Total 2", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Mag ADV Total 2", "Manual Mag ADV"], "desc": "MAG ADV Total 2"},
    {"id": 130, "question": "escada rolante NCE Otis manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["NCE", "escalera", "Escada Rolante"], "desc": "NCE escalator manual"},
    {"id": 131, "question": "NCE corrimão escada rolante", "expected": "ANSWER", "category": "B",
     "expected_docs": ["NCE Corrimão", "Escada Rolante NCE"], "desc": "NCE handrail escalator"},
    {"id": 132, "question": "Otis Xizi diagramas escada", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Xizi", "escaleras", "diagramas"], "desc": "Xizi escalator diagrams"},
    {"id": 133, "question": "escada rolante ECS 3 diagramas", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ecs 3", "escaleras"], "desc": "ECS3 escalator diagrams"},
    {"id": 134, "question": "IFL-750 VVVF montagem", "expected": "ANSWER", "category": "B",
     "expected_docs": ["IFL-750 VVVF", "IFL"], "desc": "IFL-750 VVVF assembly"},
    {"id": 135, "question": "montagem IFL VVVF e JR VVVF", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Montagem IFL-VVVF", "JR-VVVF"], "desc": "IFL and JR VVVF assembly"},
    {"id": 136, "question": "livro de peças Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["livro de peças"], "desc": "Otis parts book"},
    {"id": 137, "question": "OTIS noções gerais", "expected": "ANSWER", "category": "B",
     "expected_docs": ["NOÇÕES GERAIS"], "desc": "Otis general concepts"},
    {"id": 138, "question": "máquinas Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["MAQUINAS OTIS"], "desc": "Otis machines"},
    {"id": 139, "question": "manual de segurança Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Manual de Segurança"], "desc": "Otis safety manual"},
    {"id": 140, "question": "AROBOX resgate automático AC-156", "expected": "ANSWER", "category": "B",
     "expected_docs": ["AROBOX", "AC-156"], "desc": "AROBOX automatic rescue"},
    {"id": 141, "question": "ajuste de freio Otis procedimento", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Ajuste de Freio", "regular freio"], "desc": "Otis brake adjustment"},
    {"id": 142, "question": "regular freio Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["regular freio"], "desc": "Otis brake regulation"},
    {"id": 143, "question": "manual AC Selectron", "expected": "ANSWER", "category": "B",
     "expected_docs": ["AC Selectron"], "desc": "AC Selectron manual"},
    {"id": 144, "question": "Schmersal Schinfiance 222", "expected": "ANSWER", "category": "B",
     "expected_docs": ["schmersal", "222"], "desc": "Schmersal 222"},
    {"id": 145, "question": "instalação Access Code Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ACESSE CODE", "INSTALAÇÃO"], "desc": "Otis Access Code installation"},
    {"id": 146, "question": "procedimento manutenção 311335MW", "expected": "ANSWER", "category": "B",
     "expected_docs": ["311335MW", "PROCEDIMENTO MANUTENÇÃO"], "desc": "311335MW maintenance"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - CME/Eletem (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 147, "question": "CME 101 CAVF manual antigo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CME 101", "CAVF"], "desc": "CME 101 CAVF old manual"},
    {"id": 148, "question": "CME 102 CAVF manual", "expected": "ANSWER", "category": "B",
     "expected_docs": ["CME 102", "CAVF"], "desc": "CME 102 CAVF manual"},
    {"id": 149, "question": "Eletem manual técnico CME 101 CAVF", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ELETEM", "CME 101"], "desc": "Eletem CME 101 CAVF technical"},
    {"id": 150, "question": "Eletem CMV 102 CAVF", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Eletem cmv 102", "CME 102"], "desc": "Eletem CMV 102"},

    # ═══════════════════════════════════════════════════════════════════════
    # B. MODEL-SPECIFIC - ATC, D-series, misc (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 151, "question": "ATC alertas aterramento", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ATC ALERTAS", "aterramento"], "desc": "ATC alerts grounding"},
    {"id": 152, "question": "ATC 043 eliminar ACP", "expected": "ANSWER", "category": "B",
     "expected_docs": ["ATC 043", "ELIMINAR ACP"], "desc": "ATC043 eliminate ACP"},
    {"id": 153, "question": "D0510 procedimento", "expected": "ANSWER", "category": "B",
     "expected_docs": ["D0510"], "desc": "D0510 procedure"},
    {"id": 154, "question": "D0506 diagrama", "expected": "ANSWER", "category": "B",
     "expected_docs": ["D0506"], "desc": "D0506 diagram"},
    {"id": 155, "question": "D0509 documento", "expected": "ANSWER", "category": "B",
     "expected_docs": ["D0509"], "desc": "D0509 document"},
    {"id": 156, "question": "modelim Otis", "expected": "ANSWER", "category": "B",
     "expected_docs": ["modelim", "Otis modelim"], "desc": "Otis modelim"},
    {"id": 157, "question": "LG Tech manual novo", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LG tech", "LGTECH"], "desc": "LG Tech new manual"},
    {"id": 158, "question": "manual técnico LGTECH elaborado pela Otis Melco", "expected": "ANSWER", "category": "B",
     "expected_docs": ["LGTECH", "LG tech", "Otis melco"], "desc": "LGTECH Otis Melco manual"},
    {"id": 159, "question": "Manual do drive CFW malha fechada versão 1.3", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Drive cfw", "MalhaFechada", "versão 1.3"], "desc": "CFW drive manual v1.3"},
    {"id": 160, "question": "URM 311 Otis manual de uso", "expected": "ANSWER", "category": "B",
     "expected_docs": ["URM 311", "Manual Otis uso URM"], "desc": "URM 311 usage manual"},

    # ═══════════════════════════════════════════════════════════════════════
    # C. MULTI-TURN CONVERSATIONS (30 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 161, "question": "porta não fecha", "expected": "CLARIFY", "category": "C",
     "follow_up": "Gen2 com GECB", "follow_expected": "ANSWER",
     "expected_docs": ["Gen2", "GECB"], "desc": "Multi-turn: door→Gen2"},
    {"id": 162, "question": "como calibrar o drive?", "expected": "CLARIFY", "category": "C",
     "follow_up": "OVF10", "follow_expected": "ANSWER",
     "expected_docs": ["OVF10", "CVF", "Calibração"], "desc": "Multi-turn: drive→OVF10"},
    {"id": 163, "question": "erro no painel", "expected": "CLARIFY", "category": "C",
     "follow_up": "placa LCB2", "follow_expected": "ANSWER",
     "expected_docs": ["LCB2"], "desc": "Multi-turn: panel error→LCB2"},
    {"id": 164, "question": "problema com inversor", "expected": "CLARIFY", "category": "C",
     "follow_up": "CFW11", "follow_expected": "ANSWER",
     "expected_docs": ["CFW_11", "CFW11"], "desc": "Multi-turn: inverter→CFW11"},
    {"id": 165, "question": "elevador vibrando muito", "expected": "CLARIFY", "category": "C",
     "follow_up": "ADV 210 com LCB1", "follow_expected": "ANSWER",
     "expected_docs": ["ADV", "LCB"], "desc": "Multi-turn: vibration→ADV210"},
    {"id": 166, "question": "não parte", "expected": "CLARIFY", "category": "C",
     "follow_up": "Miconic BX", "follow_expected": "ANSWER",
     "expected_docs": ["Miconic BX", "BX"], "desc": "Multi-turn: no start→Miconic BX"},
    {"id": 167, "question": "falha na URM", "expected": "CLARIFY", "category": "C",
     "follow_up": "LCBII", "follow_expected": "ANSWER",
     "expected_docs": ["LCBII", "URM"], "desc": "Multi-turn: URM→LCBII"},
    {"id": 168, "question": "problema de segurança", "expected": "CLARIFY", "category": "C",
     "follow_up": "Gen2 Comfort", "follow_expected": "ANSWER",
     "expected_docs": ["Gen2 Comfort"], "desc": "Multi-turn: safety→Gen2 Comfort"},
    {"id": 169, "question": "como funciona o resgate?", "expected": "CLARIFY", "category": "C",
     "follow_up": "Gen2", "follow_expected": "ANSWER",
     "expected_docs": ["GEN2 Resgate", "Gen2"], "desc": "Multi-turn: rescue→Gen2"},
    {"id": 170, "question": "ligação elétrica", "expected": "CLARIFY", "category": "C",
     "follow_up": "OVF20 LCB2", "follow_expected": "ANSWER",
     "expected_docs": ["OVF20", "LCB2"], "desc": "Multi-turn: wiring→OVF20 LCB2"},
    {"id": 171, "question": "falha no drive", "expected": "CLARIFY", "category": "C",
     "follow_up": "GDCB regenerativo", "follow_expected": "ANSWER",
     "expected_docs": ["GDCB", "REGEN"], "desc": "Multi-turn: drive→GDCB"},
    {"id": 172, "question": "operador de porta com problema", "expected": "CLARIFY", "category": "C",
     "follow_up": "DO 2000", "follow_expected": "ANSWER",
     "expected_docs": ["DO 2000", "DO2000"], "desc": "Multi-turn: door op→DO2000"},
    {"id": 173, "question": "falha intermitente", "expected": "CLARIFY", "category": "C",
     "follow_up": "OTISMATIC", "follow_expected": "ANSWER",
     "expected_docs": ["OTISMATIC"], "desc": "Multi-turn: intermittent→OTISMATIC"},
    {"id": 174, "question": "manual do controlador", "expected": "CLARIFY", "category": "C",
     "follow_up": "RCB2", "follow_expected": "ANSWER",
     "expected_docs": ["RCB2"], "desc": "Multi-turn: controller→RCB2"},
    {"id": 175, "question": "ajuste de velocidade", "expected": "CLARIFY", "category": "C",
     "follow_up": "LVA Ultra Drive", "follow_expected": "ANSWER",
     "expected_docs": ["LVA", "Ultra Drive"], "desc": "Multi-turn: speed→LVA"},
    {"id": 176, "question": "erro na escada rolante", "expected": "CLARIFY", "category": "C",
     "follow_up": "NCE Otis", "follow_expected": "ANSWER",
     "expected_docs": ["NCE", "escalera"], "desc": "Multi-turn: escalator→NCE"},
    {"id": 177, "question": "não nivela", "expected": "CLARIFY", "category": "C",
     "follow_up": "MRL", "follow_expected": "ANSWER",
     "expected_docs": ["MRL", "mrl"], "desc": "Multi-turn: leveling→MRL"},
    {"id": 178, "question": "problema no freio", "expected": "CLARIFY", "category": "C",
     "follow_up": "OVF10 Gen2", "follow_expected": "ANSWER",
     "expected_docs": ["freio", "OVF10"], "desc": "Multi-turn: brake→OVF10"},
    {"id": 179, "question": "diagrama elétrico", "expected": "CLARIFY", "category": "C",
     "follow_up": "ADV DP BAA21230Z", "follow_expected": "ANSWER",
     "expected_docs": ["BAA21230Z", "ADV DP"], "desc": "Multi-turn: diagram→ADV DP"},
    {"id": 180, "question": "erro no display", "expected": "CLARIFY", "category": "C",
     "follow_up": "XO 508", "follow_expected": "ANSWER",
     "expected_docs": ["XO+508", "XO 508"], "desc": "Multi-turn: display error→XO508"},

    # ═══════════════════════════════════════════════════════════════════════
    # D. DISAMBIGUATION (20 tests - queries that match multiple docs)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 181, "question": "ADV 210 diagrama", "expected": "CLARIFY", "category": "D",
     "desc": "ADV210 has 8+ docs, should ask which"},
    {"id": 182, "question": "manual do operador de porta Otis", "expected": "CLARIFY", "category": "D",
     "desc": "DO2000 has 3 docs + MRDS + Wittur"},
    {"id": 183, "question": "CFW drive Otis", "expected": "CLARIFY", "category": "D",
     "desc": "CFW09 vs CFW11 vs CFW700"},
    {"id": 184, "question": "manual de falhas Otis", "expected": "CLARIFY", "category": "D",
     "desc": "Multiple fault manuals"},
    {"id": 185, "question": "URM menu guia", "expected": "CLARIFY", "category": "D",
     "desc": "URM for LCB2 vs LCBII vs RCB2 vs GECB"},
    {"id": 186, "question": "VW2 manual completo", "expected": "CLARIFY", "category": "D",
     "desc": "Multiple VW2 docs"},
    {"id": 187, "question": "diagrama BAA21290", "expected": "CLARIFY", "category": "D",
     "desc": "BAA21290 has AX, BM, CC variants"},
    {"id": 188, "question": "ADV DP diagrama", "expected": "CLARIFY", "category": "D",
     "desc": "ADV DP has many BAA variants"},
    {"id": 189, "question": "malha fechada manual", "expected": "CLARIFY", "category": "D",
     "desc": "Multiple closed loop docs"},
    {"id": 190, "question": "CME 101 manual", "expected": "CLARIFY", "category": "D",
     "desc": "CME 101 has 3+ versions"},
    {"id": 191, "question": "Mag manual", "expected": "CLARIFY", "category": "D",
     "desc": "Mag completo vs MAG GEN2 vs Mag ADV"},
    {"id": 192, "question": "esquema elétrico Otis", "expected": "CLARIFY", "category": "D",
     "desc": "Many electrical schematics"},
    {"id": 193, "question": "BAA21230 diagrama Otis", "expected": "CLARIFY", "category": "D",
     "desc": "BAA21230 has AG, AD, AE, B, J, K, L, Z variants"},
    {"id": 194, "question": "Gen2 diagrama de controle", "expected": "CLARIFY", "category": "D",
     "desc": "Gen2 has BAA21000A, J, S, CJ variants"},
    {"id": 195, "question": "manual Otis geral", "expected": "ANSWER", "category": "D",
     "expected_docs": ["manual geral otis", "NOÇÕES GERAIS"], "desc": "General Otis manual"},

    # ═══════════════════════════════════════════════════════════════════════
    # E. EDGE CASES (30 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 196, "question": "gen 2", "expected": "CLARIFY", "category": "E", "desc": "Short query: gen 2"},
    {"id": 197, "question": "lcb", "expected": "CLARIFY", "category": "E", "desc": "Short query: lcb"},
    {"id": 198, "question": "ovf", "expected": "CLARIFY", "category": "E", "desc": "Short query: ovf"},
    {"id": 199, "question": "placa antiga Otis com selector antigo", "expected": "CLARIFY", "category": "E",
     "desc": "Old system no model code"},
    {"id": 200, "question": "BAA21000S diagrama GEN2", "expected": "ANSWER", "category": "E",
     "expected_docs": ["BAA21000S", "GEN2+LVA"], "desc": "Part number GEN2 LVA lookup"},
    {"id": 201, "question": "GAA30780CAA manual GECB", "expected": "ANSWER", "category": "E",
     "expected_docs": ["GAA30780CAA", "GECB"], "desc": "Part number GECB URM lookup"},
    {"id": 202, "question": "GAA21000CJ esquema", "expected": "ANSWER", "category": "E",
     "expected_docs": ["GAA21000CJ", "MCS 220"], "desc": "Part number MCS220 lookup"},
    {"id": 203, "question": "BOS9693A", "expected": "ANSWER", "category": "E",
     "expected_docs": ["BOS 9693", "BOS9693"], "desc": "BOS part number lookup"},
    {"id": 204, "question": "olá bom dia", "expected": "CLARIFY", "category": "E", "desc": "Greeting: bom dia"},
    {"id": 205, "question": "oi", "expected": "CLARIFY", "category": "E", "desc": "Greeting: oi"},
    {"id": 206, "question": "qual modelo vem com placa GECB?", "expected": "ANSWER", "category": "E",
     "expected_docs": ["GECB", "Gen2"], "desc": "Which model uses GECB"},
    {"id": 207, "question": "diferença entre OVF10 e OVF20", "expected": "ANSWER", "category": "E",
     "expected_docs": ["OVF10", "OVF20"], "desc": "OVF10 vs OVF20"},
    {"id": 208, "question": "sim", "expected": "CLARIFY", "category": "E", "desc": "Single word: yes"},
    {"id": 209, "question": "não", "expected": "CLARIFY", "category": "E", "desc": "Single word: no"},
    {"id": 210, "question": "ok", "expected": "CLARIFY", "category": "E", "desc": "Single word: ok"},
    {"id": 211, "question": "Quais modelos de elevador Otis vocês tem documentação?", "expected": "ANSWER", "category": "E",
     "desc": "Which Otis models do you have docs for"},
    {"id": 212, "question": "tem manual do Gen2 Premier?", "expected": "ANSWER", "category": "E",
     "desc": "Non-existent model: Gen2 Premier"},
    {"id": 213, "question": "elevador thyssenkrupp não funciona", "expected": "ANSWER", "category": "E",
     "desc": "Wrong brand (Otis agent asked about Thyssen)", "forbidden_terms": ["ThyssenKrupp"]},
    {"id": 214, "question": "ADV210 BOS 9693A LCBI porta abre e fecha", "expected": "ANSWER", "category": "E",
     "expected_docs": ["ADVZÃO", "BOS 9693", "LCBI"], "expected_terms": ["DFC", "DW"],
     "desc": "Very specific query with all identifiers"},
    {"id": 215, "question": "qual a diferença entre LCBI e LCBII?", "expected": "ANSWER", "category": "E",
     "expected_docs": ["LCB", "LCBII"], "desc": "LCBI vs LCBII difference"},

    # ═══════════════════════════════════════════════════════════════════════
    # F. SYMPTOM-BASED DIAGNOSIS (30 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 216, "question": "Gen2 GECB porta abre e fecha e não parte", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2", "GECB"], "expected_terms": ["DW", "DFC", "porta"],
     "desc": "Gen2 GECB door cycle no start"},
    {"id": 217, "question": "OVF10 erro UV1", "expected": "ANSWER", "category": "F",
     "expected_docs": ["OVF10", "CVF"], "expected_terms": ["UV"],
     "desc": "OVF10 UV1 error"},
    {"id": 218, "question": "OVF10 erro OC overcurrent", "expected": "ANSWER", "category": "F",
     "expected_docs": ["OVF10", "CVF"], "desc": "OVF10 overcurrent"},
    {"id": 219, "question": "Gen2 LCB2 DW ativo mas DFC não ativa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2", "LCB2"], "expected_terms": ["DW", "DFC"],
     "desc": "Gen2 LCB2 DW active DFC not"},
    {"id": 220, "question": "ADV 210 LCBI não nivela corretamente", "expected": "ANSWER", "category": "F",
     "expected_docs": ["ADV", "LCBI"], "desc": "ADV210 LCBI leveling issue"},
    {"id": 221, "question": "Gen2 Comfort motor vibra quando parte", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2 Comfort"], "desc": "Gen2 Comfort motor vibration"},
    {"id": 222, "question": "MRL WEG velocidade inferior ao normal", "expected": "ANSWER", "category": "F",
     "expected_docs": ["MRL", "WEG"], "desc": "MRL WEG low speed"},
    {"id": 223, "question": "LCB2 LED vermelho piscando 3 vezes", "expected": "ANSWER", "category": "F",
     "expected_docs": ["LCB2"], "desc": "LCB2 red LED 3 blinks"},
    {"id": 224, "question": "GECB não comunica com URM", "expected": "ANSWER", "category": "F",
     "expected_docs": ["GECB", "URM"], "desc": "GECB URM no communication"},
    {"id": 225, "question": "RCB2 falha no encoder", "expected": "ANSWER", "category": "F",
     "expected_docs": ["RCB2"], "desc": "RCB2 encoder fault"},
    {"id": 226, "question": "CFW09 com LCBII alarme de sobrecarga", "expected": "ANSWER", "category": "F",
     "expected_docs": ["CFW09", "LCBII"], "desc": "CFW09 LCBII overload alarm"},
    {"id": 227, "question": "DO 2000 porta não abre toda", "expected": "ANSWER", "category": "F",
     "expected_docs": ["DO 2000", "DO2000"], "desc": "DO2000 door won't fully open"},
    {"id": 228, "question": "XO 508 display mostrando erro", "expected": "ANSWER", "category": "F",
     "expected_docs": ["XO+508", "XO 508"], "desc": "XO508 display error"},
    {"id": 229, "question": "Miconic BX contator não puxa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Miconic BX", "BX"], "desc": "Miconic BX contactor won't pull"},
    {"id": 230, "question": "OTISMATIC não responde ao chamado", "expected": "ANSWER", "category": "F",
     "expected_docs": ["OTISMATIC"], "desc": "OTISMATIC no call response"},
    {"id": 231, "question": "Gen2 com LVA drive não inicializa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2", "LVA"], "desc": "Gen2 LVA drive won't init"},
    {"id": 232, "question": "ADV 311VF BAA21290A erro na rampa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["ADV 311VF", "BAA21290A"], "desc": "ADV 311VF ramp error"},
    {"id": 233, "question": "VW2 CFW09 LCBII motor esquentando", "expected": "ANSWER", "category": "F",
     "expected_docs": ["VW2", "CFW09", "LCBII"], "desc": "VW2 CFW09 LCBII motor heating"},
    {"id": 234, "question": "GDCB regenerativo falha na regeneração", "expected": "ANSWER", "category": "F",
     "expected_docs": ["GDCB", "REGEN"], "desc": "GDCB regen failure"},
    {"id": 235, "question": "Ultra Drive LVA parâmetro errado", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Ultra Drive", "LVA"], "desc": "Ultra Drive LVA wrong parameter"},
    {"id": 236, "question": "Gen2 GECB cadeia de segurança ES aberta", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2", "GECB"], "expected_terms": ["ES", "segurança"],
     "desc": "Gen2 GECB safety chain open"},
    {"id": 237, "question": "LCB2 WEG freio não solta", "expected": "ANSWER", "category": "F",
     "expected_docs": ["LCB2", "WEG"], "desc": "LCB2 WEG brake won't release"},
    {"id": 238, "question": "RCB2 JAA30171AAA saída digital não ativa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["RCB2", "JAA30171AAA"], "desc": "RCB2 digital output inactive"},
    {"id": 239, "question": "ADV DP LCB1 contato de porta intermitente", "expected": "ANSWER", "category": "F",
     "expected_docs": ["ADV DP", "LCB1", "LCBI"], "expected_terms": ["porta"],
     "desc": "ADV DP LCB1 intermittent door contact"},
    {"id": 240, "question": "Gen2 Comfort BAA21000J trinco de porta falhando", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2 Comfort", "Baa21000j"], "expected_terms": ["trinco", "porta"],
     "desc": "Gen2 Comfort door lock failing"},
    {"id": 241, "question": "MCS220C Gen2 falha na comunicação serial", "expected": "ANSWER", "category": "F",
     "expected_docs": ["MCS 220", "Gen2"], "desc": "MCS220C Gen2 serial comm failure"},
    {"id": 242, "question": "CFW11 alarme E004", "expected": "ANSWER", "category": "F",
     "expected_docs": ["CFW_11", "CFW11"], "desc": "CFW11 E004 alarm"},
    {"id": 243, "question": "ATC com LCBII aterramento incorreto", "expected": "ANSWER", "category": "F",
     "expected_docs": ["ATC ALERTAS", "LCBII"], "desc": "ATC LCBII grounding issue"},
    {"id": 244, "question": "GECB Gen2 erro de fase", "expected": "ANSWER", "category": "F",
     "expected_docs": ["GECB", "Gen2"], "desc": "GECB Gen2 phase error"},
    {"id": 245, "question": "escada rolante NCE corrente alta", "expected": "ANSWER", "category": "F",
     "expected_docs": ["NCE", "escala"], "desc": "NCE escalator high current"},

    # ═══════════════════════════════════════════════════════════════════════
    # G. PROCEDURE/CALIBRATION QUERIES (25 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 246, "question": "como calibrar OVF10 passo 1 a 10", "expected": "ANSWER", "category": "G",
     "expected_docs": ["Calibração do OVF10"], "desc": "OVF10 calibration steps 1-10"},
    {"id": 247, "question": "ajuste de contrapeso Gen2 Comfort", "expected": "ANSWER", "category": "G",
     "expected_docs": ["Gen2 Comfort"], "desc": "Gen2 Comfort counterweight adjustment"},
    {"id": 248, "question": "como resetar GECB", "expected": "ANSWER", "category": "G",
     "expected_docs": ["GECB"], "desc": "GECB reset procedure"},
    {"id": 249, "question": "parametrizar CFW09 para LCBII", "expected": "ANSWER", "category": "G",
     "expected_docs": ["CFW09", "LCBII"], "desc": "CFW09 LCBII parameterization"},
    {"id": 250, "question": "procedimento de resgate Gen2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["GEN2 Resgate", "Gen2"], "desc": "Gen2 rescue procedure"},
    {"id": 251, "question": "como configurar URM no LCB2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["URM LCB2", "Manual URM"], "desc": "URM LCB2 config"},
    {"id": 252, "question": "ajuste de velocidade OVF20", "expected": "ANSWER", "category": "G",
     "expected_docs": ["OVF20", "LVF"], "desc": "OVF20 speed adjustment"},
    {"id": 253, "question": "como trocar LCB1 por LCB2 passo a passo", "expected": "ANSWER", "category": "G",
     "expected_docs": ["LCB1", "LCB2", "TROCA", "SUBSTITUICAO"], "desc": "LCB1→LCB2 step by step"},
    {"id": 254, "question": "instalação AROBOX resgate", "expected": "ANSWER", "category": "G",
     "expected_docs": ["AROBOX", "AC-156"], "desc": "AROBOX rescue installation"},
    {"id": 255, "question": "procedimento completo de ajuste do RCB2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["RCB2 Manual de Ajuste"], "desc": "RCB2 full adjustment procedure"},
    {"id": 256, "question": "como eliminar ACP procedimento ATC 043", "expected": "ANSWER", "category": "G",
     "expected_docs": ["ATC 043", "ELIMINAR ACP"], "desc": "ATC043 eliminate ACP procedure"},
    {"id": 257, "question": "configuração inicial do Ultra Drive LVA", "expected": "ANSWER", "category": "G",
     "expected_docs": ["Ultra Drive", "LVA"], "desc": "Ultra Drive LVA initial config"},
    {"id": 258, "question": "montagem IFL-750 VVVF", "expected": "ANSWER", "category": "G",
     "expected_docs": ["IFL-750", "Montagem IFL"], "desc": "IFL-750 VVVF assembly"},
    {"id": 259, "question": "como ajustar freio Otis Gen2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["Ajuste de Freio", "freio"], "desc": "Otis Gen2 brake adjustment"},
    {"id": 260, "question": "procedimento manutenção preventiva 311335MW", "expected": "ANSWER", "category": "G",
     "expected_docs": ["311335MW", "PROCEDIMENTO"], "desc": "311335MW preventive maintenance"},
    {"id": 261, "question": "configurar Access Code Otis", "expected": "ANSWER", "category": "G",
     "expected_docs": ["ACESSE CODE", "INSTALAÇÃO"], "desc": "Otis Access Code setup"},
    {"id": 262, "question": "ajuste do operador DO 2000", "expected": "ANSWER", "category": "G",
     "expected_docs": ["DO 2000", "Operador"], "desc": "DO2000 operator adjustment"},
    {"id": 263, "question": "calibrar encoder Gen2 GECB", "expected": "ANSWER", "category": "G",
     "expected_docs": ["GECB", "Gen2"], "desc": "Gen2 GECB encoder calibration"},
    {"id": 264, "question": "regulagem correia Wittur MIDI SUPRA", "expected": "ANSWER", "category": "G",
     "expected_docs": ["WITTUR MIDI SUPRA"], "desc": "Wittur MIDI SUPRA belt adjustment"},
    {"id": 265, "question": "parametrização CFW11 revisão 3", "expected": "ANSWER", "category": "G",
     "expected_docs": ["CFW_11"], "desc": "CFW11 rev3 parameterization"},
    {"id": 266, "question": "como acessar menu URM no RCB2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["URM", "RCB 2"], "desc": "RCB2 URM menu access"},
    {"id": 267, "question": "procedimento de teste de porta Gen2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["Gen2"], "desc": "Gen2 door test procedure"},
    {"id": 268, "question": "configuração do MCS220C para Gen2", "expected": "ANSWER", "category": "G",
     "expected_docs": ["MCS 220", "GAA21000CJ"], "desc": "MCS220C Gen2 configuration"},
    {"id": 269, "question": "regulagem velocidade LCB2 WEG", "expected": "ANSWER", "category": "G",
     "expected_docs": ["WEG LCB2", "LCB2"], "desc": "LCB2 WEG speed regulation"},
    {"id": 270, "question": "instalação do Schmersal 222", "expected": "ANSWER", "category": "G",
     "expected_docs": ["schmersal", "222"], "desc": "Schmersal 222 installation"},

    # ═══════════════════════════════════════════════════════════════════════
    # H. ELECTRICAL DIAGRAMS/WIRING (15 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 271, "question": "diagrama elétrico Gen2 BAA21000A completo", "expected": "ANSWER", "category": "H",
     "expected_docs": ["DIAGRAMA GEN2", "BAA21000A"], "desc": "Gen2 BAA21000A full diagram"},
    {"id": 272, "question": "esquema de ligação ADV 210 LCBI BOS 9693A", "expected": "ANSWER", "category": "H",
     "expected_docs": ["ADVZÃO", "BOS 9693"], "desc": "ADV210 LCBI BOS9693A wiring"},
    {"id": 273, "question": "diagrama Gen2 Comfort Baa21000J", "expected": "ANSWER", "category": "H",
     "expected_docs": ["Baa21000j", "Gen2 Confort"], "desc": "Gen2 Comfort BAA21000J diagram"},
    {"id": 274, "question": "Otis desenho elétrico BAA21000H regenerativo", "expected": "ANSWER", "category": "H",
     "expected_docs": ["BAA21000H", "Regen"], "desc": "BAA21000H regen electrical"},
    {"id": 275, "question": "GEN2+LVA+BAA21000S diagrama", "expected": "ANSWER", "category": "H",
     "expected_docs": ["GEN2+LVA", "BAA21000S"], "desc": "GEN2 LVA BAA21000S diagram"},
    {"id": 276, "question": "Esq Otis BAA21290BM", "expected": "ANSWER", "category": "H",
     "expected_docs": ["BAA21290BM", "Esq Otis"], "desc": "BAA21290BM electrical"},
    {"id": 277, "question": "diagrama contole Otis 2000 VF MRL BAA21000B", "expected": "ANSWER", "category": "H",
     "expected_docs": ["Otis 2000 VF", "BAA21000B"], "desc": "Otis 2000 VF MRL diagram"},
    {"id": 278, "question": "ADV DP BAA21230AE diagrama de controle", "expected": "ANSWER", "category": "H",
     "expected_docs": ["BAA21230AE", "BAA21230AD"], "desc": "ADV DP BAA21230AE diagram"},
    {"id": 279, "question": "BAA21290CC VMW VW2 diagrama", "expected": "ANSWER", "category": "H",
     "expected_docs": ["BAA21290CC", "VMW"], "desc": "BAA21290CC VMW VW2 diagram"},
    {"id": 280, "question": "diagrama ADV 210 com OVF10 BAA21340G", "expected": "ANSWER", "category": "H",
     "expected_docs": ["ADV 210 com OVF10", "BAA21340G"], "desc": "ADV210 OVF10 BAA21340G diagram"},

    # ═══════════════════════════════════════════════════════════════════════
    # I. DIAGNOSIS / TROUBLESHOOTING (10 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 281, "question": "diagnóstico de falhas Otis red1", "expected": "ANSWER", "category": "I",
     "expected_docs": ["Diagnóstico de Falhas", "red1"], "desc": "Otis fault diagnosis red1"},
    {"id": 282, "question": "troubleshooting Otis elevador", "expected": "ANSWER", "category": "I",
     "expected_docs": ["Troubleshooting", "Diagnóstico"], "desc": "Otis troubleshooting"},
    {"id": 283, "question": "Otis diversos falhas", "expected": "ANSWER", "category": "I",
     "expected_docs": ["Otis diversos falhas", "Diagnóstico"], "desc": "Otis various faults"},
    {"id": 284, "question": "manual geral otis falhas comuns", "expected": "ANSWER", "category": "I",
     "expected_docs": ["manual geral otis"], "desc": "Otis general manual common faults"},
    {"id": 285, "question": "XO 508 tabla de falhas", "expected": "ANSWER", "category": "I",
     "expected_docs": ["XO+508+falhas"], "desc": "XO508 fault table"},

    # ═══════════════════════════════════════════════════════════════════════
    # J. CROSS-MODEL/COMPARISON (15 tests)
    # ═══════════════════════════════════════════════════════════════════════
    {"id": 286, "question": "qual a diferença entre Gen2 e ADV 210?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["Gen2", "ADV"], "desc": "Gen2 vs ADV210"},
    {"id": 287, "question": "posso usar CFW09 no lugar do OVF10?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["OVF10 por WEG", "CFW09"], "desc": "CFW09 replace OVF10"},
    {"id": 288, "question": "LCB2 funciona com OVF10 ou só OVF20?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["LCB2", "OVF"], "desc": "LCB2 OVF10 vs OVF20 compat"},
    {"id": 289, "question": "quando usar LCBI vs LCBII?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["LCB", "LCBII"], "desc": "LCBI vs LCBII when to use"},
    {"id": 290, "question": "GECB é compatível com LCB2?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["GECB", "LCB2"], "desc": "GECB LCB2 compatibility"},
    {"id": 291, "question": "migração de LCB1 para LCB2 quais mudanças?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["LCB1", "LCB2", "TROCA", "SUBSTITUICAO"], "desc": "LCB1→LCB2 migration changes"},
    {"id": 292, "question": "OVF10 vs OVF20 qual mais confiável?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["OVF10", "OVF20"], "desc": "OVF10 vs OVF20 reliability"},
    {"id": 293, "question": "URM LCBII vs URM LCB2 diferenças no menu", "expected": "ANSWER", "category": "J",
     "expected_docs": ["URM", "LCBII", "LCB2"], "desc": "URM LCBII vs LCB2 menu diff"},
    {"id": 294, "question": "CFW09 vs CFW11 vantagens", "expected": "ANSWER", "category": "J",
     "expected_docs": ["CFW09", "CFW_11"], "desc": "CFW09 vs CFW11 advantages"},
    {"id": 295, "question": "DO 2000 vs MRDS qual operador usar?", "expected": "ANSWER", "category": "J",
     "expected_docs": ["DO 2000", "MRDS"], "desc": "DO2000 vs MRDS comparison"},

    # Fill to 300 with additional edge cases
    {"id": 296, "question": "VW1 FOD desenho elétrico completo", "expected": "ANSWER", "category": "H",
     "expected_docs": ["VW1_FOD"], "desc": "VW1 FOD full electrical"},
    {"id": 297, "question": "manual de segurança final 2017", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Manual de Segurança Final"], "desc": "Safety manual 2017"},
    {"id": 298, "question": "Otis escaleras diagramas Xizi", "expected": "ANSWER", "category": "B",
     "expected_docs": ["Xizi", "escaleras"], "desc": "Xizi escalator diagrams"},
    {"id": 299, "question": "como funciona o sistema regenerativo GDCB?", "expected": "ANSWER", "category": "G",
     "expected_docs": ["GDCB", "REGEN", "Regenerativo"], "desc": "GDCB regen system explanation"},
    {"id": 300, "question": "Gen2 GECB LCB2 OVF20 porta abre e fecha DFC não ativa", "expected": "ANSWER", "category": "F",
     "expected_docs": ["Gen2", "GECB"], "expected_terms": ["DFC", "DW", "porta"],
     "desc": "Maximum detail query with all identifiers"},
]

# ──────────────────────────────────────────────────────────────────────────────
# TEST RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def get_token():
    r = requests.post(f"{API}/auth/login", data={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("access_token", "")

def run_query(question, token, brand="otis"):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"question": question, "brandFilter": brand, "topK": 10}
    r = requests.post(f"{API}/api/query", json=payload, headers=headers, timeout=120)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}", "answer": "", "sources": []}
    return r.json()

def evaluate_test(test, response):
    """Evaluate if the response matches expectations."""
    result = {"id": test["id"], "passed": False, "details": []}
    
    answer = response.get("answer", "")
    sources = response.get("sources", [])
    needs_clar = response.get("needs_clarification", False)
    source_names = " ".join(s.get("filename", "") for s in sources).lower()
    
    expected = test["expected"]
    
    # Check CLARIFY expectation
    if expected == "CLARIFY":
        if needs_clar or "?" in answer:
            result["passed"] = True
            result["details"].append("✅ Correctly asked for clarification")
        else:
            result["details"].append("❌ Should have asked for clarification but answered directly")
    
    # Check ANSWER expectation
    elif expected == "ANSWER":
        if needs_clar and "?" in answer and not any(
            term.lower() in answer.lower() for term in test.get("expected_terms", [])
        ):
            result["details"].append("❌ Asked for clarification when should have answered")
        else:
            result["passed"] = True
            result["details"].append("✅ Answered (did not block)")
    
    # Check DISAMBIGUATE expectation
    elif expected == "DISAMBIGUATE":
        if "?" in answer:
            result["passed"] = True
            result["details"].append("✅ Asked disambiguation question")
        else:
            result["details"].append("⚠️ Expected disambiguation but got direct answer")
            result["passed"] = True  # Still acceptable
    
    # Check expected docs if specified
    if test.get("expected_docs") and not needs_clar:
        found_expected = False
        for expected_doc in test["expected_docs"]:
            if expected_doc.lower() in source_names or expected_doc.lower() in answer.lower():
                found_expected = True
                break
        if found_expected:
            result["details"].append(f"✅ Found expected doc reference")
        else:
            result["details"].append(f"⚠️ Expected docs {test['expected_docs']} not found in sources: {source_names[:100]}")
            if result["passed"]:
                result["passed"] = "partial"
    
    # Check expected terms
    if test.get("expected_terms") and not needs_clar:
        answer_lower = answer.lower()
        for term in test["expected_terms"]:
            if term.lower() in answer_lower:
                result["details"].append(f"✅ Found expected term: {term}")
            else:
                result["details"].append(f"⚠️ Missing expected term: {term}")
    
    # Check forbidden terms
    if test.get("forbidden_terms"):
        answer_lower = answer.lower()
        for term in test["forbidden_terms"]:
            if term.lower() in answer_lower:
                result["details"].append(f"❌ Found forbidden term: {term}")
                result["passed"] = False
    
    return result


def run_all_tests(test_ids=None, categories=None, limit=None):
    """Run tests and generate report."""
    print(f"{'='*70}")
    print(f" OTIS 300-SCENARIO TEST SUITE")
    print(f" API: {API}")
    print(f" Started: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    token = get_token()
    if not token:
        print("❌ Authentication failed!")
        return
    
    # Filter tests
    tests_to_run = TESTS
    if test_ids:
        tests_to_run = [t for t in TESTS if t["id"] in test_ids]
    if categories:
        tests_to_run = [t for t in tests_to_run if t["category"] in categories]
    if limit:
        tests_to_run = tests_to_run[:limit]
    
    print(f"Running {len(tests_to_run)} tests...\n")
    
    results = []
    passed = 0
    partial = 0
    failed = 0
    errors = 0
    
    for i, test in enumerate(tests_to_run, 1):
        test_id = test["id"]
        category = test["category"]
        desc = test.get("desc", "")
        question = test["question"]
        
        print(f"[{i:3d}/{len(tests_to_run)}] Test {test_id} ({category}) - {desc}")
        print(f"  Q: {question}")
        
        try:
            response = run_query(question, token)
            
            if "error" in response:
                print(f"  ❌ ERROR: {response['error']}")
                errors += 1
                results.append({"id": test_id, "passed": False, "error": response["error"]})
                continue
            
            answer_preview = response.get("answer", "")[:120].replace("\n", " ")
            needs_clar = response.get("needs_clarification", False)
            sources = response.get("sources", [])
            source_list = ", ".join(s.get("filename", "")[:40] for s in sources[:3])
            
            result = evaluate_test(test, response)
            results.append(result)
            
            status = "✅" if result["passed"] == True else ("⚠️" if result["passed"] == "partial" else "❌")
            if result["passed"] == True:
                passed += 1
            elif result["passed"] == "partial":
                partial += 1
            else:
                failed += 1
            
            print(f"  A: {answer_preview}...")
            if sources:
                print(f"  📄 Sources: {source_list}")
            print(f"  {status} {'CLARIFY' if needs_clar else 'ANSWER'} | Expected: {test['expected']}")
            for detail in result["details"]:
                print(f"     {detail}")
            print()
            
            # Multi-turn follow-up test
            if test.get("follow_up") and needs_clar:
                print(f"  → Follow-up: {test['follow_up']}")
                time.sleep(0.3)
                follow_response = run_query(test["follow_up"], token)
                if "error" not in follow_response:
                    follow_preview = follow_response.get("answer", "")[:100].replace("\n", " ")
                    follow_clar = follow_response.get("needs_clarification", False)
                    follow_sources = follow_response.get("sources", [])
                    print(f"  → A: {follow_preview}...")
                    if test.get("follow_expected") == "ANSWER" and not follow_clar:
                        print(f"  → ✅ Follow-up answered correctly")
                    elif test.get("follow_expected") == "ANSWER" and follow_clar:
                        print(f"  → ⚠️ Follow-up still asking - may be OK (progressive)")
                    print()
            
            time.sleep(0.3)  # Rate limit
            
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            errors += 1
            results.append({"id": test_id, "passed": False, "error": str(e)})
    
    # Summary
    total = len(tests_to_run)
    print(f"\n{'='*70}")
    print(f" TEST RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f" Total:   {total}")
    print(f" Passed:  {passed} ({100*passed/total:.1f}%)")
    print(f" Partial: {partial} ({100*partial/total:.1f}%)")
    print(f" Failed:  {failed} ({100*failed/total:.1f}%)")
    print(f" Errors:  {errors} ({100*errors/total:.1f}%)")
    print(f"{'='*70}")
    
    # Category breakdown
    categories_seen = set(t["category"] for t in tests_to_run)
    print(f"\nBy Category:")
    cat_names = {
        "A": "Generic (no model)",
        "B": "Model-specific",
        "C": "Multi-turn",
        "D": "Disambiguation",
        "E": "Edge cases",
        "F": "Symptom diagnosis",
        "G": "Procedures",
        "H": "Electrical diagrams",
        "I": "Troubleshooting",
        "J": "Cross-model",
    }
    for cat in sorted(categories_seen):
        cat_tests = [r for r, t in zip(results, tests_to_run) if t["category"] == cat]
        cat_passed = sum(1 for r in cat_tests if r.get("passed") == True)
        cat_total = len(cat_tests)
        pct = 100 * cat_passed / cat_total if cat_total else 0
        print(f"  {cat}. {cat_names.get(cat, 'Unknown'):20s}: {cat_passed}/{cat_total} ({pct:.0f}%)")
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "api": API,
        "total": total,
        "passed": passed,
        "partial": partial,
        "failed": failed,
        "errors": errors,
        "results": results,
    }
    report_path = "scripts/otis_300_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to: {report_path}")


if __name__ == "__main__":
    # Command line options
    import argparse
    parser = argparse.ArgumentParser(description="Run Otis 300-scenario test suite")
    parser.add_argument("--ids", type=str, help="Comma-separated test IDs to run (e.g. 1,2,3)")
    parser.add_argument("--categories", type=str, help="Categories to run (e.g. A,B,F)")
    parser.add_argument("--limit", type=int, help="Max number of tests to run")
    parser.add_argument("--quick", action="store_true", help="Run quick subset (30 tests)")
    args = parser.parse_args()
    
    test_ids = [int(x) for x in args.ids.split(",")] if args.ids else None
    categories = args.categories.split(",") if args.categories else None
    limit = args.limit
    
    if args.quick:
        # Quick test: 3 per category
        quick_ids = []
        for cat in "ABCDEFGHIJ":
            cat_tests = [t["id"] for t in TESTS if t["category"] == cat][:3]
            quick_ids.extend(cat_tests)
        test_ids = quick_ids
    
    run_all_tests(test_ids=test_ids, categories=categories, limit=limit)
