"""Demo: Event sourcing.

  Parte 1 — Recuperacion tras corrupcion: el estado cacheado
            (proyectado) se corrompe; se reconstruye desde cero
            reproduciendo el log de eventos, que nunca se toco.
  Parte 2 — Multiples proyecciones del mismo log: agregar una vista
            nueva no requiere cambiar como se registran los eventos.
  Parte 3 — Snapshots: reproducir un log enorme desde el principio
            cada vez es caro; un snapshot periodico acota cuanto hay
            que reproducir, con una mejora de velocidad medida de
            verdad (no simulada).
"""
import time

from event_sourcing import (
    EventLog,
    project_balance,
    project_total_deposits,
    project_transaction_counts,
)


def demo_recovery_after_corruption():
    print("=" * 70)
    print("Parte 1: reconstruir el estado tras una corrupcion")
    print("=" * 70)

    log = EventLog()
    log.append("Deposited", {"amount": 100.0})
    log.append("Deposited", {"amount": 50.0})
    log.append("Withdrawn", {"amount": 30.0})

    cached_balance = project_balance(log.events)
    print(f"  saldo proyectado (cacheado en algun lugar): {cached_balance}")

    print("\n  ...un bug pisa el valor cacheado con basura...")
    cached_balance = -999999.0
    print(f"  saldo cacheado ahora: {cached_balance} (corrupto)")

    print("\n  reconstruccion: se ignora el valor cacheado y se reproduce el log completo")
    recovered_balance = project_balance(log.events)
    print(f"  saldo reconstruido desde el log: {recovered_balance}")
    print("  -> el log de eventos nunca se corrompio, asi que el estado se recupera")
    print("     exactamente igual a como estaba, sin haber guardado un backup del")
    print("     valor cacheado en si.\n")


def demo_multiple_projections():
    print("=" * 70)
    print("Parte 2: multiples proyecciones del mismo log de eventos")
    print("=" * 70)

    log = EventLog()
    log.append("Deposited", {"amount": 200.0})
    log.append("Withdrawn", {"amount": 50.0})
    log.append("Deposited", {"amount": 75.0})
    log.append("Withdrawn", {"amount": 20.0})
    log.append("Deposited", {"amount": 10.0})

    print(f"  saldo actual: {project_balance(log.events)}")
    print(f"  cantidad de transacciones por tipo: {project_transaction_counts(log.events)}")
    print(f"  total depositado historicamente: {project_total_deposits(log.events)}")
    print("\n  las tres vistas salen del MISMO log, sin haber cambiado nada de como")
    print("  se registraron los eventos originales — una vista nueva es solo una")
    print("  funcion nueva sobre datos que ya estaban ahi.\n")


def demo_snapshots():
    print("=" * 70)
    print("Parte 3: snapshots — acotar cuanto hay que reproducir")
    print("=" * 70)

    n_events = 500_000
    events = [
        ("Withdrawn", {"amount": 0.5}) if i % 3 == 0 else ("Deposited", {"amount": 1.0})
        for i in range(n_events)
    ]

    print(f"Un log de {n_events:,} eventos.\n")

    start = time.perf_counter()
    full_balance = project_balance(events)
    full_time = time.perf_counter() - start
    print(f"  reproducir TODO el log desde el evento 0: {full_time * 1000:.1f}ms -> saldo={full_balance}")

    snapshot_at = 480_000
    snapshot_balance = project_balance(events[:snapshot_at])
    start = time.perf_counter()
    recovered_balance = project_balance(events[snapshot_at:], start_balance=snapshot_balance)
    snapshot_time = time.perf_counter() - start
    print(f"  reproducir solo desde el snapshot (evento {snapshot_at:,}): "
          f"{snapshot_time * 1000:.1f}ms -> saldo={recovered_balance}")

    print(f"\n  ambos coinciden: {abs(full_balance - recovered_balance) < 1e-6}")
    print(f"  -> {full_time / snapshot_time:.1f}x mas rapido reproduciendo solo los ultimos "
          f"{n_events - snapshot_at:,} eventos en vez de los {n_events:,} completos.")


def main():
    demo_recovery_after_corruption()
    demo_multiple_projections()
    demo_snapshots()


if __name__ == "__main__":
    main()
