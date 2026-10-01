# Postmortem: circuit breaker no abrió durante degradación de saldo-service

- **Fecha del incidente**: 2026-06-14
- **Duración**: 47 minutos (14:03–14:50 UTC)
- **Severidad**: SEV-2
- **Autor**: equipo de checkout
- **Estado**: final

> Este postmortem es **sin culpa** (blameless): el objetivo es entender
> que condiciones del sistema permitieron el impacto, no evaluar el
> desempeño de ninguna persona. Ver [blame_checker.py](blame_checker.py)
> para el chequeo que se corrió sobre este documento antes de
> publicarlo.

## Resumen

Durante 47 minutos, `checkout-api` siguió enviando el 100% del tráfico
a `saldo-service` mientras este fallaba el 80% de sus requests, en vez
de que el circuit breaker abriera y activara el fallback. Los clientes
vieron errores directos (HTTP 500) en el checkout en lugar del mensaje
de fallback esperado. Aproximadamente el 12% de los intentos de compra
en la ventana fallaron sin poder reintentarse automáticamente.

## Impacto

- ~12% de los checkouts entre 14:03 y 14:50 UTC terminaron en error
  visible al usuario.
- 0 incidentes de pérdida de datos.
- Sin impacto en otros servicios.

## Línea de tiempo (UTC)

- **13:40** — Se mergea un refactor de `checkout-api` que reorganiza la
  configuración de resiliencia por servicio downstream.
- **14:03** — `saldo-service` empieza a degradarse (tasa de error sube
  del 0.5% al 80%) por saturación de conexiones a su base de datos.
- **14:03–14:50** — El circuit breaker de `checkout-api` hacia
  `saldo-service` permanece cerrado durante toda la degradación.
  `checkout-api` sigue enviando el 100% del tráfico, cada request
  esperando el timeout completo antes de fallar.
- **14:41** — Un ingeniero de guardia nota la alerta de latencia p99 de
  `checkout-api` y empieza a investigar siguiendo
  [RUNBOOK_EJEMPLO.md](RUNBOOK_EJEMPLO.md).
- **14:47** — Se identifica que el umbral del circuit breaker
  (`failure_threshold`) quedó en su valor por defecto (50 fallos
  consecutivos) en vez del valor de 5 usado antes del refactor.
- **14:50** — Se aplica un hotfix que corrige el umbral; el circuit
  breaker abre de inmediato y el fallback se activa. `saldo-service`
  se recupera por su cuenta minutos después.

## Causa raíz

El refactor del 13:40 movió la configuración de cada circuit breaker a
un archivo YAML centralizado. La migración copió los umbrales por
default del framework en vez de los valores explícitos que estaban
antes en el código (`failure_threshold=5`), y ningún test existente
verificaba el valor del umbral en sí — solo que el circuit breaker
"funcionara" en el caso feliz. Con el umbral en 50, `saldo-service`
necesitaba fallar 50 veces seguidas antes de que el circuito
considerara abrir, algo que con su patrón de fallos intermitentes
(80% de tasa de error, no 100%) casi nunca se cumplía en una racha
consecutiva.

## Factores contribuyentes

1. **La migración de configuración no tenía validación automática**
   contra los valores esperados por servicio — dependía de que quien
   revisara el PR notara la diferencia entre el YAML nuevo y el código
   viejo, en un diff de varios cientos de líneas.
2. **El ambiente de staging no reproduce fallos intermitentes**
   realistas (solo tiene un modo "downstream caído al 100%" o "downstream
   sano"), por lo que un umbral mal configurado para fallos parciales
   nunca se hubiera detectado ahí.
3. **No había una alerta directa sobre el estado del circuit breaker**
   (abierto/cerrado) — la única señal disponible era la latencia y tasa
   de error agregada de `checkout-api`, que tardó en cruzar el umbral
   de alerta porque el 20% de requests que sí tenían éxito diluían el
   promedio.

## Qué salió bien

- El runbook existente para "circuit breaker abierto" no aplicaba
  directamente (el circuito nunca abrió), pero la sección de
  diagnóstico igual guio al ingeniero de guardia a revisar
  configuración reciente, lo que llevó a la causa raíz en minutos.
- El hotfix fue de una sola línea y no requirió rollback de todo el
  refactor.

## Acción items

| Acción | Dueño | Estado |
|---|---|---|
| Agregar test que verifique el valor de `failure_threshold` por servicio contra un valor esperado explícito, no solo el comportamiento del circuit breaker | equipo checkout | pendiente |
| Agregar alerta directa sobre `circuit_breaker_state` por servicio (no solo latencia/error agregados) | SRE | pendiente |
| Extender el entorno de staging para simular fallos intermitentes (X% de tasa de error), no solo binario arriba/abajo | plataforma | pendiente |
| Agregar chequeo automático en CI que compare umbrales de resiliencia entre el YAML nuevo y los valores previos antes de un refactor de configuración | equipo checkout | pendiente |

## Por qué este postmortem es "sin culpa"

La primera versión de este documento decía que alguien "olvidó
actualizar el umbral" y que "debería haber revisado la configuración
antes de mergear". Esa version es honesta sobre lo que pasó, pero no
es **accionable**: la próxima persona que haga un refactor similar
puede cometer exactamente el mismo desliz, porque el problema real no
era la atención de una persona en un momento dado — era que **el
proceso de migración no tenía ninguna validación automática que
hiciera visible la diferencia**, y que **staging no podía haber
detectado el problema aunque alguien lo hubiera revisado con cuidado**.
Los action items de arriba atacan esas dos condiciones del sistema, no
la memoria o el cuidado de ninguna persona — por eso previenen la
recurrencia incluso si mañana es otra persona haciendo otro refactor.
