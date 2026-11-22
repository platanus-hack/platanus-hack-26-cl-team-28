# Wati para impresión 3D

La figura de 120 mm tiene más volumen hacia delante, brazos cortos, mechón curvo y suelas planas, sin pedestal. La cara tiene alojamientos para tres piezas negras que se imprimen aparte y se pegan. Usar estos archivos como un conjunto: el cuerpo fue actualizado con alojamientos más profundos y no es intercambiable con el STL de una versión anterior.

## Archivos y montaje

- `wati-120mm.stl`: cuerpo con los tres alojamientos; imprimir del color principal, con las suelas sobre la cama.
- `ojo-izquierdo.stl`: ojo izquierdo al mirar la cara de frente; imprimir una vez en negro.
- `ojo-derecho.stl`: ojo derecho al mirar la cara de frente; imprimir una vez en negro.
- `boca.stl`: sonrisa; imprimir una vez en negro.

Los tres insertos están orientados con su cara plana sobre la cama y la superficie curva hacia arriba. Mantener esa orientación al laminar. No son planos por arriba: la altura varía para seguir la curvatura de la cara. En cada ojo, el borde más alto apunta hacia el centro y hacia los pies de la figura. La abertura de la sonrisa apunta hacia arriba. Presentar primero cada pieza en seco y pegarla después; hay una holgura nominal de aproximadamente 0,4 mm por lado y espacio en el fondo para adhesivo. El ajuste real depende de la impresora y puede requerir limpiar o lijar ligeramente las piezas.

El STL no almacena colores ni unidades: al importar los archivos en el laminador, interpretar sus dimensiones en milímetros y no cambiar la escala de las piezas por separado. Revisar la necesidad de soportes para el cuerpo según la impresora y el material.

## Regenerar

Se necesita Python 3 con NumPy, scikit-image y trimesh:

```sh
python -m pip install numpy scikit-image trimesh
python modelo-3d/generar_wati.py
```

El script genera el cuerpo y las tres piezas, y comprueba que cada una sea una malla cerrada y de una sola pieza.
