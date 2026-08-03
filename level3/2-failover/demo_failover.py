"""Demo: Failover — automatico o manual, disparado por health checks.
Su enemigo es el split-brain.

Un health checker solo sabe una cosa con certeza: "pude o no pude
contactar al primario en este check". No puede distinguir entre "esta
muerto" y "esta vivo pero inalcanzable desde mi posicion" (una
particion de red). Esa ambiguedad es el origen de todo este ejemplo.

  Parte 1 — El trigger: cuantos checks fallidos seguidos hacen falta
            para considerar caido a un nodo, y como reacciona cada
            estrategia (automatica vs manual) ante una falla REAL.
  Parte 2 — El enemigo: la misma secuencia de checks, mostrando que
            una particion de red se ve IGUAL que una falla real para
            el health checker. El failover automatico promueve un
            nuevo primario mientras el viejo sigue vivo y sirviendo
            del otro lado de la particion -> dos primarios escriben
            al mismo tiempo, con resultados que divergen.
  Parte 3 — La defensa estructural: fencing por numero de generacion.
            Se deja que el failover automatico siga siendo rapido,
            pero el primario viejo ya no puede hacer dano: sus
            escrituras se rechazan en cuanto intenta usarlas.
"""
from fencing import FencedError, FencedStorage
from health_check import AutomaticFailover, HealthChecker, ManualFailover

FAIL_THRESHOLD = 3
AUTO_PROMOTION_DELAY = 2
MANUAL_CONFIRM_DELAY = 5
MANUAL_PROMOTION_DELAY = 2


def run_scenario(health_sequence):
    checker = HealthChecker(FAIL_THRESHOLD)
    auto = AutomaticFailover(AUTO_PROMOTION_DELAY)
    manual = ManualFailover(MANUAL_CONFIRM_DELAY, MANUAL_PROMOTION_DELAY)
    log = []

    for t, is_healthy in enumerate(health_sequence):
        changed = checker.record(is_healthy)
        if checker.considered_down:
            auto.on_considered_down(t)
            manual.on_considered_down(t)
        else:
            auto.on_considered_up(t)
            manual.on_considered_up(t)
        if changed:
            state = "CAIDO" if checker.considered_down else "SANO de nuevo"
            log.append(f"  t={t:>2}: el health check pasa a considerar al primario {state}")

    return checker, auto, manual, log


def describe_failover(name: str, failover):
    if failover.triggered_at is None:
        print(f"  {name}: nunca se disparo")
    else:
        print(f"  {name}: disparado en t={failover.triggered_at}, promocion completa en t={failover.promoted_at}")


def demo_part1_real_outage():
    print("=" * 70)
    print("Parte 1: falla REAL del primario (no se recupera)")
    print("=" * 70)
    healthy = [True] * 5 + [False] * 15  # se cae en t=5 y no vuelve
    checker, auto, manual, log = run_scenario(healthy)
    for line in log:
        print(line)
    describe_failover("automatico", auto)
    describe_failover("manual", manual)
    print(f"  -> automatico restaura servicio {manual.promoted_at - auto.promoted_at} ticks antes que manual\n")


def demo_part2_split_brain():
    print("=" * 70)
    print("Parte 2: PARTICION de red (el primario en realidad sigue vivo)")
    print("=" * 70)
    # el health checker pierde contacto en t=5..10, pero el primario real
    # nunca dejo de funcionar del otro lado de la particion; en t=11 la
    # particion se cura y el checker vuelve a verlo sano.
    healthy = [True] * 5 + [False] * 6 + [True] * 9
    checker, auto, manual, log = run_scenario(healthy)
    for line in log:
        print(line)
    describe_failover("automatico", auto)
    describe_failover("manual", manual)

    print("\n  El failover automatico promovio un standby en "
          f"t={auto.promoted_at} creyendo que el primario habia muerto.")
    print("  El primario viejo NUNCA se entero: siguio aceptando escrituras de sus")
    print("  propios clientes durante toda la particion. Split-brain: dos nodos que")
    print("  se creen primario, escribiendo al mismo tiempo.\n")

    storage = {}  # storage compartido SIN fencing: gana quien escriba ultimo, sin avisar
    storage["saldo_cuenta_42"] = 100
    print(f"  saldo inicial (antes del split-brain): {storage['saldo_cuenta_42']}")
    storage["saldo_cuenta_42"] = 130  # el primario NUEVO acepta un deposito de 30, sin saber del viejo
    print(f"  t={auto.promoted_at + 1}: primario NUEVO procesa un deposito -> saldo={storage['saldo_cuenta_42']}")
    storage["saldo_cuenta_42"] = 70  # el primario VIEJO acepta (por su cuenta) un retiro de 30 sobre el saldo ORIGINAL
    print(f"  t={auto.promoted_at + 2}: primario VIEJO procesa un retiro -> saldo={storage['saldo_cuenta_42']}")
    print(f"\n  saldo final en el storage compartido: {storage['saldo_cuenta_42']}")
    print("  el deposito del primario NUEVO (el vigente) quedo PISADO por una escritura")
    print("  de un nodo que ya no deberia poder escribir — sin ningun error, sin que")
    print("  nadie se entere hasta que alguien audite los numeros y no cierren.\n")

    print("  Con failover MANUAL: la particion se curo en t=11, antes de que se")
    print("  cumpliera la confirmacion humana -> el manual nunca llego a dispararse,")
    print("  asi que en este caso puntual no hubo split-brain. Pero fue cuestion de")
    print("  timing, no una garantia: si la particion hubiera durado mas, el humano")
    print("  igual habria confirmado un failover innecesario.\n")


def demo_part3_fencing():
    print("=" * 70)
    print("Parte 3: la misma particion, esta vez con fencing por generacion")
    print("=" * 70)
    healthy = [True] * 5 + [False] * 6 + [True] * 9
    checker, auto, manual, log = run_scenario(healthy)

    storage = FencedStorage()
    old_primary_generation = 1
    storage.write(old_primary_generation, "saldo_cuenta_42", 100)
    print(f"  saldo inicial (generacion {old_primary_generation}): {storage.read('saldo_cuenta_42')[0]}")

    new_primary_generation = old_primary_generation + 1  # se asigna al promover en t=auto.promoted_at
    storage.advance_generation(new_primary_generation)  # el servicio de coordinacion registra la nueva epoca YA, sin esperar la primera escritura
    print(f"  t={auto.promoted_at}: standby promovido a primario con generacion {new_primary_generation}")

    print(f"\n  t={auto.promoted_at + 1}: primario NUEVO (generacion {new_primary_generation}) procesa un deposito de 30...")
    storage.write(new_primary_generation, "saldo_cuenta_42", 130)
    print(f"    -> aceptado, saldo={storage.read('saldo_cuenta_42')[0]}")

    print(f"\n  t={auto.promoted_at + 2}: primario VIEJO (generacion {old_primary_generation}) intenta procesar un retiro de 30...")
    try:
        storage.write(old_primary_generation, "saldo_cuenta_42", 70)
        print("    -> aceptado (esto NO deberia pasar)")
    except FencedError as exc:
        print(f"    -> RECHAZADO: {exc}")

    print(f"\n  saldo final: {storage.read('saldo_cuenta_42')[0]} (correcto: solo se aplico la escritura del primario vigente)")
    print("  el primario viejo recibio un error explicito en vez de corromper datos")
    print("  en silencio — sus clientes pueden reintentar contra el primario correcto")
    print("  en cuanto se enteren de que ya no lo es.")


def main():
    demo_part1_real_outage()
    demo_part2_split_brain()
    demo_part3_fencing()


if __name__ == "__main__":
    main()
