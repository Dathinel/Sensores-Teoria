// Valores por defecto de las piezas que se MUEVEN (revisar.py las barre en todo su recorrido para ver que no
// choquen). Va incluido ANTES de los subsistemas: si un subsistema define su lista, la suya gana.
// Cada entrada: [pieza o nombre del barrido, [piezas que se mueven con ella o la tocan a proposito]].
// El subsistema define module <sub>_barrido(n): la union de la pieza en varias posiciones de su recorrido.
MOVILES_ALM = []; MOVILES_MON = []; MOVILES_VAS = []; MOVILES_TAP = []; MOVILES_CAN = [];

// Agujeros que un subsistema necesita en piezas de OTRO (p. ej. el paso de un eje por un riel de la estructura):
// [[p0, p1, diametro], ...]. maqueta.scad los resta en todas las piezas, igual que los de los remaches.
// Tambien como lista LITERAL (solo numeros).
AGUJEROS_ALM = []; AGUJEROS_MON = []; AGUJEROS_VAS = []; AGUJEROS_TAP = []; AGUJEROS_CAN = [];
