import sys
import json
import datetime
import ssl
import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AdaptadorTLS(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        contexto = ssl.create_default_context()
        contexto.set_ciphers("DEFAULT@SECLEVEL=1")
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = contexto
        return super().init_poolmanager(*args, **kwargs)


sesion = requests.Session()
sesion.mount("https://", AdaptadorTLS())

if len(sys.argv) > 1 and sys.argv[1] != "":
    ayer_ecuador = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
else:
    # Ecuador es UTC-5 fijo, sin horario de verano
    ahora_utc = datetime.datetime.utcnow()
    ahora_ecuador = ahora_utc - datetime.timedelta(hours=5)
    hoy_ecuador = ahora_ecuador.date()
    # CENACE publica el informe a dia vencido: hoy tenemos el dato de ayer
    ayer_ecuador = hoy_ecuador - datetime.timedelta(days=1)

fecha_cenace = ayer_ecuador.strftime("%Y/%m/%d")

url = "https://smec.cenace.gob.ec/SMEC/ResultadoInforme1.do?fecha=" + fecha_cenace

respuesta = sesion.get(url, timeout=30, verify=False)
soup = BeautifulSoup(respuesta.text, "html.parser")

etiquetas = ["Generación Hidráulica", "Generación Vapor Bunker", "Generación Turbinas a Gas",
             "Generación Turbinas a Diesel", "Generación Motores Bunker",
             "Generación de Otros Tipos", "Importación de Colombia"]

valores = {}
for celda in soup.find_all("td", class_="bordegris", align="left"):
    etiqueta = celda.get_text(strip=True)
    if etiqueta in etiquetas:
        valor_celda = celda.find_next_sibling("td")
        valor_texto = valor_celda.get_text(strip=True).replace(",", "")
        valores[etiqueta] = float(valor_texto)

hidraulica_mw = round(valores["Generación Hidráulica"] / 24 / 1000, 2)
termica_kwh = (valores["Generación Vapor Bunker"] + valores["Generación Turbinas a Gas"]
               + valores["Generación Turbinas a Diesel"] + valores["Generación Motores Bunker"])
termica_mw = round(termica_kwh / 24 / 1000, 2)
otros_mw = round(valores["Generación de Otros Tipos"] / 24 / 1000, 2)
importacion_col_mw = round(valores["Importación de Colombia"] / 24 / 1000, 2)

datos_cenace = {
    "hidraulica_mw": hidraulica_mw,
    "termica_mw": termica_mw,
    "otros_mw": otros_mw,
    "importacion_colombia_mw": importacion_col_mw,
}

fecha_cierre = ayer_ecuador.strftime("%Y-%m-%d")

print("CENACE | dia objetivo:", fecha_cierre, "|", datos_cenace)

historico = json.load(open("data/historico.json"))

indice_existente = None
for i in range(len(historico)):
    if historico[i]["fecha"] == fecha_cierre:
        indice_existente = i

if indice_existente is not None:
    historico[indice_existente].update(datos_cenace)
else:
    punto_nuevo = dict(datos_cenace)
    punto_nuevo["fecha"] = fecha_cierre
    historico.append(punto_nuevo)

json.dump(historico, open("data/historico.json", "w"), ensure_ascii=False, indent=2)
print("historico.json actualizado, total dias:", len(historico))
