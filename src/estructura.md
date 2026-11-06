```
mexico-competencia-2km/
├── notebooks/        00 validación y datos · 01 efecto a 2 km · 02 tipo de competidor
│                     03 radio y distancia · 04 implicaciones · 05 visualizaciones
├── config.yaml       objetivo, preguntas y textos del README y del reporte
├── src/              entorno.py, competencia.py (índice por tienda y distancias), graficas.py, reporte.py
├── data/processed/   tiendas focales con índice y distancias, efectos por cadena, radio y tipo (CSV) y resultados.json
├── data/metadata/    parametros.json, manifiesto_insumos.json
├── outputs/charts/   gráficas PNG (la principal también en SVG)
├── outputs/social/   versiones de 1280×720 y 1080×1350
├── docs/index.html   reporte interactivo autocontenido
├── build_notebooks.py
└── verify_project.py
```

```powershell
python -m pip install -r requirements.txt
python build_notebooks.py
$env:OMP_NUM_THREADS = 1; $env:OPENBLAS_NUM_THREADS = 1; $env:MKL_NUM_THREADS = 1
foreach ($n in Get-ChildItem notebooks/0*.ipynb) {
  python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 $n.FullName
}
python verify_project.py
```

`verify_project.py` recalcula las cifras clave solo con pandas y numpy a partir de los precios originales y comprueba que
coinciden con este README.
