"""Gráficas de competencia local con la plantilla del núcleo (charts.py).

Convenciones: verde ▲ = la tienda con competidor cerca cobra más; rojo ▼ = cobra menos; gris = no distinta de cero
(el intervalo cruza 0); dorado = referencia (sin competidor cerca = 0).
"""
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator, FixedLocator, NullFormatter
from matplotlib.transforms import blended_transform_factory

import charts as C
from charts import n, b, g, r, minus, _box, _finish, _canvas, _frame, _save

SRC_K = C.SRC + ". «Sin competidor» = sin competidor monitoreado por PROFECO."
GROUP_COLOR = {"Walmart de México": "#5b8fd6", "Soriana": C.SAND}


def gold(t):
    return (t, True, C.GOLD)


def _col(lo, hi):
    return C.GREEN if lo > 0 else (C.RED if hi < 0 else C.NEUTRAL)


def _txt(v, lo, hi, dec=2):
    solid = lo > 0 or hi < 0
    if not solid:
        return minus(f"{v:+.{dec}f}%"), C.TEXT2
    return minus(f"{'▲' if v > 0 else '▼'} {v:+.{dec}f}%"), (C.GREEN_T if v > 0 else C.RED_T)


def _rows(fig, ax, rows, L, xlim, xlabel, dec=2):
    tr = blended_transform_factory(fig.transFigure, ax.transData)
    for i, rw in enumerate(rows):
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.015, i - 0.5), 0.97, 1, transform=tr, color=C.ZEBRA, lw=0, zorder=0))
        ax.text(L - 0.012, i - 0.13, rw["label"], transform=tr, ha="right", va="center", fontsize=8.4, fontweight="bold",
                color=rw.get("color", C.TEXT))
        ax.text(L - 0.012, i + 0.24, rw["sub"], transform=tr, ha="right", va="center", fontsize=6.4, color=C.TEXT2)
        if rw.get("v") is None:
            ax.text(0, i, rw.get("nota", "no evaluable"), ha="center", va="center", fontsize=7.4, color=C.TEXT2, fontstyle="italic")
            continue
        col = _col(rw["lo"], rw["hi"])
        ax.hlines(i, rw["lo"], rw["hi"], color=col, lw=9, alpha=0.45, zorder=2)
        ax.scatter([rw["v"]], [i], s=150, marker="D", color=col, edgecolor=C.TEXT, lw=1, zorder=3)
        t, tc = _txt(rw["v"], rw["lo"], rw["hi"], dec)
        ax.text(0.79, i - 0.1, t, transform=tr, ha="left", va="center", fontsize=8.6, fontweight="bold", color=tc)
        ax.text(0.79, i + 0.25, minus(f"IC90 {rw['lo']:+.{dec}f} a {rw['hi']:+.{dec}f}") + ("" if col != C.NEUTRAL else " · no distinto de 0"),
                transform=tr, ha="left", va="center", fontsize=6.4, color=C.TEXT2)
    ax.axvline(0, color=C.GOLD, lw=1.3, ls=(0, (4, 3)), zorder=1)
    ax.set(xlim=xlim, ylim=(len(rows) - 0.5, -0.5), yticks=[])
    _frame(ax, grid="x", size=7.2)
    ax.xaxis.set_major_formatter(lambda x, _: "0" if abs(x) < 1e-9 else minus(f"{x:+.1f}%"))
    ax.set_xlabel(xlabel, fontsize=7.4, labelpad=5)


