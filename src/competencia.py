"""Competencia local: índice de precio por tienda y diferencia entre tiendas con y sin competidor cercano.

- Índice de precio de la tienda = promedio, sobre sus SKUs, de log(precio de la tienda) − log(precio promedio del mismo SKU
  en las demás tiendas de supermercado del mismo municipio). Mismo producto y misma ciudad.
- Competidor = supermercado de otro grupo corporativo monitoreado por PROFECO, con coordenada confiable (coord_ok).
  «Sin competidor» = sin competidor monitoreado por PROFECO a esa distancia.
- Diferencia = coeficiente de «tiene competidor» en una regresión del índice con efectos fijos de municipio y de cadena
  (formato). IC90 por bootstrap de municipios, semilla 2026.
"""
import numpy as np
import pandas as pd

import entorno
import estadistica as E

CANAL = "Supermercado / Tienda de Autoservicio"
SEMILLA = 2026
FOCALES = ["Walmart de México", "Soriana", "Chedraui"]
EVALUABLES = ["Walmart de México", "Soriana"]   # Chedraui: casi no tiene tiendas sin competidor (plan aprobado)
RADIOS = [1, 2, 3]
RADIO = 2
MIN_SIN = 10            # tiendas sin competidor (en ciudades con ambos tipos) para estimar el efecto de un grupo
TIPOS = {"Walmart de México": "walmex", "Soriana": "soriana", "Chedraui": "chedraui"}


def load():
    st = entorno.tabla("tiendas")
    st = st[st.giro == CANAL].copy()
    pts = entorno.tabla("precio_tienda_sku", columns=["establecimiento_id", "sku_id", "precio"])
    pts = pts[pts.establecimiento_id.isin(st.establecimiento_id)].reset_index(drop=True)
    return pts, st


def store_index(pts, st):
    """Índice por tienda frente a las demás tiendas del municipio (mismo SKU). Solo celdas SKU–municipio con 2+ tiendas;
    el promedio de comparación excluye a la propia tienda."""
    x = pts.merge(st[["establecimiento_id", "municipio_id"]], on="establecimiento_id")
    x["lp"] = np.log(x.precio)
    g = x.groupby(["sku_id", "municipio_id"]).lp
    n, s = g.transform("size"), g.transform("sum")
    x = x[n >= 2].copy()
    x["dev"] = x.lp - (s[n >= 2] - x.lp) / (n[n >= 2] - 1)
    return x.groupby("establecimiento_id").agg(indice=("dev", "mean"), skus=("dev", "size")).reset_index()


def _hav(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def focal_stores(st, idx):
    """Tiendas focales con coordenada confiable, distancia al competidor más cercano (total y por grupo) e índice."""
    ok = st[st.coord_ok].copy()
    foc = ok[ok.grupo.isin(FOCALES)].copy()
    other_groups = {g: "otro" for g in ok.grupo.unique()}
    other_groups.update({g: TIPOS[g] for g in TIPOS})
    ok["tipo"] = ok.grupo.map(other_groups)
    rows = []
    for _, f in foc.iterrows():
        d = _hav(f.lat, f.lon, ok.lat.to_numpy(), ok.lon.to_numpy())
        comp = ok.grupo.to_numpy() != f.grupo
        r = {"establecimiento_id": f.establecimiento_id, "dmin": d[comp].min()}
        for t in ["walmex", "soriana", "chedraui", "otro"]:
            m = comp & (ok.tipo.to_numpy() == t)
            r[f"d_{t}"] = d[m].min() if m.any() else np.inf
        for R in RADIOS:
            r[f"n_{R}km"] = int((comp & (d <= R)).sum())
        rows.append(r)
    out = foc.merge(pd.DataFrame(rows), on="establecimiento_id").merge(idx, on="establecimiento_id", how="inner")
    return out


def coverage(foc):
    rows = []
    for R in RADIOS:
        c = foc.dmin <= R
        by = pd.DataFrame({"c": c, "m": foc.municipio_id}).groupby("m").c.agg(["sum", "size"])
        both = by[(by["sum"] > 0) & (by["sum"] < by["size"])].index
        for g_ in FOCALES + ["Total"]:
            s = foc if g_ == "Total" else foc[foc.grupo == g_]
            cs = s.dmin <= R
            rows.append({"radio_km": R, "grupo": g_, "tiendas": len(s), "con_competidor": int(cs.sum()),
                         "sin_competidor": int((~cs).sum()),
                         "sin_en_ciudades_con_ambos": int(((~cs) & s.municipio_id.isin(both)).sum()),
                         "ciudades_con_ambos": len(both) if g_ == "Total" else s[s.municipio_id.isin(both)].municipio_id.nunique()})
    return pd.DataFrame(rows)


def _X(d, terms):
    X = pd.get_dummies(d[["municipio_id", "formato"]].astype(str), drop_first=True, dtype=float)
    for k, v in terms.items():
        X[k] = v
    X.insert(0, "constante", 1.0)
    return X


def fit(d, terms_fn):
    terms = terms_fn(d)
    X = _X(d, terms)
    b = np.linalg.lstsq(X.to_numpy(), d.indice.to_numpy(), rcond=None)[0]
    return pd.Series(b, X.columns)[list(terms)]


def estimate(d, terms_fn, reps=500, seed=SEMILLA):
    """Coeficientes (en %, como diferencia del índice) con IC90 por bootstrap de municipios."""
    est = fit(d, terms_fn)
    (lo, hi), _ = E.bootstrap_municipios(d.reset_index(drop=True), lambda z: fit(z, terms_fn).reindex(est.index).to_numpy(),
                                         reps=reps, seed=seed)
    pct = lambda v: (np.exp(np.asarray(v, float)) - 1) * 100
    out = pd.DataFrame({"diferencia_pct": pct(est), "ic90_inf": pct(lo), "ic90_sup": pct(hi)}, index=est.index)
    out["solido"] = (out.ic90_inf > 0) | (out.ic90_sup < 0)
    return out


def comp(R=RADIO):
    return lambda d: {"competidor": (d.dmin <= R).astype(float)}


def comp_by_group(R=RADIO, groups=EVALUABLES):
    return lambda d: {f"competidor · {g_}": ((d.dmin <= R) & (d.grupo == g_)).astype(float) for g_ in groups}


def comp_by_type(R=RADIO):
    return lambda d: {f"competidor {t}": (d[f"d_{t}"] <= R).astype(float) for t in ["walmex", "soriana", "chedraui", "otro"]
                      if (d[f"d_{t}"] <= R).any()}


def distance_term():
    """Log de la distancia al competidor más cercano (topado en 0.2 y 10 km)."""
    return lambda d: {"log_distancia": np.log(d.dmin.clip(0.2, 10))}
