# Migraciones expand/contract

## Que es

Durante un [rolling deploy](../1-canary-blue-green-rolling), el
codigo viejo y el nuevo corren **al mismo tiempo** durante un rato —
no hay un instante unico en el que "todo" pase a la version nueva de
golpe. Un cambio de esquema destructivo hecho en un solo paso
(renombrar una columna, atomicamente) rompe a cualquier version de
codigo que no coincida exactamente con el esquema en ese instante —
sea la vieja o la nueva.

**Expand/contract** (tambien llamado *parallel change*) evita esto
separando el cambio en pasos, nunca uno solo:

1. **Expand**: agregar lo nuevo, sin tocar lo viejo. Ambas versiones
   de codigo pueden seguir funcionando, cada una con su propio campo.
2. Migrar/backfillear los datos existentes al campo nuevo.
3. **Contract**: recien cuando el 100% del codigo ya usa el campo
   nuevo (y paso una ventana de seguridad), borrar el campo viejo.

El paso destructivo va **al final**, cuando ya no puede romper a
nadie — nunca al principio ni a mitad de camino.

## Estructura del ejemplo

- `migrations.py`: `Schema` (el esquema mutable) y `simulate_rollout`
  — simula un rolling deploy de 10 instancias, cada una haciendo
  requests contra el esquema segun si corre codigo viejo o nuevo.
- `demo_migrations.py`: compara una migracion naive (un solo paso
  destructivo a mitad del rollout) contra expand/contract (agregar al
  principio, borrar al final).

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_migrations.py
```

Salida esperada:

```
naive (drop+add en un solo paso, a mitad del rollout):
  requests fallidos: 50/200 (25%)
expand/contract (agrega al principio, borra recien al final):
  requests fallidos: 0/200
```

## Puntos clave

- El riesgo no es "cambiar el esquema" — es cambiarlo mientras hay mas
  de una version de codigo activa al mismo tiempo. Cualquier
  despliegue gradual ([rolling, canary](../1-canary-blue-green-rolling))
  garantiza que eso va a pasar.
- El paso de "migrar los datos existentes" (backfill) puede tardar —
  minutos u horas en una tabla grande — y durante todo ese tiempo el
  esquema tiene que seguir aceptando ambas formas. Expand/contract no
  es instantaneo, es un proceso con una ventana de tiempo real.
- El paso de contract debe ser el ULTIMO en aplicarse, y solo despues
  de confirmar que el 100% del trafico ya uso el campo nuevo por un
  tiempo razonable — revertir un despliegue que ya paso por contract
  puede volver a romper todo si el rollback trae de vuelta codigo
  viejo que ya no tiene su columna.
- Esta es la misma logica de compatibilidad hacia atras y adelante que
  [tolerant reader](../5-tolerant-reader): expand/contract la aplica
  al esquema de datos; tolerant reader, al formato de los mensajes que
  se leen.