# --------------------------------------------------------------------------- 01 principal
def effect_by_group(ef, rad, res, path, svg=True):
    v = res
    rows = [dict(label="Walmart de México y Soriana", sub=f"{v['tiendas_ev']:.0f} tiendas · {v['tiendas_ev'] - v['radio_2km_sin']:.0f} con y {v['radio_2km_sin']:.0f} sin competidor",
                 v=v["ef_total"], lo=v["ef_total_inf"], hi=v["ef_total_sup"]),
            dict(label="Walmart de México", sub=f"{v['con_walmex_2km']:.0f} con y {v['sin_walmex_2km']:.0f} sin competidor",
                 v=v["ef_walmex"], lo=v["ef_walmex_inf"], hi=v["ef_walmex_sup"], color=GROUP_COLOR["Walmart de México"]),
            dict(label="Soriana", sub=f"{v['con_soriana_2km']:.0f} con y {v['sin_soriana_2km']:.0f} sin competidor",
                 v=v["ef_soriana"], lo=v["ef_soriana_inf"], hi=v["ef_soriana_sup"], color=GROUP_COLOR["Soriana"]),
            dict(label="Chedraui", sub=f"{v['con_chedraui_2km']:.0f} con y solo {v['sin_chedraui_2km']:.0f} sin competidor",
                 v=None, nota="no evaluable: casi no tiene tiendas sin competidor")]
    k = len(rows)
    fig = _canvas(2000, 1250)
    L = 0.27
    ax = fig.add_axes([L, 0.15, 0.48, 0.5])
    ax.patch.set_alpha(0)
    _rows(fig, ax, rows, L, (-2.5, 2.5), "Índice de precio de la tienda con competidor a 2 km o menos, frente a una de la misma cadena y ciudad sin competidor")
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    _box(fig, 0.03, 0.80, [[b("¿Cómo leer?  "), b("◆"), n(" cuánto más (o menos) cobra en promedio una tienda con competidor de otra cadena a 2 km o menos,")],
                           [n("frente a una de la misma cadena y ciudad sin competidor; barra: rango probable (IC 90%); gris: no distinto de 0.")],
                           [b("Sin competidor = sin competidor monitoreado por PROFECO."), n(" Es correlación, no causalidad: las tiendas no se ubican al azar.")]],
         "ul", size=7.4)
    _finish(fig, [[n("Una tienda con competidor a menos de 2 km no es más barata: su índice es "), b(minus(f"{v['ef_total']:+.2f}%"))],
                  [n("(IC90 "), b(minus(f"{v['ef_total_inf']:+.2f} a {v['ef_total_sup']:+.2f}")),
                   n(") frente a una de la misma cadena y ciudad sin competidor cerca")]],
            "Diferencia en el índice de precio entre tiendas con y sin competidor de otra cadena a 2 km, con efectos fijos de ciudad y "
            "cadena; IC90 por bootstrap de municipios",
            [n(SRC_K)], size=12.5, foot=6.0, top=1 - 26 / 1250)
    return _save(fig, path, svg)


def effect_social(ef, res, fmt, path):
    v = res
    rows = [("Walmart de México\ny Soriana", v["ef_total"], v["ef_total_inf"], v["ef_total_sup"]),
            ("Walmart de México", v["ef_walmex"], v["ef_walmex_inf"], v["ef_walmex_sup"]),
            ("Soriana", v["ef_soriana"], v["ef_soriana_inf"], v["ef_soriana_sup"])]
    fig = C.social_canvas(fmt)
    W, H = C.SOCIAL[fmt]
    vertical = H > W
    top = (360 if vertical else 210) / H
    bot = (170 if vertical else 140) / H
    L = 0.34 if vertical else 0.26
    ax = fig.add_axes([L, bot, 0.92 - L, 1 - top - bot])
    for i, (lab, e, lo, hi) in enumerate(rows):
        col = _col(lo, hi)
        ax.hlines(i, lo, hi, color=col, lw=9, alpha=0.5)
        ax.scatter([e], [i], s=130, marker="D", color=col, edgecolor=C.TEXT, lw=0.8, zorder=3)
        ax.text(e, i - 0.28, minus(f"{e:+.2f}%"), ha="center", va="bottom", fontsize=7.2, fontweight="bold", color=C.TEXT2)
        ax.text(-0.03, i, lab, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=7.2, fontweight="bold",
                linespacing=1.1)
    ax.axvline(0, color=C.GOLD, lw=1.2, ls=(0, (4, 3)))
    ax.set(xlim=(-2.5, 2.5), ylim=(2.6, -0.7), yticks=[])
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.xaxis.set_major_formatter(lambda x, _: "sin\ncompetidor" if abs(x) < 1e-9 else minus(f"{x:+.0f}%"))
    _frame(ax, grid="x", size=6.2)
    ax.set_xlabel("Índice de la tienda con competidor a 2 km frente a una sin competidor", fontsize=6.4)
    if vertical:
        title = [[n("¿Un competidor a 2 km baja")], [n("tus precios? En el anaquel, no:")],
                 [b(minus(f"{v['ef_total']:+.2f}%")), n(", no distinto de 0")]]
        sub = "Misma cadena y ciudad; sin competidor = sin competidor monitoreado por PROFECO"
    else:
        title = [[n("Una tienda con competidor a menos de 2 km no es más barata:")],
                 [n("su índice es "), b(minus(f"{v['ef_total']:+.2f}%")), n(" frente a una sin competidor (no distinto de 0)")]]
        sub = "Misma cadena y ciudad; gris: no distinto de 0; sin competidor = sin competidor monitoreado por PROFECO; 16–31 ago 2026"
    C.finish_social(fig, title, sub, [n("Fuente: elaboración propia con datos de PROFECO, Quién es Quién en los Precios. Correlación, no causalidad.")],
                    size=13 if vertical else 11, foot=5.4)
    fig.savefig(path, dpi=fig.dpi)
    return fig


