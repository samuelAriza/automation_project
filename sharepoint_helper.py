import os
import requests
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import logging

load_dotenv()

# --- Autenticación con MSAL ---
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("APP_ID")              # ← equivale a Client ID de tu app
CLIENT_SECRET = os.getenv("APP_PASSWORD")    # ← equivale a Client Secret

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY
)

CAMPO_MAP = {
    "Title": "Title",
    "field_2": "CorreoInstitucional",
    "field_3": "Nombre",
    "field_4": "Apellido",
    "field_5": "Carrera",
    "field_6": "Semestre",
    "field_7": "Título",
    "field_8": "TipoDeCaso",
    "field_9": "SubtipoDeCaso",
    "field_10": "Descripción",
    "field_11": "FechaSolicitud",
    "field_12": "Estado",
    "field_13": "Urgencia",
    "field_14": "AsignadoA",
    "field_15": "Adjunto",
    "field_16": "Notas",
    "field_17": "FechaSeguimiento",
    "field_18": "EnlaceReuniónVirtual",
    "field_19": "IDInteracciónBot",
    "field_20": "RequiereEscalamiento",
    "field_21": "NotasResolución"
}

CAMPO_MAP_INV = {v: k for k, v in CAMPO_MAP.items()}

def traducir_a_campos_sharepoint(campos_legibles):
    return {CAMPO_MAP_INV[k]: v for k, v in campos_legibles.items() if k in CAMPO_MAP_INV}

def mapear_campos(fields_raw):
    return {CAMPO_MAP.get(k, k): v for k, v in fields_raw.items()}

def get_token():
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Error al obtener el token: {result.get('error_description')}")

# --- Configuración de SharePoint ---
SHAREPOINT_SITE_ID = os.getenv("SHAREPOINT_SITE_ID")
LIST_ID = os.getenv("SHAREPOINT_LIST_ID")
BASE_URL = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/lists/{LIST_ID}/items"

# --- Función: Buscar estudiante por ID (Title) ---
def buscar_estudiante_por_id(student_id):
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"
    }
    # Se añade $expand=fields para obtener los datos reales
    url = f"{BASE_URL}?$filter=fields/Title eq '{student_id}'&$expand=fields"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['value']:
            logging.debug("-----"*100)
            return data['value'][0]['fields']  # <-- Ahora sí contiene lo importante
        else:
            logging.debug("Nada"*100)
            return None
    else:
        raise Exception(f"Error en la consulta: {response.status_code} - {response.text}")

# --- Función: Actualizar campos de un registro existente ---
def actualizar_registro_por_title(student_id, campos_actualizados):
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "Prefer": "HonorNonIndexedQueriesWarningMayFailRandomly"
    }

    # Buscar item con Title
    url_busqueda = f"{BASE_URL}?$filter=fields/Title eq '{student_id}'&$expand=fields"
    response = requests.get(url_busqueda, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error al buscar el estudiante: {response.status_code} - {response.text}")

    data = response.json()
    if not data['value']:
        raise Exception(f"No se encontró ningún estudiante con Title = {student_id}")

    item_id = data['value'][0]['id']  # ID interno de SharePoint

    # Actualizar campos
    url_actualizacion = f"{BASE_URL}/{item_id}/fields"
    response = requests.patch(url_actualizacion, headers=headers, json=campos_actualizados)
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"Error al actualizar el registro: {response.status_code} - {response.text}")