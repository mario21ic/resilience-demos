# Multiplexing + connection pooling — HTTP/2 y gRPC

## Que es

Abrir una conexion TCP (y su handshake TLS) cuesta tiempo real, y ese
costo se paga **una vez por conexion**, no una vez por request. Dos
tecnicas relacionadas reducen ese costo:

- **Connection pooling**: reusar una conexion ya abierta para muchos
  requests (HTTP/1.1 keep-alive), en vez de abrir y cerrar una por
  cada uno.
- **Multiplexing**: ir un paso mas alla y permitir MUCHOS requests
  concurrentes ("streams") sobre esa misma conexion, sin que se
  bloqueen entre si — esto es lo que hacen HTTP/2 y gRPC (que corre
  sobre HTTP/2).

Esto no es solo una optimizacion de latencia. Reducir el costo de
abrir una conexion es lo que hace **barato el hedging**: mandar el
mismo request a un backup en paralelo y quedarse con el que responda
primero (la tecnica que describe el paper "The Tail at Scale" de
Google) — sin pooling, cada hedge pagaria su propio handshake
completo, y podria terminar costando mas de lo que ahorra.

## Estructura del ejemplo

- `server.py`: servidor HTTP/1.1 con keep-alive, que simula un costo
  de handshake de 150ms **por conexion aceptada** (no por request) —
  para poder medir la diferencia real entre pooling y no pooling.
- `multiplexer.py`: `Provider` (conexion pooled + circuit breaker) y
  `Multiplexer` (prueba proveedores en orden, con failover automatico
  y transparente).
- `demo_multiplexer.py`: cuatro partes.

### Parte 1 — Costo de conexion, medido de verdad

20 requests, `http.client.HTTPConnection` nueva por request vs una
sola conexion reusada (keep-alive). Ambos casos hacen las mismas
llamadas HTTP reales contra el mismo servidor.

### Parte 2 — Concurrencia: pool limitado vs multiplexado

20 requests concurrentes con duraciones variables. Un pool de
conexiones HTTP/1.1 solo permite tantos requests en paralelo como
conexiones tenga (los de mas hacen cola); HTTP/2 permite cientos de
streams concurrentes sobre una sola conexion — muy por encima de
cualquier demanda realista, asi que en la practica no hay cola.

### Parte 3 — Hedging barato con conexion caliente

El mismo hedge (disparado a los 50ms si el primario no respondio),
comparando una conexion al backup recien abierta (fria) contra una ya
pooled de antes (caliente). Ambos ganan al primario lento, pero el
hedge frio gasta buena parte de su ventaja en el handshake que el
caliente ya no tiene que pagar.

### Parte 4 — El multiplexer como sintesis

En un router de proveedores/modelos (llamar a distintos backends de
LLM, distintas regiones de una misma API), lo que parece un objeto
simple — `multiplexer.request(payload)` — es en realidad la
composicion de:

- **Connection pooling**: cada proveedor tiene su conexion ya
  establecida.
- **Load balancing**: el orden en que se prueban los proveedores es,
  en su forma mas simple, una politica de balanceo (siempre preferir
  el primero disponible); las estrategias de
  [load balancing](../4-load-balancing) aplican igual de bien aca.
- **Circuit breaker**: cada proveedor tiene el suyo (version
  simplificada aca; la completa esta en
  [level2/1-circuit-breaker](../../level2/1-circuit-breaker)).
- **Failover**: si el proveedor preferido falla o tiene el circuito
  abierto, se sigue automaticamente al siguiente — el mismo concepto
  de [failover](../2-failover), aplicado dentro de un solo cliente en
  vez de entre primario y standby.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_multiplexer.py
```

Salida esperada (resumen; los tiempos exactos pueden variar levemente):

```
Parte 1: sin pooling 3.39s, con pooling 0.41s -> 8.3x mas lento sin pooling

Parte 2: secuencial 0.95s, pool de 6: 0.20s, multiplexado (HTTP/2): 0.07s

Parte 3: hedge frio 0.26s, hedge caliente 0.11s (ambos ganan al primario de 0.30s)

Parte 4: A falla -> failover transparente a B -> circuito de A se abre -> A se recupera
```

## Puntos clave

- El costo de una conexion nueva no es un detalle de implementacion
  menor: en la Parte 1 explica **la mayor parte** de la diferencia de
  tiempo total, mas que el trabajo real de cada request.
- Multiplexar no cambia CUANTO trabajo hace el servidor — cambia
  cuanta CONCURRENCIA puede haber sin pagar el costo de abrir mas
  conexiones.
- Hedging y pooling son complementarios: hedging sin conexiones ya
  calientes hacia los backups puede costar casi tanto como no
  hedgear; con pooling, es casi gratis dispararlo.
- Lo que en gRPC o un SDK de HTTP/2 se ve como "un canal" es, por
  dentro, la misma composicion de piezas que este ejemplo arma a
  mano: pool + balanceo + circuit breaker + failover. Entender cada
  pieza por separado (los ejemplos anteriores de este repositorio) es
  lo que permite razonar sobre que esta pasando cuando algo falla
  dentro de ese "canal" que, de afuera, parece una caja negra.
