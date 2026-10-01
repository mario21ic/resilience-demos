"""Demo: DR con RTO/RPO explicitos.

  Parte 1 — Las cuatro estrategias de DR y su tradeoff explicito entre
            RTO, RPO y costo.
  Parte 2 — Probar el restore, no solo el backup: cuanto sube la
            probabilidad real de recuperacion al testear el proceso de
            restore periodicamente, en vez de confiar en que "hay
            backups" sin haberlos probado nunca.
"""
from dr_strategies import DR_STRATEGIES, probability_recovery_never_tested, probability_recovery_tested


def demo_strategies_table():
    print("=" * 70)
    print("Parte 1: RTO, RPO y costo por estrategia de DR")
    print("=" * 70)

    header = f"{'estrategia':>28} | {'RTO':>18} | {'RPO':>24} | {'costo':>18}"
    print(header)
    print("-" * len(header))
    for s in DR_STRATEGIES:
        print(f"{s['name']:>28} | {s['rto']:>18} | {s['rpo']:>24} | {s['costo_relativo']:>18}")

    print("\nCada escalon reduce RTO y RPO a costa de mas infraestructura corriendo")
    print("permanentemente en el sitio de DR — no hay una estrategia 'correcta'")
    print("universal, depende de cuanto cuesta cada minuto de downtime o cada minuto")
    print("de datos perdidos para el negocio en particular.\n")


def demo_test_the_restore():
    print("=" * 70)
    print("Parte 2: probar el restore, no solo el backup")
    print("=" * 70)

    p_bug = 0.20
    print(f"Probabilidad de que el PROCESO de backup tenga un bug no descubierto: {p_bug:.0%}")
    print("(algo tan comun como una clave de cifrado rotada que el restore no")
    print("contempla, un formato que cambio, un paso manual que quedo desactualizado).\n")

    never_tested = probability_recovery_never_tested(p_bug)
    print(f"  SIN ningun restore de prueba: probabilidad de recuperacion real = {never_tested:.1%}")

    print("\n  CON restores de prueba periodicos antes del desastre real:")
    for n_tests in (1, 2, 4, 8):
        prob = probability_recovery_tested(p_bug, n_tests)
        print(f"    {n_tests} restore(s) de prueba: probabilidad de recuperacion = {prob:.1%}")

    print("\n  'tener backups' y 'poder recuperarse de verdad' son afirmaciones distintas.")
    print("  Solo un restore real, ensayado, cierra esa brecha — la misma logica de")
    print("  verificar en vez de asumir que aparece en")
    print("  chaos engineering (../1-chaos-engineering).")


def main():
    demo_strategies_table()
    demo_test_the_restore()


if __name__ == "__main__":
    main()
