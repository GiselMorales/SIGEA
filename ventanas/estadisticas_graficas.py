from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


AZUL = "#2D80D3"
AZUL_OSCURO = "#174A7E"
AZUL_CLARO = "#75A9E6"
ROSA = "#E16B91"
GRIS_TEXTO = "#526173"
GRIS_REJILLA = "#E8EDF3"
COLORES_SEMESTRE = (
    "#4F91E8",
    "#63B36E",
    "#F0A44B",
    "#9B72D2",
    "#39AAB3",
    ROSA,
    "#6282C4",
    "#77A96B",
    "#D78956",
    "#8068AD",
    "#4B9D9A",
    "#B56780",
)


def _preparar_eje(eje):
    eje.set_facecolor("white")
    eje.tick_params(axis="both", colors=GRIS_TEXTO, labelsize=8)
    eje.yaxis.set_major_locator(MaxNLocator(integer=True))
    eje.grid(axis="y", color=GRIS_REJILLA, linewidth=0.8)
    eje.set_axisbelow(True)
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)
    eje.spines["left"].set_visible(False)
    eje.spines["bottom"].set_color(GRIS_REJILLA)


def _grupos_ordenados(datos):
    return sorted(
        datos.get("grupos", []),
        key=lambda grupo: grupo["clave_grupo"],
    )


def _figura_vacia(mensaje):
    figura = Figure(figsize=(6, 2.45), facecolor="white")
    eje = figura.subplots()
    eje.text(
        0.5,
        0.5,
        mensaje,
        ha="center",
        va="center",
        transform=eje.transAxes,
        color=GRIS_TEXTO,
        fontsize=10,
    )
    eje.set_axis_off()
    figura.subplots_adjust(left=0.07, right=0.98, top=0.95, bottom=0.2)
    return figura


def crear_figura_alumnos(datos):
    grupos = _grupos_ordenados(datos)
    if not grupos:
        return _figura_vacia("Sin grupos para los filtros seleccionados")

    figura = Figure(figsize=(6, 2.45), facecolor="white")
    eje = figura.subplots()
    posiciones = list(range(len(grupos)))
    cantidades = [grupo["alumnos"] for grupo in grupos]
    etiquetas = [grupo["clave_grupo"] for grupo in grupos]
    barras = eje.bar(
        posiciones,
        cantidades,
        color=AZUL,
        width=0.68,
        zorder=3,
    )
    eje.set_xticks(posiciones, etiquetas)
    eje.set_ylabel("Alumnos", color=GRIS_TEXTO, fontsize=8)
    eje.margins(x=0.02, y=0.17)
    eje.bar_label(barras, padding=3, fontsize=8, color=AZUL_OSCURO)
    _preparar_eje(eje)
    figura.subplots_adjust(left=0.09, right=0.98, top=0.96, bottom=0.2)
    return figura


def _crear_dona(datos, claves, colores, total_centro, mensaje_vacio):
    valores = [
        (etiqueta, int(valor))
        for etiqueta, valor in datos
        if int(valor) > 0
    ]
    if not valores:
        return _figura_vacia(mensaje_vacio)

    figura = Figure(figsize=(6, 2.45), facecolor="white")
    eje = figura.subplots()
    cantidades = [valor for _, valor in valores]
    etiquetas = [etiqueta for etiqueta, _ in valores]
    color_por_etiqueta = dict(zip(claves, colores))
    colores_usados = [
        color_por_etiqueta.get(etiqueta, "#94A3B8")
        for etiqueta in etiquetas
    ]
    eje.pie(
        cantidades,
        colors=colores_usados,
        radius=0.9,
        startangle=65,
        counterclock=False,
        wedgeprops={"width": 0.32, "edgecolor": "white", "linewidth": 2},
        autopct=lambda porcentaje: f"{porcentaje:.1f}%",
        pctdistance=0.82,
        textprops={
            "color": "white",
            "fontsize": 7,
            "weight": "bold",
            "clip_on": False,
        },
    )
    eje.text(
        0,
        0.07,
        str(total_centro),
        ha="center",
        va="center",
        color=AZUL_OSCURO,
        fontsize=16,
        fontweight="bold",
    )
    eje.text(
        0,
        -0.17,
        "alumnos",
        ha="center",
        va="center",
        color=GRIS_TEXTO,
        fontsize=8,
    )
    leyenda = [
        f"{etiqueta}\n{valor} ({valor / sum(cantidades) * 100:.2f}%)"
        for etiqueta, valor in valores
    ]
    eje.legend(
        leyenda,
        loc="center left",
        bbox_to_anchor=(0.95, 0.5),
        frameon=False,
        labelcolor=GRIS_TEXTO,
        fontsize=8,
        handlelength=0.8,
        handletextpad=0.5,
        labelspacing=1.2,
    )
    eje.set_xlim(-1.3, 1.8)
    eje.set_ylim(-1.15, 1.15)
    eje.set_aspect("equal")
    figura.subplots_adjust(left=0.04, right=0.98, top=0.96, bottom=0.06)
    return figura


def crear_figura_genero(datos):
    return _crear_dona(
        [
            ("Hombres", datos.get("hombres", 0)),
            ("Mujeres", datos.get("mujeres", 0)),
        ],
        ["Hombres", "Mujeres"],
        [AZUL, ROSA],
        datos.get("total_alumnos", 0),
        "Sin datos de género",
    )


def crear_figura_semestre(datos):
    distribucion = sorted(
        datos.get("por_semestre", []),
        key=lambda elemento: elemento["semestre"],
    )
    if not distribucion:
        return _figura_vacia("Sin alumnos para los filtros seleccionados")

    figura = Figure(figsize=(6, 2.45), facecolor="white")
    eje = figura.subplots()
    etiquetas = [f"{item['semestre']}°" for item in distribucion]
    cantidades = [item["alumnos"] for item in distribucion]
    barras = eje.bar(
        range(len(distribucion)),
        cantidades,
        color=[
            COLORES_SEMESTRE[
                (int(item["semestre"]) - 1) % len(COLORES_SEMESTRE)
            ]
            for item in distribucion
        ],
        width=0.68,
        zorder=3,
    )
    eje.set_xticks(range(len(distribucion)), etiquetas)
    eje.set_ylabel("Alumnos", color=GRIS_TEXTO, fontsize=8)
    eje.margins(x=0.04, y=0.18)
    eje.bar_label(barras, padding=3, fontsize=8, color=GRIS_TEXTO)
    _preparar_eje(eje)
    figura.subplots_adjust(left=0.09, right=0.98, top=0.96, bottom=0.2)
    return figura


def crear_figura_turno(datos):
    distribucion = [
        (
            item["turno"].capitalize() if item["turno"] else "Sin turno",
            item["alumnos"],
        )
        for item in datos.get("por_turno", [])
    ]
    return _crear_dona(
        distribucion,
        ["Matutino", "Vespertino"],
        [AZUL, ROSA],
        datos.get("total_alumnos", 0),
        "Sin datos de turno",
    )
