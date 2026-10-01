"""Demo: SLO + error budgets.

  Parte 1 — El presupuesto como cantidad concreta: cuantos requests
            fallidos permite un SLO en un periodo, y cuanto de eso
            consume un incidente real.
  Parte 2 — El costo de cada nueve adicional: cuanto se achica el
            presupuesto (geometricamente) al subir el SLO.
  Parte 3 — Burn rate: a que velocidad se esta gastando el presupuesto
            ahora mismo, y cuando hace falta actuar.
"""
from error_budgets import allowed_downtime_minutes, error_budget_requests, time_to_exhaust_days

PERIOD_DAYS = 30


def demo_budget_as_quantity():
    print("=" * 70)
    print("Parte 1: el presupuesto de errores como cantidad concreta")
    print("=" * 70)

    slo = 0.999
    requests_per_day = 10_000_000
    budget = error_budget_requests(slo, requests_per_day, PERIOD_DAYS)

    print(f"  SLO={slo * 100:.1f}%, {requests_per_day:,} requests/dia, ventana de {PERIOD_DAYS} dias")
    print(f"  presupuesto de errores del mes: {budget:,.0f} requests fallidos permitidos\n")

    incident_failures = 50_000
    pct = incident_failures / budget
    remaining_incidents = budget / incident_failures
    print(f"  un incidente que genera {incident_failures:,} fallos consume el {pct:.1%} del presupuesto")
    print(f"  ese presupuesto alcanza para {remaining_incidents:.1f} incidentes como ese en todo el mes\n")


def demo_cost_of_nines():
    print("=" * 70)
    print("Parte 2: el costo de cada nueve adicional")
    print("=" * 70)

    header = f"{'SLO':>10} | {'downtime permitido / mes':>26}"
    print(header)
    print("-" * len(header))
    for slo in (0.99, 0.999, 0.9999, 0.99999):
        minutes = allowed_downtime_minutes(slo, PERIOD_DAYS)
        if minutes >= 1:
            display = f"{minutes:.2f} min"
        else:
            display = f"{minutes * 60:.1f} seg"
        print(f"{slo * 100:>9.3f}% | {display:>26}")

    print("\n  cada nueve adicional divide por 10 el presupuesto disponible — y, en la")
    print("  practica, el costo de INGENIERIA para conseguirlo crece mucho mas rapido")
    print("  que eso. Elegir el SLO correcto (no el mas alto posible) es en si mismo")
    print("  parte del trabajo: cuanta confiabilidad necesita realmente el negocio.\n")


def demo_burn_rate():
    print("=" * 70)
    print("Parte 3: burn rate — a que velocidad se gasta el presupuesto")
    print("=" * 70)
    print(f"1.0x = gastando el presupuesto exactamente al ritmo que lo agota en los")
    print(f"{PERIOD_DAYS} dias del periodo (el ritmo 'sostenible', ni de mas ni de menos).\n")

    header = f"{'burn rate':>10} | {'se agota en':>14} | {'veredicto':>45}"
    print(header)
    print("-" * len(header))
    for burn_rate in (0.5, 1.0, 5.0, 10.0, 50.0):
        days_left = time_to_exhaust_days(burn_rate, PERIOD_DAYS)
        if burn_rate <= 1.0:
            veredicto = "dentro del presupuesto, sin apuro"
        elif days_left >= 1:
            veredicto = f"atencion: se agota en {days_left:.1f} dias"
        else:
            veredicto = f"URGENTE: se agota en {days_left * 24:.1f} horas"
        print(f"{burn_rate:>9.1f}x | {days_left:>12.2f}d | {veredicto:>45}")

    print("\n  las alertas de burn rate reaccionan a la VELOCIDAD de consumo, no solo al")
    print("  nivel absoluto restante — un burn rate alto amerita respuesta inmediata")
    print("  aunque todavia quede presupuesto 'en el papel', porque a ese ritmo no va")
    print("  a durar.")


def main():
    demo_budget_as_quantity()
    demo_cost_of_nines()
    demo_burn_rate()


if __name__ == "__main__":
    main()
