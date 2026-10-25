// Primera capa cerrada (usuario, 2026-10-21): con PLA humedo, cada salto de la boquilla en la
// primera capa deja un hilo o un puntito y la capa se arruina. Esto toma una pieza YA ACOSTADA
// (apoyada en z = 0) y le agrega una membrana de una capa que tapa todos sus vaciados y agujeros
// chicos: la primera capa queda de un solo contorno (salvo los huecos grandes, como el del vaso).
// Despues de imprimir, los agujeros que hacen falta se abren con una broca a mano y las
// ventanas (infrarrojo de la cuna, lengueta) con un bisturi. La llama exportar.py.
archivo = "";
membrana = 0.6;   // primera capa (0.3) + 2 capas de 0.15: con 0.3 justo, Creality Print cortaba la capa 1 en su tope y ya veia los vaciados
r_abierto = 20;   // los huecos donde cabe un circulo de este radio quedan abiertos (hueco del vaso: r 30)

module seccion() projection(cut = true) translate([0, 0, -0.05]) import(archivo);
union() {
  import(archivo);
  linear_extrude(membrana) difference() {
    fill() seccion();
    offset(r = r_abierto) offset(delta = -r_abierto) difference() { fill() seccion(); seccion(); }
  }
}
