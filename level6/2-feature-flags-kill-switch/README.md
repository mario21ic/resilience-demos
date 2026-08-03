# Feature flags y kill switch

## Que es

Un **feature flag** decide si una funcionalidad esta activa via
**configuracion**, no via codigo desplegado. Esto separa dos cosas que
suelen confundirse: **desplegar** (llevar codigo nuevo a produccion) y
**lanzar** (hacerlo visible o activo para los usuarios). Se puede
desplegar una funcionalidad completamente apagada, y encenderla
despues sin volver a tocar el pipeline de deploy.

Un **kill switch** es la aplicacion mas critica de esto: un apagador
de emergencia. Si algo recien lanzado esta causando problemas,
mitigar el incidente es tan rapido como apagar un flag — sin esperar
a que termine un ciclo completo de revertir, buildear, testear y
desplegar.

## Por que la velocidad importa tanto

Durante un incidente, cada minuto cuenta. Revertir codigo pasa por un
pipeline completo (build, tests, deploy progresivo) que, aunque este
bien optimizado, se mide en minutos. Apagar un flag es una escritura
de configuracion que el codigo YA DESPLEGADO lee en la siguiente
consulta — se mide en segundos.

## Rollout gradual sin reordenar a nadie

Un flag tambien sirve para exponer una funcionalidad a un porcentaje
creciente de usuarios (parecido a un [canary](../1-canary-blue-green-rolling),
pero a nivel de usuario en vez de instancia). La forma correcta de
implementarlo usa un **hash estable** del ID de cada usuario para
decidir su "bucket": asi, subir el porcentaje de 10% a 30% solo
AGREGA usuarios nuevos al grupo — nunca le saca la funcionalidad a
alguien que ya la tenia, ni reordena a nadie.

## Estructura del ejemplo

- `feature_flags.py`: `is_enabled` (rollout por hash estable) y los
  tiempos de cada etapa de un pipeline de deploy vs un kill switch.
- `demo_feature_flags.py`: dos partes.
  1. Compara cuanto tarda mitigar un incidente por cada via.
  2. Muestra que subir el porcentaje de rollout nunca reordena a los
     usuarios ya expuestos.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_feature_flags.py
```

Salida esperada:

```
Parte 1: redeploy completo = 16.0 min, kill switch = 0.6 min -> 27x mas rapido

Parte 2: usuarios activos al 10%: 1040
         usuarios activos al 30%: 2996
         de los que estaban en 10%, siguen activos en 30%: 1040/1040
```

## Puntos clave

- Un kill switch solo funciona si el codigo YA ESTA desplegado con la
  logica del flag adentro — no sirve para apagar algo que nunca se
  penso como apagable. Hay que diseñar el flag ANTES de necesitarlo,
  no durante el incidente.
- El hash estable por usuario es la misma tecnica que la asignacion
  estable de [cell-based architecture](../../level3/9-cell-based-arch):
  crecer no deberia significar reordenar lo que ya funcionaba.
- Los flags acumulan deuda tecnica si no se limpian: una vez que una
  funcionalidad esta 100% lanzada (o definitivamente descartada), el
  flag y sus ramas condicionales deberian eliminarse — de lo
  contrario, la cantidad de combinaciones posibles entre flags viejos
  crece y se vuelve dificil de razonar.
- Combinado con un criterio automatico (ver
  [1-canary-blue-green-rolling](../1-canary-blue-green-rolling)), un
  kill switch puede dispararse SOLO, sin esperar a que una persona lo
  note y actue — la misma señal que frena un rollout puede apagar un
  flag automaticamente.
