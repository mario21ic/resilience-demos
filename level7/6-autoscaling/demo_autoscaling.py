"""Demo: Autoscaling — reactivo, predictivo, y el limite de fondo.

  Parte 1 — El retraso del autoscaling reactivo: cuanta demanda se
            pierde en la ventana entre que la demanda sube y la
            capacidad nueva esta lista.
  Parte 2 — Predictivo vs reactivo, para un pico CONOCIDO de antemano:
            el predictivo evita el retraso por completo.
  Parte 3 — "Nunca escala mas rapido que el fallo": cuando un incidente
            crece mas rapido de lo que el autoscaler puede reaccionar,
            ningun autoscaling alcanza para evitar la perdida.
"""
from autoscaling import exponential_demand, simulate_predictive, simulate_reactive

CAPACITY_PER_INSTANCE = 100.0


def sudden_spike(t):
    return 300.0 if t < 10 else 900.0


def demo_reactive_lag():
    print("=" * 70)
    print("Parte 1: el retraso del autoscaling reactivo")
    print("=" * 70)
    print("La demanda se TRIPLICA de golpe en el tick 10 (300 -> 900). El autoscaler")
    print("revisa metricas cada 3 ticks y una instancia nueva tarda 5 ticks en estar lista.\n")

    dropped = simulate_reactive(
        sudden_spike, ticks=30, detection_interval=3, provision_time=5, initial_instances=3
    )
    print(f"  demanda total perdida durante la ventana de reaccion: {dropped:.0f}")
    print("  (nada de esa demanda se atendio, aunque el autoscaler haya reaccionado")
    print("  'correctamente' segun su propia configuracion)\n")


def demo_predictive_vs_reactive():
    print("=" * 70)
    print("Parte 2: predictivo vs reactivo, para un pico conocido de antemano")
    print("=" * 70)

    dropped_reactive = simulate_reactive(
        sudden_spike, ticks=30, detection_interval=3, provision_time=5, initial_instances=3
    )
    dropped_predictive = simulate_predictive(
        sudden_spike, ticks=30, provision_time=5, initial_instances=3,
        known_spike_tick=10, known_spike_demand=900.0,
    )

    print(f"  reactivo (reacciona DESPUES de ver la demanda subir): {dropped_reactive:.0f} perdidos")
    print(f"  predictivo (sabe que a las t=10 sube, escala antes):   {dropped_predictive:.0f} perdidos")
    print("\n  para un patron conocido (la hora pico de todos los dias, un evento")
    print("  programado), el predictivo elimina el retraso por completo. Para algo")
    print("  imprevisto, no tiene de donde sacar esa anticipacion.\n")


def demo_never_faster_than_failure():
    print("=" * 70)
    print("Parte 3: el autoscaling nunca escala mas rapido que el fallo")
    print("=" * 70)
    print("Un incidente que crece exponencialmente (ej. una tormenta de reintentos),")
    print("comparado contra un autoscaler con ~8 ticks de tiempo de reaccion")
    print("(deteccion + aprovisionamiento).\n")

    header = f"{'el incidente duplica la demanda cada':>38} | {'demanda perdida':>16}"
    print(header)
    print("-" * len(header))
    for doubling_time in (2, 5, 8, 15, 30):
        dropped = 0.0
        total = 0.0
        instances = 3
        pending = []
        for t in range(40):
            ready = [p for p in pending if p[0] <= t]
            for _, qty in ready:
                instances += qty
            pending = [p for p in pending if p[0] > t]
            demand = exponential_demand(t, base=100.0, doubling_time=doubling_time)
            capacity = instances * CAPACITY_PER_INSTANCE
            total += demand
            if demand > capacity:
                dropped += demand - capacity
            if t % 3 == 0:
                needed = max(0, -(-int(demand) // int(CAPACITY_PER_INSTANCE)) - instances)
                if needed > 0:
                    pending.append((t + 5, needed))
        pct = 100 * dropped / total if total else 0.0
        print(f"{doubling_time:>36} ticks | {pct:>14.1f}%")

    print("\n  cuando el incidente crece a un ritmo comparable (o mas rapido) que el")
    print("  tiempo de reaccion del autoscaler, la perdida es masiva — no importa que")
    print("  tan 'bien configurado' este, la capacidad nueva siempre llega tarde.")
    print("  Solo cuando el incidente es MUCHO mas lento que la reaccion, el")
    print("  autoscaling alcanza a compensarlo por si solo.")


def main():
    demo_reactive_lag()
    demo_predictive_vs_reactive()
    demo_never_faster_than_failure()


if __name__ == "__main__":
    main()
