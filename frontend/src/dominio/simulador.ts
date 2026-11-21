import { hashTexto, mezclar } from './azar';
import { ACCIONES, RAZONES } from './catalogos';
import type { Caso, Persona, Postura, Respuesta, ResultadoCaso } from './tipos';

/**
 * Contrato con el motor de simulación. El backend real debe entregar, por cada caso,
 * una respuesta por persona en el mismo orden en que se le enviaron.
 */
export interface Simulador {
  nombre: string;
  /** Verdadero mientras las respuestas no vengan del motor real. La interfaz lo avisa. */
  esDemostracion: boolean;
  simular(casos: Caso[], personas: Persona[]): Promise<ResultadoCaso[]>;
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

function responder(persona: Persona, semilla: number): Respuesta {
  const valores = rasgos(persona);
  let puntaje = (mezclar(semilla, 99) - 0.5) * 0.7;
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

/**
 * Simulador de demostración: respuestas deterministas generadas en el navegador a partir
 * del texto del caso y los atributos de cada persona. Sirve para probar la interfaz;
 * no modela opinión real.
 */
export const simuladorDemostracion: Simulador = {
  nombre: 'Demostración local',
  esDemostracion: true,
  async simular(casos, personas) {
    return casos.map((caso) => {
      const semilla = hashTexto(caso.texto.trim().toLowerCase());
      return { casoId: caso.id, respuestas: personas.map((persona) => responder(persona, semilla)) };
    });
  },
};
