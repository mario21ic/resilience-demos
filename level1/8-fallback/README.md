# 8. Fallback

## Que es

Timeout ([1-timeout](../1-timeout)) y retry ([2-retry](../2-retry))
responden "cuanto esperar" y "cuando reintentar". Pero tarde o
temprano hay que rendirse — y ahi es donde entra el **fallback**: en
vez de propagarle el error al llamador, se le devuelve una respuesta
alternativa. Se acepta que sea de peor calidad (datos viejos, un
default generico, una version simplificada) a cambio de que el
llamador nunca se quede sin nada util que mostrar.

## La cadena de fallback

Este ejemplo implementa una cadena de tres niveles, comun en sistemas
de recomendaciones, catalogos, feature flags, etc.:

1. **Primario**: llamar al servicio real, con timeout.
2. **Cache (stale-if-error)**: si el primario falla, usar la ULTIMA
   respuesta exitosa guardada para ese usuario, aunque ya no sea
   fresca.
3. **Default estatico**: si ni siquiera hay algo en cache (usuario
   nuevo, cache recien reiniciada), devolver un valor generico
   predefinido.

Cada nivel es progresivamente peor en calidad pero mas confiable en
disponibilidad — la idea central del fallback es esa: cambiar
calidad por disponibilidad, nunca al reves.

## Un detalle importante: marcar el degradado

Cada respuesta trae `source` (`primario` / `cache (stale)` /
`default estatico`) y un flag `degraded`. Un fallback **silencioso**
— que el llamador no puede distinguir de una respuesta real — es en
si mismo un riesgo: alguien puede tomar una decision (de negocio, de
UX, de otro sistema aguas abajo) sobre un dato viejo sin saber que lo
es. El fallback deberia ser visible para quien lo consume, no solo
funcional.

## Estructura del ejemplo

- `server.py`: servicio de recomendaciones simulado con salud
  configurable via `GET /admin/health?state=healthy|slow|down`.
- `client_fallback.py`: `get_recommendations(user_id)` implementa la
  cadena primario -> cache -> default, y un demo de 4 fases:
  1. Backend sano: `alice` y `bob` reciben datos reales (se puebla la
     cache).
  2. Backend caido: `alice` y `bob` caen a cache; `charlie` (sin
     historial) cae al default estatico.
  3. Backend lento (supera el timeout del cliente): mismo fallback
     que un backend caido — el llamador no distingue "caido" de
     "demasiado lento", y no deberia tener que hacerlo.
  4. Backend recuperado: vuelve a sevir datos reales y refresca la
     cache.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 client_fallback.py
```

Salida esperada:

```
Fase 2: backend caido -> fallback en accion
  alice (tiene cache)      [DEGRADADO] source=cache (stale)    items=[...]
  charlie (sin cache)      [DEGRADADO] source=default estatico items=['mas vendidos', ...]

Fase 4: backend se recupera -> se vuelve a servir dato real y se refresca la cache
  alice (backend recuperado) [OK] source=primario items=[...]
```

## Puntos clave

- El fallback es el complemento natural de timeout/retry: define que
  pasa DESPUES de agotar los reintentos, no una alternativa a ellos.
- Ordenar los niveles de mejor a peor calidad (cache antes que
  default estatico) maximiza el valor entregado sin sacrificar
  disponibilidad.
- Marcar la respuesta como degradada (`source`, `degraded`) es tan
  importante como el fallback en si: evita que un dato viejo se trate
  como si fuera fresco en algun otro punto del sistema.
- El fallback es apropiado para operaciones de **lectura** tolerantes
  a datos desactualizados. Para escrituras con efectos secundarios
  (cobros, creacion de pedidos), la herramienta correcta no es un
  fallback silencioso sino [idempotency keys](../7-idempotency-keys)
  + reintento explicito, o directamente propagar el error.
- Un fallback mal elegido puede ocultar un incidente real: si el
  default estatico es "razonable" pero incorrecto (ej. precios
  desactualizados), el sistema puede parecer sano por fuera mientras
  esta sirviendo datos malos — el monitoreo deberia contar cuantas
  respuestas vienen degradadas, no solo si hay errores duros.
