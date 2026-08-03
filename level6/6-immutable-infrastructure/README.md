# Infraestructura inmutable

## Que es

En vez de modificar un servidor que ya esta corriendo (entrar por
SSH, aplicar un parche, cambiar un archivo de configuracion), la
infraestructura inmutable construye una **imagen nueva** con el
cambio adentro y **reemplaza** el servidor entero — nunca se muta uno
que ya existe. Si algo necesita cambiar, se tira el servidor viejo y
se levanta uno nuevo de la imagen actualizada.

## El problema que resuelve: "servidores copo de nieve"

Con infraestructura mutable, cada parche puntual se aplica a mano —
tipicamente a los servidores donde el problema se noto en su momento,
no necesariamente a todos. Con el tiempo, servidores que empezaron
siendo **exactamente iguales** terminan siendo todos distintos entre
si: cada uno con su propia historia de intervenciones, en gran parte
indocumentada. Son "servidores copo de nieve": unicos, fragiles, y
nadie sabe con certeza que tienen adentro sin entrar a revisarlos uno
por uno.

## La garantia de la inmutabilidad

Si el unico mecanismo de cambio es "reemplazar por una imagen nueva",
es matematicamente imposible que dos servidores de la misma version
difieran entre si — son, literalmente, la misma imagen. Y volver
atras es tan simple como desplegar la imagen anterior: no hace falta
saber que cambios revertir, porque no hay cambios incrementales que
rastrear.

## Estructura del ejemplo

- `immutable.py`: `simulate_mutable_drift` (parches aplicados a mano a
  subconjuntos al azar de servidores) y
  `simulate_immutable_replacement` (cada release reemplaza a todos los
  servidores por una imagen nueva).
- `demo_immutable.py`: 20 servidores originalmente identicos, 25
  cambios con el tiempo, bajo ambos modelos.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_immutable.py
```

Salida esperada:

```
MUTABLE: 11/20 configuraciones UNICAS despues de 25 cambios
         (servidores 'identicos' en el papel, todos distintos en la practica)

INMUTABLE: 1/20 version UNICA — todos los servidores son, byte a
           byte, la misma imagen, sin importar cuantos releases pasaron
```

## Puntos clave

- El costo de la inmutabilidad es operativo: hace falta poder
  construir y desplegar una imagen completa rapido — sin eso,
  "reemplazar en vez de mutar" es demasiado lento para cambios
  chicos y frecuentes. Contenedores e infraestructura como codigo
  bajaron muchisimo ese costo, por eso el patron se volvio la norma.
- Inmutable no significa "sin estado" — el estado persistente
  (bases de datos, volumenes) vive SEPARADO de los servidores
  reemplazables, exactamente para que reemplazar un servidor no
  implique perder datos.
- Esto es la misma logica que
  [checkpointing / durable execution](../../level5/5-checkpointing-durable-execution):
  en vez de confiar en que un proceso mutable mantenga su estado
  correctamente para siempre, se separa el estado (la imagen, el log)
  de la ejecucion (el servidor, el worker) — la ejecucion es
  descartable, el estado no.
- Combinado con [rolling/canary deployments](../1-canary-blue-green-rolling),
  la inmutabilidad es lo que garantiza que "10% de las instancias en
  la version nueva" signifique exactamente eso — no "10% con la
  version nueva y ademas quien sabe que otros cambios acumulados".
