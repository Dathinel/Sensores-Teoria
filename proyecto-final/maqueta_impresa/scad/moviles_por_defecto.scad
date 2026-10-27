// Valores por defecto de las piezas que se MUEVEN (revisar.py las barre en todo su recorrido para ver que no
// choquen). Va incluido ANTES de los subsistemas: si un subsistema define su lista, la suya gana.
// Cada entrada: [pieza o nombre del barrido, [piezas que se mueven con ella o la tocan a proposito]].
// El subsistema define module <sub>_barrido(n): la union de la pieza en varias posiciones de su recorrido.
MOVILES_ALM = []; MOVILES_MON = []; MOVILES_VAS = []; MOVILES_TAP = []; MOVILES_CAN = [];

// Agujeros que un subsistema necesita en piezas de OTRO (p. ej. el paso de un eje por un riel de la estructura):
// [[p0, p1, diametro], ...]. maqueta.scad los resta en todas las piezas, igual que los de los remaches.
// Tambien como lista LITERAL (solo numeros).
AGUJEROS_ALM = []; AGUJEROS_MON = []; AGUJEROS_VAS = []; AGUJEROS_TAP = []; AGUJEROS_CAN = [];

// Mecanismos que se mueven juntos pero distinto (leva y seguidor, manivela y carro, escape y vasos): los barridos
// se excluyen entre si, asi que se revisan FASE POR FASE. [[nombre, pasos], ...] (LITERAL) y
// module <sub>_fase(n, k, lado) con k = 0..pasos: lado 0 = lo que mueve, lado 1 = lo que sigue, en ese paso.
// revisar.py intersecta los dos lados en cada paso (> 1 mm3 = choque).
SINCRONOS_ALM = []; SINCRONOS_MON = []; SINCRONOS_VAS = []; SINCRONOS_TAP = []; SINCRONOS_CAN = [];
