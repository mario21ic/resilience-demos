# Transactional outbox / inbox

## Que es

Cuando un servicio necesita (1) guardar un cambio en su base y (2)
avisarle al resto del sistema publicando un evento, hacer ambas cosas
como dos operaciones **separadas** es peligroso: si la segunda falla
despues de que la primera tuvo exito (o al reves), el sistema queda
en un estado inconsistente que ningun retry puede arreglar — el
codigo que debia publicar el evento ya termino de ejecutarse, y nadie
mas sabe que hacia falta reintentar.

El **transactional outbox** resuelve esto escribiendo el evento en
una tabla dentro de la **misma transaccion de base de datos** que el
cambio de negocio. Como es la misma transaccion, la base de datos
garantiza que ambas escrituras se confirman juntas o ninguna lo hace
— nunca puede quedar la orden guardada sin su evento correspondiente.

## Como se termina de publicar el evento

Guardar el evento en una tabla local no lo manda al broker real —
hace falta un proceso separado (el **relay**) que lea las filas no
publicadas y las mande, marcandolas como publicadas recien cuando el
broker confirma. Si el broker esta caido, las filas simplemente
quedan pendientes — nada se pierde, el relay las va a reintentar en
la proxima pasada.

## El espejo del lado del consumidor: transactional inbox

El mismo problema existe al recibir: si un mensaje puede llegar mas
de una vez (la garantia real de casi todo broker es *at-least-once*,
no *exactly-once*), aplicar su efecto y marcarlo como procesado
tambien tienen que ser atomicos. Una tabla `inbox` con el ID del
mensaje como llave primaria hace que un segundo intento de procesar
el MISMO mensaje simplemente falle al insertar — y esa falla es la
señal de "ya lo procese, no hagas nada".

## Estructura del ejemplo

- `broker.py`: un broker simulado que puede fallar a voluntad.
- `outbox.py`: `create_order_naive` (el problema, dos pasos separados)
  vs `create_order_with_outbox` (la escritura atomica) +
  `relay_outbox` (el proceso que drena la outbox hacia el broker).
- `inbox.py`: `handle_message_with_inbox`, la version minima del lado
  del consumidor.
- `demo_outbox_inbox.py`: tres partes, usando una base de datos SQLite
  real (de la libreria estandar) para que la atomicidad sea genuina,
  no simulada.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`) — `sqlite3` viene incluido.

## Como ejecutarlo

```bash
python3 demo_outbox_inbox.py
```

Salida esperada:

```
Parte 1: la orden existe en la base, pero el evento nunca se publico
         (el broker estaba caido) — inconsistencia real y permanente.

Parte 2: la orden y el evento se escriben atomicamente. El relay
         reintenta hasta que el broker se recupera, y entonces publica
         el evento pendiente — nada se pierde en ningun momento.

Parte 3: el mismo mensaje entregado dos veces solo aplica su efecto
         una vez (saldo final: 50.0, no 100.0).
```

## Puntos clave

- El outbox no elimina la necesidad de reintentar — el relay
  reintenta indefinidamente contra el broker — pero mueve el punto de
  reintento a un lugar donde SI se sabe con certeza que hace falta
  reintentar (una fila marcada como no publicada), en vez de depender
  de que el codigo de negocio original siga vivo para hacerlo.
- Esto convierte una garantia "o todo o nada" (ACID local) en una
  garantia "eventualmente todo" (el evento se publica seguro, pero no
  necesariamente al instante) — el mismo tipo de tradeoff que
  [replicacion asincrona](../../level3/7-replicacion).
- El outbox por si solo no evita que el evento se publique **dos
  veces** (si el relay confirma la publicacion pero se cae antes de
  marcarla) — por eso el consumidor necesita ser idempotente del otro
  lado (el inbox, o las estrategias mas generales de
  [3-consumidor-idempotente-dedup](../3-consumidor-idempotente-dedup)).
  Outbox + inbox juntos dan at-least-once en el envio y
  exactly-once en el efecto percibido.
- Esta tecnica es la base de muchas herramientas de "Change Data
  Capture" (Debezium y similares): en vez de un relay que hace
  polling a una tabla outbox, leen directamente el log de replicacion
  de la base de datos — mismo principio, sin necesidad de la tabla
  extra.
