# Tolerant reader / ley de Postel

## Que es

La ley de Postel dice: "se conservador en lo que envias, liberal en lo
que aceptas". Aplicada a consumir mensajes o respuestas de una API,
esto se traduce en el patron **tolerant reader**: extraer solo los
campos que REALMENTE hacen falta, e ignorar cualquier otro — no fallar
solo porque el productor agrego algo nuevo que a este consumidor no le
importa.

## Por que esto es resiliencia, no solo buen gusto

Sin tolerancia, cualquier evolucion **aditiva** del esquema (agregar
un campo — en teoria, el tipo de cambio mas inofensivo que existe)
obliga a actualizar a TODOS los consumidores al mismo tiempo que el
productor. Eso es exactamente el despliegue en lockstep que la
independencia entre servicios deberia evitar — el mismo problema de
fondo que resuelven las
[migraciones expand/contract](../4-expand-contract-migrations), visto
del lado del consumidor de mensajes en vez del esquema de una base de
datos.

## Estructura del ejemplo

- `tolerant_reader.py`: `strict_consumer` (valida el esquema exacto),
  `tolerant_consumer` (extrae solo lo necesario), y
  `tolerant_consumer_with_default` (tambien tolera que un campo
  opcional desaparezca, con un valor por defecto razonable).
- `demo_tolerant_reader.py`: tres partes.
  1. El productor agrega un campo — el consumidor estricto se rompe,
     el tolerante ni lo nota.
  2. Cuatro versiones del esquema, cada vez con mas campos, procesadas
     por el mismo consumidor tolerante sin cambiar una linea.
  3. El limite del patron: perder un campo indispensable no se
     resuelve con tolerancia sola.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_tolerant_reader.py
```

Salida esperada:

```
Parte 1: consumidor estricto FALLA cuando se agrega 'currency';
         consumidor tolerante sigue funcionando sin cambios.

Parte 2: el mismo consumidor tolerante procesa 4 versiones del esquema,
         cada una con mas campos que la anterior.

Parte 3: perder un campo OPCIONAL se resuelve con un default;
         perder un campo INDISPENSABLE (amount) no se resuelve solo
         con tolerancia — hace falta una decision explicita.
```

## Puntos clave

- Tolerant reader protege contra cambios **aditivos** del productor
  (campos nuevos) — no es una excusa para no validar los campos que
  la logica de negocio realmente necesita.
- Validar de mas (exigir que el esquema completo coincida
  exactamente) es un acoplamiento oculto: ata al consumidor a la
  version EXACTA del productor en el momento en que se escribio el
  codigo, en vez de a lo que realmente usa.
- Esto se complementa con un versionado explicito (un campo
  `version` en el mensaje) para los casos donde SI hace falta un
  cambio incompatible — tolerant reader resuelve la evolucion
  aditiva; el versionado explicito resuelve la evolucion que rompe
  algo a proposito, de forma controlada.
- La misma logica aplica a cualquier formato de intercambio (JSON,
  protobuf con campos opcionales, eventos de un broker) — el
  principio no es especifico de un protocolo, es una postura sobre
  cuanto acoplarse a la forma exacta de lo que se recibe.
