"""Demo: Chaos engineering / fault injection / game days.

Hipotesis: "un mecanismo de resiliencia (circuit breaker + failover)
mantiene la tasa de exito aunque se inyecte una falla real en una
fraccion del trafico". Se prueba con un radio de impacto CRECIENTE,
empezando chico, contra dos sistemas: uno donde el mecanismo funciona
de verdad, y otro donde esta sutilmente roto.
"""
import random

from chaos import simulate_experiment

BLAST_RADIUS_PROGRESSION = [0.01, 0.10, 0.50, 1.00]
N_REQUESTS = 5000


def run_progression(resilience_mechanism_works: bool, label: str):
    print(f"Sistema con mecanismo de resiliencia {label}:")
    for blast_radius in BLAST_RADIUS_PROGRESSION:
        rng = random.Random(1)
        success_rate = simulate_experiment(N_REQUESTS, blast_radius, resilience_mechanism_works, rng)
        status = "hipotesis se sostiene" if success_rate > 0.999 else "hipotesis REFUTADA"
        print(f"  blast radius={blast_radius:>4.0%}: tasa de exito={success_rate:>6.1%}  ({status})")
    print()


def main():
    print("Hipotesis: 'la tasa de exito se mantiene aunque inyectemos esta falla'.")
    print(f"Radio de impacto del experimento, creciendo de a poco: {BLAST_RADIUS_PROGRESSION}\n")

    run_progression(resilience_mechanism_works=True, label="funcionando de verdad")
    run_progression(resilience_mechanism_works=False, label="sutilmente ROTO")

    print("Con el mecanismo funcionando, la hipotesis se sostiene en todos los niveles")
    print("de radio de impacto — cada experimento exitoso da mas confianza para probar")
    print("un radio mayor la proxima vez.")
    print()
    print("Con el mecanismo roto, el experimento de apenas 1% YA muestra una caida")
    print("medible (98.8% en vez de 100%) — suficiente para detectar el problema real")
    print("con un impacto minimo, en vez de descubrirlo durante un incidente real sin")
    print("ningun limite ni nadie preparado para reaccionar.")


if __name__ == "__main__":
    main()
