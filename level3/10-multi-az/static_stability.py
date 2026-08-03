"""Multi-AZ / multi-region con static stability.

La idea central: la recuperacion ante la caida de una zona de
disponibilidad (AZ) o region NO debe depender de que el "control
plane" (las APIs que lanzan instancias nuevas, escalan autoscaling
groups, actualizan DNS) funcione bien durante el incidente — porque
esas APIs suelen estar MAS degradadas justo durante un incidente
grande: muchos clientes reaccionando al mismo evento las golpean al
mismo tiempo (el mismo problema de fondo que
[6-retry-budget](../../level1/6-retry-budget) y
[bulkhead](../../level2/2-bulkhead) atacan, aca a escala de
infraestructura de nube completa).

La alternativa es **static stability**: PRE-aprovisionar la capacidad
que hara falta durante un failover, para que perder una AZ solo
signifique redirigir trafico hacia capacidad que YA esta corriendo
(una operacion de "data plane": el load balancer deja de mandar
trafico a la AZ caida) — sin necesitar lanzar nada nuevo.
"""
import random


def simulate_static_recovery(total_demand: float, n_az: int, capacity_fraction_per_az: float, failure_at: int, detection_delay: int, ticks: int) -> int:
    """Cada AZ esta pre-aprovisionada para `capacity_fraction_per_az`
    de la demanda total. Al perder una AZ, el load balancer redirige
    trafico a las sanas tras `detection_delay` ticks — una operacion
    de data plane, sin llamar a ninguna API de control plane.

    Devuelve cuantos ticks la capacidad disponible quedo por debajo
    de la demanda total.
    """
    capacity_per_az = total_demand * capacity_fraction_per_az
    dropped_ticks = 0
    for t in range(ticks):
        healthy_azs = n_az if t < failure_at + detection_delay else n_az - 1
        if t >= failure_at:
            healthy_azs = min(healthy_azs, n_az - 1)
        capacity = healthy_azs * capacity_per_az
        if capacity < total_demand:
            dropped_ticks += 1
    return dropped_ticks


def simulate_dynamic_recovery(total_demand: float, n_az: int, failure_at: int, boot_time: int, control_plane_success_rate: float, ticks: int, rng: random.Random):
    """Cada AZ solo esta aprovisionada para su propia porcion, sin
    margen. Al perder una AZ, hace falta lanzar capacidad nueva en las
    sanas — una llamada al control plane, que durante el incidente
    tiene exito con probabilidad `control_plane_success_rate` en cada
    intento (se reintenta cada tick hasta que funciona).

    Devuelve (ticks_con_capacidad_insuficiente, intentos_de_scale_up,
    ticks_hasta_recuperarse_o_None).
    """
    capacity_per_az = total_demand / n_az
    extra_capacity = 0.0
    launching = False
    boot_remaining = 0
    dropped_ticks = 0
    scale_attempts = 0
    recovered_at = None

    for t in range(ticks):
        healthy_azs = n_az if t < failure_at else n_az - 1
        if t == failure_at:
            launching = True

        if launching and boot_remaining == 0:
            scale_attempts += 1
            if rng.random() < control_plane_success_rate:
                boot_remaining = boot_time
                launching = False

        if boot_remaining > 0:
            boot_remaining -= 1
            if boot_remaining == 0:
                extra_capacity = total_demand - (n_az - 1) * capacity_per_az
                if recovered_at is None:
                    recovered_at = t - failure_at

        capacity = healthy_azs * capacity_per_az + extra_capacity
        if capacity < total_demand:
            dropped_ticks += 1

    return dropped_ticks, scale_attempts, recovered_at


def provisioning_overhead(n_az: int) -> float:
    """Que fraccion de la demanda total tiene que pre-aprovisionar CADA
    AZ para que las `n_az - 1` restantes cubran el 100% si una cae —
    la regla "N-1" de static stability.
    """
    return 1.0 / (n_az - 1)
