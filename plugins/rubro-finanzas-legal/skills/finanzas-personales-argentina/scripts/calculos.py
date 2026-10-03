#!/usr/bin/env python3
"""
calculos.py — Aritmética de finanzas personales en contexto argentino.

Usalo en vez de hacer las cuentas a mano: es reproducible, no se equivoca y deja
el cálculo auditable. Todas las tasas se expresan en decimal (0.30 = 30%).

Uso rápido:
    python calculos.py --demo

Importable:
    from calculos import tasa_ahorro, runway, fondo_emergencia
"""

from dataclasses import dataclass
from typing import Iterable, Sequence


# ---------------------------------------------------------------- conversión

def ars_a_usd(monto_ars: float, mep: float) -> float:
    """Convierte un importe al MEP de SU PROPIA fecha. Nunca al promedio del período."""
    if mep <= 0:
        raise ValueError("El MEP debe ser positivo.")
    return monto_ars / mep


def flujos_a_usd(flujos: Sequence[tuple]) -> float:
    """
    Convierte una serie de flujos, cada uno a su tipo de cambio.
    flujos: [(fecha, monto_ars, mep), ...]  -- la fecha es solo trazabilidad.
    """
    return sum(ars_a_usd(monto, mep) for _, monto, mep in flujos)


# --------------------------------------------------------------- rendimiento

def rendimiento_nominal(valor_inicial: float, valor_final: float) -> float:
    """Cuántos pesos más tengo. Solo comparable contra otra tasa nominal."""
    return valor_final / valor_inicial - 1


def rendimiento_real_ars(r_nominal: float, inflacion: float) -> float:
    """Cuánto más puedo comprar en Argentina. Para dinero con destino en ARS."""
    return (1 + r_nominal) / (1 + inflacion) - 1


def rendimiento_real_usd(
    valor_inicial_ars: float,
    mep_inicial: float,
    valor_final_ars: float,
    mep_final: float,
    inflacion_usa: float = 0.0,
) -> float:
    """
    Cuánto más valgo medido en la unidad de reserva.
    Con inflacion_usa > 0 devuelve el real deflactado (usalo en horizontes > 1 año).
    """
    vi = ars_a_usd(valor_inicial_ars, mep_inicial)
    vf = ars_a_usd(valor_final_ars, mep_final)
    r = vf / vi - 1
    return (1 + r) / (1 + inflacion_usa) - 1


def tres_rendimientos(
    valor_inicial_ars: float,
    mep_inicial: float,
    valor_final_ars: float,
    mep_final: float,
    inflacion_ars: float,
    inflacion_usa: float = 0.0,
) -> dict:
    """Las tres tasas juntas. Mostralas siempre juntas o aclará cuál usás."""
    nom = rendimiento_nominal(valor_inicial_ars, valor_final_ars)
    return {
        "nominal_ars": nom,
        "real_ars": rendimiento_real_ars(nom, inflacion_ars),
        "real_usd": rendimiento_real_usd(
            valor_inicial_ars, mep_inicial, valor_final_ars, mep_final, inflacion_usa
        ),
    }


# ------------------------------------------------------------------ métricas

def tasa_ahorro(ingresos_usd: float, gastos_usd: float) -> float:
    if ingresos_usd <= 0:
        raise ValueError("Los ingresos deben ser positivos para calcular tasa de ahorro.")
    return (ingresos_usd - gastos_usd) / ingresos_usd


def runway(liquidos_usd: float, gasto_mensual_usd: float) -> float:
    """Meses. Pasale el gasto comprimido para el escenario de contingencia."""
    if gasto_mensual_usd <= 0:
        raise ValueError("El gasto mensual debe ser positivo.")
    return liquidos_usd / gasto_mensual_usd


def ratio_rigidez(gasto_fijo_usd: float, ingreso_minimo_usd: float) -> float:
    """
    Denominador = PISO del ingreso, no promedio.
    <0,5 holgado | 0,5-0,8 ajustado | >0,8 tenso | >1 dependiente de meses buenos.
    """
    if ingreso_minimo_usd <= 0:
        raise ValueError("El ingreso mínimo debe ser positivo.")
    return gasto_fijo_usd / ingreso_minimo_usd


def yield_neto(
    renta_bruta_anual_usd: float,
    valor_mercado_usd: float,
    expensas_anual: float = 0.0,
    impuestos_anual: float = 0.0,
    mantenimiento_pct: float = 0.06,
    vacancia_meses_por_anio: float = 0.4,
    otros_anual: float = 0.0,
) -> dict:
    """
    Yield neto sobre VALOR DE MERCADO (nunca sobre precio de compra).
    mantenimiento_pct: 5-8% de la renta bruta si no hay dato real.
    vacancia_meses_por_anio: 0.4 ≈ 1 mes cada 30.
    """
    mantenimiento = renta_bruta_anual_usd * mantenimiento_pct
    vacancia = renta_bruta_anual_usd * (vacancia_meses_por_anio / 12)
    neta = (
        renta_bruta_anual_usd
        - expensas_anual
        - impuestos_anual
        - mantenimiento
        - vacancia
        - otros_anual
    )
    return {
        "renta_neta_anual_usd": neta,
        "yield_bruto": renta_bruta_anual_usd / valor_mercado_usd,
        "yield_neto": neta / valor_mercado_usd,
    }


