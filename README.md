# scraper-mazar

Este repositorio contiene scrapers automatizados que bajan datos hidrológicos y de generación eléctrica de Ecuador desde fuentes públicas, y los dejan en JSON dentro de este mismo repo, listos para ser consumidos por cualquier cliente (`data/historico.json` y `data/en_vivo.json`).

## Fuentes

1. **CELEC (API interna, JSON)** — `generacioncsr.celec.gob.ec:8443/ords/csr/sardomcsr/pointValues`
   API tipo Oracle ORDS. Se le pide una ventana de 24 horas (parámetro `mrid` identifica la variable: `30031` = cota Mazar, `30538` = caudal Mazar) y se toma el último valor no-nulo como dato del día.

2. **CENACE (informe HTML, día vencido)** — `smec.cenace.gob.ec/SMEC/ResultadoInforme1.do?fecha=YYYY/MM/DD`
   Página HTML con el "Informe de Balance Energético" del día solicitado. Se parsea la tabla con BeautifulSoup y se extrae **Energía Activa en el Día (kWh)** para: Generación Hidráulica, Generación Térmica (suma de Vapor Bunker + Turbinas a Gas + Turbinas a Diesel + Motores Bunker), Generación de Otros Tipos, e Importación de Colombia. Cada valor se divide entre 24 y entre 1000 para dejarlo en MW promedio del día.

## Estructura

```
scraper-mazar/
├── .github/workflows/
│   ├── actualizar.yml            # cota + caudal (CELEC)
│   └── actualizar_cenace.yml     # generación (CENACE)
├── scripts/
│   ├── actualizar_cota.py        # cota + caudal
│   └── scraper_cenace.py         # generación
└── data/
    ├── historico.json            # una entrada por día, va creciendo
    └── en_vivo.json              # snapshot del dato más reciente, se sobreescribe
```

## Horarios (todos en cron UTC; Ecuador = UTC-5 fijo, sin horario de verano)
 
| Workflow | Cron (UTC) | Hora Ecuador | Qué hace |
|---|---|---|---|
| `actualizar.yml` | `15 5 * * *` | 00:15 | Cierra el día anterior de cota/caudal → agrega punto a `historico.json` + actualiza `en_vivo.json` |
| `actualizar.yml` | `10 11 * * *` | 06:10 | Actualiza `en_vivo.json` con el dato más reciente del día en curso |
| `actualizar.yml` | `10 23 * * *` | 18:10 | Igual que la anterior |
| `actualizar_cenace.yml` | `15 16 * * *` | 11:15 | Pide el informe de CENACE de "ayer" y agrega/actualiza esos 4 campos en `historico.json` |
 
Los dos workflows son independientes a propósito: distintas dependencias (uno solo usa `requests`, el otro también `beautifulsoup4`) y distinto nivel de fragilidad (CENACE es scraping de HTML con un workaround de SSL; CELEC es una API JSON estable).

## Esquema de `historico.json`

Un array de objetos, uno por día, sin fechas repetidas:

```json
{
  "fecha": "2026-09-10",
  "cota": 2143.12,
  "caudal": 77.79,
  "hidraulica_mw": 3822.64,
  "termica_mw": 910.01,
  "otros_mw": 89.05,
  "importacion_colombia_mw": 5.95
}
```

Los campos de cota/caudal y los de CENACE se escriben en corridas distintas (00:15 y 05:00 respectivamente) pero terminan en el mismo objeto del día, gracias a que ambos scripts buscan la fecha existente antes de decidir si actualizan o agregan una entrada nueva.

## Cosas a tener en cuenta
 
- **CENACE usa un certificado SSL autofirmado y con cifrado débil.** El script monta una sesión de `requests` con un adaptador TLS que baja el nivel de seguridad (`SECLEVEL=1`) y desactiva la verificación del certificado (`verify=False`, `CERT_NONE`). Es un workaround deliberado, no un descuido — el sitio no tiene alternativa segura disponible.
- **La hora en que CENACE publica el informe del día anterior se calibró empíricamente:** a las 05:00 Ecuador el informe todavía no estaba listo (fallaba con `KeyError`, tabla sin las filas esperadas); a las 11:15 ya está disponible. Si en algún momento vuelve a fallar con ese mismo error, no es necesariamente que el sitio esté caído — puede ser que ese día en particular el informe se publicó más tarde de lo normal.
- **`workflow_dispatch` de CENACE acepta un input opcional `fecha` (formato `YYYY-MM-DD`).** Sirve para forzar una fecha puntual (por ejemplo, para rellenar un día que falló en el cron automático) sin depender de qué día es "hoy" para el script. Si se deja vacío, usa el día anterior como de costumbre.
- **Deduplicación de fechas:** ambos scripts revisan si la fecha ya existe en `historico.json` antes de escribir — así, si un workflow corre dos veces el mismo día (reintento manual, etc.), no se duplican ni se pisan entradas de otras fuentes.
