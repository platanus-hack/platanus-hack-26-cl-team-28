#!/usr/bin/env python3
"""Genera la figura imprimible del wati a partir de volúmenes implícitos.

Las coordenadas del frente siguen el dibujo de frontend/src/enjambre/wati.ts.
Se requiere NumPy, scikit-image y trimesh; véase README.md.
"""
from pathlib import Path
import numpy as np
from skimage.measure import marching_cubes
import trimesh

OUTPUT = Path(__file__).with_name('wati-120mm.stl')
STEP = 0.13  # unidades del dibujo (~0,4 mm en la figura terminada)
PASO_INSERTO = 0.045
HOLGURA = 0.14  # por lado, unidades del dibujo (~0,4 mm a escala final)
FONDO_OJO = 9.15
FONDO_BOCA = 11.7
HOLGURA_FONDO = 0.08  # espacio para adhesivo


def suave(a, b, k):
    """Unión suave de campos de distancia aproximados."""
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def elipsoide(x, y, z, cx, cy, cz, rx, ry, rz):
    return (np.sqrt(((x-cx)/rx)**2 + ((y-cy)/ry)**2 + ((z-cz)/rz)**2) - 1) * min(rx, ry, rz)


def distancia_poligono(x, z, vertices):
    """Distancia con signo a un contorno, también si es cóncavo."""
    distancia = np.full(np.broadcast_shapes(x.shape, z.shape), np.inf, dtype=np.float32)
    dentro = np.zeros(distancia.shape, dtype=bool)
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        dx, dz = b[0]-a[0], b[1]-a[1]
        t = np.clip(((x-a[0])*dx + (z-a[1])*dz) / (dx*dx + dz*dz), 0, 1)
        distancia = np.minimum(distancia, np.sqrt((x-a[0]-t*dx)**2 + (z-a[1]-t*dz)**2))
        if dz:
            dentro ^= ((a[1] > z) != (b[1] > z)) & (x < a[0] + (z-a[1])*dx/dz)
    return np.where(dentro, -distancia, distancia)


def mechon():
    """Mechón fino de la referencia, curvado hacia la derecha al verlo de frente."""
    curvas = [
        ((-1.8, 27.2), (-1.9, 34.4), (1.2, 40.5), (6.1, 42.9)),
        ((6.1, 42.9), (3.6, 40.5), (2.0, 35.4), (2.1, 27.2)),
    ]
    puntos = []
    for a, b, c, d in curvas:
        for t in np.linspace(0, 1, 13, endpoint=False):
            u = 1-t
            puntos.append((-(u**3*a[0] + 3*u*u*t*b[0] + 3*u*t*t*c[0] + t**3*d[0]),
                           u**3*a[1] + 3*u*u*t*b[1] + 3*u*t*t*c[1] + t**3*d[1]))
    return puntos


def superficie_frente(x, z):
    restante = np.maximum(0, 1 - np.abs(x/14)**2.6 - np.abs((z-16.9)/12.5)**2.6)
    return 13.4 * np.sqrt(restante)


