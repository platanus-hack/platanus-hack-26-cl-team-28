import { describe, expect, it } from 'vitest';
import { REGIONES } from '../dominio/catalogos';
import { apilar, disponerResultado, puntoEnBurbuja, radioDe, ubicarBurbujas, type NivelRotulo } from './disposicion';

describe('ubicarBurbujas', () => {
  const pedidos = [
    { y: 100, r: 40 },
    { y: 110, r: 30 },
    { y: 115, r: 12 },
    { y: 400, r: 20 },
  ];
  const puestas = ubicarBurbujas(pedidos, 1, 500, 0, 800);
  it('ninguna se toca con otra', () => {
    for (let i = 0; i < puestas.length; i++) {
      for (let j = i + 1; j < puestas.length; j++) {
        const d = Math.hypot(puestas[i].x - puestas[j].x, puestas[i].y - puestas[j].y);
        expect(d).toBeGreaterThanOrEqual(puestas[i].r + puestas[j].r);
      }
    }
  });
  it('quedan del lado pedido y sin invadir el país', () => {
    for (const b of puestas) expect(b.x - b.r).toBeGreaterThanOrEqual(500 - 0.01);
    const izquierda = ubicarBurbujas(pedidos, -1, 500, 0, 800);
    for (const b of izquierda) expect(b.x + b.r).toBeLessThanOrEqual(500.01);
  });
  it('reserva espacio para que etiquetas y grupos no se superpongan', () => {
    const ubicadas = ubicarBurbujas([{ y: 100, r: 20, anchoTexto: 100, altoTexto: 16 }, { y: 100, r: 15, anchoTexto: 90, altoTexto: 16 }], 1, 100, 0, 400);
    const [a, b] = ubicadas;
    const separadas = a.x + a.r + 100 <= b.x - b.r || b.x + b.r + 90 <= a.x - a.r || Math.abs(a.y - b.y) >= a.r + b.r;
    expect(separadas).toBe(true);
  });
  it('una burbuja sola queda pegada al borde y a su altura', () => {
    expect(puestas[3]).toMatchObject({ x: 520, y: 400 });
  });
});

describe('burbuja', () => {
  it('todos sus puntos caben dentro de su radio', () => {
    const r = radioDe(500, 3);
    for (let k = 0; k < 500; k++) {
      const [x, y] = puntoEnBurbuja(k, 3);
      expect(Math.hypot(x, y)).toBeLessThanOrEqual(r);
    }
  });
  it('sin puntos no tiene radio', () => {
    expect(radioDe(0, 3)).toBe(0);
  });
});

describe('apilar', () => {
  it('sin choques, cada tramo queda en su lugar', () => {
    expect(apilar([50, 150], [20, 20], 0, 300)).toEqual([50, 150]);
  });

  it('los que se pisan se separan lo justo, sin cambiar de orden', () => {
    const centros = apilar([100, 105, 110], [20, 30, 20], 0, 300)!;
    expect(centros[1] - centros[0]).toBeCloseTo(25);
    expect(centros[2] - centros[1]).toBeCloseTo(25);
    // El grupo queda centrado en lo que querían en promedio.
    expect((centros[0] + centros[1] + centros[2]) / 3).toBeCloseTo(105, 0);
  });

  it('no se salen de los extremos', () => {
    const centros = apilar([5, 8, 295], [20, 20, 20], 0, 300)!;
    expect(centros[0] - 10).toBeGreaterThanOrEqual(0);
    expect(centros[1] - centros[0]).toBeGreaterThanOrEqual(20 - 0.01);
    expect(centros[2] + 10).toBeLessThanOrEqual(300);
  });

  it('respeta el orden de entrada aunque vengan desordenados', () => {
    const centros = apilar([200, 100, 102], [20, 20, 20], 0, 300)!;
    expect(centros[0]).toBe(200);
    expect(centros[2] - centros[1]).toBeCloseTo(20);
  });

  it('si no caben ni pegados, lo dice', () => {
    expect(apilar([10, 20, 30], [50, 50, 50], 0, 100)).toBeNull();
  });
});

