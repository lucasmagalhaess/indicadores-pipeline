import azure.functions as func
import requests
import json
import logging
import os
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

STORAGE_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

INDICADORES = {
    "11":   "Selic",
    "1":    "Dolar PTAX",
    "433":  "IPCA",
    "12":   "CDI",
    "189":  "IGP-M",
    "7326": "IPCA Acumulado 12m"
}

def get_serie(codigo, data_inicio="01/01/2024"):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    params = {"formato": "json", "dataInicial": data_inicio}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def save_to_blob(data, blob_name):
    client = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
    container = client.get_container_client("bronze")
    container.upload_blob(
        name=blob_name,
        data=json.dumps(data, ensure_ascii=False, indent=2),
        overwrite=True
    )
    logging.info(f"Salvo no Blob Storage: {blob_name}")

@app.route(route="extract", auth_level=func.AuthLevel.ANONYMOUS)
def extract_indicadores(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Iniciando extracao de indicadores economicos...")

    try:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")

        todos_registros = []

        for codigo, nome in INDICADORES.items():
            logging.info(f"Extraindo {nome}...")
            dados = get_serie(codigo)
            for d in dados:
                todos_registros.append({
                    "codigo": codigo,
                    "indicador": nome,
                    "data": d.get("data"),
                    "valor": d.get("valor"),
                    "extraction_date": today,
                    "extraction_timestamp": timestamp
                })
            logging.info(f"  {len(dados)} registros extraidos")

        payload = {
            "extraction_date": today,
            "extraction_timestamp": timestamp,
            "total_registros": len(todos_registros),
            "registros": todos_registros
        }

        blob_name = f"indicadores/{today}/dados_{timestamp.replace(':', '-')}.json"
        save_to_blob(payload, blob_name)

        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "registros": len(todos_registros),
                "file": blob_name
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Erro: {e}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            mimetype="application/json",
            status_code=500
        )
