"""Genera los notebooks del proyecto. Después ejecutarlos en orden 00→05 (ver README)."""
from pathlib import Path
import nbformat as nbf
import yaml

root = Path(__file__).resolve().parent
CFG = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
OBJ = CFG.get("objetivo", "")
KERNEL = {"display_name": "Python 3", "language": "python", "name": "python3"}
SETUP = """import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
import entorno
entorno.setup()
import profeco, tablas, estadistica as E, charts as C
import competencia as K
PROC, META, CHARTS, SOCIAL = entorno.PROC, entorno.META, entorno.CHARTS, entorno.SOCIAL
CFG = entorno.config()
reg = entorno.registrar
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 80)
REPS = 500
"""
LOAD = """foc = pd.read_csv(PROC / "tiendas_focales.csv")
ev = foc[foc.grupo.isin(K.EVALUABLES)].copy()
"""


def write(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    nb.metadata.kernelspec = KERNEL
    (root / "notebooks").mkdir(exist_ok=True)
    nbf.write(nb, root / "notebooks" / name)


def head(num, title, question, why):
    return ("md", f"# {num} · {title}\n\n**Objetivo:** {OBJ}\n\n**Pregunta:** {question}\n\n{why}")


# --------------------------------------------------------------------------- 00
write("00_validacion_y_datos.ipynb", [
    head("00", "Validación de coordenadas, cobertura e índice por tienda", CFG.get("pregunta", ""),
         """Este notebook responde, antes de cualquier estimación: ¿cuántas tiendas tienen coordenadas confiables y hay
suficientes tiendas **con y sin** competidor cercano **en la misma ciudad**? Si no alcanzara, el análisis se detendría
aquí. Cierra con la tabla de decisiones metodológicas (plan aprobado en `_specs/plan_metodologico_6_12.md`).

**«Sin competidor cerca» significa «sin competidor monitoreado por PROFECO cerca».** Puede haber una tienda que PROFECO
no visita a 500 metros. Y es correlación, no causalidad: las cadenas no abren tiendas al azar."""),
    ("code", SETUP + """raw = entorno.load_raw()
manifest = entorno.write_manifest(raw)
pts, st = K.load()
allst = entorno.tabla("tiendas")
print(f"Tiendas en el archivo: {len(allst):,} · con coordenada confiable: {allst.coord_ok.sum():,}")
display(allst.coord_motivo.replace("", "confiable").value_counts().to_frame("tiendas"))
print(f"Supermercados: {len(st)} · con coordenada confiable: {st.coord_ok.sum()}")"""),
    ("md", """## 1. Coordenadas

**Decisión:** usar solo tiendas con `coord_ok` (tabla común `tiendas`). La bandera descarta, sin borrar del archivo, las
tiendas sin coordenada, fuera de México, con coordenada que cambia entre visitas, compartida con otra tienda (señal de
que se geocodificó al centro de la ciudad) o a más de 30 km de su municipio. Alternativa descartada: corregir
coordenadas a mano, porque sería inventar ubicaciones."""),
    ("code", """idx = K.store_index(pts, st)
foc = K.focal_stores(st, idx)
print(f"Tiendas focales (Walmart de México, Soriana y Chedraui) con coordenada confiable e índice: {len(foc)}")
cov = K.coverage(foc)
display(cov)"""),
    ("md", """## 2. ¿Alcanzan los datos?

Para comparar dentro de la misma ciudad se necesitan ciudades con tiendas de los dos tipos.
- **A 2 km** hay 29 ciudades así. Walmart de México y Soriana tienen tiendas sin competidor en esas ciudades.
- **Chedraui** casi no tiene tiendas sin competidor (2 en esas ciudades): **no se estima su efecto**, como preveía el
  plan. Sus tiendas entran a la regresión, pero solo para ayudar a estimar el nivel de cada ciudad.
- **A 3 km** casi no quedan tiendas sin competidor: ese radio es solo sensibilidad, con poca potencia.

**Los datos alcanzan para Walmart de México y Soriana, con intervalos que pueden ser amplios.**"""),
    ("md", """## 3. Índice de precio de cada tienda

**Decisión:** índice = promedio, sobre todos los SKUs de la tienda, de log(precio de la tienda / precio promedio del
mismo SKU en las otras tiendas de supermercado del municipio). Así se compara la tienda con su ciudad usando sus
propios productos (la canasta que comparte con su ciudad). Alternativa descartada: índice contra la mediana nacional,
porque mezclaría ciudad y competencia."""),
    ("code", """display(foc.groupby("grupo")[["skus", "indice"]].describe().round(3))
foc.to_csv(PROC / "tiendas_focales.csv", index=False, encoding="utf-8-sig")
cov.to_csv(PROC / "cobertura_por_radio.csv", index=False, encoding="utf-8-sig")
params = {"semilla": K.SEMILLA, "bootstrap_replicas": REPS, "canal": K.CANAL, "focales": K.FOCALES,
          "evaluables": K.EVALUABLES, "radios_km": K.RADIOS, "radio_principal_km": K.RADIO, "min_sin": K.MIN_SIN}
_ = (META / "parametros.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
F = "00_validacion_y_datos"
reg("tiendas_total", len(allst), fuente=F); reg("coord_ok_total", allst.coord_ok.sum(), fuente=F)
reg("super_total", len(st), fuente=F); reg("super_coord_ok", st.coord_ok.sum(), fuente=F)
reg("focales", len(foc), fuente=F); reg("skus_mediana", foc.skus.median(), fuente=F)
for _, r_ in cov.iterrows():
    k = f"{K.TIPOS.get(r_.grupo, 'total')}_{r_.radio_km}km"
    reg(f"con_{k}", r_.con_competidor, fuente=F); reg(f"sin_{k}", r_.sin_competidor, fuente=F)
    reg(f"sinamb_{k}", r_.sin_en_ciudades_con_ambos, fuente=F); reg(f"ciud_{k}", r_.ciudades_con_ambos, fuente=F)"""),
    ("md", "## 4. Decisiones metodológicas"),
    ("code", """display(Markdown(f'''
| # | Decisión | Propuesta | Por qué | Alternativas descartadas |
|---|---|---|---|---|
| 1 | Ubicación | solo `coord_ok` ({st.coord_ok.sum()} de {len(st)} supermercados) | coordenadas compartidas o lejanas no ubican la tienda | corregir coordenadas a mano |
| 2 | Competidor | supermercado de otro grupo monitoreado por PROFECO, a 2 km o menos (sensibilidad 1 y 3 km) | lo que el archivo permite observar | contar tiendas no monitoreadas (no hay datos) |
| 3 | Índice por tienda | promedio de log(precio / promedio del mismo SKU en las otras tiendas del municipio) | mismo producto, misma ciudad | índice contra la mediana nacional |
| 4 | Comparación | regresión del índice con efectos fijos de municipio y cadena (formato) | compara tiendas de la misma cadena en la misma ciudad | comparar tiendas de ciudades distintas |
| 5 | Grupos | Walmart de México y Soriana; Chedraui no evaluable (casi sin tiendas sin competidor) | sin tiendas de los dos tipos no hay comparación | forzar una cifra para Chedraui |
| 6 | Incertidumbre | IC90 por bootstrap de municipios, 500 réplicas, semilla 2026 | las tiendas de una ciudad no son independientes | errores por tienda |
| 7 | Variantes | tipo de competidor, radio de 1, 2 y 3 km, distancia continua | ¿quién compite y a qué distancia importa? | — |
| — | Alcance | correlación, no causalidad; «sin competidor» = sin competidor monitoreado | las tiendas no se ubican al azar | afirmar que la competencia baja precios |
'''))"""),
    ("code", """c2 = cov[(cov.radio_km == 2)].set_index("grupo")
display(Markdown(
    f"**Conclusión.** Hay {len(foc)} tiendas focales con coordenada confiable e índice. A 2 km, {c2.loc['Total', 'con_competidor']} tienen competidor "
    f"y {c2.loc['Total', 'sin_competidor']} no; {c2.loc['Total', 'ciudades_con_ambos']} ciudades tienen tiendas de los dos tipos. Alcanza para "
    f"Walmart de México ({c2.loc['Walmart de México', 'sin_en_ciudades_con_ambos']} tiendas sin competidor en esas ciudades) y Soriana "
    f"({c2.loc['Soriana', 'sin_en_ciudades_con_ambos']}); no para Chedraui ({c2.loc['Chedraui', 'sin_en_ciudades_con_ambos']})."))"""),
])

# --------------------------------------------------------------------------- 01
write("01_efecto_a_2km.ipynb", [
    head("01", "¿Una tienda con competidor a 2 km tiene precios distintos?",
         "Con la misma cadena y en la misma ciudad, ¿cuánto difiere el índice de precio de las tiendas con y sin competidor a 2 km?",
         """Importa porque decide si conviene fijar precios por tienda según la competencia local o mantener un precio por
zona. **Diferencia** = cuánto más (o menos) cobra, en promedio, una tienda con competidor cerca que otra de la misma cadena
y ciudad sin competidor. IC90 = rango probable (bootstrap de ciudades)."""),
    ("code", SETUP + LOAD + """tot = K.estimate(ev, K.comp(), reps=REPS)
byg = K.estimate(ev, K.comp_by_group(), reps=REPS)
res_ = pd.concat([tot.rename(index={"competidor": "Walmart de México y Soriana"}),
                  byg.rename(index=lambda s: s.split(" · ")[1])])
display(res_.round(2))
for k_, r_ in res_.iterrows():
    assert r_.ic90_inf <= r_.diferencia_pct <= r_.ic90_sup, k_"""),
    ("md", """## Sensibilidad

- incluir las tiendas de Chedraui en la regresión (su efecto no se reporta);
- solo tiendas con 300 SKUs o más en el índice;
- solo ciudades con tiendas de los dos tipos;
- controlar por grupo corporativo en lugar de formato."""),
    ("code", """both = ev.groupby("municipio_id").apply(lambda z: (z.dmin <= 2).any() and (z.dmin > 2).any(), include_groups=False)
var = {"Principal": ev, "Con Chedraui en la regresión": foc, "Tiendas con 300+ SKUs": ev[ev.skus >= 300],
       "Solo ciudades con ambos tipos": ev[ev.municipio_id.isin(both[both].index)],
       "Efecto fijo de grupo": ev.assign(formato=ev.grupo)}
sens = pd.DataFrame({k: K.estimate(v, K.comp(), reps=200).iloc[0] for k, v in var.items()}).T
sens["tiendas"] = [len(v) for v in var.values()]
display(sens.round(2))"""),
    ("code", """res_.to_csv(PROC / "efecto_2km.csv", encoding="utf-8-sig")
sens.to_csv(PROC / "sensibilidad_2km.csv", encoding="utf-8-sig")
F = "01_efecto_a_2km"
for k_, kk in {"Walmart de México y Soriana": "total", "Walmart de México": "walmex", "Soriana": "soriana"}.items():
    r_ = res_.loc[k_]
    reg(f"ef_{kk}", r_.diferencia_pct, [r_.ic90_inf, r_.ic90_sup], n=len(ev) if kk == "total" else (ev.grupo == k_).sum(), fuente=F)
reg("sens_min", sens.diferencia_pct.min(), fuente=F); reg("sens_max", sens.diferencia_pct.max(), fuente=F)
reg("sens_solidas", int(sens.solido.sum()), n=len(sens), fuente=F)
reg("tiendas_ev", len(ev), fuente=F)
t = res_.loc["Walmart de México y Soriana"]
display(Markdown(
    f"**Conclusión.** Con la misma cadena y en la misma ciudad, una tienda con competidor a 2 km o menos tiene un índice **{t.diferencia_pct:+.2f}%** "
    f"frente a una sin competidor (IC90 {t.ic90_inf:+.2f} a {t.ic90_sup:+.2f}%; {len(ev)} tiendas). No es más barata: la diferencia es de "
    f"décimas de punto y, si acaso, hacia arriba. En las sensibilidades va de {sens.diferencia_pct.min():+.2f}% a {sens.diferencia_pct.max():+.2f}%."))"""),
])

# --------------------------------------------------------------------------- 02
write("02_tipo_de_competidor.ipynb", [
    head("02", "¿Cambia según quién sea el competidor?",
         "¿Importa si el competidor cercano es de Walmart de México, Soriana, Chedraui u otra cadena?",
         """Importa porque un retailer no compite igual contra una bodega de descuento que contra un supermercado regional.
Indicadores de cada tipo de competidor a 2 km (una tienda puede tener varios); mismos controles."""),
    ("code", SETUP + LOAD + """nt = pd.DataFrame({t: (ev[f"d_{t}"] <= 2).sum() for t in ["walmex", "soriana", "chedraui", "otro"]}, index=["tiendas con ese competidor a 2 km"])
display(nt)
ty = K.estimate(ev, K.comp_by_type(), reps=REPS)
display(ty.round(2))"""),
    ("code", """ty.to_csv(PROC / "efecto_por_tipo.csv", encoding="utf-8-sig")
F = "02_tipo_de_competidor"
for k_, r_ in ty.iterrows():
    t_ = k_.split()[-1]
    reg(f"tipo_{t_}", r_.diferencia_pct, [r_.ic90_inf, r_.ic90_sup], n=int((ev[f"d_{t_}"] <= 2).sum()), fuente=F)
reg("tipo_solidos", int(ty.solido.sum()), n=len(ty), fuente=F)
display(Markdown(
    "**Conclusión.** Ningún tipo de competidor se asocia con precios más bajos de forma clara: " +
    "; ".join(f"{k_.replace('competidor ', '')} {r_.diferencia_pct:+.1f}% (IC90 {r_.ic90_inf:+.1f} a {r_.ic90_sup:+.1f})" for k_, r_ in ty.iterrows()) + "."))"""),
])

# --------------------------------------------------------------------------- 03
write("03_radio_y_distancia.ipynb", [
    head("03", "¿Qué tan sensible es el resultado al radio?",
         "¿Cambia la diferencia si «cerca» es 1, 2 o 3 km, o si se usa la distancia al competidor más cercano?",
         """Importa porque «cerca» depende de cómo se mueve el cliente. Si el resultado cambia mucho con el radio, no hay un
efecto robusto. A 3 km casi no quedan tiendas sin competidor: ahí el intervalo es muy amplio."""),
    ("code", SETUP + LOAD + """rows = []
for R in K.RADIOS:
    t = K.estimate(ev, K.comp(R), reps=REPS).iloc[0]
    rows.append({"radio_km": R, **t.to_dict(), "con": int((ev.dmin <= R).sum()), "sin": int((ev.dmin > R).sum())})
rad = pd.DataFrame(rows).set_index("radio_km")
display(rad.round(2))
ds = K.estimate(ev, K.distance_term(), reps=REPS)
print("Distancia continua: cambio del índice al duplicar la distancia al competidor más cercano")
dup = ds.loc["log_distancia"]
dup2 = {k: (np.exp(np.log1p(dup[k] / 100) * np.log(2)) - 1) * 100 for k in ["diferencia_pct", "ic90_inf", "ic90_sup"]}
print({k: round(v, 2) for k, v in dup2.items()})"""),
    ("code", """rad.to_csv(PROC / "efecto_por_radio.csv", encoding="utf-8-sig")
pd.DataFrame([dup2]).to_csv(PROC / "efecto_distancia.csv", index=False, encoding="utf-8-sig")
F = "03_radio_y_distancia"
for R, r_ in rad.iterrows():
    reg(f"radio_{R}km", r_.diferencia_pct, [r_.ic90_inf, r_.ic90_sup], n=r_.con + r_.sin, fuente=F)
    reg(f"radio_{R}km_sin", r_.sin, fuente=F)
reg("duplicar_distancia", dup2["diferencia_pct"], [dup2["ic90_inf"], dup2["ic90_sup"]], fuente=F)
display(Markdown(
    f"**Conclusión.** A 1 km la diferencia es {rad.loc[1, 'diferencia_pct']:+.2f}% (IC90 {rad.loc[1, 'ic90_inf']:+.2f} a {rad.loc[1, 'ic90_sup']:+.2f}), a 2 km "
    f"{rad.loc[2, 'diferencia_pct']:+.2f}% y a 3 km {rad.loc[3, 'diferencia_pct']:+.2f}% (con solo {int(rad.loc[3, 'sin'])} tiendas sin competidor). Duplicar "
    f"la distancia al competidor más cercano cambia el índice {dup2['diferencia_pct']:+.2f}%. En ningún radio aparece un descuento por competencia."))"""),
])

# --------------------------------------------------------------------------- 04
write("04_implicaciones.ipynb", [
    head("04", "¿Por qué no aparece un efecto y qué implica?",
         "¿Cuánto margen tienen las cadenas para fijar precio por tienda?",
         """Importa porque si las sucursales de una cadena cobran lo mismo en toda la ciudad, la competencia de la esquina
no tiene por dónde reflejarse en el precio de anaquel. Se mide cuánto varía el precio entre sucursales del mismo formato
en la misma ciudad (`estadistica.same_chain_same_city`, tolerancia de 2%)."""),
    ("code", SETUP + LOAD + """pts, st = K.load()
x = pts.merge(st[["establecimiento_id", "formato", "municipio_id"]], on="establecimiento_id").rename(columns={"sku_id": "sku"})
x["cadena_comercial"] = x.formato
fm = ["Walmart", "Bodega Aurrerá", "Walmart Express", "Hipermercado Soriana", "Mega Soriana"]  # Chedraui casi no tiene 2 sucursales en la misma ciudad
_, same = E.same_chain_same_city(x, fm)
display(same.round(1))
w = ev.copy()
w["resid"] = w.indice - w.groupby(["municipio_id", "formato"]).indice.transform("mean")
sd = (w.groupby("formato").resid.std() * 100).rename("desviación del índice entre sucursales (puntos %)")
display(sd.round(2).to_frame())"""),
    ("code", """same.to_csv(PROC / "mismo_formato_misma_ciudad.csv", encoding="utf-8-sig")
F = "04_implicaciones"
reg("igual_walmart", same.loc["Walmart", "igual_pct"], fuente=F); reg("igual_bodega", same.loc["Bodega Aurrerá", "igual_pct"], fuente=F)
reg("igual_soriana", same.loc["Hipermercado Soriana", "igual_pct"], fuente=F); reg("igual_mega", same.loc["Mega Soriana", "igual_pct"], fuente=F)
display(Markdown(
    f"**Conclusión.** Las sucursales del mismo formato en la misma ciudad cobran el mismo precio (±2%) en {same.loc['Walmart', 'igual_pct']:.0f}% de los "
    f"productos en Walmart, {same.loc['Bodega Aurrerá', 'igual_pct']:.0f}% en Bodega Aurrerá y {same.loc['Hipermercado Soriana', 'igual_pct']:.0f}% en Hipermercado "
    "Soriana. Con precios casi iguales por ciudad, el competidor de la esquina tiene poco espacio para mover el precio de una sucursal."))"""),
])

# --------------------------------------------------------------------------- 05
write("05_visualizaciones.ipynb", [
    head("05", "Visualizaciones, reporte e implicaciones", "¿Cómo se comunica el hallazgo y qué hace cada audiencia?",
         """Convenciones: **verde ▲** = la tienda con competidor cerca cobra más; **rojo ▼** = cobra menos; gris = no
distinta de cero (el intervalo cruza 0); dorado = referencia (sin competidor = 0)."""),
    ("code", SETUP + LOAD + """import graficas as G, reporte, plantillas, re
res = entorno.cifras()
ef = pd.read_csv(PROC / "efecto_2km.csv", index_col=0)
ty = pd.read_csv(PROC / "efecto_por_tipo.csv", index_col=0)
rad = pd.read_csv(PROC / "efecto_por_radio.csv", index_col=0)
cov = pd.read_csv(PROC / "cobertura_por_radio.csv")"""),
    ("md", "## Gráfica principal: diferencia con y sin competidor, por cadena"),
    ("code", """G.effect_by_group(ef, rad, res, CHARTS / "01_efecto_por_cadena.png", svg=True); plt.show()"""),
    ("md", "### Versiones para publicar (1280×720 y 1080×1350)"),
    ("code", """G.effect_social(ef, res, "horizontal", SOCIAL / "01_efecto_cadena_1280x720.png"); plt.show()
G.effect_social(ef, res, "vertical", SOCIAL / "01_efecto_cadena_1080x1350.png"); plt.show()"""),
    ("md", "## Complementarias"),
    ("code", """G.by_radius(rad, res, CHARTS / "02_efecto_por_radio.png"); plt.show()"""),
    ("code", """G.by_type(ty, ev, res, CHARTS / "03_efecto_por_tipo.png"); plt.show()"""),
    ("code", """G.index_vs_distance(ev, res, CHARTS / "04_indice_vs_distancia.png"); plt.show()"""),
    ("md", "## Reporte HTML y README"),
    ("code", """GALERIA = [(g_["titulo"], g_["pie"], CHARTS / g_["archivo"]) for g_ in CFG["graficas"]]
out = reporte.build(ef, rad, ty, cov, res, CFG, GALERIA, ROOT / "docs/index.html")
print(out, f"{out.stat().st_size / 1e6:.1f} MB")
estructura = (ROOT / "src/estructura.md").read_text(encoding="utf-8")
(ROOT / "README.md").write_text(plantillas.readme(CFG, res, estructura), encoding="utf-8")
txt = (ROOT / "README.md").read_text(encoding="utf-8")
assert not re.search(r"\\{[a-z][a-z0-9_]*(:[^}]*)?\\}", txt), re.findall(r"\\{[a-z][a-z0-9_]*(?::[^}]*)?\\}", txt)[:5]
print("README actualizado")"""),
    ("md", "## Qué hacer con esto"),
    ("code", """for aud, acc in CFG["readme"]["acciones"].items():
    display(Markdown(f"**{aud}**\\n\\n" + "\\n".join(f"- {plantillas.render(a, res)}" for a in acc)))"""),
])

print("Notebooks generados.")