def concentracion(valores_por_activo: dict) -> dict:
    """Participación de cada activo sobre el total + HHI (1,0 = todo en uno)."""
    total = sum(valores_por_activo.values())
    if total <= 0:
        raise ValueError("El total de activos debe ser positivo.")
    part = {k: v / total for k, v in valores_por_activo.items()}
    return {
        "participaciones": part,
        "hhi": sum(p ** 2 for p in part.values()),
        "mayor_activo": max(part, key=part.get),
    }


def exposicion_empresa(pct_pn_en_empresa: float, pct_ingreso_de_empresa: float) -> dict:
    """
    Suma de exposiciones (escala 0-200). >100 = el patrimonio familiar ES la empresa.
    """
    total = (pct_pn_en_empresa + pct_ingreso_de_empresa) * 100
    if total < 60:
        lectura = "la empresa es una parte del cuadro"
    elif total < 100:
        lectura = "exposición alta: conviene verla escrita"
    elif total < 150:
        lectura = "el patrimonio familiar ES la empresa, con decoración alrededor"
    else:
        lectura = "concentración dominante: diversificar el resto es marginal"
    return {"exposicion_efectiva": total, "lectura": lectura}


def fondo_emergencia(
    gasto_comprimido_usd: float,
    meses_peor_racha: float,
    factor_correlacion: float = 1.0,
) -> float:
    """
    factor_correlacion: 1,0 fuentes independientes | 1,5 ingreso de una sola empresa
    | 2,0 además el patrimonio principal es esa empresa y hay deuda con garantía personal.
    """
    return gasto_comprimido_usd * meses_peor_racha * factor_correlacion


def valor_equity_en_balance(
    valuacion_100_usd: float,
    participacion: float,
    dlom: float = 0.30,
    dloc: float = 0.0,
) -> float:
    """
    DLOM (iliquidez) 0,20-0,35. DLOC (falta de control) 0,10-0,30, SOLO si no controla
    la distribución de utilidades. Nunca valor libro, nunca precio esperado sin descuento.
    """
    return valuacion_100_usd * participacion * (1 - dlom) * (1 - dloc)


# ----------------------------------------------------------------- escenarios

@dataclass
class Escenarios:
    conservador: float
    base: float
    optimista: float

    def como_tabla(self, etiqueta: str = "Valor") -> str:
        return (
            f"| Escenario | {etiqueta} |\n|---|---|\n"
            f"| Conservador | {self.conservador:,.2f} |\n"
            f"| Base | {self.base:,.2f} |\n"
            f"| Optimista | {self.optimista:,.2f} |"
        )


def escenarios(base: float, castigo: float = 0.25, mejora: float = 0.15) -> Escenarios:
    """Toda proyección va en tres escenarios. Un número solo es una certeza falsa."""
    return Escenarios(base * (1 - castigo), base, base * (1 + mejora))


def peor_racha(serie_ingresos: Iterable[float], umbral: float) -> int:
    """Meses consecutivos con ingreso por debajo del gasto comprimido. Input del FE."""
    mayor = actual = 0
    for x in serie_ingresos:
        actual = actual + 1 if x < umbral else 0
        mayor = max(mayor, actual)
    return mayor


# ---------------------------------------------------------------------- demo

def _demo() -> None:
    print("=== Tres rendimientos: plazo fijo 38% nominal, inflación 30% ===")
    r = tres_rendimientos(1_000_000, 1_000, 1_380_000, 1_150, 0.30)
    for k, v in r.items():
        print(f"  {k:<12} {v:>8.2%}")
    print("  Mismo hecho, tres respuestas. El 38% nominal es 6,2% real en ARS.")
    print("  El 20% en USD es sobre todo atraso cambiario: el MEP subió 15% con IPC 30%.\n")

    print("=== Tasa de ahorro y runway ===")
    print(f"  tasa_ahorro(6000, 4500) = {tasa_ahorro(6000, 4500):.2%}")
    print(f"  runway(20000, 3200)     = {runway(20000, 3200):.1f} meses\n")

    print("=== Fondo de emergencia con ingreso de una sola empresa ===")
    serie = [5200, 4100, 2800, 2600, 3000, 6100, 5800, 2400, 2900, 3100, 7000, 5500]
    racha = peor_racha(serie, umbral=3200)
    fe = fondo_emergencia(3200, max(racha, 1), factor_correlacion=1.5)
    print(f"  peor racha observada: {racha} meses")
    print(f"  FE sugerido: USD {fe:,.0f}\n")

    print("=== Exposición a la empresa ===")
    print(" ", exposicion_empresa(0.62, 0.85))
    print()

    print("=== Yield neto de un inmueble ===")
    y = yield_neto(7200, 120_000, expensas_anual=600, impuestos_anual=900)
    print(f"  bruto {y['yield_bruto']:.2%} | neto {y['yield_neto']:.2%}\n")

    print("=== Equity en empresa propia, control total ===")
    v = valor_equity_en_balance(800_000, 0.5, dlom=0.30, dloc=0.0)
    print(f"  valor en balance: USD {v:,.0f} (vs USD 400.000 sin descuento)\n")

    print("=== Escenarios ===")
    print(escenarios(1200).como_tabla("Excedente mensual USD"))


if __name__ == "__main__":
    import sys

    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