# --------------------------------------------------------------------------- 02 radio
def by_radius(rad, res, path):
    v = res
    rows = [dict(label=f"A {R} km o menos", sub=f"{int(rr.con)} con y {int(rr.sin)} sin competidor", v=rr.diferencia_pct,
                 lo=rr.ic90_inf, hi=rr.ic90_sup) for R, rr in rad.iterrows()]
    fig = _canvas(2000, 1100)
    L = 0.27
    ax = fig.add_axes([L, 0.16, 0.48, 0.46])
    ax.patch.set_alpha(0)
    _rows(fig, ax, rows, L, (-1.5, 3.5), "Índice de la tienda con competidor dentro del radio, frente a una sin competidor (misma cadena y ciudad)")
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    _box(fig, 0.03, 0.80, [[b("¿Cómo leer?  "), n("Misma comparación con tres definiciones de «cerca». "), g("▲ verde"),
                            n(": la tienda con competidor cobra más; gris: no distinto de 0.")],
                           [n("A 3 km casi no quedan tiendas sin competidor.")],
                           [n(f"Distancia continua: duplicar la distancia al competidor más cercano se asocia con "),
                            b(minus(f"{v['duplicar_distancia']:+.2f}%")), n(" en el índice.")]], "ul", size=7.4)
    _finish(fig, [[n("Con ningún radio aparece un descuento por competencia: "), b(minus(f"{v['radio_1km']:+.2f}%")), n(" a 1 km, "),
                   b(minus(f"{v['radio_2km']:+.2f}%")), n(" a 2 km")],
                  [n("y "), b(minus(f"{v['radio_3km']:+.2f}%")), n(f" a 3 km, este último con solo {v['radio_3km_sin']:.0f} tiendas sin competidor")]],
            "Diferencia en el índice de precio según el radio que define «competidor cercano»; Walmart de México y Soriana; IC90 por bootstrap de municipios",
            [n(SRC_K)], size=12.5, foot=6.0, top=1 - 26 / 1100)
    return _save(fig, path)


# --------------------------------------------------------------------------- 03 tipo de competidor
def by_type(ty, ev, res, path):
    lab = {"walmex": "Walmart de México", "soriana": "Soriana", "chedraui": "Chedraui", "otro": "Otras cadenas"}
    rows = []
    for k_, rr in ty.iterrows():
        t_ = k_.split()[-1]
        rows.append(dict(label=f"Competidor {lab[t_]}", sub=f"{int((ev[f'd_{t_}'] <= 2).sum())} tiendas lo tienen a 2 km",
                         v=rr.diferencia_pct, lo=rr.ic90_inf, hi=rr.ic90_sup))
    fig = _canvas(2000, 1150)
    L = 0.27
    ax = fig.add_axes([L, 0.15, 0.48, 0.5])
    ax.patch.set_alpha(0)
    _rows(fig, ax, rows, L, (-2, 2.5), "Índice de la tienda con ese tipo de competidor a 2 km, frente a una sin él (misma cadena y ciudad)")
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    _box(fig, 0.03, 0.80, [[b("¿Cómo leer?  "), n("Cada fila: diferencia asociada a tener ese tipo de competidor a 2 km (una tienda puede tener varios). "
                                                 "Gris: no distinto de 0.")]], "ul", size=7.4)
    v = res
    _finish(fig, [[n("Ningún tipo de competidor se asocia con precios más bajos:")],
                  [n("frente a Chedraui, "), b(minus(f"{v['tipo_chedraui']:+.2f}%")), n(" (no distinto de 0); frente a otras cadenas, "),
                   g(minus(f"▲ {v['tipo_otro']:+.2f}%"))]],
            "Diferencia en el índice de precio según el grupo del competidor a 2 km; Walmart de México y Soriana; IC90 por bootstrap de municipios",
            [n(SRC_K)], size=12.5, foot=6.0, top=1 - 26 / 1150)
    return _save(fig, path)


