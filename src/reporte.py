"""Reporte HTML de competencia local, con la plantilla del núcleo (reporte_base) y los textos de config.yaml."""
import re

import charts as C
import plantillas as PL
import reporte_base as RB


def _html(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def _cell(v, lo, hi):
    solid = lo > 0 or hi < 0
    return f"#{RB.pct(v, 2)}" if solid else f"#{v:+.2f}%".replace("-", "−")


def build(ef, rad, ty, cov, res, cfg, gallery, path):
    import plotly.graph_objects as go

    v = res
    d = ef.iloc[::-1]
    cols = [C.GREEN if lo > 0 else (C.RED if hi < 0 else C.NEUTRAL) for lo, hi in zip(d.ic90_inf, d.ic90_sup)]
    fig = go.Figure(go.Scatter(
        x=d.diferencia_pct, y=d.index, mode="markers", marker=dict(size=15, symbol="diamond", color=cols, line=dict(width=1, color=C.TEXT)),
        error_x=dict(type="data", symmetric=False, array=d.ic90_sup - d.diferencia_pct, arrayminus=d.diferencia_pct - d.ic90_inf,
                     color=C.AXIS, thickness=6, width=0),
        customdata=d[["ic90_inf", "ic90_sup"]].to_numpy(),
        hovertemplate="<b>%{y}</b><br>%{x:+.2f}% (IC90 %{customdata[0]:+.2f} a %{customdata[1]:+.2f})<extra></extra>", showlegend=False))
    fig.add_vline(0, line=dict(color=C.GOLD, width=1.5, dash="dash"))
    fig.update_layout(**RB.layout(height=420, margin=dict(l=220, r=40, t=100, b=60),
                                  title=RB.title("Tienda con competidor a 2 km frente a una sin competidor",
                                                 "Misma cadena y ciudad; barra: IC 90%; gris: no distinto de 0")),
                      xaxis=RB.axis(title="Diferencia en el índice de precio", ticksuffix="%", range=[-2.5, 2.5]),
                      yaxis=RB.axis(tickfont=dict(size=13, color=C.TEXT)))
    rows_r = [[f"<b>{R} km</b>", _cell(r_.diferencia_pct, r_.ic90_inf, r_.ic90_sup), f"#{r_.ic90_inf:+.2f} a {r_.ic90_sup:+.2f}".replace("-", "−"),
               f"#{int(r_.con)}", f"#{int(r_.sin)}"] for R, r_ in rad.iterrows()]
    t1 = RB.table(["Radio", "Diferencia", "IC90", "Con competidor", "Sin competidor"], rows_r)
    lab = {"walmex": "Walmart de México", "soriana": "Soriana", "chedraui": "Chedraui", "otro": "Otras cadenas"}
    rows_t = [[lab[k.split()[-1]], _cell(r_.diferencia_pct, r_.ic90_inf, r_.ic90_sup),
               f"#{r_.ic90_inf:+.2f} a {r_.ic90_sup:+.2f}".replace("-", "−")] for k, r_ in ty.iterrows()]
    t2 = RB.table(["Competidor a 2 km", "Diferencia", "IC90"], rows_t)
    c2 = cov[cov.radio_km == 2]
    rows_c = [[f"<b>{r_.grupo}</b>", f"#{r_.tiendas}", f"#{r_.con_competidor}", f"#{r_.sin_competidor}", f"#{r_.sin_en_ciudades_con_ambos}"]
              for _, r_ in c2.iterrows()]
    t3 = RB.table(["Grupo", "Tiendas", "Con competidor a 2 km", "Sin competidor", "Sin competidor en ciudades con ambos tipos"], rows_c)
    rep = cfg["reporte"]
    R_ = lambda t: _html(PL.render(t, v))
    ap = cfg["readme"]["hallazgos_apoyo"]
    html = RB.page(
        titulo=cfg["titulo"], descripcion=PL.render(rep["descripcion"], v), objetivo=R_(cfg["objetivo"]), h1=R_(rep["h1"]),
        intro=R_(rep["intro"]), stats=[(R_(s["valor"]), s.get("clase", ""), R_(s["texto"])) for s in rep["stats"]],
        secciones=[
            ("Con y sin <b>competidor</b>", R_(cfg["readme"]["hallazgo_principal"]), f"<div class='card'>{RB.fig_div(fig, 'efecto')}</div>"),
            ("¿Alcanzan los <b>datos</b>?", "Tiendas focales con coordenada confiable, a 2 km.", t3),
            ("Según el <b>radio</b>", R_(ap[0]), t1),
            ("Según el <b>competidor</b>", R_(ap[1]), t2),
            ("Por qué casi no se mueve", R_(ap[2]), ""),
            ("Lo que no resultó sólido", R_(cfg["readme"]["no_solido"]), ""),
        ],
        acciones=[(aud, " ".join(R_(a) for a in acc)) for aud, acc in cfg["readme"]["acciones"].items()],
        galeria=gallery, metodo=[R_(m) for m in rep["metodo"]])
    return RB.write(html, path)
