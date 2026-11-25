# Autor: Eduardo Tovar Ruiz

# En este archivo se realizan los requisitos descritos en el enunciado de la parte 5
# realizando una recomendacion de articulos que un usuario no ha consumido previamente.

import mysql.connector

from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
)

CATEGORIAS = ["Toys and Games", "Video Games", "Digital Music", "Musical Instruments"]


# Conexión

def conectar_mysql():
    """Devuelve conexión y cursor a MySQL."""
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    return conn, conn.cursor()


# Recomendación

def top10_no_consumidos(reviewer_id, categoria):
    """
    Devuelve los 10 artículos más populares de una categoría
    que el usuario no ha consumido previamente.

    Args:
        reviewer_id: Identificador del usuario.
        categoria:   Tipo de artículo (categoría).

    Returns:
        Lista de tuplas (asin, num_reviews) o None si el usuario no existe.
    """
    conn, cursor = conectar_mysql()

    # Comprobamos que el usuario existe
    cursor.execute("SELECT COUNT(*) FROM Usuario WHERE reviewerID = %s", (reviewer_id,))
    if cursor.fetchone()[0] == 0:
        cursor.close(); conn.close()
        return None

    cursor.execute("""
        SELECT p.asin, COUNT(*) as popularidad
        FROM Review r
        JOIN Producto p ON r.asin = p.asin
        WHERE p.categoria = %s
          AND p.asin NOT IN (
              SELECT asin FROM Review WHERE reviewerID = %s
          )
        GROUP BY p.asin
        ORDER BY popularidad DESC
        LIMIT 10
    """, (categoria, reviewer_id))

    resultados = cursor.fetchall()
    cursor.close(); conn.close()
    return resultados




def main():
    reviewer_id = input("Introduce el ID del usuario: ").strip()

    print("\nCategorías disponibles:")
    for i, cat in enumerate(CATEGORIAS, 1):
        print(f"  {i}. {cat}")

    while True:
        op = input("Selecciona categoría: ").strip()
        if op.isdigit() and 1 <= int(op) <= len(CATEGORIAS):
            categoria = CATEGORIAS[int(op) - 1]
            break
        print("Opción no válida.")

    resultados = top10_no_consumidos(reviewer_id, categoria)

    if resultados is None:
        print(f"El usuario '{reviewer_id}' no existe.")
        return

    if not resultados:
        print("No hay artículos recomendables para este usuario en esta categoría.")
        return

    print(f"\nTop 10 artículos de '{categoria}' no consumidos por '{reviewer_id}':")
    for i, (asin, popularidad) in enumerate(resultados, 1):
        print(f"  {i}. {asin} ({popularidad} reviews)")


if __name__ == "__main__":
    main()