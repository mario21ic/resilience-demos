# Graceful shutdown / connection draining

## Que es

Cuando una instancia tiene que dejar de existir (un deploy, un
scale-down, mantenimiento de un nodo), matarla de golpe (`SIGKILL`)
corta cualquier request en curso a mitad de camino — el cliente recibe
un error por algo que no tenia nada de malo, solo mala suerte de
timing. La secuencia correcta:

1. El orquestador manda `SIGTERM` (o corre un hook `preStop`, en
   Kubernetes): "terminá lo que estás haciendo, por favor".
2. La instancia deja de aceptar trafico **nuevo**, pero sigue
   procesando lo que ya tenia en curso.
3. Recien cuando termina (o se agota un periodo de gracia), el
   proceso sale solo — el orquestador manda `SIGKILL` solo si se tomo
   demasiado tiempo.

## La carrera de desregistro

Hay un problema mas sutil: aunque la instancia deje de aceptar
conexiones en el mismo instante en que recibe la señal, el **load
balancer** puede tardar un rato en enterarse de que se esta apagando
(un intervalo de polling, una propagacion de configuracion) y seguir
mandandole trafico nuevo durante esa ventana — trafico que ahora
rebota, porque la app ya dejo de escuchar.

El hook `preStop` de Kubernetes suele usarse justamente para **dormir
unos segundos antes** de empezar a rechazar conexiones nuevas —
dandole tiempo al balanceador a enterarse primero de que la instancia
se va, para que el momento en que la app deja de aceptar trafico
coincida con el momento en que el LB deja de mandarselo.

## Estructura del ejemplo

- `graceful_shutdown.py`: `simulate_abrupt_kill` vs
  `simulate_graceful_shutdown` (Parte 1), y
  `simulate_deregistration_race` (Parte 2).
- `demo_graceful_shutdown.py`: las dos comparaciones descriptas
  arriba.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_graceful_shutdown.py
```

Salida esperada:

```
Parte 1: SIGKILL inmediato: 0/50 completados
         SIGTERM + 30s de gracia: 48/50 completados

Parte 2: sin preStop: 723 requests fallidos
         con preStop (4s): 0 requests fallidos
```

## Puntos clave

- El periodo de gracia tiene un limite practico: no se puede esperar
  para siempre a que termine un request colgado — por eso existe un
  timeout maximo (en Kubernetes, `terminationGracePeriodSeconds`)
  despues del cual el orquestador manda `SIGKILL` igual.
- El tiempo de `preStop` deberia ser, como minimo, igual al peor caso
  de cuanto tarda el mecanismo de descubrimiento de servicio en
  propagar un cambio — no un numero elegido al azar.
- Esto es parte de lo mismo que un
  [rolling deployment](../../level6/1-canary-blue-green-rolling) bien
  hecho: no alcanza con levantar instancias nuevas de a poco, tambien
  hay que bajar las viejas sin que eso genere errores visibles para
  los clientes que ya estaban conectados.
- El mismo principio aplica a recursos que no son requests HTTP:
  conexiones de base de datos, mensajes de una cola que se estaban
  procesando, transacciones a medio terminar — "terminar
  ordenadamente" siempre implica dejar que lo que ya esta en curso
  llegue a un estado consistente antes de soltar el recurso.