describe('disponerResultado en el teléfono', () => {
  /** Arma el pedido como lo hace EscenaEnjambre con 5000 puntos, 60 % a favor y 36 % en contra. */
  function pedido(ancho: number, alto: number, arriba: number, abajo: number, niveles: readonly NivelRotulo[] = ['completo', 'abreviado', 'cifra']) {
    const letra = 11;
    const margenArriba = arriba + 10;
    const u = (alto - margenArriba - abajo - 10) / 39.1;
    const pesoTotal = REGIONES.reduce((suma, r) => suma + r.peso, 0);
    const puntos = (region: number, parte: number) => Math.round((5000 * REGIONES[region].peso * parte) / pesoTotal);
    const filas = REGIONES.map((region, k) => ({
      y: margenArriba + (-17.2 - region.capitalLat) * u,
      radio: (lado: 1 | -1, paso: number) => radioDe(puntos(k, lado === 1 ? 0.6 : 0.36), paso),
      texto: (lado: 1 | -1, nivel: NivelRotulo) => {
        const valor = `${lado === 1 ? 60 : 36} %`;
        return nivel === 'completo' ? `${region.corto} ${valor}` : nivel === 'abreviado' ? `${region.abreviado} ${valor}` : valor;
      },
    }));
    return {
      filas,
      ancho,
      arriba: margenArriba - 4,
      abajo: alto - abajo - 6,
      lateral: 8,
      bordeIzq: ancho / 2 - 4.5 * 0.8 * u - 12,
      bordeDer: ancho / 2 + 3.4 * 0.8 * u + 12,
      paso: 2,
      pisoPaso: 1.3,
      altoTexto: letra * 1.3,
      separa: 9,
      niveles,
      // Unos 0,6 em por letra con la letra de los rótulos: un poco más ancho que la real, para no quedar justos.
      medir: (texto: string) => texto.length * letra * 0.6,
      acotado: true,
    };
  }

  /** Cada burbuja con su rótulo queda dentro del lienzo y de la franja libre. */
  function dentroDeLaPantalla(p: ReturnType<typeof pedido>, r: ReturnType<typeof disponerResultado>) {
    expect(r.favor).toHaveLength(16);
    expect(r.contra).toHaveLength(16);
    for (const [lado, puestas] of [[1, r.favor], [-1, r.contra]] as const) {
      puestas.forEach((b, k) => {
        const ancho = p.medir(p.filas[k].texto(lado, r.nivel));
        const izq = lado === 1 ? b.x - b.r : b.x - b.r - p.separa - ancho;
        const der = lado === 1 ? b.x + b.r + p.separa + ancho : b.x + b.r;
        expect(izq).toBeGreaterThanOrEqual(0);
        expect(der).toBeLessThanOrEqual(p.ancho);
        expect(b.y - b.r).toBeGreaterThanOrEqual(p.arriba - 0.01);
        expect(b.y + b.r).toBeLessThanOrEqual(p.abajo + 0.01);
      });
    }
  }

  for (const [ancho, alto] of [[360, 740], [390, 844], [412, 915]]) {
    it(`a ${ancho}×${alto} caben las 16 regiones con su nombre a ambos lados, sin encimarse`, () => {
      const p = pedido(ancho, alto, 64, 150);
      const r = disponerResultado(p);
      expect(r.cabe).toBe(true);
      expect(r.nivel).not.toBe('cifra');
      dentroDeLaPantalla(p, r);
      // De norte a sur, en el mismo orden que el país.
      for (const puestas of [r.favor, r.contra]) {
        const ys = puestas.map((b) => b.y);
        expect(ys).toEqual([...ys].sort((a, b) => a - b));
      }
    });
  }

  it('con el borde del país por altura, cada fila parte de donde termina el país a su altura', () => {
    // Un país angosto arriba (hasta 40 px del centro) y ancho abajo (hasta 70 px).
    const base = pedido(390, 844, 64, 150);
    const bordeEntre = (lado: 1 | -1, _desde: number, hasta: number) => base.ancho / 2 + lado * (hasta < 400 ? 40 : 70);
    const p = { ...base, bordeEntre };
    const r = disponerResultado(p);
    expect(r.cabe).toBe(true);
    dentroDeLaPantalla(p, r);
    for (const [lado, puestas] of [[1, r.favor], [-1, r.contra]] as const) {
      for (const b of puestas) expect(lado * (b.x - lado * b.r - p.ancho / 2)).toBeGreaterThanOrEqual(40 - 0.01);
    }
    // Arriba, donde el país es angosto, las burbujas quedan más cerca del centro que abajo.
    expect(r.favor[0].x - r.favor[0].r).toBeLessThan(r.favor[15].x - r.favor[15].r);
  });

  it('en una pantalla muy chica (320×640) nada se sale, aunque no quepa holgado', () => {
    const p = pedido(320, 640, 64, 150);
    dentroDeLaPantalla(p, disponerResultado(p));
  });

  it('en escritorio, con un solo nivel y sin acotar, usa el nombre completo', () => {
    const p = { ...pedido(1440, 900, 0, 0, ['completo']), acotado: false, lateral: 470, arriba: 18, abajo: 882 };
    expect(disponerResultado(p).nivel).toBe('completo');
  });
});
