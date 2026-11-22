import io
import sys
import threading
import time
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servidor import documentos
from servidor.limites import Cola, Cupo, Reparto, Tasa


class RepartoEntreCorridas(unittest.TestCase):
    def test_nunca_pasa_del_tope_y_todo_se_atiende(self):
        reparto = Reparto(4)
        en_vuelo, maximo, cerrojo = [0], [0], threading.Lock()

        def tarea(k):
            with cerrojo:
                en_vuelo[0] += 1
                maximo[0] = max(maximo[0], en_vuelo[0])
            time.sleep(0.01)
            with cerrojo:
                en_vuelo[0] -= 1
            return k

        futuros = [Cola(reparto, f"corrida-{k % 3}").submit(tarea, k) for k in range(60)]
        self.assertEqual(sorted(f.result(timeout=10) for f in futuros), list(range(60)))
        self.assertLessEqual(maximo[0], 4)
        self.assertEqual(reparto.pendientes(), 0)

    def test_una_corrida_chica_no_espera_detras_de_una_grande(self):
        reparto = Reparto(2)
        orden = []
        cerrojo = threading.Lock()

        def tarea(quien):
            time.sleep(0.02)
            with cerrojo:
                orden.append(quien)

        grandes = [reparto.encolar("grande", tarea, "grande") for _ in range(40)]
        chicas = [reparto.encolar("chica", tarea, "chica") for _ in range(4)]
        for f in grandes + chicas:
            f.result(timeout=10)
        # Las cuatro de la chica salen intercaladas al principio, no después de las cuarenta.
        self.assertLess(max(i for i, quien in enumerate(orden) if quien == "chica"), 14)

    def test_adelante_pasa_antes_que_lo_propio_que_ya_esperaba(self):
        reparto = Reparto(1)
        orden = []
        tapon, empezo = threading.Event(), threading.Event()
        primera = reparto.encolar("a", lambda: (empezo.set(), tapon.wait(5)))
        self.assertTrue(empezo.wait(5))
        tareas = [reparto.encolar("a", orden.append, "normal"), reparto.encolar("a", orden.append, "urgente", adelante=True)]
        tapon.set()
        for f in [primera, *tareas]:
            f.result(timeout=5)
        self.assertEqual(orden, ["urgente", "normal"])

    def test_un_error_viaja_a_quien_espera_y_el_hilo_sigue(self):
        reparto = Reparto(1)
        malo = reparto.encolar("a", lambda: 1 / 0)
        bueno = reparto.encolar("a", lambda: "sigue")
        with self.assertRaises(ZeroDivisionError):
            malo.result(timeout=5)
        self.assertEqual(bueno.result(timeout=5), "sigue")

    def test_descartar_suelta_a_quien_espera(self):
        reparto = Reparto(1)
        tapon, empezo = threading.Event(), threading.Event()
        reparto.encolar("a", lambda: (empezo.set(), tapon.wait(5)))
        # El único hilo ya está ocupado con la tarea de «a»: lo de «b» queda en cola.
        self.assertTrue(empezo.wait(5))
        en_cola = [reparto.encolar("b", lambda: "no debería correr") for _ in range(5)]
        reparto.descartar("b")
        self.assertEqual([f.result(timeout=1) for f in en_cola], [None] * 5)
        self.assertEqual(reparto.pendientes(), 0)
        tapon.set()


class TasaPorDireccion(unittest.TestCase):
    def test_corta_al_pasar_el_maximo_y_se_recupera_al_pasar_la_ventana(self):
        tasa = Tasa(3, segundos=60)
        self.assertEqual([tasa.permite("a", ahora=t) for t in (0, 1, 2, 3)], [True, True, True, False])
        # Otra dirección no se ve afectada.
        self.assertTrue(tasa.permite("b", ahora=3))
        # Justo al cumplirse la ventana del primer pedido vuelve a haber lugar para uno.
        self.assertFalse(tasa.permite("a", ahora=59.9))
        self.assertTrue(tasa.permite("a", ahora=60))
        self.assertFalse(tasa.permite("a", ahora=60.5))

    def test_no_recuerda_direcciones_sin_limite(self):
        tasa = Tasa(1)
        tasa.RECORDADAS = 50
        for k in range(500):
            tasa.permite(f"dir-{k}", ahora=k)
        self.assertLessEqual(len(tasa._marcas), 50)


class CupoDePedidos(unittest.TestCase):
    def test_no_entra_mas_que_el_maximo(self):
        cupo = Cupo(2)
        self.assertEqual([cupo.tomar(), cupo.tomar(), cupo.tomar()], [True, True, False])
        cupo.soltar()
        self.assertTrue(cupo.tomar())


class DocumentosHostiles(unittest.TestCase):
    def test_un_docx_que_se_infla_se_corta(self):
        archivo = io.BytesIO()
        with zipfile.ZipFile(archivo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", "<w:p>" + "hola mundo " * 4_000_000 + "</w:p>")
        self.assertLess(len(archivo.getvalue()), 200_000)
        texto = documentos.extraer_texto("bomba.docx", archivo.getvalue())
        self.assertLessEqual(len(texto), documentos.TEXTO_MAXIMO)

    def test_un_zip_roto_o_sin_documento_es_ilegible(self):
        for datos in (b"PK\x03\x04 esto no es un zip", b""):
            with self.assertRaises(documentos.DocumentoIlegible):
                documentos.extraer_texto("x.docx", datos)

    def test_el_nombre_no_trae_ruta_ni_saltos_de_linea(self):
        self.assertEqual(documentos.nombre_limpio("../../etc/pas\nswd.pdf"), "pas swd.pdf")
        self.assertEqual(documentos.nombre_limpio("C:\\leyes\\ley.docx"), "ley.docx")
        self.assertEqual(documentos.nombre_limpio(""), "documento.txt")
        self.assertEqual(len(documentos.nombre_limpio("a" * 500 + ".pdf")), 120)


if __name__ == "__main__":
    unittest.main()