def distancia_boca(x, z):
    """Distancia al centro de la sonrisa en el plano frontal."""
    distancia = np.full(np.broadcast_shapes(x.shape, z.shape), np.inf, dtype=np.float32)
    puntos = [(1.7*np.cos(t), 20.3 - 1.7*np.sin(t))
              for t in np.linspace(0.15*np.pi, 0.85*np.pi, 24)]
    for a, b in zip(puntos, puntos[1:]):
        dx, dz = b[0]-a[0], b[1]-a[1]
        t = np.clip(((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz), 0, 1)
        distancia = np.minimum(distancia, np.sqrt((x-a[0]-t*dx)**2+(z-a[1]-t*dz)**2))
    return distancia


def campo(x, y, z):
    # Cuerpo redondeado: las cotas vienen de (CX +/- 14, arriba=15, abajo=40).
    # La mitad frontal (+Y) es más profunda; la espalda conserva su perfil.
    profundidad_cuerpo = np.where(y >= 0, 13.4, 8.8)
    contorno = (np.abs(x/14)**2.6 + np.abs((z-16.9)/12.5)**2.6 + (y/profundidad_cuerpo)**2)
    d = (np.sqrt(contorno) - 1) * 9
    for lado in (-1, 1):
        d = suave(d, elipsoide(x, y, z, lado*6, 2.0, 3.1, 3.2, 5.3, 2.7), 0.9)
        # Brazos cortos inclinados y unidos al costado.
        xx = x - lado*14.4 + lado*(z-15.3)*0.32
        brazo = (np.sqrt((xx/2.15)**2 + (y/3.3)**2 + ((z-15.3)/4.1)**2)-1)*2.15
        d = suave(d, brazo, 0.8)
    # Mechón curvado y redondeado que se integra con la cabeza.
    perfil = distancia_poligono(x, z, mechon())
    semiespesor = 0.75 + 1.6*np.clip((43-z)/15.8, 0, 1)
    lateral = np.abs(y-0.7)-semiespesor
    adorno = (np.sqrt(np.maximum(perfil, 0)**2 + np.maximum(lateral, 0)**2)
              + np.minimum(np.maximum(perfil, lateral), 0) - 0.45)
    d = suave(d, adorno, 1.0)
    # Intersección con un plano común: solo las suelas tocan la mesa.
    d = np.maximum(d, 0.75-z)

    # Los alojamientos tienen fondo plano para apoyar y pegar los insertos.
    # La pared deja HOLGURA por lado respecto a las piezas negras.
    for lado in (-1, 1):
        circulo = np.sqrt((x-lado*7.84)**2 + (z-20.4)**2) - (2.1 + HOLGURA)
        corte = np.maximum(circulo, FONDO_OJO - y)
        d = np.maximum(d, -corte)
    corte_boca = np.maximum(distancia_boca(x, z) - (0.575 + HOLGURA), FONDO_BOCA - y)
    d = np.maximum(d, -corte_boca)
    return d


def generar_inserto(nombre, centro_x, centro_z, fondo, tipo, escala):
    """Exporta un inserto con la cara plana hacia la cama y la cara visible curva.

    Para volver al montaje: x = X/escala + centro_x,
    z = Y/escala + centro_z, y = Z/escala + fondo + HOLGURA_FONDO.
    X,Y,Z son las coordenadas del STL del inserto.
    """
    radio = 2.4 if tipo == 'ojo' else 2.3
    xs = np.arange(centro_x-radio, centro_x+radio+PASO_INSERTO, PASO_INSERTO, dtype=np.float32)
    zs = np.arange(centro_z-radio, centro_z+radio+PASO_INSERTO, PASO_INSERTO, dtype=np.float32)
    ys = np.arange(fondo-0.25, 14.2, PASO_INSERTO, dtype=np.float32)
    x, y, z = xs[:, None, None], ys[None, :, None], zs[None, None, :]
    perfil = (np.sqrt((x-centro_x)**2 + (z-centro_z)**2) - 2.1
              if tipo == 'ojo' else distancia_boca(x, z) - 0.575)
    # El inserto queda una fracción por encima de la superficie. El reverso plano
    # queda separado del fondo del alojamiento para permitir una capa de pegamento.
    campo_inserto = np.maximum(np.maximum(perfil, fondo + HOLGURA_FONDO - y),
                                y - superficie_frente(x, z) - 0.06)
    verts, faces, _, _ = marching_cubes(campo_inserto, 0, spacing=(PASO_INSERTO,)*3)
    verts += (xs[0], ys[0], zs[0])
    # Ejes STL: X y Y siguen el frente de la cara; Z es altura sobre la cama.
    verts = np.column_stack((verts[:, 0]-centro_x, verts[:, 2]-centro_z,
                             verts[:, 1]-(fondo+HOLGURA_FONDO))) * escala
    verts[:, 2] -= verts[:, 2].min()  # asegurar contacto exacto con la cama
    pieza = trimesh.Trimesh(vertices=verts, faces=faces, process=True, validate=True)
    if pieza.volume < 0:
        pieza.invert()
    if not pieza.is_watertight or not pieza.is_winding_consistent or len(pieza.split()) != 1 or pieza.volume <= 0:
        raise RuntimeError(f'{nombre}: la pieza no es un sólido cerrado y orientado')
    destino = OUTPUT.with_name(nombre + '.stl')
    pieza.export(destino)
    print(f'{destino}: {len(pieza.faces)} caras; dimensiones en mm: {pieza.extents}')


def main():
    xs = np.arange(-19.7, 19.7, STEP, dtype=np.float32)
    ys = np.arange(-11.7, 16.0, STEP, dtype=np.float32)
    zs = np.arange(-1.13, 45.0, STEP, dtype=np.float32)
    campo_3d = np.empty((len(xs), len(ys), len(zs)), dtype=np.float32)
    x = xs[:, None, None]
    y = ys[None, :, None]
    # Bloques limitan la memoria y dejan el resultado determinista.
    for inicio in range(0, len(zs), 24):
        fin = min(inicio+24, len(zs))
        campo_3d[:, :, inicio:fin] = campo(x, y, zs[None, None, inicio:fin])
    verts, faces, _, _ = marching_cubes(campo_3d, 0, spacing=(STEP, STEP, STEP))
    verts += (xs[0], ys[0], zs[0])
    verts[:, 2] -= verts[:, 2].min()
    escala = 120.0 / verts[:, 2].max()
    verts *= escala
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True, validate=True)
    if mesh.volume < 0:
        mesh.invert()
    if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split()) != 1 or mesh.volume <= 0:
        raise RuntimeError('La malla generada no es una sola pieza cerrada y orientada.')
    mesh.export(OUTPUT, file_type='stl')
    print(f'{OUTPUT}: {len(mesh.faces)} caras; dimensiones en mm: {mesh.extents}; volumen: {mesh.volume:.1f} mm³')
    print(f'Cerrada: {mesh.is_watertight}; orientación consistente: {mesh.is_winding_consistent}; componentes: {len(mesh.split())}')
    # Vista de frente (+Y): el ojo situado en x positivo aparece a la izquierda.
    generar_inserto('ojo-izquierdo', 7.84, 20.4, FONDO_OJO, 'ojo', escala)
    generar_inserto('ojo-derecho', -7.84, 20.4, FONDO_OJO, 'ojo', escala)
    generar_inserto('boca', 0, 19.0, FONDO_BOCA, 'boca', escala)


if __name__ == '__main__':
    main()
