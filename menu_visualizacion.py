# Autor: Eduardo Tovar Ruiz

# En este archivo se crea un menu de visualizacion de los datos extraidos de los json.

# Al ejecutarse se muestra un menu con varias opciones de visualizacion en donde el usuario
# debe escoger el grafico que desea ver y a continuacion la categoria que se quiere analizar.

import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pymysql
from pymongo import MongoClient

from configuracion import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    MONGO_URI, MONGO_DB, MONGO_COLLECTION
)

CATEGORIAS = ["Toys and Games", "Video Games", "Digital Music", "Musical Instruments"]


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
    """Devuelve la colección de MongoDB."""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB][MONGO_COLLECTION], client


# Utilidades

def pedir_categoria():
    """Pide al usuario que seleccione una categoría o 'todo'."""
    print("\nCategorías disponibles:")
    for i, cat in enumerate(CATEGORIAS, 1):
        print(f"  {i}. {cat}")
    print("  0. Todas")
    while True:
        opcion = input("Selecciona opción: ").strip()
        if opcion == "0":
            return None
        if opcion.isdigit() and 1 <= int(opcion) <= len(CATEGORIAS):
            return CATEGORIAS[int(opcion) - 1]
        print("Opción no válida.")


def filtro_categoria(categoria):
    """Devuelve la cláusula WHERE y parámetros según categoría."""
    if categoria:
        return "WHERE p.categoria = %s", (categoria,)
    return "", ()


# Opción 1: Evolución de reviews por año

def reviews_por_año():
    """Histograma del número de reviews por año."""
    categoria = pedir_categoria()
    conn, cursor = conectar_mysql()

    where, params = filtro_categoria(categoria)
    query = f"""
        SELECT YEAR(r.reviewTime), COUNT(*)
        FROM Review r
        JOIN Producto p ON r.asin = p.asin
        {where}
        GROUP BY YEAR(r.reviewTime)
        ORDER BY YEAR(r.reviewTime)
    """
    cursor.execute(query, params)
    resultados = cursor.fetchall()
    cursor.close(); conn.close()

    años  = [str(row[0]) for row in resultados]
    counts = [row[1] for row in resultados]
    titulo = f"Reviews por año — {categoria or 'todos los productos'}"

    plt.figure(figsize=(12, 5))
    plt.bar(años, counts)
    plt.title(titulo)
    plt.xlabel("Año")
    plt.ylabel("Número de reviews")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# Opción 2: Popularidad de artículos

def popularidad_articulos():
    """Curva de popularidad (nº reviews por artículo, ordenado desc)."""
    categoria = pedir_categoria()
    conn, cursor = conectar_mysql()

    where, params = filtro_categoria(categoria)
    query = f"""
        SELECT COUNT(*) as num_reviews
        FROM Review r
        JOIN Producto p ON r.asin = p.asin
        {where}
        GROUP BY r.asin
        ORDER BY num_reviews DESC
    """
    cursor.execute(query, params)
    counts = [row[0] for row in cursor.fetchall()]
    cursor.close(); conn.close()

    titulo = f"Popularidad de artículos — {categoria or 'todos los productos'}"
    plt.figure(figsize=(12, 5))
    plt.plot(range(len(counts)), counts)
    plt.title(titulo)
    plt.xlabel("Artículos")
    plt.ylabel("Número de reviews")
    plt.tight_layout()
    plt.show()


# Opción 3: Histograma por nota

def histograma_por_nota():
    """Histograma de reviews agrupadas por nota (1-5)."""
    print("\n¿Filtrar por artículo individual? (s/n): ", end="")
    individual = input().strip().lower() == "s"

    conn, cursor = conectar_mysql()

    if individual:
        asin = input("Introduce el ASIN del artículo: ").strip()
        cursor.execute("""
            SELECT overall, COUNT(*) FROM Review
            WHERE asin = %s GROUP BY overall ORDER BY overall
        """, (asin,))
        resultados = cursor.fetchall()
        if not resultados:
            print("Artículo no encontrado.")
            cursor.close(); conn.close()
            return
        titulo = f"Reviews por nota — artículo {asin}"
    else:
        categoria = pedir_categoria()
        where, params = filtro_categoria(categoria)
        query = f"""
            SELECT r.overall, COUNT(*)
            FROM Review r
            JOIN Producto p ON r.asin = p.asin
            {where}
            GROUP BY r.overall ORDER BY r.overall
        """
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        titulo = f"Reviews por nota — {categoria or 'todos los productos'}"

    cursor.close(); conn.close()

    notas  = [str(int(row[0])) for row in resultados]
    counts = [row[1] for row in resultados]

    plt.figure(figsize=(8, 5))
    plt.bar(notas, counts)
    plt.title(titulo)
    plt.xlabel("Nota")
    plt.ylabel("Número de reviews")
    plt.tight_layout()
    plt.show()


# Opción 4: Evolución acumulada por categoría

