# Canary / blue-green / rolling con criterios de promoción automáticos

## Que es

La mayoria de las caidas las causa un cambio, no el hardware. Tres
estrategias para desplegar una version nueva sin apostar todo de una:

- **Rolling**: reemplaza instancias de a poco (ej. 10% por oleada),
  varias oleadas hasta llegar al 100%.
- **Blue-green**: dos ambientes completos corriendo en paralelo; se
  cambia TODO el trafico de una vez del viejo (blue) al nuevo (green).
  Rollback instantaneo: volver a apuntar al ambiente viejo.
- **Canary**: como rolling, pero con la intencion explicita de que las
  primeras oleadas sean chicas (5%, 10%...) para minimizar el costo de
  descubrir un problema antes de comprometerse a mas.

## Lo que realmente importa: el criterio, no el porcentaje

Ninguna de las tres estrategias es segura por si sola. Lo que las
protege de un deploy malo es el **criterio automatico** que decide,
despues de cada oleada, si conviene seguir adelante o frenar — sin
eso, "desplegar de a poco" solo demora el desastre en vez de evitarlo:
si nadie mira las metricas entre oleadas, el rollout va a llegar al
100% en el horario programado, tenga o no un problema real.

## Estructura del ejemplo

- `deployments.py`: `simulate_rollout` — aplica un plan de oleadas y,
  si `use_gate` esta activo, frena en cuanto la tasa de error del
  trafico ya expuesto supera un umbral.
- `demo_deployments.py`: dos partes.
  1. Compara el radio de impacto de un deploy malo entre las tres
     estrategias, todas con el mismo criterio automatico.
  2. Aisla el valor del criterio en si: la misma estrategia canary,
     con y sin chequeo automatico entre oleadas.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_deployments.py
```

Salida esperada (version nueva con 50% de tasa de error, umbral de
frenado en 5%):

```
Parte 1:
  rolling:    se frena en 10% expuesto, daño=5.0
  blue-green: se frena en 100% expuesto, daño=50.0
  canary:     se frena en 5% expuesto, daño=2.5

Parte 2 (misma estrategia canary):
  CON criterio automatico: daño=2.5
  SIN criterio (horario fijo): daño=50.0 -> 20x mas daño
```

## Puntos clave

- Blue-green optimiza para velocidad de rollback (instantaneo), no
  para radio de impacto durante la deteccion — un problema solo se
  nota despues de que el 100% del trafico ya esta expuesto.
- Canary con oleadas iniciales chicas minimiza cuanto se paga por
  descubrir un problema, a costa de que el rollout completo tarda
  mas tiempo cuando todo sale bien.
- El criterio automatico es exactamente el mismo tipo de señal que
  [outlier detection](../../level3/5-outlier-detection) (tasa de
  error observada) o un [circuit breaker](../../level2/1-circuit-breaker)
  — la novedad aca es que la decision no es "dejar de llamar a una
  replica", es "dejar de avanzar con un cambio".
- Esto es la misma logica que el rollout celda-por-celda de
  [cell-based architecture](../../level3/9-cell-based-arch): contener
  el radio de impacto de un cambio malo antes de que llegue a todo el
  sistema, verificando con datos reales entre cada paso.
