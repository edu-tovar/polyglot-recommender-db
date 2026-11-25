# Autor: Eduardo Tovar Ruiz

# En este archivo se crea la base de datos de Neo4j
import math
import csv
from collections import defaultdict

import pymysql
from neo4j import GraphDatabase

from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)

N_USUARIOS = 30

# Conexiones

def conectar_mysql():
    """Devuelve conexión y cursor a MySQL."""
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return conn, conn.cursor()


def conectar_neo4j():
    """Devuelve driver de Neo4J."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# Neo4J

def limpiar_neo4j(driver):
    """Elimina todos los nodos y relaciones de Neo4J."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


# 4.1 Similitudes entre usuarios

def obtener_top_usuarios(cursor, n):
    """Devuelve los n usuarios con más reviews."""
    cursor.execute("""
        SELECT reviewerID, COUNT(*) as num_reviews
        FROM Review
        GROUP BY reviewerID
        ORDER BY num_reviews DESC
        LIMIT %s
    """, (n,))
    return [row[0] for row in cursor.fetchall()]


def obtener_reviews_usuario(cursor, reviewer_id):
    cursor.execute("""
        SELECT asin, overall FROM Review WHERE reviewerID = %s
    """, (reviewer_id,))
    return {row[0]: row[1] for row in cursor.fetchall()}


def pearson(reviews_u, reviews_v):
    """
    Calcula la correlación de Pearson entre dos usuarios.

    Args:
        reviews_u: dict
        reviews_v: dict

    Returns:
        Correlación de Pearson.
    """
    comunes = set(reviews_u.keys()) & set(reviews_v.keys())
    if not comunes:
        return None

    ru = sum(reviews_u.values()) / len(reviews_u)
    rv = sum(reviews_v.values()) / len(reviews_v)

    num = sum((reviews_u[i] - ru) * (reviews_v[i] - rv) for i in comunes)
    den_u = math.sqrt(sum((reviews_u[i] - ru) ** 2 for i in comunes))
    den_v = math.sqrt(sum((reviews_v[i] - rv) ** 2 for i in comunes))

    if den_u == 0 or den_v == 0:
        return None

    return num / (den_u * den_v)


def calcular_similitudes(n=N_USUARIOS, fichero_salida="similitudes.csv"):
    """
    Calcula la correlación de Pearson entre los n usuarios con más reviews
    y guarda los resultados en un fichero CSV.

    Args:
        n: Número de usuarios.
        fichero_salida: Ruta del fichero de salida.
    """
    conn, cursor = conectar_mysql()
    usuarios = obtener_top_usuarios(cursor, n)
    print(f"Top {n} usuarios obtenidos.")

    # Cargamos las reviews de cada usuario
    reviews = {}
    for uid in usuarios:
        reviews[uid] = obtener_reviews_usuario(cursor, uid)
    cursor.close(); conn.close()

    similitudes = []
    for i in range(len(usuarios)):
        for j in range(i + 1, len(usuarios)):
            u, v = usuarios[i], usuarios[j]
            sim = pearson(reviews[u], reviews[v])
            if sim is not None:
                similitudes.append((u, v, sim))

    with open(fichero_salida, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["usuario_u", "usuario_v", "similitud"])
        writer.writerows(similitudes)

    print(f"Similitudes guardadas en '{fichero_salida}' ({len(similitudes)} pares).")
    return similitudes


def cargar_similitudes_neo4j(driver, similitudes):
    """
    Carga los nodos de usuario y las relaciones de similitud en Neo4J.

    Args:
        driver: Driver de Neo4J.
        similitudes: Lista de tuplas (usuario_u, usuario_v, similitud).
    """
    with driver.session() as session:
        for u, v, sim in similitudes:
            session.run("""
                MERGE (a:Usuario {id: $u})
                MERGE (b:Usuario {id: $v})
                MERGE (a)-[:SIMILAR {similitud: $sim}]->(b)
                MERGE (b)-[:SIMILAR {similitud: $sim}]->(a)
            """, u=u, v=v, sim=sim)
    print("Similitudes cargadas en Neo4J.")


def usuario_mas_vecinos(driver):
    """Muestra por pantalla el usuario con más vecinos en Neo4J."""
    with driver.session() as session:
        result = session.run("""
            MATCH (u:Usuario)-[:SIMILAR]->()
            RETURN u.id AS usuario, COUNT(*) AS vecinos
            ORDER BY vecinos DESC
            LIMIT 1
        """)
        record = result.single()
        if record:
            print(f"Usuario con más vecinos: {record['usuario']} ({record['vecinos']} vecinos)")


def apartado_41():
    """Ejecuta el apartado 4.1 completo."""
    print("\n=== 4.1 Similitudes entre usuarios ===")
    similitudes = calcular_similitudes(N_USUARIOS)
    driver = conectar_neo4j()
    limpiar_neo4j(driver)
    cargar_similitudes_neo4j(driver, similitudes)
    usuario_mas_vecinos(driver)
    driver.close()


# 4.2 Enlaces entre usuarios y artículos

