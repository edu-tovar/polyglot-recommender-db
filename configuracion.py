# Autor: Eduardo Tovar Ruiz
# En este archivo se definen las configuraciones de cada uno de los sistemas que se utilizaran
# Tambien se indican la ruta a los ficheros utilizados.
# Las credenciales se leen de variables de entorno (ver .env.example).

import os

# MySQL
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = "amazon_reviews"

# MongoDB
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "amazon_reviews"
MONGO_COLLECTION = "reviews_text"

# Neo4J
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


# Rutas de los ficheros
DATA_FILES = {
    "Toys and Games": "data/Toys_and_Games_5.json",
    "Video Games": "data/Video_Games_5.json",
    "Digital Music": "data/Digital_Music_5.json",
    "Musical Instruments": "data/Musical_Instruments_5.json",
}