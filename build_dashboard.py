#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador del Dashboard (index.html) - Condominio Barrio Oriente I (v2.0, Julio 2026).

Contexto: el Dashboard vive como un sitio estatico en GitHub Pages (repo
condominio-dashboard) embebido en la pagina de Notion. Antes se armaba a mano una
vez y quedaba congelado con los datos del mes en que se genero. Este script lo
regenera a partir de data/historico.json, que vive en este mismo repo y es
autosuficiente: cada entrada mensual trae todo lo necesario (KPIs + desglose de
categorias), asi que este script NO necesita leer nada fuera del repo. Se ejecuta
automaticamente via GitHub Actions (.github/workflows/build.yml) cada vez que
alguien actualiza data/historico.json.

Quien agrega el mes nuevo a data/historico.json es un paso separado (Make, Flujo 8),
a partir de resumen_final_<anio>_<mes>.json que produce el pipeline de conciliacion
en Drive (ver agregar_mes_historico.py en Drive/Scripts).

ALCANCE (MVP, julio 2026): se automatiza solo lo que hoy tiene una fuente de datos
real y confiable:
  - Ingresos Recaudados, Total Egresos, Saldo Banco, Resultado del Mes (KPIs)
  - Egresos por Categoria (grafico, del ultimo mes)
  - Ingresos vs Egresos historico y Saldo Mensual historico (tendencias)

Se dejan FUERA (hasta tener fuente de datos real):
  - Presupuesto vs Real (no existe input de presupuesto en el pipeline)
  - Fondo de Reserva / Balance General (no forman parte del pipeline de conciliacion)
  - Morosidad por tramo y detalle de unidades morosas (el motor conciliar_mes.py ya
    soporta el arrastre de morosidad con --morosidad-anterior, pero aun no se ha
    corrido un ciclo real con esa hoja "Morosidad" generada; se debe incorporar
    aqui apenas exista un mes real con ese archivo)

La pestana "Tareas y Acuerdos" deja de ser una foto fija con graficos Chart.js y
pasa a ser un embed en vivo de la base de datos de Notion (publicada via
"Publish to web"), para que se actualice sola sin depender de este script.

Formato esperado de cada entrada en data/historico.json:
{
  "anio": 2026, "mes": 6, "mes_label": "Jun 26", "nombre_mes": "Junio",
  "ingresos_real": 10396309, "egresos_real": 6822289, "saldo_banco": 4887413,
  "egresos_por_categoria": {"Administración": 4731292.0, "Aseo": 145718.0, ...}
}

Uso:
  python3 build_dashboard.py --historico data/historico.json \
    --tareas-embed-url https://zenith-dawn-f07.notion.site/... \
    --outdir .
