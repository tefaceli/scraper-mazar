import sys
import json
import datetime
import requests

# argumento opcional: fuerza una fecha puntual (YYYY-MM-DD) en vez de calcular "ayer"
FECHA_FORZADA = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "" else None

# Ecuador es UTC-5 fijo, sin horario de verano
ahora_utc = datetime.datetime.utcnow()
ahora_ecuador = ahora_utc - datetime.timedelta(hours=5)
hoy_ecuador = ahora_ecuador.date()

# esta fuente siempre trae el cierre del dia anterior (dia ya completo)
if FECHA_FORZADA:
    dia_objetivo = datetime.datetime.strptime(FECHA_FORZADA, "%Y-%m-%d").date()
else:
    dia_objetivo = hoy_ecuador - datetime.timedelta(days=1)

dia_siguiente = dia_objetivo + datetime.timedelta(days=1)

# la ventana va de 01:00 local del dia_objetivo a 00:00 local del dia_siguiente
fecha_inicio = dia_objetivo.strftime("%Y-%m-%dT06:00:00.000Z")
fecha_fin = dia_siguiente.strftime("%Y-%m-%dT05:00:00.000Z")
fecha_param = dia_objetivo.strftime("%d/%m/%Y 01:00:00")

url = "https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/pointValues"
params = {
    "mrid": 100037,
    "fechaInicio": fecha_inicio,
    "fechaFin": fecha_fin,
    "fecha": fecha_param,
}

respuesta = requests.get(url, params=params, timeout=30)
items = respuesta.json()["items"]

# items vienen del mas reciente al mas viejo; nos quedamos con el primero que SI tenga dato
items_con_valor = [item for item in items if item["valueedit"] is not None]
ultimo = items_con_valor[0]

valor_actual = round(ultimo["valueedit"], 2)
fecha_cierre = dia_objetivo.strftime("%Y-%m-%d")

print(f"Caudal CCS | dia objetivo: {fecha_cierre} | valor: {valor_actual}")

# fusiona con historico.json: actualiza la entrada si la fecha ya existe (la crearon
# cota/caudal o CENACE ese mismo dia), o la crea si esta fuente llega primero
historico = json.load(open("data/historico.json"))
datos_ccs = {"caudal_ccs": valor_actual}

indice_existente = None
for i in range(len(historico)):
    if historico[i]["fecha"] == fecha_cierre:
        indice_existente = i

if indice_existente is not None:
    historico[indice_existente].update(datos_ccs)
else:
    punto_nuevo = dict(datos_ccs)
    punto_nuevo["fecha"] = fecha_cierre
    historico.append(punto_nuevo)

json.dump(historico, open("data/historico.json", "w"), ensure_ascii=False, indent=2)
print(f"historico.json ahora tiene {len(historico)} dias")
