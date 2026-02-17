"""
TaxCalculator - инструмент для расчёта налогов Испании

Поддерживает:
- IRPF (прогрессивная шкала)
- IVA (21%, 10%, 4%)
- Квоты автономо
- Impuesto sobre Sociedades
"""
import re
import time
from typing import Optional
from app.models.agent import ToolType, ToolResult, QueryType
from app.services.agent.tools.base_tool import BaseTool


# ============================================================
# IRPF 2025-2026 - трамы (общегосударственная + автономная)
# ============================================================
IRPF_BRACKETS_2025 = [
    (0,       12_450,  0.19),
    (12_450,  20_200,  0.24),
    (20_200,  35_200,  0.30),
    (35_200,  60_000,  0.37),
    (60_000,  300_000, 0.45),
    (300_000, float('inf'), 0.47),
]

# Минимальный личный минимум (mínimo personal)
MINIMO_PERSONAL = 5_550.0

# ============================================================
# IVA rates
# ============================================================
IVA_GENERAL = 0.21
IVA_REDUCIDO = 0.10
IVA_SUPERREDUCIDO = 0.04

# ============================================================
# Cuota de autónomos 2025-2026 (sistema de cotización por ingresos reales)
# ============================================================
CUOTAS_AUTONOMOS_2025 = [
    (0,       670,     200),
    (670,     900,     230),
    (900,     1_166.70, 267),
    (1_166.70, 1_300,  294),
    (1_300,   1_500,   294),
    (1_500,   1_700,   294),
    (1_700,   1_850,   350),
    (1_850,   2_030,   370),
    (2_030,   2_330,   390),
    (2_330,   2_760,   415),
    (2_760,   3_190,   465),
    (3_190,   3_620,   545),
    (3_620,   4_050,   570),
    (4_050,   6_000,   590),
    (6_000,   float('inf'), 590),
]

# Sociedades
TIPO_SOCIEDADES_GENERAL = 0.25
TIPO_SOCIEDADES_REDUCIDO = 0.23  # Para entidades con cifra de negocios < 1M€
TIPO_SOCIEDADES_EMPRENDEDORES = 0.15  # Primeros 2 años


