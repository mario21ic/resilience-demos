"""Demo: Feature flags y kill switch.

  Parte 1 — Velocidad de mitigacion: apagar un flag contra revertir
            el codigo y esperar todo el pipeline de deploy.
  Parte 2 — Rollout gradual estable: subir el porcentaje de usuarios
            expuestos nunca le saca la funcionalidad a alguien que ya
            la tenia, gracias a un hash estable por usuario.
"""
from feature_flags import KILL_SWITCH_STAGES, PIPELINE_STAGES, is_enabled


def demo_mitigation_speed():
    print("=" * 70)
    print("Parte 1: velocidad de mitigacion — kill switch vs redeploy")
    print("=" * 70)

    print("Mitigar via rollback de codigo + redeploy:")
    for stage, minutes in PIPELINE_STAGES.items():
        print(f"  {stage}: {minutes:.1f} min")
    redeploy_total = sum(PIPELINE_STAGES.values())
    print(f"  TOTAL: {redeploy_total:.1f} min\n")

    print("Mitigar via kill switch:")
    for stage, minutes in KILL_SWITCH_STAGES.items():
        print(f"  {stage}: {minutes:.1f} min")
    kill_switch_total = sum(KILL_SWITCH_STAGES.values())
    print(f"  TOTAL: {kill_switch_total:.1f} min")

    print(f"\n  -> {redeploy_total / kill_switch_total:.0f}x mas rapido apagando un flag que")
    print("     esperando un ciclo completo de build, tests y deploy — la diferencia")
    print("     entre 'ya esta resuelto' y 'todavia estamos building' durante un incidente.\n")


def demo_stable_rollout():
    print("=" * 70)
    print("Parte 2: rollout gradual estable — subir el % no reordena a nadie")
    print("=" * 70)

    users = [f"user-{i}" for i in range(10_000)]

    enabled_at_10 = {u for u in users if is_enabled(u, 10, "new_checkout")}
    enabled_at_30 = {u for u in users if is_enabled(u, 30, "new_checkout")}
    enabled_at_100 = {u for u in users if is_enabled(u, 100, "new_checkout")}

    still_enabled = enabled_at_10 & enabled_at_30

    print(f"  usuarios con el flag activo al 10%: {len(enabled_at_10)}")
    print(f"  usuarios con el flag activo al 30%: {len(enabled_at_30)}")
    print(f"  de los que ya estaban activos en 10%, siguen activos en 30%: "
          f"{len(still_enabled)}/{len(enabled_at_10)}")
    print(f"  al 100%, todos los usuarios quedan activos: {len(enabled_at_100)}/{len(users)}")
    print("\n  subir el porcentaje de rollout solo AGREGA usuarios nuevos al grupo —")
    print("  nunca saca a alguien que ya tenia la funcionalidad activa, porque el")
    print("  bucket de cada usuario sale de un hash estable de su propio ID.")


def main():
    demo_mitigation_speed()
    demo_stable_rollout()


if __name__ == "__main__":
    main()
