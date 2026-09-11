import sys
import json
import datetime
import requests

# MODE viene del workflow de GitHub Actions: "madrugada" o "dia"
MODE = sys.argv[1]

# Ecuador es UTC-5 fijo, sin horario de verano
ahora_utc = datetime.datetime.utcnow()
ahora_ecuador = ahora_utc - datetime.timedelta(hours=5)
hoy_ecuador = ahora_ecuador.date()

# en madrugada buscamos el CIERRE de ayer; en las corridas del dia, el dato EN VIVO de hoy
dia_objetivo = hoy_ecuador - datetime.timedelta(days=1) if MODE == "madrugada" else hoy_ecuador
dia_siguiente = dia_objetivo + datetime.timedelta(days=1)

# la ventana va de 01:00 local del dia_objetivo a 00:00 local del dia_siguiente
fecha_inicio = dia_objetivo.strftime("%Y-%m-%dT06:00:00.000Z")
fecha_fin = dia_siguiente.strftime("%Y-%m-%dT05:00:00.000Z")
fecha_param = dia_objetivo.strftime("%d/%m/%Y 01:00:00")

url = "https://generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/pointValues"
params = {
    "mrid": 30031,
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
hora_actual = ultimo["loctimestamp"]

print(f"Modo: {MODE} | dia objetivo: {dia_objetivo} | valor: {valor_actual} | hora dato: {hora_actual}")

# --- en_vivo.json se actualiza SIEMPRE, en las 3 corridas ---
en_vivo = {"cota": valor_actual, "actualizado": hora_actual}
with open("data/en_vivo.json", "w") as f:
    json.dump(en_vivo, f, ensure_ascii=False, indent=2)

# --- historico.json solo se toca en la corrida de madrugada (cierre del dia anterior) ---
if MODE == "madrugada":
    historico = json.load(open("data/historico.json"))
    fecha_cierre = dia_objetivo.strftime("%Y-%m-%d")
    fechas_existentes = set(punto["fecha"] for punto in historico)
    punto_nuevo = {"fecha": fecha_cierre, "cota": valor_actual}
    historico = historico + ([punto_nuevo] if fecha_cierre not in fechas_existentes else [])
    json.dump(historico, open("data/historico.json", "w"), ensure_ascii=False, indent=2)
    print(f"historico.json ahora tiene {len(historico)} dias")
