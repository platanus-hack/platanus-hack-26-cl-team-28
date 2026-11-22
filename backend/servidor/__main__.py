"""Servidor HTTP del simulador. Solo biblioteca estándar (la API de Anthropic es opcional).

    cd backend && python3 -m servidor            # puerto 8787
    MOTOR=claude python3 -m servidor             # fuerza un motor: local, api o claude

Rutas:
    GET  /api/estado                  motor, modelo, población disponible y la encuesta (fija): preguntas,
                                      nombres y escalas ([1, 7]: qué significa cada extremo)
    POST /api/muestra                 {filtros, tamano}: filtra la población y sortea hasta `tamano` agentes
    GET  /api/agentes                 la muestra por defecto (sin filtros), como lista
    POST /api/documentos              cuerpo: el archivo; cabecera X-Nombre. Devuelve texto o resumen
    POST /api/corridas                {casos:[{id,letra,texto,documento?}], muestra:id, agentes?:[i], iteraciones,
                                       filtros?: los de la interfaz, que se guardan con la corrida y vuelven al reabrirla}
    GET  /api/historial               las últimas simulaciones: hora, propuestas y resultado de cada variante
    GET  /api/historial/<id>          una simulación guardada, para volver a verla: {muestra, agentes, filtros, eventos}
    GET  /api/corridas/<id>/eventos   eventos de la corrida (text/event-stream)
    POST /api/corridas/<id>/cancelar
"""

import gzip
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from collections import OrderedDict

from . import limites, metodo
from .corridas import REPARTO, Cache, Caso, Corrida, resumir_documento
from .historial import Historial
from .documentos import DocumentoIlegible, extraer_texto, nombre_limpio
from .limites import Cupo, Ocupado, Tasa
from .motor import elegir_motor
from .poblacion import Muestra, elegir_poblacion, identificador, limpiar

LETRAS = "ABCDEFGH"
MAXIMO_DOCUMENTO = 25 * 1024 * 1024
# Un pedido en JSON (una corrida con sus variantes, sus documentos ya resumidos y su lista de agentes) no pasa de esto.
MAXIMO_PEDIDO = 768 * 1024
# Largo de una propuesta escrita. Un texto más largo se sube como documento, que se resume antes de preguntar.
LARGO_PROPUESTA = 8000
# El texto de un documento ya leído (lo arma este servidor: `LARGO_RESUMIR` × 3 en corridas.py).
LARGO_DOCUMENTO = 10_500
LOTE = int(os.environ.get("LOTE", "10"))
CONCURRENCIA = int(os.environ.get("CONCURRENCIA", "30"))
MAXIMO_ITERACIONES = 3

TAMANO_POR_DEFECTO = 2000
# El tamaño con que parte la interfaz (TAMANO_INICIAL en frontend/src/vivo/useEnVivo.ts).
TAMANO_AL_ABRIR = 1000
# En un servidor con memoria de sobra se puede subir con MAXIMO_MUESTRA (cada lote es un proceso de 240 MB).
MAXIMO_MUESTRA = int(os.environ.get("MAXIMO_MUESTRA", "10000"))
MUESTRAS_GUARDADAS = 60

# El motor primero: sin uno disponible no tiene sentido leer la población.
MOTOR = elegir_motor()
POBLACION = elegir_poblacion()
CACHE = Cache()
HISTORIAL = Historial()
CORRIDAS: dict[str, Corrida] = {}
#: De qué dirección vino cada corrida en curso, para el tope por dirección.
ORIGEN: dict[str, str] = {}
CERROJO_CORRIDAS = threading.Lock()
MUESTRAS: OrderedDict[str, Muestra] = OrderedDict()
CERROJO_MUESTRAS = threading.Lock()

