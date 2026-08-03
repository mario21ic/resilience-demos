# Level 6 — Cambio y despliegue

La mayoria de las caidas las causa un cambio, no el hardware. Los
niveles anteriores tratan sobre sobrevivir a fallas que ya existen en
un sistema estable; este trata sobre no CAUSAR la falla en primer
lugar cuando algo cambia — un deploy, una migracion de esquema, un
mensaje con un campo nuevo, un parche aplicado a mano.

Las preguntas de este nivel:

- ¿Como se expone una version nueva sin apostar el 100% del trafico
  de una, y quien decide si conviene seguir adelante?
- Si algo recien lanzado esta causando problemas, ¿cuanto tarda
  mitigarlo?
- ¿El sistema puede revertir un despliegue malo SOLO, sin que una
  persona lo note y actue a tiempo?
- ¿Como se cambia el esquema de datos sin romper al codigo viejo que
  todavia esta corriendo durante el despliegue?
- ¿Que pasa cuando un mensaje trae un campo que el consumidor no
  conoce?
- ¿Los servidores que "deberian ser iguales" realmente lo son?

Todos los ejemplos son autocontenidos y usan solo la libreria
estandar de Python (no requieren `pip install`).

## Como se relacionan entre si

```
canary/blue-green/rolling  -> como exponer una version nueva gradualmente
     └─ progressive delivery + auto-rollback -> el criterio automatico,
                                                 llevado a monitoreo continuo
                                                 multi-metrica

feature flags / kill switch -> desactivar una funcionalidad sin desplegar

expand/contract migrations -> el esquema de datos sobrevive a que
                               conviva codigo viejo y nuevo
tolerant reader             -> el consumidor de mensajes tambien
                               sobrevive a esa convivencia

infraestructura inmutable  -> la base que hace que "desplegar" sea
                               reemplazar, nunca mutar
```

Los primeros tres (canary/blue-green/rolling, progressive delivery,
feature flags) son sobre COMO exponer un cambio de forma controlada.
Los ultimos tres (expand/contract, tolerant reader, infraestructura
inmutable) son sobre que el cambio en si mismo — el esquema, el
formato de los mensajes, los servidores — este diseñado para convivir
con versiones distintas al mismo tiempo, sin romperse.

## Indice

| # | Ejemplo | De que trata |
|---|---|---|
| 1 | [1-canary-blue-green-rolling](1-canary-blue-green-rolling) | Radio de impacto de un deploy malo segun la estrategia, y por que el criterio automatico importa mas que el porcentaje. |
| 2 | [2-feature-flags-kill-switch](2-feature-flags-kill-switch) | Desactivar una funcionalidad via configuracion, sin desplegar; rollout gradual con hash estable por usuario. |
| 3 | [3-progressive-delivery-auto-rollback](3-progressive-delivery-auto-rollback) | Auto-rollback por SLO con multiples metricas y chequeos consecutivos, al estilo Flagger/Argo Rollouts. |
| 4 | [4-expand-contract-migrations](4-expand-contract-migrations) | Cambiar un esquema de datos sin romper al codigo viejo que sigue corriendo durante el rollout. |
| 5 | [5-tolerant-reader](5-tolerant-reader) | Ley de Postel: un consumidor que solo lee lo que necesita sobrevive a que el productor agregue campos nuevos. |
| 6 | [6-immutable-infrastructure](6-immutable-infrastructure) | Reemplazar servidores en vez de mutarlos, para eliminar el "configuration drift" y los servidores copo de nieve. |

## Orden de lectura sugerido

`1 -> 3 -> 2 -> 4 -> 5 -> 6`.

Cada README individual explica el patron, por que importa, la
estructura del codigo y como ejecutar el demo correspondiente.
