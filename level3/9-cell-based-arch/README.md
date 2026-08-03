# Cell-based architecture

## Que es

Una **celda** es una copia **completa** del stack de un servicio —
compute, base de datos, colas, todo — que atiende a un subconjunto
fijo de clientes, sin dependencias compartidas con otras celdas salvo
un **router delgado** que solo sabe mapear `cliente -> celda`.

Es distinto del sharding simple ([8-sharding](../8-sharding)), que
particiona un recurso puntual (una base de datos, un pool de
workers) dentro de un sistema que sigue siendo, en todo lo demas, un
monolito compartido. Cell-based architecture particiona el
**servicio entero**, de punta a punta — es la combinacion, a nivel
arquitectonico, de [bulkhead](../../level2/2-bulkhead) (aislar
recursos), [redundancia](../redundancia-n1-n2) (cada celda con su
propia capacidad de sobra) y
[shuffle sharding](../8-sharding) (asignacion que limita cuanto
comparten los clientes entre si) — por eso AWS lo describe como el
estado del arte para limitar el radio de impacto.

## Tres propiedades, tres partes

### 1) Tamaño fijo y probado: radio de impacto constante

Cada celda se carga-testea a un tamaño conocido de antemano. Escalar
el sistema es agregar **mas celdas** de ese mismo tamaño — nunca
agrandar una celda existente. La consecuencia: el radio de impacto de
una falla total de UNA celda **no crece con el sistema**, mientras
que en un monolito, una falla total siempre expone al 100% de los
clientes actuales — y ese 100% es cada vez mas gente a medida que el
sistema crece.

### 2) Router delgado: contener un mal deploy

El router no tiene logica de negocio — solo enruta. Eso permite
desplegar cambios **celda por celda** (canary): probar en una sola
celda, verificar con las mismas señales de
[health checks](../3-health-check) u
[outlier detection](../5-outlier-detection), y recien entonces seguir
con el resto. Un deploy malo se frena despues de una celda en vez de
llegar al 100% de una vez.

### 3) Asignacion estable: crecer sin migrar

Agregar capacidad no deberia reasignar a los clientes que ya estaban
en celdas existentes — cada reasignacion es en si misma un evento de
riesgo (migrar datos, invalidar cache, cortar conexiones). Un
esquema de particionado ingenuo (`hash(cliente) % cantidad_de_celdas`)
reasigna una fraccion enorme de clientes existentes cada vez que se
agrega capacidad; un router delgado con asignacion estatica
(append-only: los clientes nuevos van a la celda nueva, los
existentes no se tocan nunca) no reasigna a nadie.

## Estructura del ejemplo

- `cells.py`: `ThinRouter` (asignacion estatica append-only),
  `blast_radius_table` (Parte 1), `simulate_canary_rollout`
  (Parte 2), `naive_mod_reassignment_fraction` (Parte 3).
- `demo_cell_based.py`: las tres comparaciones descriptas arriba.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_cell_based.py
```

Salida esperada:

```
Parte 1 (celda de 1000 clientes):
    1,000 clientes: monolito 100%     | 1 celda 100.0%
    5,000 clientes: monolito 100%     | 1 celda  20.0%
   20,000 clientes: monolito 100%     | 1 celda   5.0%
  100,000 clientes: monolito 100%     | 1 celda   1.0%

Parte 2 (20 celdas, deploy malo):
  monolito: 20000 clientes afectados
  cell-based con canary: 1000 clientes afectados (5.0%), 1/20 celdas tocadas

Parte 3 (agregar una 11va celda a 10 llenas):
  particion naive (hash % n_celdas): 90.8% de clientes existentes reasignados
  router delgado (append-only):       0.0% reasignados
```

## Puntos clave

- El radio de impacto de un monolito crece CON el sistema; el de una
  arquitectura por celdas queda fijo en el tamaño de celda, sin
  importar cuanto crezca el resto. Esa es la propiedad central: no
  hace falta "acordarse" de limitar el impacto, es una consecuencia
  del diseño.
- El router tiene que ser la parte MAS simple y MAS confiable de todo
  el sistema — es la unica pieza compartida entre todas las celdas, y
  la unica cuya falla puede tumbar a todas a la vez.
- Cell-based architecture no es un patron nuevo desde cero: es la
  combinacion deliberada de bulkhead, redundancia y sharding a nivel
  de todo el servicio, no solo de un recurso puntual — el mismo
  principio que se ve en `level3/6-multiplexer` para clientes, aplicado
  aca del lado del servidor.
- El costo real es operativo: probar y mantener N copias completas del
  stack es mas trabajo que operar una sola instancia grande — el
  tradeoff es aceptar ese costo a cambio de que ninguna falla,
  deploy malo, o cliente toxico pueda afectar a mas que una fraccion
  fija y conocida del negocio.