# Pedidos por minuto desde una misma dirección. Son holgados a propósito: toda una sala puede salir
# a internet por la misma dirección. Lo que de verdad protege a la máquina son los topes globales.
TASA_TODO = Tasa(limites.entero("PEDIDOS_POR_MINUTO", 3000))
TASA_CORRIDAS = Tasa(limites.entero("CORRIDAS_POR_MINUTO", 60))
TASA_DOCUMENTOS = Tasa(limites.entero("DOCUMENTOS_POR_MINUTO", 30))
TASA_MUESTRAS = Tasa(limites.entero("MUESTRAS_POR_MINUTO", 600))
# Cada documento largo es una llamada al modelo de redacción con todo su texto: pocas a la vez.
CUPO_DOCUMENTOS = Cupo(limites.entero("DOCUMENTOS_A_LA_VEZ", 3))
# Sortear una muestra nueva ocupa la tabla de agentes, de a una: las que esperan no pasan de estas.
CUPO_MUESTRAS = Cupo(limites.entero("MUESTRAS_EN_ESPERA", 12))
# Una corrida terminada se puede seguir leyendo este rato (quien reconecta); después se olvida.
SEGUNDOS_TERMINADA = 180
#: Flujos de eventos abiertos por dirección.
FLUJOS: dict[str, int] = {}


def olvidar_corridas() -> None:
    """Saca de la memoria las corridas que terminaron hace rato: cada una guarda todas sus respuestas."""
    ahora = time.time()
    with CERROJO_CORRIDAS:
        for identificador, corrida in list(CORRIDAS.items()):
            if corrida.terminada:
                ORIGEN.pop(identificador, None)
                if ahora - getattr(corrida, "fin", ahora) > SEGUNDOS_TERMINADA:
                    del CORRIDAS[identificador]
        # Aunque sean recientes, las terminadas que se recuerdan tienen tope: repetir corridas que salen
        # de la caché en segundos no acumula sus respuestas en memoria.
        terminadas = sorted((c for c in CORRIDAS.values() if c.terminada), key=lambda c: getattr(c, "fin", 0))
        for corrida in terminadas[: max(0, len(terminadas) - limites.CORRIDAS_RECORDADAS)]:
            del CORRIDAS[corrida.id]


def respuestas_pendientes() -> int:
    """Cuántas respuestas faltan entre todas las corridas en curso (para no aceptar más de las que caben)."""
    en_curso = [c for c in list(CORRIDAS.values()) if not c.terminada and not c.cancelada]
    return sum(max(0, len(c.agentes) * (len(c.casos) + c.iteraciones) - sum(len(caso.respuestas) for caso in c.casos)) for c in en_curso)


def sacar_muestra(filtros: dict | None, tamano) -> Muestra:
    """Filtra la población y sortea; las últimas muestras se guardan para poder correrlas."""
    tamano = max(1, min(MAXIMO_MUESTRA, int(tamano or TAMANO_POR_DEFECTO)))
    # Una muestra ya pedida se devuelve tal cual: el sorteo es fijo, así que sería la misma.
    conocida = identificador(limpiar(filtros), tamano)
    with CERROJO_MUESTRAS:
        if conocida in MUESTRAS:
            MUESTRAS.move_to_end(conocida)
            return MUESTRAS[conocida]
    # La tabla atiende de a una muestra: si ya hay muchas esperando, se avisa en vez de sumar otra a la fila.
    if not CUPO_MUESTRAS.tomar(espera=0.05):
        raise Ocupado("Hay mucha gente eligiendo a quiénes preguntar. Intenta de nuevo en unos segundos.")
    try:
        muestra = POBLACION.muestra(filtros, tamano)
    finally:
        CUPO_MUESTRAS.soltar()
    with CERROJO_MUESTRAS:
        MUESTRAS[muestra.id] = muestra
        MUESTRAS.move_to_end(muestra.id)
        while len(MUESTRAS) > MUESTRAS_GUARDADAS:
            MUESTRAS.popitem(last=False)
    return muestra


class Invalido(ValueError):
    """Un pedido mal formado, con un mensaje escrito para quien lo hizo."""