def evolucion_temporal():
    """Evolución acumulada del número de reviews a lo largo del tiempo."""
    conn, cursor = conectar_mysql()

    plt.figure(figsize=(12, 5))

    for categoria in CATEGORIAS:
        cursor.execute("""
            SELECT r.unixReviewTime
            FROM Review r
            JOIN Producto p ON r.asin = p.asin
            WHERE p.categoria = %s
            ORDER BY r.unixReviewTime
        """, (categoria,))
        timestamps = [row[0] for row in cursor.fetchall()]
        if timestamps:
            plt.plot(timestamps, range(1, len(timestamps) + 1), label=categoria)

    cursor.close(); conn.close()

    plt.title("Evolución acumulada de reviews a lo largo del tiempo")
    plt.xlabel("Tiempo (unix timestamp)")
    plt.ylabel("Número de reviews acumuladas")
    plt.legend()
    plt.tight_layout()
    plt.show()


# Opción 5: Histograma de reviews por usuario

def reviews_por_usuario():
    """Histograma: eje x = nº reviews, eje y = nº usuarios con esa cantidad."""
    conn, cursor = conectar_mysql()
    cursor.execute("""
        SELECT COUNT(*) as num_reviews
        FROM Review
        GROUP BY reviewerID
    """)
    counts = [row[0] for row in cursor.fetchall()]
    cursor.close(); conn.close()

    plt.figure(figsize=(12, 5))
    plt.hist(counts, bins=100)
    plt.title("Distribución de reviews por usuario")
    plt.xlabel("Número de reviews")
    plt.ylabel("Número de usuarios")
    plt.tight_layout()
    plt.show()


# Opción 6: Nube de palabras

def nube_palabras():
    """Nube de palabras del campo summary para una categoría concreta."""
    print("\nCategorías disponibles:")
    for i, cat in enumerate(CATEGORIAS, 1):
        print(f"  {i}. {cat}")
    while True:
        opcion = input("Selecciona categoría (no se permite 'todas'): ").strip()
        if opcion.isdigit() and 1 <= int(opcion) <= len(CATEGORIAS):
            categoria = CATEGORIAS[int(opcion) - 1]
            break
        print("Opción no válida.")

    # Obtenemos los ASINs
    conn, cursor = conectar_mysql()
    cursor.execute("SELECT asin FROM Producto WHERE categoria = %s", (categoria,))
    asins = {row[0] for row in cursor.fetchall()}
    cursor.close(); conn.close()

    # Obtenemos los summaries desde MongoDB
    mongo_col, mongo_client = conectar_mongo()
    texto_completo = []
    for doc in mongo_col.find({"asin": {"$in": list(asins)}}, {"summary": 1}):
        summary = doc.get("summary", "")
        palabras = [p.strip(".,!?\"'") for p in summary.split()]
        palabras = [p for p in palabras if len(p) > 3]
        texto_completo.extend(palabras)
    mongo_client.close()

    if not texto_completo:
        print("No hay datos para esta categoría.")
        return

    wc = WordCloud(width=800, height=400, background_color="white")
    wc.generate(" ".join(texto_completo))

    plt.figure(figsize=(12, 6))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title(f"Nube de palabras — {categoria}")
    plt.tight_layout()
    plt.show()


# Opción 7: nota media por categoría

def nota_media_por_categoria():
    """Gráfica de barras con la nota media de cada categoría."""
    conn, cursor = conectar_mysql()
    cursor.execute("""
        SELECT p.categoria, AVG(r.overall)
        FROM Review r
        JOIN Producto p ON r.asin = p.asin
        GROUP BY p.categoria
        ORDER BY AVG(r.overall) DESC
    """)
    resultados = cursor.fetchall()
    cursor.close(); conn.close()

    categorias = [row[0] for row in resultados]
    medias     = [round(row[1], 2) for row in resultados]

    plt.figure(figsize=(10, 5))
    bars = plt.bar(categorias, medias, color="steelblue")
    plt.bar_label(bars, fmt="%.2f")
    plt.title("Nota media por categoría")
    plt.xlabel("Categoría")
    plt.ylabel("Nota media")
    plt.ylim(0, 5.5)
    plt.tight_layout()
    plt.show()


# Menú

def menu():
    """Muestra el menú y ejecuta la opción seleccionada en bucle."""
    opciones = {
        "1": ("Evolución de reviews por año", reviews_por_año),
        "2": ("Popularidad de artículos", popularidad_articulos),
        "3": ("Histograma por nota", histograma_por_nota),
        "4": ("Evolución acumulada por categoría", evolucion_temporal),
        "5": ("Histograma de reviews por usuario", reviews_por_usuario),
        "6": ("Nube de palabras por categoría",nube_palabras),
        "7": ("Nota media por categoría",nota_media_por_categoria),
        "0": ("Salir",None),
    }

    while True:
        print("\n========== MENÚ DE VISUALIZACIÓN ==========")
        for key, (descripcion, _) in opciones.items():
            print(f"  {key}. {descripcion}")
        print("============================================")

        opcion = input("Selecciona una opción: ").strip()

        if opcion == "0":
            break
        elif opcion in opciones:
            try:
                opciones[opcion][1]()
            except Exception as e:
                print(f"Error al ejecutar la opción: {e}")
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    menu()