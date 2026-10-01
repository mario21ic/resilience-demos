# Runbooks y postmortems sin culpa

## Que es

Un **runbook** es un documento que se escribe ANTES del incidente:
sintomas, diagnostico paso a paso, mitigaciones probadas y criterio de
escalamiento, para que durante el incidente nadie tenga que razonar
desde cero bajo presion y con el reloj corriendo.

Un **postmortem** se escribe DESPUES del incidente: reconstruye la
linea de tiempo, identifica la causa raiz y los factores que
contribuyeron, y define acciones concretas para que la misma clase de
falla sea menos probable o menos severa la proxima vez.

La practica de postmortems **sin culpa** (blameless) no es una
cuestion de cortesia: es una condicion para que el postmortem sirva
para algo. Si la conclusion de un incidente es "Marcos se equivoco", la
correccion natural es confiar en que Marcos (o cualquier otra persona)
tenga mas cuidado la proxima vez — algo que no se puede verificar ni
forzar, y que no previene nada si es otra persona la que se encuentra
en la misma situacion. Si la conclusion es "el proceso permitia que
este tipo de error pasara desapercibido", la correccion es un cambio
concreto al sistema (una validacion automatica, una alerta, un test)
que reduce la probabilidad de esa clase de falla sin importar quien
este operando el sistema ese dia.

Ademas, si la gente teme ser señalada individualmente en un postmortem,
deja de contar la version completa de lo que paso — omite detalles,
suaviza su propio rol, evita mencionar la decision dudosa que tomo bajo
presion. Sin esa honestidad, el equipo entiende el incidente a medias,
y el mismo modo de falla — o uno parecido — vuelve a ocurrir.

## Estructura del ejemplo

- `blame_checker.py`: un chequeo mecanico simple (basado en patrones de
  texto) que detecta lenguaje que tipicamente señala culpa individual
  en un postmortem ("error humano", "deberia haber revisado",
  "negligencia", "olvido", etc.) y sugiere una reformulacion sistemica
  para cada caso. No reemplaza el criterio humano — es una revision
  automatica rapida antes de publicar.
- `demo_blame_checker.py`: corre el chequeo sobre dos versiones del
  resumen de causa raiz del MISMO incidente ficticio — una con lenguaje
  de culpa, otra reformulada en terminos sistemicos — y muestra que
  ambas describen los mismos hechos pero solo una lleva a acciones
  preventivas reales.
- `RUNBOOK_EJEMPLO.md`: un runbook completo para el escenario "circuit
  breaker abierto en produccion", con sintoma, impacto, diagnostico,
  mitigacion y escalamiento.
- `POSTMORTEM_EJEMPLO.md`: un postmortem blameless completo para un
  incidente relacionado ("el circuit breaker NO abrio cuando debia"),
  con linea de tiempo, causa raiz, factores contribuyentes y action
  items — y una seccion final que compara explicitamente la version
  con culpa contra la version sistemica del mismo resumen.

Todo el codigo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_blame_checker.py
```

Salida esperada (resumida):

```
Version CON lenguaje de culpa:
  ...
  encontrado: 'olvido'
  encontrado: 'error humano'
  encontrado: 'deberia haber revisado'
  encontrado: 'negligencia'

Version SIN culpa (sistemica):
  ...
  sin lenguaje de culpa individual detectado.

Ambas versiones describen exactamente el MISMO incidente y llevan a la
MISMA correccion tecnica ...
```

## Puntos clave

- Un runbook bueno no le pide a quien esta de guardia que piense desde
  cero — le da un arbol de decision ya pensado con anticipacion. Ver
  el ejemplo de mitigacion condicional en
  [RUNBOOK_EJEMPLO.md](RUNBOOK_EJEMPLO.md): la respuesta correcta
  depende de si el sistema se esta recuperando solo o no, y el runbook
  lo deja explicito de antemano.
- Un postmortem sin culpa no evita nombrar lo que paso — el ejemplo en
  `POSTMORTEM_EJEMPLO.md` es tan especifico como uno con culpa (que
  cambio, cuando, por que), solo que describe **condiciones del
  sistema** en vez de **fallas de una persona**.
- El mismo incidente de ejemplo (circuit breaker mal configurado tras
  un refactor) se relaciona con
  [circuit breaker](../../level2/1-circuit-breaker) (el mecanismo que
  fallo en abrir) y con
  [fencing / promocion de estado](../../level7/1-leader-election-fencing-tokens)
  en el sentido de que ambos son casos donde un valor de configuracion
  desactualizado causa que un mecanismo de seguridad no actue cuando
  deberia.
- Esta disciplina es la contraparte de
  [chaos engineering](../1-chaos-engineering): chaos engineering
  encuentra estos problemas de forma proactiva y controlada; el
  postmortem sin culpa es como se aprende de los que igual llegaron a
  produccion sin haber sido encontrados antes.
