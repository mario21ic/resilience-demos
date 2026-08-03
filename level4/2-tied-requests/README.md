# Tied requests

## Que es

Es la variante de [hedged requests](../1-hedged-requests) donde, en
vez de esperar un umbral antes de disparar una copia, el request se
manda a **dos replicas al mismo tiempo, desde el instante cero**
("atadas" entre si). En cuanto una empieza a responder, le avisa a la
otra que se cancele.

La diferencia con hedging es cuando actua: hedging espera a
sospechar que la primaria va lenta (pasado un umbral) antes de
intentar un backup; tied no espera nada — corre la carrera desde el
principio y dejar que gane la mas rapida.

## Por que importa: la cola no es la ejecucion

Un umbral de hedging tipicamente se calibra contra el tiempo de
**ejecucion** esperado (cuanto tarda el trabajo en si). Pero en un
sistema real, buena parte de la latencia de cola no viene de que la
ejecucion sea lenta — viene de que la replica elegida ya tiene **otro
trabajo encolado** en este preciso instante (un hot spot de trafico,
un vecino ruidoso). Un umbral fijo no tiene forma de saber eso de
antemano.

Tied requests no necesita adivinar nada: al mandar a ambas replicas
ya mismo, automaticamente termina primero la que este menos ocupada
ahora — sin importar si la razon es que ejecuta mas rapido o
simplemente que tenia menos cola.

## El costo: sin cancelacion rapida, siempre pagas el doble

La contrapartida es que tied genera trabajo redundante real en cada
request, no solo en el 5% que sale lento (como en hedging). Para que
valga la pena, hace falta un mecanismo de **cancelacion rapido**
entre replicas: en cuanto una gana, la otra tiene que enterarse casi
al instante, para no desperdiciar ejecucion que ya no hace falta. Sin
eso, tied simplemente cuesta el doble de trabajo real, siempre.

## Estructura del ejemplo

- `tied_requests.py`: `draw_background_load` simula la cola pendiente
  de una replica (liviana la mayoria de las veces, con hot spots
  ocasionales); `simulate_wasted_work` (Parte 1) y
  `simulate_latency_comparison` (Parte 2).
- `demo_tied_requests.py`: dos partes.
  1. Cuanto trabajo se desperdicia con y sin cancelacion rapida.
  2. Tied vs hedged vs "solo una replica" vs un oraculo ideal, frente
     a una carga con hot spots ocasionales.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_tied_requests.py
```

Salida esperada (semilla fija):

```
Parte 1: desperdicio SIN cancelacion: 10.00ms (100% siempre)
         desperdicio CON cancelacion rapida: 6.73ms (-32.7%)

Parte 2:
                  estrategia |     avg |     p95 |     p99
         solo A (sin backup) |   24.5ms |  109.8ms |  150.3ms
        hedged (umbral fijo) |   16.7ms |   25.0ms |   60.4ms
 tied (dual + cancel rapido) |   14.4ms |   18.6ms |   60.4ms
             ideal (oraculo) |   14.4ms |   18.6ms |   60.4ms
```

Tied llega exactamente al oraculo — nunca pierde tiempo esperando un
umbral. La diferencia con hedged se nota sobre todo en el p95: son los
casos donde la primaria esta "un poco lenta, pero no tanto", y el
hedge tarda en darse cuenta de que la otra replica ya estaba libre.

## Puntos clave

- Tied requests exige que las replicas puedan comunicarse entre si
  para cancelar rapido — un requisito operativo real que hedging no
  tiene (hedging es "dispara y listo", cada copia es independiente).
  Por eso Google lo usa tipicamente dentro del mismo cluster/datacenter,
  donde esa comunicacion es barata y rapida, y prefiere hedging entre
  sistemas menos acoplados (cross-datacenter, terceros).
- Tied es superior a hedging especificamente cuando la fuente de
  latencia es la COLA (carga variable entre replicas), no la
  ejecucion en si — si toda la variabilidad viniera de la ejecucion
  (como en el ejemplo de hedged requests), la ventaja de tied se
  reduce, porque un umbral bien calibrado ya captura casi todo el
  beneficio.
- El costo de tied (trabajo duplicado) es real incluso con
  cancelacion rapida — la Parte 1 solo reduce el desperdicio, no lo
  elimina. Sigue siendo una tecnica para llamadas baratas de duplicar,
  igual que hedging.
- Esto es la misma dualidad que aparece en
  [level3/2-failover](../../level3/2-failover): reaccionar rapido
  (automatico) contra reaccionar solo cuando ya es seguro
  (con un umbral) — tied prioriza velocidad porque puede permitirse
  corregir el error (cancelar) casi de inmediato.