def apartado_42():
    """Ejecuta el apartado 4.2 completo."""
    print("\n=== 4.2 Enlaces entre usuarios y artículos ===")

    categorias = ["Toys and Games", "Video Games", "Digital Music", "Musical Instruments"]
    print("Categorías disponibles:")
    for i, cat in enumerate(categorias, 1):
        print(f"{i}. {cat}")

    while True:
        op = input("Selecciona categoría: ").strip()
        if op.isdigit() and 1 <= int(op) <= len(categorias):
            categoria = categorias[int(op) - 1]
            break
        print("Opción no válida.")

    while True:
        n_str = input("Número de artículos aleatorios a mostrar: ").strip()
        if n_str.isdigit() and int(n_str) > 0:
            n_articulos = int(n_str)
            break
        print("Introduce un número válido.")

    conn, cursor = conectar_mysql()
    cursor.execute("""
        SELECT asin FROM Producto
        WHERE categoria = %s
        ORDER BY RAND()
        LIMIT %s
    """, (categoria, n_articulos))
    asins = [row[0] for row in cursor.fetchall()]

    driver = conectar_neo4j()
    limpiar_neo4j(driver)

    with driver.session() as session:
        for asin in asins:
            cursor.execute("""
                SELECT reviewerID, overall, unixReviewTime
                FROM Review WHERE asin = %s
            """, (asin,))
            reviews = cursor.fetchall()

            session.run("MERGE (p:Producto {asin: $asin})", asin=asin)
            for reviewer_id, overall, unix_time in reviews:
                session.run("""
                    MERGE (u:Usuario {id: $uid})
                    MERGE (p:Producto {asin: $asin})
                    MERGE (u)-[:REVISA {nota: $nota, tiempo: $tiempo}]->(p)
                """, uid=reviewer_id, asin=asin, nota=overall, tiempo=unix_time)

    cursor.close(); conn.close()
    driver.close()
    print("Carga en Neo4J finalizada. Puedes consultar los datos.")


# 4.3 Usuarios con más de un tipo de artículo

def apartado_43():
    """Ejecuta el apartado 4.3 completo."""
    print("\n=== 4.3 Usuarios con más de un tipo de artículo ===")

    conn, cursor = conectar_mysql()

    # 400 primeros usuarios ordenados por nombre
    cursor.execute("""
        SELECT reviewerID FROM Usuario
        ORDER BY reviewerName
        LIMIT 400
    """)
    usuarios = [row[0] for row in cursor.fetchall()]

    driver = conectar_neo4j()
    limpiar_neo4j(driver)

    with driver.session() as session:
        for uid in usuarios:
            cursor.execute("""
                SELECT p.categoria, COUNT(*) as num
                FROM Review r
                JOIN Producto p ON r.asin = p.asin
                WHERE r.reviewerID = %s
                GROUP BY p.categoria
            """, (uid,))
            categorias = cursor.fetchall()

            if len(categorias) < 2:
                continue  # Solo usuarios con más de un tipo

            session.run("MERGE (u:Usuario {id: $uid})", uid=uid)
            for categoria, num in categorias:
                session.run("""
                    MERGE (t:Tipo {nombre: $cat})
                    MERGE (u:Usuario {id: $uid})
                    MERGE (u)-[:CONSUME {cantidad: $num}]->(t)
                """, uid=uid, cat=categoria, num=num)

    cursor.close(); conn.close()
    driver.close()
    print("Carga en Neo4J finalizada. Puedes consultar los datos.")


# 4.4 Artículos populares y artículos en común

def apartado_44():
    """Ejecuta el apartado 4.4 completo."""
    print("\n=== 4.4 Artículos populares con menos de 40 reviews ===")

    conn, cursor = conectar_mysql()
    cursor.execute("""
        SELECT asin, COUNT(*) as num_reviews
        FROM Review
        GROUP BY asin
        HAVING num_reviews < 40
        ORDER BY num_reviews DESC
        LIMIT 5
    """)
    articulos = [row[0] for row in cursor.fetchall()]

    driver = conectar_neo4j()
    limpiar_neo4j(driver)

    # Cargamos usuarios por artículo
    usuarios_por_articulo = defaultdict(set)
    with driver.session() as session:
        for asin in articulos:
            cursor.execute("""
                SELECT reviewerID FROM Review WHERE asin = %s
            """, (asin,))
            reviewers = [row[0] for row in cursor.fetchall()]
            usuarios_por_articulo[asin] = set(reviewers)

            session.run("MERGE (p:Producto {asin: $asin})", asin=asin)
            for uid in reviewers:
                session.run("""
                    MERGE (u:Usuario {id: $uid})
                    MERGE (p:Producto {asin: $asin})
                    MERGE (u)-[:REVISA]->(p)
                """, uid=uid, asin=asin)

        # Enlaces entre usuarios con artículos en común
        todos_usuarios = list({u for uids in usuarios_por_articulo.values() for u in uids})
        for i in range(len(todos_usuarios)):
            for j in range(i + 1, len(todos_usuarios)):
                u, v = todos_usuarios[i], todos_usuarios[j]
                # Contamos artículos en común entre ambos usuarios
                comunes = sum(
                    1 for uids in usuarios_por_articulo.values()
                    if u in uids and v in uids
                )
                if comunes > 0:
                    session.run("""
                        MERGE (a:Usuario {id: $u})
                        MERGE (b:Usuario {id: $v})
                        MERGE (a)-[:EN_COMUN {articulos_comunes: $comunes}]->(b)
                    """, u=u, v=v, comunes=comunes)

    cursor.close(); conn.close()
    driver.close()
    print("Carga en Neo4J finalizada. Puedes consultar los datos.")


# Menú principal

def menu():
    """Menú principal de neo4JProyecto."""
    opciones = {
        "1": ("Similitudes entre usuarios (4.1)", apartado_41),
        "2": ("Enlaces usuarios-artículos (4.2)", apartado_42),
        "3": ("Usuarios con más de un tipo de artículo (4.3)", apartado_43),
        "4": ("Artículos populares y artículos en común (4.4)", apartado_44),
        "0": ("Salir", None),
    }

    while True:
        print("\n========== NEO4J PROYECTO ==========")
        for key, (desc, _) in opciones.items():
            print(f"{key}. {desc}")
        print("=====================================")

        op = input("Selecciona una opción: ").strip()
        if op == "0":
            break
        elif op in opciones:
            try:
                opciones[op][1]()
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    menu()