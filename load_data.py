# Autor: Eduardo Tovar Ruiz

# En este archivo se definen las funciones necesarias para crear las bases de datos necesarias y
# de crear las conexiones a dichas bases de datos. Tambien se han creado algunas funcionalidades
# de formato como parsear_fecha que resultan utiles.

import json
from datetime import datetime

import pymysql
from pymongo import MongoClient

from configuracion import (MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_URI, MONGO_DB, MONGO_COLLECTION, DATA_FILES)


#  Conexiones

def conectar_mysql():
    """Crea y devuelve la conexión a MySQL."""
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD
    )


def conectar_mongo():
    """Crea y devuelve el cliente de MongoDB."""
    return MongoClient(MONGO_URI)


# Crear los esquemas

def crear_esquema_mysql(cursor):
    """Crea la base de datos y las tablas si no existen."""
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
    cursor.execute(f"USE {MYSQL_DB}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Usuario (
            reviewerID VARCHAR(64)  PRIMARY KEY,
            reviewerName VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Producto (
            asin     VARCHAR(32)  PRIMARY KEY,
            categoria VARCHAR(64) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Review (
            reviewerID    VARCHAR(64)  NOT NULL,
            asin          VARCHAR(32)  NOT NULL,
            overall       FLOAT        NOT NULL,
            unixReviewTime INT UNSIGNED NOT NULL,
            reviewTime    DATE         NOT NULL,
            helpful_votes INT UNSIGNED NOT NULL DEFAULT 0,
            total_votes   INT UNSIGNED NOT NULL DEFAULT 0,
            PRIMARY KEY (reviewerID, asin),
            FOREIGN KEY (reviewerID) REFERENCES Usuario(reviewerID),
            FOREIGN KEY (asin)       REFERENCES Producto(asin)
        )
    """)



def parsear_fecha(review_time_str):
    """Convierte los strings de las fechas a un objeto date de Python."""
    try:
        return datetime.strptime(review_time_str.strip(), "%m %d, %Y").date()
    except ValueError:
        return datetime.strptime(review_time_str.strip(), "%m %d, %Y").date()


# Cargar ficheros

def cargar_fichero(filepath, categoria, cursor, mongo_col):
    """
    Lee el fichero línea a línea e inserta los datos en MySQL y MongoDB.

    Args:
        filepath: Ruta al fichero que se quiere leer.
        categoria: Nombre de la categoría.
        cursor: Cursor de MySQL (necesita la BD ya seleccionada).
        mongo_col: Colección de MongoDB.
    """
    usuarios_insertados  = set()
    productos_insertados = set()

    with open(filepath, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue

            try:
                review = json.loads(linea)
            except json.JSONDecodeError:
                continue

            reviewer_id= review.get("reviewerID", "")
            asin = review.get("asin", "")
            reviewer_name = review.get("reviewerName", "")
            overall = review.get("overall", 0)
            unix_time = review.get("unixReviewTime", 0)
            review_time = review.get("reviewTime", "01 1, 1970")
            helpful = review.get("helpful", [0, 0])
            review_text = review.get("reviewText", "")
            summary = review.get("summary", "")

            helpful_votes = helpful[0] if len(helpful) > 0 else 0
            total_votes = helpful[1] if len(helpful) > 1 else 0
            fecha = parsear_fecha(review_time)

            # Usuario
            if reviewer_id not in usuarios_insertados:
                cursor.execute("""
                    INSERT IGNORE INTO Usuario (reviewerID, reviewerName)
                    VALUES (%s, %s)
                """, (reviewer_id, reviewer_name))
                usuarios_insertados.add(reviewer_id)

            # Producto
            if asin not in productos_insertados:
                cursor.execute("""
                    INSERT IGNORE INTO Producto (asin, categoria)
                    VALUES (%s, %s)
                """, (asin, categoria))
                productos_insertados.add(asin)

            # Review (MySQL)
            cursor.execute("""
                INSERT IGNORE INTO Review
                    (reviewerID, asin, overall, unixReviewTime,
                     reviewTime, helpful_votes, total_votes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (reviewer_id, asin, overall, unix_time,
                  fecha, helpful_votes, total_votes))

            # Texto (MongoDB)
            mongo_col.insert_one({
                "reviewerID":  reviewer_id,
                "asin":        asin,
                "reviewText":  review_text,
                "summary":     summary,
            })

def limpiar_mysql(cursor):
    """Elimina y recrea las tablas para evitar duplicados."""
    cursor.execute(f"USE {MYSQL_DB}")
    cursor.execute("DROP TABLE IF EXISTS Review")
    cursor.execute("DROP TABLE IF EXISTS Producto")
    cursor.execute("DROP TABLE IF EXISTS Usuario")

def main():
    print("Conectando a MySQL...")
    conn = conectar_mysql()
    cursor = conn.cursor()
    limpiar_mysql(cursor)
    crear_esquema_mysql(cursor)
    conn.commit()

    print("Conectando a MongoDB...")
    mongo_client = conectar_mongo()
    mongo_db = mongo_client[MONGO_DB]
    mongo_col = mongo_db[MONGO_COLLECTION]
    mongo_col.drop()  # Limpia la colección antes de cargar para evitar duplicados

    for categoria, filepath in DATA_FILES.items():
        print(f"Cargando '{categoria}' desde {filepath}...")
        try:
            cargar_fichero(filepath, categoria, cursor, mongo_col)
            conn.commit()
            print(f"'{categoria}' cargada correctamente.")
        except FileNotFoundError:
            print(f"ERROR: fichero no encontrado -> {filepath}")

    cursor.close()
    conn.close()
    mongo_client.close()
    print("Carga completada.")



if __name__ == "__main__":
    main()