# Runbook: circuit breaker abierto en produccion

> Un runbook se escribe ANTES del incidente, para que durante el
> incidente nadie tenga que razonar desde cero bajo presion. Cada
> seccion responde una pregunta concreta que alguien de guardia va a
> tener en el peor momento posible para pensar con claridad.

## Sintoma

Alerta: `circuit_breaker_state{service="checkout-api"} == "open"` por
mas de 2 minutos.

## Impacto

- Los requests a `checkout-api` estan siendo rechazados de inmediato
  (fail fast) en vez de esperar respuesta del backend.
- Los usuarios ven el fallback configurado (ver
  [level1/8-fallback](../../level1/8-fallback)) — normalmente un
  mensaje de "intenta de nuevo en un momento", no un error crudo.
- **No es necesariamente una emergencia**: el circuit breaker esta
  haciendo su trabajo. El problema real es lo que causo que se abra.

## Diagnostico

1. Revisar el dashboard de `checkout-api`
   (`grafana.internal/d/checkout-api`): ¿la tasa de error o la
   latencia p99 subieron ANTES de que el circuito se abriera?
2. Revisar los logs del backend downstream
   (`saldo-service`) en la misma ventana de tiempo — ¿hay errores 5xx,
   timeouts, o un pico de latencia?
3. Verificar si hubo un deploy reciente a `saldo-service`
   (`kubectl rollout history deployment/saldo-service`) — un cambio
   de codigo es la causa mas comun.
4. Verificar la capacidad del backend: ¿esta saturado (CPU, conexiones
   a la base de datos)? Ver el dashboard USE
   (`grafana.internal/d/saldo-service-use`).

## Mitigacion

- **Si el backend se recupera solo** (tras un deploy revertido, o el
  pico de trafico paso): esperar — el circuit breaker va a pasar a
  half-open automaticamente y cerrarse cuando el backend responda bien
  de nuevo. No hace falta intervenir.
- **Si el backend NO se recupera solo**: escalar a el equipo dueño de
  `saldo-service` (canal `#saldo-service-oncall`). No forzar el cierre
  manual del circuit breaker sin confirmar primero que el backend
  realmente esta sano — forzarlo antes de tiempo solo vuelve a exponer
  al backend a la carga que lo tumbo.
- **Si el impacto a usuarios es alto** y no hay ETA de resolucion del
  backend: considerar activar el
  [kill switch](../../level6/2-feature-flags-kill-switch) de la
  funcionalidad de checkout completa, para mostrar un mensaje mas
  claro que el fallback generico.

## Escalamiento

- Sin mejora en 15 minutos -> escalar a el equipo de `saldo-service`.
- Sin mejora en 30 minutos, o impacto a mas del 10% de checkouts ->
  declarar incidente formal (`#incidents`, seguir el proceso de
  incident commander).

## Referencias

- Dashboard: `grafana.internal/d/checkout-api`
- Alertas relacionadas: `saldo-service-error-rate`, `saldo-service-latency-p99`
- Postmortem del ultimo incidente similar: `POSTMORTEM_EJEMPLO.md`