class Servidor(ThreadingHTTPServer):
    """Un hilo por conexión, con tope: sobre `CONEXIONES` abiertas, la siguiente se cierra de inmediato."""

    daemon_threads = True
    # Conexiones que el sistema deja en espera mientras se atienden otras: con 5 (lo normal) una ráfaga se pierde.
    request_queue_size = 512

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._abiertas = 0
        self._cerrojo = threading.Lock()

    def process_request(self, request, client_address):
        with self._cerrojo:
            if self._abiertas >= limites.CONEXIONES:
                self.shutdown_request(request)
                return
            self._abiertas += 1
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._cerrojo:
                self._abiertas -= 1

    def handle_error(self, request, client_address):
        # Una conexión que se corta o se queda callada no es un error que valga una traza completa.
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ph26"
    sys_version = ""
    # Segundos que se espera a una conexión callada (quien abre y no manda nada, o no lee). Es más
    # que lo que Caddy mantiene abierta una conexión ociosa, para no cerrársela justo cuando la reutiliza.
    timeout = 150

    def _quien(self) -> str:
        """La dirección de quien pide. Detrás de Caddy (que llega por la interfaz local) es la que él informa."""
        directa = self.client_address[0]
        if directa in ("127.0.0.1", "::1"):
            informada = (self.headers.get("X-Forwarded-For") or "").split(",")[-1].strip()
            return informada[:64] or directa
        return directa

    def log_message(self, formato, *args):  # silencio salvo errores
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(formato, *args)

    def _json(self, codigo: int, datos, crudo: bytes | None = None) -> None:
        cuerpo = crudo if crudo is not None else json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if codigo in (429, 503):
            self.send_header("Retry-After", "10")
        if codigo >= 400:
            # No se sabe si el cuerpo del pedido se leyó entero: la conexión no se reutiliza. Lo que
            # falte de un cuerpo chico se lee y se bota, para que quien lo manda alcance a recibir el mensaje.
            self._botar_cuerpo()
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _cuerpo(self, maximo: int = MAXIMO_PEDIDO) -> bytes:
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if largo < 0 or self.headers.get("Transfer-Encoding"):
            raise Invalido("El pedido no dice cuánto pesa")
        if largo > maximo:
            raise Invalido("El archivo pesa más de 25 MB" if maximo == MAXIMO_DOCUMENTO else "El pedido es demasiado grande")
        self._leido = True
        cuerpo = self.rfile.read(largo)
        if len(cuerpo) < largo:
            raise Invalido("El pedido llegó incompleto")
        return cuerpo

    def _botar_cuerpo(self) -> None:
        if self.command != "POST" or getattr(self, "_leido", False):
            return
        self._leido = True
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            if 0 < largo <= 2 * MAXIMO_PEDIDO:
                self.rfile.read(largo)
        except (ValueError, OSError):
            pass

    def _pedido(self) -> dict:
        """El cuerpo de un pedido en JSON, que siempre es un objeto."""
        pedido = json.loads(self._cuerpo() or b"{}")
        if not isinstance(pedido, dict):
            raise Invalido("El pedido no tiene la forma esperada")
        return pedido

    def _frenar(self, tasa: Tasa, mensaje: str) -> None:
        if not tasa.permite(self._quien()):
            raise Ocupado(mensaje)

    # No hay permiso entre orígenes: el sitio y el motor se sirven desde el mismo dominio, y así
    # ninguna otra página puede lanzar simulaciones desde el navegador de quien la visita.

    def do_GET(self):
        try:
            self._frenar(TASA_TODO, "Demasiados pedidos seguidos. Espera un momento.")
            return self._get()
        except Ocupado as error:
            return self._json(429, {"error": str(error)})
        except Invalido as error:
            return self._json(400, {"error": str(error)[:200]})
        except (ValueError, KeyError, TypeError, AttributeError):
            # Un error al leer el pedido: afuera no se cuenta qué pasó adentro.
            return self._json(400, {"error": "El pedido no tiene la forma esperada"})
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except Exception:
            traceback.print_exc()
            return self._json(500, {"error": "El servidor tuvo un problema. Intenta de nuevo."})

    def _get(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/estado":
            poblacion = POBLACION.describir()
            return self._json(200, {"motor": MOTOR.describir(), "agentes": poblacion["agentes"], "poblacion": poblacion, "lote": LOTE, "concurrencia": CONCURRENCIA, "preguntas": metodo.PREGUNTAS,
                                    "nombres": metodo.NOMBRES, "escalas": metodo.ESCALAS})
        if ruta == "/api/historial":
            return self._json(200, {"corridas": HISTORIAL.ultimas()})
        if ruta.startswith("/api/historial/"):
            return self._vista(ruta.removeprefix("/api/historial/"))
        if ruta == "/api/agentes":
            return self._json(200, [a.publico() for a in sacar_muestra(None, TAMANO_POR_DEFECTO).agentes])
        partes = ruta.strip("/").split("/")
        if len(partes) == 4 and partes[:2] == ["api", "corridas"] and partes[3] == "eventos":
            return self._eventos(partes[2])
        self._json(404, {"error": "No existe"})

    def do_POST(self):
        ruta = urlparse(self.path).path
        try:
            self._frenar(TASA_TODO, "Demasiados pedidos seguidos. Espera un momento.")
            if ruta == "/api/documentos":
                return self._documento()
            if ruta == "/api/muestra":
                self._frenar(TASA_MUESTRAS, "Demasiados cambios de filtros seguidos. Espera un momento.")
                pedido = self._pedido()
                filtros = pedido.get("filtros")
                return self._json(200, None, sacar_muestra(filtros if isinstance(filtros, dict) else None, pedido.get("tamano")).cuerpo())
            if ruta == "/api/corridas":
                return self._crear_corrida()
            partes = ruta.strip("/").split("/")
            if len(partes) == 4 and partes[:2] == ["api", "corridas"] and partes[3] == "cancelar":
                corrida = CORRIDAS.get(partes[2])
                if corrida:
                    corrida.cancelada = True
                    REPARTO.descartar(corrida.id)
                return self._json(200, {"ok": True})
        except Ocupado as error:
            return self._json(429, {"error": str(error)})
        except DocumentoIlegible as error:
            return self._json(422, {"error": str(error)})
        except Invalido as error:
            return self._json(400, {"error": str(error)[:200]})
        except (ValueError, KeyError, TypeError, AttributeError):
            # Un error al leer el pedido: afuera no se cuenta qué pasó adentro.
            return self._json(400, {"error": "El pedido no tiene la forma esperada"})
        except (ConnectionError, TimeoutError):
            self.close_connection = True
            return
        except Exception:
            # El detalle queda en el registro del servidor; hacia afuera no sale nada de adentro.
            traceback.print_exc()
            return self._json(500, {"error": "El servidor tuvo un problema. Intenta de nuevo."})
        self._json(404, {"error": "No existe"})

    def _documento(self):
        self._frenar(TASA_DOCUMENTOS, "Demasiados documentos seguidos. Espera un momento.")
        nombre = nombre_limpio(unquote(self.headers.get("X-Nombre") or "documento.txt"))
        datos = self._cuerpo(MAXIMO_DOCUMENTO)
        if not CUPO_DOCUMENTOS.tomar(espera=0.05):
            raise Ocupado("Se están leyendo otros documentos. Intenta de nuevo en unos segundos.")
        try:
            texto = extraer_texto(nombre, datos)
            documento, consumo = resumir_documento(MOTOR, nombre, texto)
        except DocumentoIlegible:
            raise
        except Exception as error:
            print(f"No se pudo resumir el documento {nombre!r}: {type(error).__name__}: {error}"[:500], flush=True)
            raise DocumentoIlegible("No se pudo leer el documento. Prueba de nuevo o súbelo en otro formato.") from error
        finally:
            CUPO_DOCUMENTOS.soltar()
        self._json(200, {**documento, "llamadas": consumo.llamadas, "costo_usd": round(consumo.costo_usd, 4)})

    def _crear_corrida(self):
        quien = self._quien()
        self._frenar(TASA_CORRIDAS, "Demasiadas simulaciones seguidas. Espera un momento.")
        pedido = self._pedido()
        casos = []
        crudos = pedido.get("casos")
        for k, c in enumerate(crudos[: len(LETRAS)] if isinstance(crudos, list) else []):
            if not isinstance(c, dict):
                continue
            texto = c.get("texto") if isinstance(c.get("texto"), str) else ""
            if len(texto) > LARGO_PROPUESTA:
                raise Invalido("La propuesta es demasiado larga (más de ocho mil caracteres). Resúmela o súbela como documento.")
            # Del documento solo se usa lo que este servidor entrega al leerlo, y con su largo.
            documento = c.get("documento")
            if isinstance(documento, dict) and isinstance(documento.get("texto"), str) and documento["texto"].strip():
                documento = {"nombre": nombre_limpio(str(documento.get("nombre") or "")), "titulo": str(documento.get("titulo") or "")[:200],
                             "texto": documento["texto"][:LARGO_DOCUMENTO]}
            else:
                documento = None
            # La letra la pone el servidor: va a la pantalla de todos los que miren el historial.
            caso = Caso(id=str(c.get("id", k))[:40], letra=LETRAS[len(casos)], texto=texto, documento=documento)
            if caso.politica():
                casos.append(caso)
        if not casos:
            raise Invalido("Falta al menos una propuesta con texto")
        with CERROJO_MUESTRAS:
            muestra = MUESTRAS.get(str(pedido.get("muestra") or ""))
        if muestra is None:
            if pedido.get("muestra"):
                raise Invalido("Esa muestra ya no está disponible; vuelve a elegir a quiénes preguntar")
            muestra = sacar_muestra(None, TAMANO_POR_DEFECTO)
        indices = pedido.get("agentes")
        if isinstance(indices, list) and indices:
            # Cada agente una sola vez: una lista con repetidos no multiplica el trabajo.
            unicos = sorted({i for i in indices if type(i) is int and 0 <= i < len(muestra.agentes)})
            elegidos = [muestra.agentes[i] for i in unicos]
        else:
            elegidos = muestra.agentes
        if not elegidos:
            raise Invalido("La muestra quedó vacía")
        try:
            iteraciones = max(0, min(MAXIMO_ITERACIONES, int(pedido.get("iteraciones") or 0)))
        except (TypeError, ValueError):
            iteraciones = 0
        # El tamaño del lote lo decide el servidor: con lotes de una persona la misma corrida serían diez veces más llamadas.
        lote = LOTE
        pedidas = len(elegidos) * (len(casos) + iteraciones)
        if pedidas > limites.RESPUESTAS_POR_CORRIDA:
            raise Invalido("Son demasiados agentes para tantas variantes. Baja la cantidad de agentes o de variantes.")
        olvidar_corridas()
        # La encuesta es fija: si el pedido trae preguntas, no se usan.
        corrida = Corrida(MOTOR, CACHE, elegidos, casos, iteraciones, lote, CONCURRENCIA, LETRAS)
        # Todas las comprobaciones de cupo y el alta van bajo el mismo cerrojo: dos pedidos a la vez no pasan juntos.
        with CERROJO_CORRIDAS:
            if respuestas_pendientes() + pedidas > limites.RESPUESTAS_EN_COLA:
                raise Ocupado("Hay muchas simulaciones en curso. Intenta de nuevo en un minuto, o con menos agentes.")
            en_curso = [i for i, c in CORRIDAS.items() if not c.terminada]
            if len(en_curso) >= limites.CORRIDAS_A_LA_VEZ:
                raise Ocupado("Hay muchas simulaciones en curso. Intenta de nuevo en un minuto.")
            if sum(1 for i in en_curso if ORIGEN.get(i) == quien) >= limites.CORRIDAS_POR_DIRECCION:
                raise Ocupado("Ya hay varias simulaciones en curso desde esta conexión. Espera a que termine alguna.")
            CORRIDAS[corrida.id] = corrida
            ORIGEN[corrida.id] = quien
        # La muestra y los filtros van al historial: con ellos la corrida se puede volver a ver.
        threading.Thread(target=HISTORIAL.guardar_al_terminar, args=(corrida, muestra, pedido.get("filtros")), daemon=True).start()
        self._json(201, {"id": corrida.id, "motor": MOTOR.describir(), "agentes": len(elegidos), "preguntas": corrida.preguntas})

    def _vista(self, identificador: str):
        """Una corrida guardada. Va comprimida tal como está en el disco si quien la pide lo acepta."""
        vista = HISTORIAL.vista(identificador)
        if vista is None:
            return self._json(404, {"error": "Esa simulación ya no está guardada"})
        comprimida = "gzip" in (self.headers.get("Accept-Encoding") or "")
        cuerpo = vista if comprimida else gzip.decompress(vista)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if comprimida:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _eventos(self, identificador: str):
        corrida = CORRIDAS.get(identificador)
        if not corrida:
            return self._json(404, {"error": "No existe esa corrida"})
        # Cada flujo ocupa una conexión mientras dura: una dirección o una corrida no se las llevan todas.
        quien = self._quien()
        with CERROJO_CORRIDAS:
            if FLUJOS.get(quien, 0) >= limites.FLUJOS_POR_DIRECCION or corrida.oyentes >= limites.FLUJOS_POR_CORRIDA:
                raise Ocupado("Hay demasiadas ventanas mirando simulaciones desde esta conexión.")
            FLUJOS[quien] = FLUJOS.get(quien, 0) + 1
        try:
            return self._transmitir(corrida)
        finally:
            with CERROJO_CORRIDAS:
                if FLUJOS.get(quien, 0) <= 1:
                    FLUJOS.pop(quien, None)
                else:
                    FLUJOS[quien] -= 1

    def _transmitir(self, corrida):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            visto = max(0, int(self.headers.get("Last-Event-ID") or -1) + 1)
        except ValueError:
            visto = 0
        corrida.escuchar(True)
        try:
            while True:
                nuevos = corrida.esperar(visto)
                if not nuevos:
                    if corrida.terminada:
                        break
                    self.wfile.write(b": sigue\n\n")
                    self.wfile.flush()
                    continue
                for tipo, datos in nuevos:
                    bloque = f"id: {visto}\nevent: {tipo}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"
                    self.wfile.write(bloque.encode())
                    visto += 1
                self.wfile.flush()
                if corrida.terminada and visto >= len(corrida.eventos):
                    break
        except OSError:
            # Quien miraba cerró la pestaña, perdió la conexión o dejó de leer.
            pass
        finally:
            corrida.escuchar(False)
        self.close_connection = True


def main():
    puerto = int(os.environ.get("PUERTO", "8787"))
    # La primera muestra que pide la interfaz (sin filtros) queda lista antes de que alguien abra el sitio.
    threading.Thread(target=sacar_muestra, args=(None, TAMANO_AL_ABRIR), daemon=True).start()
    servidor = Servidor(("127.0.0.1" if not os.environ.get("ABIERTO") else "0.0.0.0", puerto), Manejador)
    descripcion = MOTOR.describir()
    poblacion = POBLACION.describir()
    print(f"Simulador en http://127.0.0.1:{puerto} · {poblacion['fuente']}: {poblacion['agentes']:,} agentes por {poblacion['personas']:,} personas · "
          f"motor {descripcion['nombre']} ({descripcion['modelo']}) · perfil {descripcion['perfil']}".replace(",", "."), flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
