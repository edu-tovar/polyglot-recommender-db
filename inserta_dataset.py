# Autor: Eduarod Tovar Ruiz

# En este fichero se inserta un nuevo dataset en la base de datos.
# En este caso se ha elegido el dataset descrito en el archivo Office_Products_5.json



import json
from datetime import datetime

import pymysql
from pymongo import MongoClient

from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_URI, MONGO_DB, MONGO_COLLECTION
)

# Configuración del nuevo dataset
NUEVO_DATASET_PATH = "data/Office_Products_5.json"
NUEVA_CATEGORIA    = "Office Products"


# Conexiones

def conectar_mysql():
    """Devuelve conexión y cursor a MySQL."""
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return conn, conn.cursor()


def conectar_mongo():
    """Devuelve la colección de MongoDB y el cliente."""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB][MONGO_COLLECTION], client


# Parseo de fecha

def parsear_fecha(review_time_str):
    """Convierte '07 9, 2012' a un objeto date de Python."""
    for fmt in ("%m %d, %Y", "%m %d, %Y"):
        try:
            return datetime.strptime(review_time_str.strip(), fmt).date()
        except ValueError:
            continue
    return datetime(1970, 1, 1).date()


# Inserción

def insertar_dataset(filepath, categoria):
    """
    Inserta un nuevo dataset en MySQL y MongoDB.
    Reutiliza usuarios ya existentes correctamente mediante INSERT IGNORE.

    Args:
        filepath:  Ruta al fichero JSON del nuevo dataset.
        categoria: Nombre de la categoría del nuevo dataset.
    """
    conn, cursor = conectar_mysql()
    mongo_col, mongo_client = conectar_mongo()

    usuarios_insertados  = set()
    productos_insertados = set()
    insertadas = 0
    omitidas   = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                review = json.loads(linea)
            except json.JSONDecodeError:
                continue

            reviewer_id   = review.get("reviewerID", "")
            asin          = review.get("asin", "")
            reviewer_name = review.get("reviewerName", "")
            overall       = review.get("overall", 0)
            unix_time     = review.get("unixReviewTime", 0)
            review_time   = review.get("reviewTime", "01 1, 1970")
            helpful       = review.get("helpful", [0, 0])
            review_text   = review.get("reviewText", "")
            summary       = review.get("summary", "")

            helpful_votes = helpful[0] if len(helpful) > 0 else 0
            total_votes   = helpful[1] if len(helpful) > 1 else 0
            fecha         = parsear_fecha(review_time)

            if reviewer_id not in usuarios_insertados:
                cursor.execute("""
                    INSERT IGNORE INTO Usuario (reviewerID, reviewerName)
                    VALUES (%s, %s)
                """, (reviewer_id, reviewer_name))
                usuarios_insertados.add(reviewer_id)

            if asin not in productos_insertados:
                cursor.execute("""
                    INSERT IGNORE INTO Producto (asin, categoria)
                    VALUES (%s, %s)
                """, (asin, categoria))
                productos_insertados.add(asin)

            cursor.execute("""
                INSERT IGNORE INTO Review
                    (reviewerID, asin, overall, unixReviewTime,
                     reviewTime, helpful_votes, total_votes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (reviewer_id, asin, overall, unix_time,
                  fecha, helpful_votes, total_votes))

            if cursor.rowcount > 0:
                mongo_col.insert_one({
                    "reviewerID": reviewer_id,
                    "asin":       asin,
                    "reviewText": review_text,
                    "summary":    summary,
                })
                insertadas += 1
            else:
                omitidas += 1

    conn.commit()
    cursor.close()
    conn.close()
    mongo_client.close()

    print(f"Dataset '{categoria}' insertado.")
    print(f"  Reviews insertadas: {insertadas}")
    print(f"  Reviews omitidas (ya existían): {omitidas}")


# Main

if __name__ == "__main__":
    print(f"Insertando dataset '{NUEVA_CATEGORIA}' desde '{NUEVO_DATASET_PATH}'...")
    try:
        insertar_dataset(NUEVO_DATASET_PATH, NUEVA_CATEGORIA)
    except FileNotFoundError:
        print(f"ERROR: fichero no encontrado -> {NUEVO_DATASET_PATH}")