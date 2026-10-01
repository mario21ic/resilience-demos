"""Demo: Observabilidad — RED, USE, trazas distribuidas, histogramas.

  Parte 1 — Por que un promedio miente: una latencia bimodal, y la
            trampa del "promedio de promedios" entre hosts con
            distinto volumen de trafico.
  Parte 2 — USE como indicador temprano: la saturacion de un recurso
            avisa antes de que las metricas RED (errores) se muevan.
  Parte 3 — Trazas distribuidas: el total no dice DONDE se fue el
            tiempo; el desglose por span si.
"""
from observability import percentile, simulate_saturation_vs_errors


def demo_averages_lie():
    print("=" * 70)
    print("Parte 1: por que un promedio esconde la realidad")
    print("=" * 70)

    fast = [10.0] * 950
    slow = [2000.0] * 50
    all_latencies = fast + slow
    sorted_latencies = sorted(all_latencies)

    avg = sum(all_latencies) / len(all_latencies)
    print(f"  1000 requests: 950 tardan 10ms, 50 tardan 2000ms.")
    print(f"  promedio: {avg:.1f}ms (parece perfectamente razonable)")
    print(f"  p50: {percentile(sorted_latencies, 0.50):.0f}ms  "
          f"p95: {percentile(sorted_latencies, 0.95):.0f}ms  "
          f"p99: {percentile(sorted_latencies, 0.99):.0f}ms")
    print(f"  -> el 5% de los requests tarda 200x mas que la mediana, y el promedio")
    print(f"     ni lo insinua.\n")

    print("  la trampa del 'promedio de promedios' (agregar sin ponderar por volumen):")
    host_a = [10.0] * 9000
    host_b = [500.0] * 100
    avg_a = sum(host_a) / len(host_a)
    avg_b = sum(host_b) / len(host_b)
    naive_avg_of_avgs = (avg_a + avg_b) / 2
    true_avg = sum(host_a + host_b) / len(host_a + host_b)

    print(f"    host A: {avg_a:.1f}ms de promedio ({len(host_a)} requests)")
    print(f"    host B: {avg_b:.1f}ms de promedio ({len(host_b)} requests)")
    print(f"    promedio de esos dos promedios (sin ponderar): {naive_avg_of_avgs:.1f}ms")
    print(f"    promedio real sobre TODOS los requests individuales: {true_avg:.1f}ms")
    print(f"    -> el numero 'sin ponderar' exagera la latencia real {naive_avg_of_avgs / true_avg:.1f}x\n")


def demo_use_leading_indicator():
    print("=" * 70)
    print("Parte 2: USE (saturacion) avisa antes que RED (errores)")
    print("=" * 70)

    history = simulate_saturation_vs_errors(60, arrival_rate=10, service_rate=8)
    first_high_saturation = next((t for t, s, e in history if s >= 0.8), None)
    first_error = next((t for t, s, e in history if e > 0), None)

    for t, s, e in history[::10]:
        print(f"  t={t:>3}: saturacion (USE)={s:>5.0%}   error_rate (RED)={e:>5.0%}")

    print(f"\n  saturacion cruza el 80% en el tick {first_high_saturation}")
    print(f"  los primeros errores reales aparecen recien en el tick {first_error}")
    print(f"  -> {first_error - first_high_saturation} ticks de aviso previo — tiempo real para actuar")
    print("     (escalar, aplicar load shedding) antes de que el problema le llegue")
    print("     a un solo usuario real.\n")


def demo_distributed_tracing():
    print("=" * 70)
    print("Parte 3: trazas distribuidas — el total no dice donde se fue el tiempo")
    print("=" * 70)

    spans = [
        ("gateway", 5),
        ("service_a", 8),
        ("service_b", 12),
        ("database", 420),
        ("service_b (vuelta)", 6),
        ("service_a (vuelta)", 4),
        ("gateway (vuelta)", 3),
    ]
    total = sum(d for _, d in spans)

    print(f"  latencia total observada por el cliente: {total}ms")
    print(f"  sin trazas, eso es TODO lo que se sabe.\n")

    print("  con trazas distribuidas, el desglose por span:")
    for name, duration in spans:
        pct = duration / total
        bar = "#" * int(pct * 40)
        print(f"    {name:<20} {duration:>4}ms {bar} ({pct:.0%})")

    print(f"\n  el {spans[3][1] / total:.0%} del tiempo esta en un solo salto (la base de datos) —")
    print("  sin la traza, esa informacion se hubiera perdido completamente detras")
    print("  de un unico numero de latencia total.")


def main():
    demo_averages_lie()
    demo_use_leading_indicator()
    demo_distributed_tracing()


if __name__ == "__main__":
    main()
