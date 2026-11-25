# polyglot-recommender-db

Polyglot persistence on Amazon product reviews: structured data in **MySQL**, review text in **MongoDB** and user–user / user–product graphs in **Neo4j**, with Python scripts to load the data, explore it and produce simple recommendations.

Final project for Databases (ICAI). Code and comments are in Spanish, as I originally wrote them.

> **Requirements and status.** Running the scripts requires local MySQL, MongoDB and Neo4j servers. The end-to-end run against the three databases has **not** been re-verified for this repository. The figures in this README describe the input data and were computed directly from the JSON files, without the databases.

## Data model

| Store | Content | Why there |
|---|---|---|
| MySQL | `Usuario(reviewerID, reviewerName)`, `Producto(asin, categoria)`, `Review(reviewerID, asin, overall, unixReviewTime, reviewTime, helpful_votes, total_votes)`, with foreign keys and primary key `(reviewerID, asin)` | Structured fields that are filtered, joined and aggregated (ratings, dates, categories) |
| MongoDB | Collection `reviews_text`: `reviewerID`, `asin`, `reviewText`, `summary` | Free text of variable length, used for the word clouds |
| Neo4j | `Usuario`, `Producto` and `Tipo` nodes; `SIMILAR`, `REVISA`, `CONSUME` and `EN_COMUN` relationships | Graph queries: similar users, users connected through common products |

## Scripts

| File | What it does |
|---|---|
| `configuracion.py` | Connection settings and data file paths. Credentials are read from environment variables (see `.env.example`) |
| `load_data.py` | Creates the MySQL schema and the MongoDB collection, then streams the JSON files line by line into both stores |
| `inserta_dataset.py` | Adds a new category (Office Products) to an existing database, reusing existing users and skipping reviews already stored |
| `menu_visualizacion.py` | Interactive menu of charts: reviews per year, product popularity curve, rating histogram (global, by category or by product), cumulative reviews over time, reviews per user, word cloud of review summaries, mean rating per category |
| `neo4jProyecto.py` | Neo4j menu covering four analyses. **Similarity:** Pearson correlation between the 30 most active users (configurable), loaded as a similarity graph, plus the user with most neighbours. **User–product links:** links for randomly chosen products of a category. **Cross-category users:** users with reviews in more than one category. **Common products:** users connected through popular products with fewer than 40 reviews |
| `parte5.py` | Recommendation: the 10 most reviewed products of a category that a given user has not reviewed yet |

Pearson similarity between users u and v follows the project definition: the sum runs over the products both have rated, and r̄ᵤ, r̄ᵥ are each user's mean over all their ratings.

## Data

The project uses the 5-core subsets of the Amazon review data (McAuley et al., 2015; He & McAuley, 2016), in which every user and every product has at least 5 reviews. They are not included in this repository. Download and decompress them into `data/`:

```bash
mkdir -p data && cd data
for c in Toys_and_Games Video_Games Digital_Music Musical_Instruments Office_Products; do
  curl -LO "https://snap.stanford.edu/data/amazon/productGraph/categoryFiles/reviews_${c}_5.json.gz"
  gunzip -c "reviews_${c}_5.json.gz" > "${c}_5.json"
done
```

Computed from the JSON files, keeping only the first review of each (user, product) pair as the MySQL primary key does:

| Category | Reviews | Users | Products | Mean rating |
|---|---|---|---|---|
| Toys and Games | 167,597 | 19,412 | 11,924 | 4.36 |
| Video Games | 231,393 | 24,303 | 10,672 | 4.09 |
| Digital Music | 64,706 | 5,541 | 3,568 | 4.22 |
| Musical Instruments | 10,261 | 1,429 | 900 | 4.49 |
| Office Products (added by `inserta_dataset.py`) | 53,258 | 4,905 | 2,420 | 4.35 |

- The four categories loaded by `load_data.py` add up to 473,957 reviews from 48,555 users on 27,025 products, written between 1998 and 2014.
- 2,028 users have reviews in at least two of those categories.
- `Video_Games_5.json` contains 387 repeated (user, product) pairs, which the loader skips in both MySQL and MongoDB.

## How to run

```bash
pip install -r requirements.txt
# MySQL, MongoDB and Neo4j must be running locally (default ports)
export MYSQL_USER=... MYSQL_PASSWORD=... NEO4J_PASSWORD=...
python load_data.py            # load MySQL + MongoDB
python menu_visualizacion.py   # charts
python neo4jProyecto.py        # graph analyses
python parte5.py               # recommendations for a user
python inserta_dataset.py      # add the Office Products category
```

## Corrections relative to the submitted version

- `load_data.py` selected the database before creating it, so the first run on a new MySQL server failed. The database is now created first.
- `load_data.py` inserted the text of every review into MongoDB, including the duplicates that MySQL skipped. MongoDB now only receives reviews that were inserted in MySQL, as `inserta_dataset.py` already did.
- Credentials are no longer hard-coded in `configuracion.py`; they are read from environment variables.

## References

- J. McAuley, C. Targett, Q. Shi, A. van den Hengel. *Image-based recommendations on styles and substitutes.* SIGIR 2015.
- R. He, J. McAuley. *Ups and downs: Modeling the visual evolution of fashion trends with one-class collaborative filtering.* WWW 2016.
