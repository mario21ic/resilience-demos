# Saga — orquestada vs coreografiada

## Que es

Una transaccion distribuida (crear un pedido que involucra
inventario, pago y envio, cada uno en un servicio distinto) no puede
usar una transaccion ACID clasica — no hay un unico motor de base de
datos que la contenga entera. Una **saga** resuelve esto con una
secuencia de transacciones LOCALES, cada una en su propio servicio, y
si algo falla a mitad de camino, se ejecutan **compensaciones**: las
operaciones que deshacen el efecto de los pasos que ya se completaron,
en orden inverso.

No es magia: la consistencia deja de ser instantanea (durante la
saga, el sistema pasa por estados intermedios reales) y pasa a ser
**eventual** — se garantiza que, al final, o todo se aplico, o todo se
deshizo, pero no en un solo instante atomico.

## Dos formas de coordinar la misma saga

- **Orquestada**: un coordinador central conoce todos los pasos, en
  orden, y sus compensaciones. Si un paso falla, el orquestador mismo
  dispara las compensaciones de los pasos ya completados. Todo el
  flujo vive en un solo lugar — facil de leer de punta a punta, facil
  de agregar o quitar un paso, pero el coordinador tiene que conocer
  a todos los servicios involucrados.
- **Coreografiada**: no hay coordinador. Cada servicio reacciona a
  eventos que le interesan y publica los suyos propios — el flujo
  completo (incluidas las compensaciones) es la SUMA de todas esas
  suscripciones repartidas entre servicios independientes. Ningun
  servicio conoce a los demas directamente, pero tampoco hay un solo
  lugar donde leer "asi se deshace esta saga completa".

## El mismo resultado, organizado distinto

Este ejemplo corre la MISMA saga (reservar inventario -> cobrar pago
-> coordinar envio) bajo ambas coordinaciones, con tres escenarios:
exito, falla en el pago, falla en el envio. Las dos formas llegan
exactamente al mismo resultado final en cada caso — la diferencia es
puramente de **donde vive la logica**, no de que hace.

## Estructura del ejemplo

- `services.py`: los tres pasos de negocio (accion + compensacion),
  compartidos por ambas coordinaciones — lo que cambia entre
  orquestada y coreografiada no es QUE hace cada paso, sino QUIEN
  decide el orden.
- `saga_orchestrated.py`: `run_orchestrated_saga` — una lista
  explicita de pasos y sus compensaciones, recorrida por un
  coordinador central.
- `event_bus.py` + `saga_choreographed.py`: un bus de eventos minimo
  y los handlers de cada servicio, cada uno suscripto solo a los
  eventos que le importan.
- `demo_saga.py`: corre los tres escenarios bajo ambas coordinaciones.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_saga.py
```

Salida esperada (falla en el envio, coordinacion orquestada):

```
  falla en el envio:
    - inventario reservado
    - pago cobrado
    - envio coordinado
    - FALLO en arrange_shipping: sin transportista disponible
    - COMPENSACION: pago reembolsado
    - COMPENSACION: inventario liberado
```

La version coreografiada, para el mismo escenario, llega al mismo
estado final (pago reembolsado, inventario liberado) pero via una
cadena de eventos (`ShippingFailed -> PaymentRefunded ->
InventoryReleaseRequested`) que ningun componente ve completa de
punta a punta.

## Puntos clave

- Las compensaciones se ejecutan en orden **inverso** al de los pasos
  originales — es la misma logica que un `finally` anidado: lo ultimo
  que se hizo es lo primero que se deshace.
- Orquestada es mas facil de operar y depurar (hay un solo lugar
  donde ver el flujo completo, incluidas las fallas), a costa de que
  el orquestador conozca a todos los servicios y sea, en la practica,
  el dueño del proceso de negocio completo.
- Coreografiada evita ese acoplamiento (cada servicio solo conoce sus
  propios eventos de entrada y salida), pero agregar un paso nuevo a
  mitad de la saga significa tocar las suscripciones de varios
  servicios existentes, no una sola lista — el costo de flexibilidad
  se paga en trazabilidad.
- Una compensacion no siempre puede deshacer perfectamente su accion
  original (un email ya enviado no se puede "des-enviar") — en esos
  casos, la compensacion es una accion de negocio distinta (mandar un
  segundo email de disculpas), no un rollback literal. Diseñar
  compensaciones es una decision de negocio, no solo tecnica.
- Esto es distinto de un [circuit breaker](../../level2/1-circuit-breaker)
  o un [retry](../../level1/2-retry): esos patrones deciden si
  reintentar UNA llamada; una saga decide que hacer con TODO UN
  PROCESO de negocio que ya avanzo parcialmente cuando una parte de
  el falla.