# --------------------------------------------------------------------------- 04 índice vs. distancia
def index_vs_distance(ev, res, path):
    d = ev.copy()
    d["resid"] = (d.indice - d.groupby(["municipio_id", "formato"]).indice.transform("mean")) * 100
    d = d[d.groupby(["municipio_id", "formato"]).indice.transform("size") >= 2]
    fig = _canvas(2000, 1200)
    ax = fig.add_axes([0.1, 0.15, 0.6, 0.55])
    for g_, s in d.groupby("grupo"):
        ax.scatter(s.dmin.clip(0.05, 15), s.resid, s=40, color=GROUP_COLOR[g_], alpha=0.75, lw=0, zorder=3, label=g_)
    bins = [0.05, 0.5, 1, 2, 3, 5, 15]
    d["bin"] = pd.cut(d.dmin.clip(0.05, 15), bins, include_lowest=True)
    med = d.groupby("bin", observed=True).agg(x=("dmin", "median"), y=("resid", "median"), n=("resid", "size"))
    ax.plot(med.x, med.y, color=C.TEXT, lw=2.2, marker="o", ms=6, zorder=4)
    for _, m_ in med.iterrows():
        ax.text(m_.x, m_.y + 0.35, f"{int(m_.n)}", ha="center", va="bottom", fontsize=6.2, color=C.TEXT2, path_effects=C.HALO)
    ax.axvline(2, color=C.GOLD, lw=1.3, ls=(0, (4, 3)), zorder=2)
    ax.axhline(0, color=C.AXIS, lw=0.8, zorder=1)
    ax.text(2.1, 2.2, "2 km", color=C.GOLD, fontsize=7.2, fontweight="bold")
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator([0.1, 0.25, 0.5, 1, 2, 5, 10]))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:g} km")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set(ylim=(-2.5, 2.5))
    ax.yaxis.set_major_formatter(lambda x, _: "promedio" if abs(x) < 1e-9 else minus(f"{x:+.0f}%"))
    _frame(ax, grid="both", size=7.2)
    ax.set_xlabel("Distancia al competidor de otra cadena más cercano (escala logarítmica)", fontsize=7.4, labelpad=5)
    ax.set_ylabel("Índice vs. su formato y ciudad", fontsize=7.2, labelpad=5)
    v = res
    _box(fig, 0.73, 0.67, [b("¿Cómo leer?"), "Cada punto: una sucursal, comparada con",
                           "las del mismo formato y ciudad.", "Línea blanca: mediana por tramo de distancia",
                           "(número de sucursales encima).",
                           [("■ ", True, GROUP_COLOR["Walmart de México"]), n("Walmart de México")],
                           [("■ ", True, GROUP_COLOR["Soriana"]), n("Soriana")]], "ul", size=7.4)
    _finish(fig, [[n("El precio de una sucursal casi no cambia con la distancia a su competidor más cercano:")],
                  [n("duplicar esa distancia se asocia con "), b(minus(f"{v['duplicar_distancia']:+.2f}%")), n(" en el índice")]],
            "Índice de precio de cada sucursal frente a las de su mismo formato y ciudad, según la distancia al competidor más cercano",
            [n(SRC_K)], size=12.5, foot=6.0, top=1 - 26 / 1200)
    return _save(fig, path)
