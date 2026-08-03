"""Tres estrategias para desplegar una version nueva, y por que el
"criterio de promocion automatico" (no el porcentaje en si) es lo que
realmente determina el radio de impacto de un deploy malo:

  - Rolling: reemplaza instancias de a poco (ej. 10% por vez), en
    varias oleadas.
  - Blue-green: dos ambientes completos; se cambia TODO el trafico de
    una vez del viejo (blue) al nuevo (green).
  - Canary: empieza con una fraccion chica del trafico (ej. 5%) y va
    creciendo, oleada por oleada, igual que rolling — la diferencia es
    de intencion: las primeras oleadas son deliberadamente chicas para
    minimizar el costo de descubrir un problema.

Ninguna de las tres es segura por si sola: lo que las protege de un
deploy malo es el CRITERIO AUTOMATICO que decide, despues de cada
oleada, si seguir adelante o frenar — sin eso, "desplegar de a
poco" solo demora el desastre, no lo evita.
"""

ROLLING_STAGES = [10, 20, 20, 20, 20, 10]   # % acumulado: 10,30,50,70,90,100
BLUE_GREEN_STAGES = [100]                    # todo de una
CANARY_STAGES = [5, 10, 15, 20, 50]          # % acumulado: 5,15,30,50,100


def simulate_rollout(stages: list, bad_error_rate: float, halt_threshold: float, use_gate: bool = True):
    """Simula un rollout oleada por oleada. Tras cada oleada, si
    `use_gate` esta activo, se mide la tasa de error observada en el
    trafico ya expuesto a la version nueva; si supera
    `halt_threshold`, el rollout se frena ahi mismo.

    Devuelve (porcentaje_expuesto_al_frenar, daño_acumulado,
    oleada_en_la_que_se_freno). El "daño acumulado" es una medida
    simple: por cada oleada, cuanto trafico nuevo se expuso multiplicado
    por la tasa de error real de esa version.
    """
    exposed_pct = 0
    damage = 0.0
    halted_at = None

    for stage_pct in stages:
        exposed_pct += stage_pct
        damage += stage_pct * bad_error_rate

        if use_gate and bad_error_rate > halt_threshold:
            halted_at = exposed_pct
            break

    return exposed_pct, damage, halted_at