class TaxCalculator(BaseTool):
    """Калькулятор налогов Испании"""

    def __init__(self):
        super().__init__(ToolType.TAX_CALCULATOR)

    def should_run(self, query: str, query_type: str) -> bool:
        """Запускать для расчётных запросов с числами"""
        if query_type == QueryType.TAX_CALCULATION:
            return True

        q = query.lower()
        # Проверяем наличие числа + налогового термина
        has_number = bool(re.search(r'\d+[\.,]?\d*', q))
        tax_keywords = [
            'irpf', 'iva', 'impuesto', 'cuota', 'autónomo', 'autonomo',
            'calcul', 'cuánto', 'cuanto', 'pagar', 'pago',
            'сколько', 'налог', 'расчет', 'рассчит', 'платить',
            'sociedades', 'retención', 'retencion',
        ]
        has_tax = any(kw in q for kw in tax_keywords)
        return has_number and has_tax

    async def execute(self, **kwargs) -> ToolResult:
        """Выполнить расчёт на основе запроса"""
        start = time.time()
        query = kwargs.get('query', '')

        try:
            results = []

            # Извлекаем числа из запроса
            amounts = self._extract_amounts(query)
            q = query.lower()

            if not amounts:
                return self._success(
                    "No he encontrado una cantidad específica en tu pregunta. "
                    "Indica un importe para calcular.",
                    (time.time() - start) * 1000
                )

            main_amount = amounts[0]

            # Определяем тип расчёта
            if any(kw in q for kw in ['irpf', 'renta', 'ирпф', 'подоходн']):
                results.append(self.calculate_irpf(main_amount))

            if any(kw in q for kw in ['iva', 'ива', 'ндс']):
                results.append(self.calculate_iva(main_amount))

            if any(kw in q for kw in [
                'autónomo', 'autonomo', 'cuota', 'автоном', 'квота'
            ]):
                results.append(self.calculate_autonomo_cuota(main_amount))

            if any(kw in q for kw in ['sociedades', 'sociedad', 'empresa']):
                results.append(self.calculate_sociedades(main_amount))

            # Если тип не определён, делаем IRPF (самый частый запрос)
            if not results:
                results.append(self.calculate_irpf(main_amount))

            result_text = "\n\n".join(results)
            return self._success(result_text, (time.time() - start) * 1000)

        except Exception as e:
            return self._error(str(e), (time.time() - start) * 1000)

    def calculate_irpf(self, gross_income: float) -> str:
        """Расчёт IRPF по прогрессивной шкале"""
        taxable = max(0, gross_income - MINIMO_PERSONAL)
        total_tax = 0
        breakdown = []

        remaining = taxable
        for low, high, rate in IRPF_BRACKETS_2025:
            if remaining <= 0:
                break
            bracket_base = min(remaining, high - low)
            bracket_tax = bracket_base * rate
            total_tax += bracket_tax
            breakdown.append(
                f"  {low:>10,.0f}€ - {min(high, low + bracket_base):>10,.0f}€ "
                f"al {rate*100:.0f}% = {bracket_tax:,.2f}€"
            )
            remaining -= bracket_base

        effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0
        net_income = gross_income - total_tax

        lines = [
            f"**Cálculo IRPF 2025 para {gross_income:,.0f}€ brutos:**",
            f"",
            f"Base imponible: {gross_income:,.0f}€ - {MINIMO_PERSONAL:,.0f}€ (mínimo personal) = {taxable:,.0f}€",
            f"",
            f"Desglose por tramos:",
        ]
        lines.extend(breakdown)
        lines.extend([
            f"",
            f"**Total IRPF: {total_tax:,.2f}€**",
            f"**Tipo efectivo: {effective_rate:.1f}%**",
            f"**Neto estimado: {net_income:,.2f}€**",
            f"",
            f"_Nota: Este cálculo usa la escala general estatal + autonómica media. "
            f"La escala autonómica puede variar. No incluye deducciones personales._"
        ])
        return "\n".join(lines)

    def calculate_iva(self, amount: float, rate: Optional[str] = None) -> str:
        """Расчёт IVA"""
        lines = [f"**Cálculo IVA para base imponible de {amount:,.2f}€:**", ""]

        rates = {
            'general': (IVA_GENERAL, "General"),
            'reducido': (IVA_REDUCIDO, "Reducido"),
            'superreducido': (IVA_SUPERREDUCIDO, "Superreducido"),
        }

        for key, (r, label) in rates.items():
            iva_amount = amount * r
            total = amount + iva_amount
            lines.append(
                f"  IVA {label} ({r*100:.0f}%): {iva_amount:,.2f}€ → "
                f"Total: {total:,.2f}€"
            )

        lines.append("")
        lines.append(
            "_El tipo general (21%) aplica a la mayoría de bienes y servicios. "
            "El reducido (10%) a alimentos, transporte, hostelería. "
            "El superreducido (4%) a pan, leche, medicamentos, libros._"
        )
        return "\n".join(lines)

    def calculate_autonomo_cuota(self, monthly_net: float) -> str:
        """Расчёт квоты автономо по реальным доходам"""
        cuota = None
        for low, high, amount in CUOTAS_AUTONOMOS_2025:
            if low <= monthly_net < high:
                cuota = amount
                break

        if cuota is None:
            cuota = CUOTAS_AUTONOMOS_2025[-1][2]

        annual_cuota = cuota * 12

        lines = [
            f"**Cuota de autónomo 2025 para rendimiento neto de {monthly_net:,.0f}€/mes:**",
            "",
            f"  Cuota mensual: **{cuota}€/mes**",
            f"  Cuota anual: **{annual_cuota:,}€/año**",
            "",
            f"_Sistema de cotización por ingresos reales (vigente desde 2023). "
            f"El rendimiento neto se calcula: ingresos - gastos deducibles._",
        ]
        return "\n".join(lines)

    def calculate_sociedades(self, profit: float) -> str:
        """Расчёт Impuesto sobre Sociedades"""
        tax_general = profit * TIPO_SOCIEDADES_GENERAL
        tax_reducido = profit * TIPO_SOCIEDADES_REDUCIDO
        tax_emprendedor = profit * TIPO_SOCIEDADES_EMPRENDEDORES

        lines = [
            f"**Impuesto sobre Sociedades para beneficio de {profit:,.0f}€:**",
            "",
            f"  Tipo general (25%): **{tax_general:,.2f}€**",
            f"  Tipo reducido (23%, cifra negocio < 1M€): **{tax_reducido:,.2f}€**",
            f"  Tipo emprendedores (15%, primeros 2 años): **{tax_emprendedor:,.2f}€**",
            "",
            "_El tipo general es 25%. Empresas con cifra de negocios inferior a "
            "1 millón de euros en el período anterior tributan al 23%. "
            "Entidades de nueva creación tributan al 15% los primeros dos períodos._"
        ]
        return "\n".join(lines)

    def _extract_amounts(self, text: str) -> list:
        """Извлечь числовые суммы из текста"""
        # Паттерны для денежных сумм
        patterns = [
            r'(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?)\s*(?:€|euro|EUR)',
            r'(?:€|euro|EUR)\s*(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*(?:€|euro)',
            r'(\d+[\.,]?\d*)\s*(?:€|euro|EUR|евро)',
            r'(\d+[\.,]?\d*)\s*(?:al mes|mensuales|anuales|al año)',
            r'(\d{4,}(?:[.,]\d+)?)',  # Числа от 4 цифр
        ]

        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                clean = m.replace('.', '').replace(' ', '').replace(',', '.')
                try:
                    val = float(clean)
                    if val > 0 and val not in amounts:
                        amounts.append(val)
                except ValueError:
                    continue

        return sorted(set(amounts), reverse=True)
