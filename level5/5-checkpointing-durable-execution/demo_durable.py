"""Demo: Checkpointing / durable execution.

Un workflow de 4 pasos (reservar inventario, cobrar, enviar, notificar)
se cae a mitad de camino — despues de ejecutar 2 pasos reales — y un
worker nuevo lo retoma.

  Parte 1 — Sin checkpointing: el worker nuevo no tiene forma de saber
            que ya se hicieron los primeros 2 pasos, asi que vuelve a
            ejecutar TODO desde cero — duplicando efectos reales
            (doble cobro, doble reserva).
  Parte 2 — Con checkpointing (durable execution): el worker nuevo
            reusa el historial. Los pasos ya hechos se REPLAYEAN (sin
            efecto real); solo los que faltaban se ejecutan de verdad.
  Parte 3 — Por que esto importa a escala: cuantos workflows en curso
            puede sostener un pool fijo de workers, con y sin esta
            propiedad.
"""
from durable import History, World, WorkerCrashed, run_order_workflow

CRASH_AFTER_STEPS = 2


def demo_without_checkpointing():
    print("=" * 70)
    print("Parte 1: SIN checkpointing — el reinicio repite todo desde cero")
    print("=" * 70)

    world = World()

    print("  intento 1 (el worker se cae despues de 2 pasos reales):")
    try:
        run_order_workflow(world, History(), crash_after_real_steps=CRASH_AFTER_STEPS)
    except WorkerCrashed as exc:
        print(f"    -> {exc}")

    print("  un worker NUEVO reinicia el workflow desde el principio (sin historial):")
    results = run_order_workflow(world, History())
    for r in results:
        print(f"    - {r}")

    print(f"\n  efectos reales totales: reservas={world.reservations}, cobros={world.charges}, "
          f"envios={world.shipments}, notificaciones={world.notifications}")
    print("  -> se cobro DOS veces y se reservo inventario DOS veces por el mismo pedido.\n")


def demo_with_checkpointing():
    print("=" * 70)
    print("Parte 2: CON checkpointing (durable execution) — se retoma donde quedo")
    print("=" * 70)

    world = World()
    history = History()  # el MISMO historial persiste entre el intento fallido y el reinicio

    print("  intento 1 (el worker se cae despues de 2 pasos reales):")
    try:
        run_order_workflow(world, history, crash_after_real_steps=CRASH_AFTER_STEPS)
    except WorkerCrashed as exc:
        print(f"    -> {exc}")
    print(f"    historial guardado hasta ahora: {list(history.entries.keys())}")

    print("  un worker NUEVO retoma el workflow, reusando el historial:")
    results = run_order_workflow(world, history)
    for r in results:
        print(f"    - {r}")

    print(f"\n  efectos reales totales: reservas={world.reservations}, cobros={world.charges}, "
          f"envios={world.shipments}, notificaciones={world.notifications}")
    print("  -> cada efecto real ocurrio exactamente UNA vez, aunque el worker haya")
    print("     muerto a mitad de camino.\n")


def demo_capacity_argument():
    print("=" * 70)
    print("Parte 3: por que esto importa a escala — capacidad de workers")
    print("=" * 70)

    worker_pool = 10
    total_lifetime_hours = 24.0       # ej: un workflow que espera confirmacion de pago hasta 24hs
    active_execution_seconds = 50.0   # cuanto tiempo de trabajo REAL tiene, sumando sus pasos

    fraction_active = active_execution_seconds / (total_lifetime_hours * 3600)
    naive_capacity = worker_pool
    durable_capacity = int(worker_pool / fraction_active)

    print(f"  pool fijo de {worker_pool} workers. Cada workflow vive hasta "
          f"{total_lifetime_hours:.0f}hs (esperando eventos externos),")
    print(f"  pero solo necesita {active_execution_seconds:.0f}s de trabajo REAL en total.\n")
    print(f"  sin checkpointing (cada workflow ocupa un worker TODO su ciclo de vida):")
    print(f"    -> maximo {naive_capacity} workflows en curso al mismo tiempo")
    print(f"  con checkpointing (un worker solo hace falta durante la ejecucion activa):")
    print(f"    -> hasta {durable_capacity:,} workflows en curso al mismo tiempo")
    print("\n  el mismo pool de 10 workers sostiene ordenes de magnitud mas workflows")
    print("   'en vuelo' simultaneamente, porque la mayor parte de su vida la pasan")
    print("  suspendidos (sin ocupar ningun worker), no bloqueados esperando.")


def main():
    demo_without_checkpointing()
    demo_with_checkpointing()
    demo_capacity_argument()


if __name__ == "__main__":
    main()
