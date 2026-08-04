"""Demo: Constant work pattern.

Un sistema de propagacion de configuracion (piensen DNS, feature
flags, reglas de firewall) normalmente procesa unos pocos cambios por
ciclo. Durante un incidente, llegan 500 cambios de golpe.

  Sistema delta: dimensionado para el caso normal, se desborda con la
                 rafaga real y tarda muchos ciclos en ponerse al dia.
  Sistema de trabajo constante: siempre reenvia el estado completo
                 (1000 registros) por ciclo — la rafaga de 500 cambios
                 ya cabe en ese volumen habitual, sin generar backlog.
"""
from constant_work import constant_work_cycles_to_recover, simulate_delta_recovery

BURST_SIZE = 500
NORMAL_CAPACITY = 5
WORST_CASE_CAPACITY = 500
NORMAL_LOAD = 2
TOTAL_RECORDS = 1000


def main():
    print(f"Un incidente genera una rafaga de {BURST_SIZE} cambios reales de golpe.\n")

    print("=" * 70)
    print("Sistema DELTA (solo procesa lo que cambio)")
    print("=" * 70)

    cycles = simulate_delta_recovery(BURST_SIZE, NORMAL_CAPACITY)
    print(f"  dimensionado para el caso normal ({NORMAL_CAPACITY} cambios/ciclo):")
    print(f"    tarda {cycles} ciclos en absorber la rafaga completa")

    utilization = NORMAL_LOAD / WORST_CASE_CAPACITY
    print(f"\n  si en cambio se dimensiona para el PEOR caso ({WORST_CASE_CAPACITY}/ciclo):")
    print(f"    utilizacion real en el dia a dia: {utilization:.1%}")
    print(f"    y esa capacidad para el peor caso NUNCA se ejercito de verdad hasta que")
    print(f"    ocurre el incidente — es el camino de codigo menos probado del sistema.\n")

    print("=" * 70)
    print("Sistema de TRABAJO CONSTANTE (siempre reenvia el estado completo)")
    print("=" * 70)

    cycles_constant = constant_work_cycles_to_recover(BURST_SIZE, TOTAL_RECORDS)
    print(f"  siempre reenvia los {TOTAL_RECORDS} registros completos, cada ciclo, haya o no")
    print(f"  cambios reales:")
    print(f"    ciclos de backlog generados por la rafaga: {cycles_constant}")
    print(f"\n  la rafaga de {BURST_SIZE} cambios no le pide al sistema hacer nada que no")
    print(f"  estuviera haciendo YA, todos los ciclos, desde siempre — el 'modo incidente'")
    print("  es exactamente el mismo camino de codigo que el modo normal, probado en")
    print("  cada ciclo, no solo cuando hay una crisis.")


if __name__ == "__main__":
    main()
