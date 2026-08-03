"""Dead Letter Queue (DLQ): cuando un mensaje falla de forma
persistente (un "poison pill" — datos corruptos, un bug que ese
payload especifico dispara), reintentarlo en el mismo lugar de la
cola bloquea a TODOS los mensajes buenos que estan detras de el. La
cola es FIFO: nadie mas avanza hasta que el primero se resuelva.

La DLQ es la valvula de escape: tras un numero maximo de intentos, el
mensaje problematico se saca de la cola principal y se guarda aparte
(con el motivo del fallo) para investigarlo despues, sin seguir
bloqueando al resto.
"""
from collections import deque


class Message:
    def __init__(self, msg_id: str, poison: bool = False):
        self.msg_id = msg_id
        self.poison = poison
        self.attempts = 0


def process(msg: Message) -> str:
    if msg.poison:
        raise RuntimeError(f"{msg.msg_id}: payload corrupto")
    return f"{msg.msg_id}: procesado ok"


def build_queue(n_good: int, poison_position: int) -> deque:
    queue = deque(Message(f"msg-{i}") for i in range(n_good))
    queue.insert(poison_position, Message("POISON", poison=True))
    return queue


def simulate_without_dlq(queue: deque, max_ticks: int):
    """Sin DLQ: el mensaje que falla se reintenta en el mismo lugar,
    sin limite — bloquea la cola para siempre (o hasta agotar
    `max_ticks`, en esta simulacion).
    """
    processed = []
    for _ in range(max_ticks):
        if not queue:
            break
        msg = queue[0]
        try:
            processed.append(process(msg))
            queue.popleft()
        except RuntimeError:
            msg.attempts += 1  # se reintenta el MISMO mensaje, en el mismo lugar

    return processed, list(queue)


def simulate_with_dlq(queue: deque, max_ticks: int, max_attempts: int = 3):
    """Con DLQ: tras `max_attempts` fallos, el mensaje se saca de la
    cola principal y se archiva en la DLQ junto con el motivo del
    fallo — el resto de la cola sigue avanzando normalmente.
    """
    processed = []
    dead_letters = []
    for _ in range(max_ticks):
        if not queue:
            break
        msg = queue[0]
        try:
            processed.append(process(msg))
            queue.popleft()
        except RuntimeError as exc:
            msg.attempts += 1
            if msg.attempts >= max_attempts:
                queue.popleft()
                dead_letters.append({"msg_id": msg.msg_id, "error": str(exc), "attempts": msg.attempts})

    return processed, list(queue), dead_letters


def reprocess_dlq(dead_letters: list, bug_fixed: bool):
    """Reprocesa los mensajes de la DLQ. Si el bug que los causo ya se
    arreglo (`bug_fixed=True`), ahora deberian procesarse bien. Si no,
    van a fallar exactamente igual — la DLQ no es magia, solo aisla el
    problema para poder investigarlo con calma.
    """
    recovered = []
    still_dead = []
    for entry in dead_letters:
        msg = Message(entry["msg_id"], poison=not bug_fixed)
        try:
            recovered.append(process(msg))
        except RuntimeError as exc:
            still_dead.append({"msg_id": entry["msg_id"], "error": str(exc), "attempts": entry["attempts"] + 1})

    return recovered, still_dead
