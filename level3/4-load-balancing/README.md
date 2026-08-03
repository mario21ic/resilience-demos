# Load balancing — round robin, least-connections, EWMA, P2C, consistent hashing

## Que es

Elegir a que backend mandar cada request es, en el fondo, un problema
de balance: repartir trafico de forma que ningun backend termine
sobrecargado mientras otros estan ociosos. Cada estrategia de este
ejemplo mejora a la anterior en un eje distinto — cuanto sabe del
estado real de los backends, que tan barata es la decision, o si
necesita afinidad por clave.

## 1) Round robin vs least-connections: capacidad heterogenea

**Round robin** reparte por turno fijo, sin mirar el estado de nadie.
Funciona bien si todos los backends son igual de capaces. Si uno es
mas lento (menos CPU, un disco mas viejo, no una falla), round robin
igual le manda la misma proporcion de trafico — y ese backend
acumula una cola creciente mientras los demas quedan ociosos.

**Least-connections** elige el backend con menos requests en curso.
Al reaccionar al atraso real, le manda menos trafico al backend lento
de forma natural, sin necesidad de saber de antemano cual es mas
lento.

> Nota de implementacion: cuando varios backends empatan en carga, el
> desempate tiene que ser al azar. Con un desempate fijo (ej. "el de
> menor indice"), ese backend gana todos los empates y termina
> absorbiendo mucho mas trafico del que deberia — un bug real que
> aparecio al construir este demo y quedo corregido en
> `load_balancers.py`.

## 2) Least-connections vs EWMA: un pico de latencia sin cola visible

Least-connections mide **cantidad** de conexiones, no **latencia**.
Si un backend tiene capacidad de sobra, puede volverse mas lento por
request sin que su conteo de conexiones en curso se dispare — least
connections no lo detecta hasta que el atraso finalmente se nota en
la cola.

**EWMA** (promedio movil exponencial de latencia) elige el backend
con menor latencia observada recientemente. Reacciona en cuanto
llegan las primeras respuestas lentas, porque mide directamente lo
que le importa al cliente.

## 3) P2C (power of two choices): casi tan bueno, mucho mas barato

Least-connections "perfecto" requiere escanear TODOS los backends
para encontrar el de menor carga — caro cuando hay cientos de ellos.
**P2C** mira solo **2 al azar** y elige el mejor de esos 2. El
resultado teorico (Mitzenmacher, "The Power of Two Choices in
Randomized Load Balancing") es sorprendente: el desbalance maximo cae
de forma exponencial con solo 2 opciones en vez de 1, y queda muy
cerca de lo que lograria escanear todos los backends.

## 4) Consistent hashing vs consistent hashing con bounded loads

Cuando hace falta **afinidad** (la misma clave siempre al mismo
backend, por cache locality o sesiones), round-robin/least-connections
no sirven — para eso esta el **consistent hashing**: cada clave se
mapea de forma estable a un punto de un anillo. El problema: si una
clave es muy popular ("hot key"), el backend que le toca en el anillo
puede saturarse, y no hay forma de "balancear" una sola clave entre
varios backends sin romper la afinidad.

**Consistent hashing con bounded loads** (Mirrokni, Thorup,
Zadimoghaddam, "Consistent Hashing with Bounded Loads") le pone un
techo a cuanta carga puede acumular cualquier backend
(`promedio * balance_factor`). Si el backend que le toca a una clave
ya esta en su limite, la clave se deriva al siguiente backend distinto
en el anillo — la gran mayoria de las claves (las que no son
calientes) conservan su afinidad de siempre; solo las que colisionan
con un backend saturado se redirigen.

## Estructura del ejemplo

- `load_balancers.py`: `RoundRobinBalancer`, `LeastConnectionsBalancer`,
  `EWMABalancer`, `P2CBalancer`, `ConsistentHashRing` y
  `BoundedLoadConsistentHash`.
- `demo_load_balancing.py`: las cuatro comparaciones descriptas
  arriba, cada una con su propia simulacion.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_load_balancing.py
```

Salida esperada (resumen):

```
Parte 1: round robin termina en el tick 81; least-connections en el tick 54 (33% mas rapido)

Parte 2: least-connections manda 2/15 requests al backend degradado durante el pico (latencia promedio 5.8)
          EWMA manda 1/15 (latencia promedio 4.4, casi el baseline de 3)

Parte 3 (100 backends, 1000 requests, promedio ideal=10):
    estrategia | carga maxima | inspeccionados/decision
        random |           17 |  1
           p2c |           12 |  2
  least_loaded |           10 |  100

Parte 4 (10 backends, 20000 requests, promedio ideal=2000):
  consistent hashing plano:     carga maxima = 7757 (3.9x el promedio)
  consistent hashing + bounded: carga maxima = 2500 (1.2x el promedio)
```

## Puntos clave

- No hay una estrategia universalmente mejor — cada una asume algo
  distinto sobre los backends (homogeneos, sin necesidad de afinidad,
  costo de decision aceptable) y falla cuando esa asuncion no se
  cumple.
- Round robin necesita backends homogeneos; en la practica casi nunca
  lo son del todo (autoscaling con instancias de distinto tamaño,
  hardware viejo mezclado con nuevo, JIT warmup).
- "Menos conexiones" es una aproximacion barata a "menos carga real";
  cuando la aproximacion falla (backend lento pero con capacidad de
  sobra), hace falta medir la señal real (latencia, EWMA).
- P2C es el punto dulce entre round robin (barato pero ciego) y
  least-connections exhaustivo (preciso pero caro) — es lo que usan
  en la practica sistemas con cientos o miles de backends.
- Consistent hashing es la unica opcion de esta lista pensada para
  afinidad por clave; bounded loads es lo que evita que esa misma
  propiedad se convierta en un punto unico de sobrecarga.
