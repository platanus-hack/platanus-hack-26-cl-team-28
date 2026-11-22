"""Lo que mantiene al servidor en pie cuando entra mucha gente a la vez, o alguien con mala intención.

El sitio puede quedar abierto al público, y cada corrida lanza procesos de la CLI de Claude (unos
200 MB cada uno) que gastan la suscripción. Sin tope, quince personas con el máximo de agentes
piden miles de procesos a la vez y la máquina se queda sin memoria. Aquí están los topes:

- `Reparto`: todas las corridas comparten un número fijo de llamadas simultáneas al modelo, y se
  turnan de a una tarea por corrida. Una corrida sola usa todo; con varias, cada una avanza a la
  par y una chica no queda esperando detrás de una gigante.
- `Tasa`: cuántos pedidos por minuto acepta de una misma dirección.
- `Cupo`: cuántos pedidos pesados de una clase se atienden a la vez; el resto recibe un «vuelve a
  intentar» en vez de apilarse.

Todo se ajusta por variables de entorno (ver los valores al final) sin tocar el código.
"""

import os
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import Future


class Reparto:
    """Un grupo fijo de hilos que atiende, por turnos, las tareas de todas las corridas."""

    def __init__(self, hilos: int):
        self.hilos = max(1, hilos)
        #: Por corrida, dos filas: lo urgente (en el orden en que llegó) y el resto.
        self._colas: OrderedDict[str, tuple[deque, deque]] = OrderedDict()
        self._condicion = threading.Condition()
        self._pendientes = 0
        self._partidos = 0
        self._ociosos = 0

    def _asegurar_hilos(self) -> None:
        # Los hilos parten a medida que falta quien atienda: un servidor sin uso no tiene cientos de
        # hilos ociosos, y una tarea nueva nunca espera a un hilo ocupado si todavía se puede partir otro.
        while self._partidos < self.hilos and self._ociosos < self._pendientes:
            self._partidos += 1
            self._ociosos += 1
            threading.Thread(target=self._atender, daemon=True, name=f"reparto-{self._partidos}").start()

    def encolar(self, quien: str, funcion, *args, adelante: bool = False) -> Future:
        """Deja una tarea en la cola de `quien`. `adelante`: pasa antes que las suyas que no lo son."""
        futuro: Future = Future()
        with self._condicion:
            urgentes, resto = self._colas.setdefault(quien, (deque(), deque()))
            (urgentes if adelante else resto).append((futuro, funcion, args))
            self._pendientes += 1
            self._asegurar_hilos()
            self._condicion.notify()
        return futuro

    def pendientes(self) -> int:
        with self._condicion:
            return self._pendientes

    def descartar(self, quien: str) -> None:
        """Bota lo que `quien` tenía en cola (una corrida detenida): quien las espera recibe None."""
        with self._condicion:
            urgentes, resto = self._colas.pop(quien, ((), ()))
            self._pendientes -= len(urgentes) + len(resto)
        for futuro, _, _ in (*urgentes, *resto):
            futuro.set_result(None)

    def _siguiente(self):
        """La próxima tarea, de la corrida a la que le toca; esa corrida pasa al final de la fila."""
        for quien in list(self._colas):
            urgentes, resto = self._colas[quien]
            if not urgentes and not resto:
                del self._colas[quien]
                continue
            tarea = (urgentes or resto).popleft()
            self._colas.move_to_end(quien)
            self._pendientes -= 1
            return tarea
        return None

    def _atender(self) -> None:
        while True:
            with self._condicion:
                # Al partir y al volver de una tarea el hilo cuenta como ocioso hasta que toma otra.
                tarea = self._siguiente()
                while tarea is None:
                    self._condicion.wait()
                    tarea = self._siguiente()
                self._ociosos -= 1
            futuro, funcion, args = tarea
            try:
                futuro.set_result(funcion(*args))
            except BaseException as error:  # el error viaja a quien espera la tarea
                futuro.set_exception(error)
            with self._condicion:
                self._ociosos += 1


