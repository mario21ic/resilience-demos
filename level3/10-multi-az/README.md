# Multi-AZ / multi-región con static stability

## Que es

Repartir infraestructura entre varias zonas de disponibilidad (AZ) o
regiones es la base de la alta disponibilidad — pero **como** se
recupera el sistema cuando pierde una AZ importa tanto como el hecho
de tenerlas. **Static stability** es el principio (popularizado por
AWS) de que esa recuperacion **no debe depender del control plane**
funcionando durante el incidente.

## Control plane vs data plane

- **Data plane**: lo que efectivamente sirve trafico ahora mismo —
  instancias ya corriendo, un load balancer redirigiendo trafico. Son
  operaciones simples y robustas.
- **Control plane**: lo que **provisiona o cambia configuracion** —
  APIs de autoscaling, de lanzar instancias, de actualizar DNS. Son
  sistemas mas complejos, a menudo compartidos entre muchos clientes,
  y — el punto clave — **suelen estar mas degradados justo durante un
  incidente grande**, porque muchos sistemas reaccionan al mismo
  evento al mismo tiempo y lo golpean simultaneamente (el mismo
  problema que [retry budget](../../level1/6-retry-budget) ataca a
  escala de una sola aplicacion, aca a escala de nube entera).

Un plan de recuperacion que dice "si perdemos una AZ, lanzamos mas
instancias en las que quedan" esta apostando a que el control plane
va a responder bien exactamente cuando es menos probable que lo haga.

## La alternativa: pre-aprovisionar

Static stability significa que la capacidad que va a hacer falta
durante un failover **ya esta corriendo**, de antemano, en las AZs
sanas. Perder una AZ solo requiere una operacion de data plane (el
load balancer deja de mandarle trafico) — cero llamadas a una API que
podria estar ocupada atendiendo a todo el resto de internet
reaccionando al mismo incidente.

## Estructura del ejemplo

- `static_stability.py`: `simulate_static_recovery` y
  `simulate_dynamic_recovery` (Parte 1 y 3), `provisioning_overhead`
  (la regla N-1, Parte 2).
- `demo_multi_az.py`: tres partes.
  1. Recuperacion estatica vs dinamica ante la misma caida de AZ.
  2. Cuanto hay que pre-aprovisionar por AZ segun cuantas AZs tenga
     el sistema.
  3. La estatica es constante; la dinamica tiene una varianza enorme
     porque depende del estado del control plane en el peor momento.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_multi_az.py
```

Salida esperada (resumen):

```
Parte 1: estatica -> 0 ticks con capacidad insuficiente
         dinamica (control plane al 10% de exito por intento) -> 9 ticks insuficiente,
                   6 intentos de scale-up, recuperada recien en t+9

Parte 2: N=2 AZs -> 100% extra por AZ (2.00x el sistema)
         N=3 AZs -> 50% extra por AZ (1.50x)
         N=6 AZs -> 20% extra por AZ (1.20x)

Parte 3: estatica siempre 1 tick; dinamica entre 5 y 42 ticks segun 30 corridas
```

## Puntos clave

- Pre-aprovisionar cuesta dinero de forma constante y predecible (la
  regla N-1 de la Parte 2). Depender del control plane cuesta menos
  el 99% del tiempo, pero la factura llega exactamente cuando mas
  duele, y en una moneda que no se puede pagar con dinero: tiempo de
  recuperacion impredecible.
- 3 AZs no es un numero arbitrario: es el punto donde el
  sobre-aprovisionamiento por AZ (50%) deja de ser prohibitivo — con
  solo 2, sobrevivir a perder una implica pagar el doble todo el
  tiempo.
- Esto es la misma logica de
  [redundancia N+1/N+2](../redundancia-n1-n2) y de
  [failover](../2-failover), pero con un matiz adicional: no alcanza
  con TENER redundancia, la recuperacion tiene que poder usarla sin
  pedirle permiso a nada que pueda estar ocupado en ese momento.
- La leccion se generaliza mas alla de AZs: cualquier plan de
  recuperacion que dependa de un sistema compartido y potencialmente
  sobrecargado (una API de terceros, un servicio de autenticacion
  central, el propio sistema de monitoreo) hereda el mismo riesgo —
  la pregunta a hacerse siempre es "¿esto que necesito para
  recuperarme, va a estar disponible precisamente cuando lo necesite?".
