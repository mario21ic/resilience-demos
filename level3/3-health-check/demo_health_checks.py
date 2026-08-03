"""Demo: Health checks — liveness / readiness / startup, superficiales
vs profundos. Un health check profundo mal hecho propaga fallas en
cascada.

  Parte 1 — El chequeo profundo en el probe EQUIVOCADO: poner una
            dependencia externa (una base de datos) en la LIVENESS en
            vez de en la READINESS. Cuando la dependencia tiene un
            blip transitorio, la version mal diseñada no solo pierde
            trafico durante el blip — reinicia toda la flota, y el
            reinicio tarda mucho mas en completarse que el blip
            original.
  Parte 2 — El chequeo profundo sobre la dependencia EQUIVOCADA:
            incluir en la readiness una dependencia NO esencial. Una
            falla parcial y menor (algo secundario que no hacia falta
            para servir la mayoria del trafico) termina tumbando el
            100% de la capacidad.

En ambos casos, el "chequeo profundo" en si no es el problema — el
problema es DONDE se lo pone y QUE decide chequear.
"""
from health_probes import simulate_liveness_scope, simulate_readiness_scope

RESTART_TIME = 6  # ticks que tarda una instancia en terminar de reiniciar (reconectar, precalentar cache)


def summarize(fractions: list[float], label: str):
    print(label)
    prev = None
    for t, fraction in enumerate(fractions):
        if fraction != prev:
            status = "100% disponible" if fraction == 1.0 else "0% disponible"
            print(f"  t={t:>2}: {status}")
        prev = fraction
    down_ticks = sum(1 for f in fractions if f == 0.0)
    print(f"  -> ticks con 0% de capacidad: {down_ticks}/{len(fractions)}\n")


def demo_liveness_misconfig():
    print("=" * 70)
    print("Parte 1: dependencia chequeada en LIVENESS (mal) vs en READINESS (bien)")
    print("=" * 70)
    print("La base de datos tiene un blip transitorio de 5 ticks (t=5 a t=9).\n")

    db_healthy = [True] * 5 + [False] * 5 + [True] * 15

    bad = simulate_liveness_scope(db_healthy, RESTART_TIME, deep_liveness=True)
    summarize(bad, "Mal diseño: la DB se revisa en la LIVENESS (falla -> se reinicia la flota):")

    good = simulate_liveness_scope(db_healthy, RESTART_TIME, deep_liveness=False)
    summarize(good, "Buen diseño: la DB se revisa solo en la READINESS (falla -> se saca de rotacion, sin reiniciar):")

    bad_down = sum(1 for f in bad if f == 0.0)
    good_down = sum(1 for f in good if f == 0.0)
    print(f"El blip real duro 5 ticks. Con el chequeo en el lugar equivocado, la flota")
    print(f"estuvo caida {bad_down} ticks — mas del doble — porque encima del blip hubo")
    print(f"que esperar a que TODAS las instancias terminaran de reiniciarse. Con el")
    print(f"chequeo en readiness, la caida duro exactamente lo que duro el blip real ({good_down} ticks).\n")


def demo_readiness_scope():
    print("=" * 70)
    print("Parte 2: dependencia NO esencial incluida en la READINESS")
    print("=" * 70)
    print("La DB principal nunca falla. Un servicio secundario (recomendaciones)")
    print("tiene un blip de 5 ticks (t=5 a t=9), sin relacion con la funcion principal.\n")

    core_healthy = [True] * 20
    optional_healthy = [True] * 5 + [False] * 5 + [True] * 10

    bad = simulate_readiness_scope(core_healthy, optional_healthy, checks_optional=True)
    summarize(bad, "Mal diseño: la readiness tambien exige que 'recomendaciones' este sano:")

    good = simulate_readiness_scope(core_healthy, optional_healthy, checks_optional=False)
    summarize(good, "Buen diseño: la readiness solo exige que la DB principal este sana:")

    print("La funcionalidad de recomendaciones en si misma se degrada igual en ambos")
    print("casos (deberia usar un fallback, ver level1/8-fallback) — la diferencia es")
    print("que en el mal diseño, TODO el trafico se corta por una falla que no tenia")
    print("nada que ver con poder atender la mayoria de los requests.")


def main():
    demo_liveness_misconfig()
    demo_readiness_scope()


if __name__ == "__main__":
    main()
