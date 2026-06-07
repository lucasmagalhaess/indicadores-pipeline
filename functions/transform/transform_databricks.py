import requests, json
from pyspark.sql.functions import col, when, round as spark_round, avg, max, min
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from azure.storage.blob import BlobServiceClient

storage_account = "indicadoresdatalake"
sas_token = dbutils.secrets.get(scope="licitacoes", key="sas-token-indicadores")
blob_date = "2026-06-07"
blob_file = "dados_2026-06-07T03-31-14.json"

url = "https://" + storage_account + ".blob.core.windows.net/bronze/indicadores/" + blob_date + "/" + blob_file + "?" + sas_token
response = requests.get(url)
data = response.json()
registros = data["registros"]

rows = []
for r in registros:
    try:
        valor = float(r.get("valor", 0) or 0)
    except:
        valor = 0.0
    rows.append((str(r.get("codigo","")), str(r.get("indicador","")), str(r.get("data","")), valor, str(r.get("extraction_date",""))))

schema = StructType([
    StructField("codigo", StringType()),
    StructField("indicador", StringType()),
    StructField("data", StringType()),
    StructField("valor", DoubleType()),
    StructField("extraction_date", StringType()),
])

df = spark.createDataFrame(rows, schema)

df_silver = df \
    .withColumn("classificacao",
        when(col("indicador") == "Selic",
            when(col("valor") >= 12, "alta").when(col("valor") >= 8, "moderada").otherwise("baixa"))
        .when(col("indicador") == "IPCA",
            when(col("valor") >= 0.5, "alta").when(col("valor") >= 0.2, "moderada").otherwise("baixa"))
        .when(col("indicador") == "Dolar PTAX",
            when(col("valor") >= 6, "alto").when(col("valor") >= 5, "moderado").otherwise("baixo"))
        .otherwise("neutro")) \
    .withColumn("valor_arredondado", spark_round(col("valor"), 4))

storage_key = dbutils.secrets.get(scope="licitacoes", key="storage-key-indicadores")
full_conn_str = "DefaultEndpointsProtocol=https;AccountName=" + storage_account + ";AccountKey=" + storage_key + ";EndpointSuffix=core.windows.net"
output_data = [row.asDict() for row in df_silver.collect()]
silver_json = "\n".join([json.dumps(r, ensure_ascii=False) for r in output_data])
client = BlobServiceClient.from_connection_string(full_conn_str)
client.get_container_client("silver").upload_blob(name="indicadores/" + blob_date + "/dados_silver.ndjson", data=silver_json.encode("utf-8"), overwrite=True)

df_silver.write \
    .format("sqlserver") \
    .option("host", "licitacoes-sql-server.database.windows.net") \
    .option("port", "1433") \
    .option("database", "licitacoesdb") \
    .option("user", "adminlicitacoes") \
    .option("password", "LicitacoesPipeline2026!") \
    .option("dbtable", "indicadores_economicos_gold") \
    .mode("overwrite") \
    .save()

print("Pipeline completo! " + str(len(output_data)) + " registros processados")
