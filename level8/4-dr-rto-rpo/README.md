# DR con RTO/RPO explícitos

## Que es

**RTO** (Recovery Time Objective) es cuanto tiempo puede estar el
sistema caido antes de volver a funcionar. **RPO** (Recovery Point
Objective) es cuantos datos se pueden dar el lujo de perder, medido
en tiempo — la ventana entre el ultimo punto de recuperacion valido y
el momento del desastre. Cualquier plan de disaster recovery sin
estos dos numeros explicitos no es un plan — es una esperanza.

## Cuatro estrategias, un tradeoff explicito

- **Backup & restore**: solo backups periodicos, nada corriendo en el
  sitio de recuperacion. La mas barata, la mas lenta: RTO de horas o
  dias, RPO igual al intervalo entre backups.
- **Pilot light**: el nucleo minimo (tipicamente la base de datos,
  replicando) esta siempre corriendo en el sitio de DR; el resto se
  "enciende" durante el desastre. RPO chico, RTO de decenas de
  minutos.
- **Warm standby**: una copia completa pero reducida del ambiente,
  corriendo todo el tiempo. RTO de minutos: solo hay que escalar
  capacidad y redirigir trafico.
- **Hot standby / activo-activo**: una copia a escala completa, ya
  recibiendo trafico o lista para recibirlo al instante. RTO casi
  cero, RPO casi cero — el mismo concepto de
  [static stability](../../level3/10-multi-az), aplicado entre
  regiones en vez de entre zonas de disponibilidad.

Cada escalon reduce RTO y RPO a costa de mas infraestructura corriendo
permanentemente en el sitio de DR. No hay una estrategia "correcta"
universal — depende de cuanto cuesta, para ese negocio en particular,
cada minuto de downtime y cada minuto de datos perdidos.

## Probar el restore, no solo el backup

Tener backups y poder recuperarse de verdad son afirmaciones
**distintas**. Un backup puede estar corrupto, en un formato que ya
no coincide con el restore, o depender de una clave de cifrado que
rotó sin que nadie actualizara el procedimiento — y nada de eso se
nota hasta que hace falta restaurar de verdad. Solo un **restore
ensayado**, periodico, cierra esa brecha.

## Estructura del ejemplo

- `dr_strategies.py`: la tabla de las cuatro estrategias, y
  `probability_recovery_never_tested` /
  `probability_recovery_tested` — el modelo probabilistico de cuanto
  mejora la confiabilidad real de la recuperacion al probar el
  restore periodicamente.
- `demo_dr.py`: las dos partes descriptas arriba.

Todo el ejemplo usa solo la libreria estandar de Python (no requiere
`pip install`).

## Como ejecutarlo

```bash
python3 demo_dr.py
```

Salida esperada:

```
Parte 2: probabilidad de un bug no descubierto en el proceso de backup: 20%
  SIN restore de prueba: probabilidad de recuperacion real = 80.0%
  CON 1 restore de prueba: probabilidad de recuperacion = 98.0%
  CON 4 restores de prueba: probabilidad de recuperacion = 100.0%
```

## Puntos clave

- RTO y RPO no son aspiraciones — son numeros que hay que MEDIR
  probando la recuperacion real, no calcular en un documento y
  asumir que se cumplen.
- La estrategia de DR y la topologia de
  [redundancia N+1/N+2](../../level3/redundancia-n1-n2) resuelven
  problemas relacionados pero distintos: redundancia es sobrevivir a
  la perdida de una parte del sistema; DR es sobrevivir a la perdida
  de **todo** el sitio primario, algo mucho mas raro pero tambien
  mucho mas caro de mitigar.
- Un restore de prueba no tiene que simular el desastre completo cada
  vez — probar partes del proceso con regularidad (restaurar un
  backup a un ambiente de staging, por ejemplo) ya captura la mayoria
  de los problemas reales, mucho antes de necesitar el proceso
  completo bajo presion real.
- Esto es la misma disciplina que
  [chaos engineering](../1-chaos-engineering): la unica forma de
  saber si un mecanismo de recuperacion funciona es ejercitarlo de
  verdad, de forma controlada, en vez de confiar en que funcionara
  cuando mas importe.