"""
import argparse
import json
from pathlib import Path

ADMINISTRACION_DEFAULT = "Ingrid Molgas"
COMITE_DEFAULT = "Tomas, Rodrigo, Angelo, Luis, Aldo"
CAT_COLORS = ["#2563eb", "#0891b2", "#d97706", "#7c3aed", "#16a34a", "#6b7280", "#dc2626"]


def money(v):
    try:
        return "$" + f"{round(float(v)):,}".replace(",", ".")
    except Exception:
        return str(v)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--historico", required=True, help="data/historico.json (lista de meses, el ultimo es el actual)")
    p.add_argument("--tareas-embed-url", dest="tareas_url", required=True)
    p.add_argument("--administracion", default=ADMINISTRACION_DEFAULT)
    p.add_argument("--comite", default=COMITE_DEFAULT)
    p.add_argument("--outdir", default=".")
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    historico = load_json(args.historico)
    if not historico:
        raise ValueError("historico.json esta vacio, no hay ningun mes para graficar")
    historico = sorted(historico, key=lambda h: (h["anio"], h["mes"]))
    actual = historico[-1]

    ingresos_real = actual["ingresos_real"]
    egresos_real = actual["egresos_real"]
    saldo_banco = actual.get("saldo_banco")
    periodo_fin_label = f"{actual.get('nombre_mes', actual['mes_label'])} {actual['anio']}"

    meses_labels = [h["mes_label"] for h in historico]
    ing_hist = [h["ingresos_real"] for h in historico]
    egr_hist = [h["egresos_real"] for h in historico]

    resultado_mes = ingresos_real - egresos_real
    resultado_kpi_class = "gr" if resultado_mes >= 0 else "rd"
    resultado_note_text = ("Superávit del mes" if resultado_mes >= 0 else "Déficit del mes")

    cat = actual.get("egresos_por_categoria", {})
    cat_labels = list(cat.keys())
    cat_values = list(cat.values())
    cat_total = sum(cat_values) or 1
    cat_colors = (CAT_COLORS * (len(cat_labels) // len(CAT_COLORS) + 1))[:len(cat_labels)]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard — Condominio Barrio Oriente I</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<style>
:root {{
  --bg:#f0f2f5; --card:#fff; --header:#1a2e4a;
  --blue:#2563eb; --green:#16a34a; --red:#dc2626;
  --orange:#d97706; --purple:#7c3aed; --teal:#0891b2; --gray:#6b7280;
  --radius:10px; --gap:16px; --shadow:0 1px 4px rgba(0,0,0,.08);
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:#111827;font-size:14px;line-height:1.5}}
.wrap{{max-width:1280px;margin:0 auto;padding:20px}}
.hdr{{background:var(--header);color:#fff;padding:20px 28px;border-radius:var(--radius);margin-bottom:var(--gap);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
.hdr h1{{font-size:20px;font-weight:700}}
.hdr .sub{{font-size:13px;opacity:.75;margin-top:3px}}
.hdr-badge{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 14px;font-size:13px;font-weight:600}}
.tabs{{display:flex;gap:4px;margin-bottom:var(--gap);background:#e5e7eb;padding:4px;border-radius:12px;width:fit-content}}
.tab{{padding:10px 24px;border-radius:9px;border:none;background:transparent;font-size:14px;font-weight:600;color:var(--gray);cursor:pointer;transition:all .2s}}
.tab.active{{background:#fff;color:var(--header);box-shadow:0 1px 3px rgba(0,0,0,.12)}}
.tab:hover:not(.active){{background:rgba(255,255,255,.6);color:#374151}}
.panel{{display:none}}
.panel.active{{display:block}}
.sec{{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--gray);margin:16px 0 10px}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:var(--gap);margin-bottom:var(--gap)}}
.kpi{{background:var(--card);border-radius:var(--radius);padding:18px 20px;box-shadow:var(--shadow);border-left:4px solid #e5e7eb}}
.kpi.bl{{border-left-color:var(--blue)}} .kpi.gr{{border-left-color:var(--green)}}
.kpi.rd{{border-left-color:var(--red)}}  .kpi.or{{border-left-color:var(--orange)}}
.kpi-lbl{{font-size:11px;color:var(--gray);text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}}
.kpi-val{{font-size:26px;font-weight:800;line-height:1.1}}
.kpi-note{{font-size:12px;color:var(--gray);margin-top:4px}}
.kpi-note.rd{{color:var(--red);font-weight:600}} .kpi-note.gr{{color:var(--green);font-weight:600}}
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:var(--gap);margin-bottom:var(--gap)}}
.cb{{background:var(--card);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow)}}
.cb h3{{font-size:14px;font-weight:700;margin-bottom:3px}}
.cb p{{font-size:12px;color:var(--gray);margin-bottom:14px}}
.cb canvas{{max-height:270px}}
.notion-embed{{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}}
.notion-embed iframe{{width:100%;height:1400px;border:none;display:block}}
.notion-embed .hint{{padding:12px 18px;font-size:12px;color:var(--gray);border-top:1px solid #f3f4f6}}
footer{{text-align:center;font-size:12px;color:var(--gray);margin-top:8px;padding:10px}}
@media(max-width:768px){{
  .kpi-row{{grid-template-columns:repeat(2,1fr)}}
  .g2{{grid-template-columns:1fr}}
  .tabs{{width:100%}} .tab{{flex:1;padding:10px 10px;font-size:12px}}
}}
</style>
</head>
<body>
<div class="wrap">

<header class="hdr">
  <div>
    <h1>🏘 Condominio Barrio Oriente I</h1>
    <div class="sub">Administración: {args.administracion} &nbsp;|&nbsp; Comité: {args.comite}</div>
  </div>
  <div class="hdr-badge">📅 {periodo_fin_label}</div>
</header>

<div class="tabs">
  <button class="tab active" onclick="switchTab('financiero',this)">💰 Informe Financiero</button>
  <button class="tab" onclick="switchTab('tareas',this)">📋 Tareas y Acuerdos</button>
</div>

<div id="panel-financiero" class="panel active">

  <div class="sec">📊 Resumen Financiero — {periodo_fin_label}</div>
  <div class="kpi-row">
    <div class="kpi bl"><div class="kpi-lbl">Ingresos Recaudados</div><div class="kpi-val">{money(ingresos_real)}</div><div class="kpi-note">Según cartola bancaria del mes</div></div>
    <div class="kpi rd"><div class="kpi-lbl">Total Egresos</div><div class="kpi-val">{money(egresos_real)}</div><div class="kpi-note">Según cartola bancaria del mes</div></div>
    <div class="kpi or"><div class="kpi-lbl">Saldo Banco</div><div class="kpi-val">{money(saldo_banco)}</div><div class="kpi-note">Saldo bancario al cierre del mes</div></div>
    <div class="kpi {resultado_kpi_class}"><div class="kpi-lbl">Resultado del Mes</div><div class="kpi-val">{money(resultado_mes)}</div><div class="kpi-note {resultado_kpi_class}">{resultado_note_text}</div></div>
  </div>

  <div class="sec">💰 Análisis de Egresos</div>
  <div class="g2">
    <div class="cb"><h3>Egresos por Categoría — {periodo_fin_label}</h3><p>Distribución del gasto del mes ({money(cat_total)})</p><canvas id="f-egr-cat"></canvas></div>
    <div class="cb"><h3>Ingresos vs Egresos — Histórico</h3><p>Evolución mensual real (cartola bancaria)</p><canvas id="f-ing-egr" style="max-height:300px"></canvas></div>
  </div>
  <div class="g2">
    <div class="cb"><h3>Saldo Mensual</h3><p>Resultado real mes a mes (Ingresos − Egresos)</p><canvas id="f-saldo"></canvas></div>
  </div>

</div><!-- /panel-financiero -->

<div id="panel-tareas" class="panel">
  <div class="notion-embed">
    <iframe src="{args.tareas_url}" loading="lazy"></iframe>
    <div class="hint">Vista en vivo de la base de datos "Tareas y Acuerdos" en Notion — se actualiza automáticamente, sin depender de este dashboard.</div>
  </div>
</div><!-- /panel-tareas -->

<footer>Dashboard Condominio Barrio Oriente I · {periodo_fin_label} · Administración: {args.administracion} · Comité: {args.comite}</footer>
</div><!-- /wrap -->

<script>
function switchTab(name, btn) {{
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  btn.classList.add('active');
}}

const C = {{blue:'#2563eb', green:'#16a34a', red:'#dc2626', purple:'#7c3aed', gray:'#9ca3af',
  blueFill:'rgba(37,99,235,.12)', redFill:'rgba(220,38,38,.12)'}};
const fmt = n => '$' + Math.round(n).toLocaleString('es-CL');
const yMoney = {{responsive:true,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}},tooltip:{{callbacks:{{label:ctx=>' '+fmt(ctx.parsed.y)}}}}}},scales:{{y:{{ticks:{{callback:v=>'$'+(v/1000000).toFixed(1)+'M',font:{{size:11}}}},grid:{{color:'#f3f4f6'}}}},x:{{ticks:{{font:{{size:11}}}},grid:{{display:false}}}}}}}};

new Chart('f-egr-cat',{{type:'doughnut',data:{{
  labels:{json.dumps(cat_labels, ensure_ascii=False)},
  datasets:[{{data:{json.dumps(cat_values)},backgroundColor:{json.dumps(cat_colors)},hoverOffset:6,borderWidth:2}}]
}},options:{{responsive:true,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}},
  tooltip:{{callbacks:{{label:ctx=>' '+ctx.label+': '+fmt(ctx.parsed)+' ('+(ctx.parsed/{cat_total}*100).toFixed(1)+'%)'}}}}}}
}}}});

const mesesHist = {json.dumps(meses_labels, ensure_ascii=False)};
const ingHist = {json.dumps(ing_hist)};
const egrHist = {json.dumps(egr_hist)};

new Chart('f-ing-egr',{{type:'bar',data:{{labels:mesesHist,datasets:[
  {{label:'Ingresos Real', data:ingHist,backgroundColor:C.blue,borderRadius:4}},
  {{label:'Egresos Real',  data:egrHist,backgroundColor:C.red,borderRadius:4}},
]}},options:yMoney}});

new Chart('f-saldo',{{type:'line',data:{{labels:mesesHist,datasets:[{{
  label:'Saldo',data:ingHist.map((v,i)=>v-egrHist[i]),borderColor:C.purple,
  backgroundColor:'rgba(124,58,237,.1)',fill:true,tension:.4,pointRadius:5,borderWidth:2.5
}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' '+fmt(ctx.parsed.y)}}}}}},
  scales:{{y:{{ticks:{{callback:v=>'$'+(v/1000000).toFixed(1)+'M',font:{{size:11}}}},grid:{{color:'#f3f4f6'}}}},
          x:{{ticks:{{font:{{size:11}}}},grid:{{display:false}}}}}}}}}});
</script>
</body>
</html>
"""

    out_path = outdir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"OK -> {out_path} ({len(html)} bytes)")
    print(f"historico: {len(historico)} meses (actual: {periodo_fin_label})")


if __name__ == "__main__":
    main()
