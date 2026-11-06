"""Verificación independiente: recalcula la diferencia principal solo con pandas y numpy a partir de los precios
originales y de la tabla de tiendas (con la bandera de coordenadas), sin usar los módulos de src/, y comprueba que
coincide con el README y con data/processed/resultados.json."""
from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data/processed"
README = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
RES = json.loads((PROC / "resultados.json").read_text(encoding="utf-8"))
src = PROC / "profeco_extracto.parquet"
if not src.exists():
    src = ROOT.parent / "_profeco_core/data/profeco_2026_08_q2.parquet"
tsrc = PROC / "tablas/tiendas.parquet"
if not tsrc.exists():
    tsrc = ROOT.parent / "_profeco_core/data/tiendas.parquet"
CANAL = "Supermercado / Tienda de Autoservicio"
st = pd.read_parquet(tsrc)
st = st[st.giro == CANAL]
df = pd.read_parquet(src, columns=["precio_num", "giro", "sku_id", "establecimiento_id"])
df = df[(df.precio_num > 0) & (df.giro.astype(str) == CANAL)]

# Precio de tienda (mediana de la quincena) e índice frente a las otras tiendas del municipio
p = df.groupby(["establecimiento_id", "sku_id"]).precio_num.median().reset_index()
p = p.merge(st[["establecimiento_id", "municipio_id"]], on="establecimiento_id")
p["lp"] = np.log(p.precio_num)
g = p.groupby(["sku_id", "municipio_id"]).lp
n, s = g.transform("size"), g.transform("sum")
p = p[n >= 2].assign(dev=lambda z: z.lp - (s[n >= 2] - z.lp) / (n[n >= 2] - 1))
idx = p.groupby("establecimiento_id").dev.mean()

# Distancia al supermercado de otro grupo más cercano (coordenada confiable)
ok = st[st.coord_ok]
foc = ok[ok.grupo.isin(["Walmart de México", "Soriana"])].copy()
la2, lo2 = np.radians(ok.lat.to_numpy()), np.radians(ok.lon.to_numpy())
dmin = []
for la, lo, gr in zip(np.radians(foc.lat), np.radians(foc.lon), foc.grupo):
    a = np.sin((la2 - la) / 2) ** 2 + np.cos(la) * np.cos(la2) * np.sin((lo2 - lo) / 2) ** 2
    d = 6371 * 2 * np.arcsin(np.sqrt(a))
    dmin.append(d[ok.grupo.to_numpy() != gr].min())
foc["dmin"] = dmin
foc = foc.merge(idx.rename("indice"), left_on="establecimiento_id", right_index=True)

# Regresión con efectos fijos de municipio y formato
X = pd.get_dummies(foc[["municipio_id", "formato"]].astype(str), drop_first=True, dtype=float)
X["competidor"] = (foc.dmin <= 2).astype(float).to_numpy()
X.insert(0, "constante", 1.0)
beta = np.linalg.lstsq(X.to_numpy(), foc.indice.to_numpy(), rcond=None)[0]
ef = (np.exp(beta[-1]) - 1) * 100
txt = f"precio es {ef:+.2f}%".replace("-", "−")
assert abs(ef - RES["ef_total"]["cifra"]) < 1e-6, (ef, RES["ef_total"]["cifra"])
assert len(foc) == RES["tiendas_ev"]["cifra"], (len(foc), RES["tiendas_ev"]["cifra"])
assert txt in README, f"«{txt}» no aparece en el README"
print(f"OK  diferencia a 2 km            {txt} ({len(foc)} tiendas)")
assert "sin competidor monitoreado por PROFECO" in README and "no causalidad" in README.lower().replace("correlación, ", "")
print("OK  limitación «sin competidor monitoreado por PROFECO» y aviso de correlación visibles")

for nb_path in sorted((ROOT / "notebooks").glob("0*.ipynb")):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is not None, f"{nb_path.name} sin ejecutar"
            assert not any(o["output_type"] == "error" for o in cell["outputs"]), nb_path.name
for f in ["outputs/charts/01_efecto_por_cadena.png", "outputs/charts/01_efecto_por_cadena.svg",
          "outputs/social/01_efecto_cadena_1280x720.png", "outputs/social/01_efecto_cadena_1080x1350.png",
          "outputs/charts/02_efecto_por_radio.png", "outputs/charts/03_efecto_por_tipo.png",
          "outputs/charts/04_indice_vs_distancia.png", "docs/index.html", "data/metadata/manifiesto_insumos.json"]:
    assert (ROOT / f).exists(), f"Falta {f}"
assert "elaboración propia con datos de PROFECO" in README
assert "URL oficial" in README
print("Verificación correcta: la cifra clave del README se reproduce de forma independiente "
      "y los notebooks 00–05 se ejecutaron sin errores.")
