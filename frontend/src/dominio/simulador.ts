import { hashTexto, mezclar } from './azar';
import { ACCIONES, RAZONES } from './catalogos';
import type { Avance, Caso, Persona, Postura, Respuesta, ResultadoCaso } from './tipos';

/**
 * Contrato con el motor de simulación. El backend real debe entregar, por cada caso,
 * una respuesta por persona en el mismo orden en que se le enviaron.
 */
export interface Simulador {
  nombre: string;
  /** Verdadero mientras las respuestas no vengan del motor real. La interfaz lo avisa. */
  esDemostracion: boolean;
  /**
   * Corre todos los casos sobre las personas. `alAvanzar` se llama cada vez que un agente
   * termina, en cualquier orden, para que el mapa lo muestre mientras el resto sigue corriendo.
   */
  simular(casos: Caso[], personas: Persona[], alAvanzar?: (avance: Avance) => void): Promise<ResultadoCaso[]>;
  /**
   * Pide al agente `cantidad` versiones nuevas de una propuesta que busquen más apoyo.
   * Devuelve casos con `iteracion` informada; el `id` y la `letra` los asigna la interfaz.
   */
  proponerIteraciones(base: Caso, cantidad: number): Promise<Pick<Caso, 'texto' | 'iteracion'>[]>;
}

const UMBRAL = 0.22;
const RASGOS = 5;

function rasgos(persona: Persona): number[] {
  return [
    persona.quintil / 2 - 1,
    (persona.edad - 45) / 35,
    persona.politica === 5 ? 0 : persona.politica / 2 - 1,
    persona.educacion / 2 - 1,
    (persona.lat + 36) / 18,
  ];
}

function responder(persona: Persona, semilla: number, mejora: number): Respuesta {
  const valores = rasgos(persona);
  let puntaje = (mezclar(semilla, 99) - 0.5) * 0.7 + mejora;
  let razon = 0;
  let mayor = -1;
  for (let i = 0; i < RASGOS; i++) {
    const aporte = (mezclar(semilla, i) - 0.5) * 1.1 * valores[i];
    puntaje += aporte;
    if (Math.abs(aporte) > mayor) {
      mayor = Math.abs(aporte);
      razon = i;
    }
  }
  puntaje += (mezclar(semilla, 1000 + persona.id) - 0.5) * 1.5;
  const postura: Postura = puntaje > UMBRAL ? 'favor' : puntaje < -UMBRAL ? 'contra' : 'indecisa';
  const firmeza = Math.min(1, Math.abs(puntaje) / 1.2);
  if (postura === 'indecisa' && mezclar(semilla, 5000 + persona.id) < 0.5) razon = RAZONES.length - 1;
  const empuje = firmeza * 0.8 + mezclar(semilla, 3000 + persona.id) * 0.45;
  const accion = postura === 'indecisa' ? (empuje > 0.4 ? 1 : 0) : Math.min(ACCIONES.length - 1, Math.floor(empuje * 4.4));
  return { postura, firmeza, accion, razon };
}

/** Texto que identifica a un caso para la demostración: lo escrito, o el documento si no se escribió nada. */
function huella(caso: Caso): string {
  const documento = caso.documento ? `${caso.documento.nombre}:${caso.documento.tamano}` : '';
  return `${caso.texto.trim().toLowerCase()}|${documento}`;
}

/** Cuánto sube el apoyo cada iteración de demostración. */
const MEJORA_POR_ITERACION = 0.2;
const PAUSA_ENTRE_LOTES = 60;

/** Reparte las respuestas del primer caso en lotes desordenados, como si los agentes fueran terminando. */
function emitir(respuestas: Respuesta[], duracion: number, alAvanzar: (avance: Avance) => void): Promise<void> {
  const orden = respuestas.map((_, i) => i).sort((a, b) => mezclar(a, 77) - mezclar(b, 77));
  const lotes = Math.max(1, Math.round(duracion / PAUSA_ENTRE_LOTES));
  const porLote = Math.ceil(orden.length / lotes);
  return new Promise((listo) => {
    let enviados = 0;
    const lote = () => {
      for (const persona of orden.slice(enviados, enviados + porLote)) alAvanzar({ caso: 0, persona, respuesta: respuestas[persona] });
      enviados += porLote;
      if (enviados >= orden.length) listo();
      else window.setTimeout(lote, PAUSA_ENTRE_LOTES);
    };
    lote();
  });
}

/**
 * Simulador de demostración: respuestas deterministas generadas en el navegador a partir
 * del texto del caso y los atributos de cada persona. Sirve para probar la interfaz;
 * no modela opinión real. `duracion` (ms) es cuánto tarda en "llegar" la primera variante.
 */
export function crearSimuladorDemostracion(duracion: number): Simulador {
  return {
    nombre: 'Demostración local',
    esDemostracion: true,
    async simular(casos, personas, alAvanzar) {
      const resultados = casos.map((caso) => {
        // Una iteración parte de las respuestas de su variante de origen y les suma apoyo.
        const origen = caso.iteracion ? (casos.find((c) => c.letra === caso.iteracion!.de) ?? caso) : caso;
        const semilla = hashTexto(huella(origen));
        const mejora = (caso.iteracion?.numero ?? 0) * MEJORA_POR_ITERACION;
        return { casoId: caso.id, respuestas: personas.map((persona) => responder(persona, semilla, mejora)) };
      });
      if (alAvanzar && duracion > 0 && resultados.length) await emitir(resultados[0].respuestas, duracion, alAvanzar);
      return resultados;
    },
    async proponerIteraciones(base, cantidad) {
      return Array.from({ length: cantidad }, (_, k) => ({
        texto: `Iteración ${k + 1} sobre la variante ${base.letra} (texto de demostración: aquí va la versión que redacte el agente)`,
        iteracion: { de: base.letra, numero: k + 1 },
      }));
    },
  };
}

export const simuladorDemostracion = crearSimuladorDemostracion(0);