class Cola:
    """Lo que una corrida ve del reparto: `submit`, como un grupo de hilos propio."""

    def __init__(self, reparto: Reparto, quien: str):
        self._reparto = reparto
        self._quien = quien

    def submit(self, funcion, *args, adelante: bool = False) -> Future:
        return self._reparto.encolar(self._quien, funcion, *args, adelante=adelante)


class Tasa:
    """Pedidos por ventana de tiempo, por dirección. Una ventana deslizante en memoria."""

    #: Direcciones que se recuerdan; al pasarse se olvidan las que llevan más tiempo sin pedir.
    RECORDADAS = 20_000

    def __init__(self, maximo: int, segundos: float = 60.0):
        self.maximo = maximo
        self.segundos = segundos
        self._marcas: OrderedDict[str, deque] = OrderedDict()
        self._cerrojo = threading.Lock()

    def permite(self, quien: str, ahora: float | None = None) -> bool:
        ahora = time.monotonic() if ahora is None else ahora
        with self._cerrojo:
            marcas = self._marcas.setdefault(quien, deque())
            self._marcas.move_to_end(quien)
            while marcas and ahora - marcas[0] >= self.segundos:
                marcas.popleft()
            if len(marcas) >= self.maximo:
                return False
            marcas.append(ahora)
            while len(self._marcas) > self.RECORDADAS:
                self._marcas.popitem(last=False)
            return True


class Cupo:
    """Cuántos pedidos de una clase se atienden a la vez. Quien no entra recibe False de inmediato."""

    def __init__(self, maximo: int):
        self._semaforo = threading.BoundedSemaphore(max(1, maximo))

    def tomar(self, espera: float = 0.0) -> bool:
        return self._semaforo.acquire(timeout=espera) if espera > 0 else self._semaforo.acquire(blocking=False)

    def soltar(self) -> None:
        self._semaforo.release()


class Ocupado(Exception):
    """El servidor está al tope: el pedido se rechaza con un mensaje para volver a intentar."""


def entero(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, defecto))
    except ValueError:
        return defecto


#: Llamadas al modelo a la vez, sumando todas las corridas. Cada una es un proceso de unos 200 MB:
#: 150 es lo que ya corría una sola corrida en la máquina de 30 GB.
LLAMADAS = entero("LLAMADAS", entero("CONCURRENCIA", 30))
#: Corridas en curso a la vez; la siguiente recibe «hay muchas simulaciones».
CORRIDAS_A_LA_VEZ = entero("CORRIDAS_A_LA_VEZ", 40)
#: Corridas en curso desde una misma dirección (una sala entera puede salir por la misma).
CORRIDAS_POR_DIRECCION = entero("CORRIDAS_POR_DIRECCION", 12)
#: Respuestas que puede pedir una corrida: agentes × (variantes + iteraciones).
RESPUESTAS_POR_CORRIDA = entero("RESPUESTAS_POR_CORRIDA", 80_000)
#: Respuestas pendientes entre todas las corridas: sobre esto no se aceptan corridas nuevas.
RESPUESTAS_EN_COLA = entero("RESPUESTAS_EN_COLA", 200_000)
#: Conexiones abiertas a la vez (cada corrida que se mira es una).
CONEXIONES = entero("CONEXIONES", 800)
#: Flujos de eventos abiertos desde una misma dirección, y sobre una misma corrida.
FLUJOS_POR_DIRECCION = entero("FLUJOS_POR_DIRECCION", 60)
FLUJOS_POR_CORRIDA = entero("FLUJOS_POR_CORRIDA", 30)
#: Corridas terminadas que se guardan en memoria para quien reconecta; sobre esto se olvida la más antigua.
CORRIDAS_RECORDADAS = entero("CORRIDAS_RECORDADAS", 60)
#: Segundos sin nadie mirando una corrida antes de detenerla: quien cerró la pestaña deja de gastar.
ABANDONO = entero("ABANDONO", 90)
