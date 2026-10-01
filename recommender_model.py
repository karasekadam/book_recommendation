from abc import ABC, abstractmethod

import numpy as np
from sklearn.cluster import KMeans
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

import polars as pl

from database import load_ratings

RECOMMENDED_NUMBER = 10


class AbstractRecommender(ABC):
    def __init__(self, train_df: pl.DataFrame | None = None):
        # when no df is passed, loads from DB
        self.train_df = train_df if train_df is not None else load_ratings()

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def predict(self, user: int):
        pass


class RecommenderMostReadBook(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.most_read_books = None

    def load(self):
        self.most_read_books = self.train_df["ISBN"].value_counts().sort(descending=True, by="count")[:RECOMMENDED_NUMBER*10]

    def predict(self, user: int):
        user_history = set(self.train_df.filter(pl.col("User-ID") == user)["ISBN"])
        filtered_books = self.most_read_books.filter(~pl.col("ISBN").is_in(user_history))
        return list(filtered_books["ISBN"])[:RECOMMENDED_NUMBER]

    def __str__(self):
        return "Most Read Book Recommender"


class RecommenderMostReadBookByCountry(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.most_read_books = None
        self.most_read_books_by_country = {}

    def load(self):
        self.most_read_books = self.train_df["ISBN"].value_counts().sort(descending=True, by="count")[:RECOMMENDED_NUMBER*10]
        for country in self.train_df["country"].unique():
            country_ratings = self.train_df.filter(pl.col("country") == country)
            self.most_read_books_by_country[country] = country_ratings["ISBN"].value_counts().sort(descending=True, by="count")[:RECOMMENDED_NUMBER*10]

    def predict(self, user: int):
        user_history = set(self.train_df.filter(pl.col("User-ID") == user)["ISBN"])
        user_country = self.train_df.filter(pl.col("User-ID") == user)["country"].item(0)
        recommended_books = []
        if user_country in self.most_read_books_by_country:
            filtered_books = self.most_read_books_by_country[user_country].filter(~pl.col("ISBN").is_in(user_history))
            recommended_books.extend(list(filtered_books["ISBN"])[:RECOMMENDED_NUMBER])

        if len(recommended_books) < RECOMMENDED_NUMBER:
            filtered_books = self.most_read_books.filter(~pl.col("ISBN").is_in(user_history))
            recommended_books.extend(list(filtered_books["ISBN"])[:RECOMMENDED_NUMBER])

        return recommended_books[:RECOMMENDED_NUMBER]

    def __str__(self):
        return "Most Read Book By Country Recommender"


class RecommenderBestRatedBookSum(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.best_rated_books = None

    def load(self):
        self.best_rated_books = self.train_df.select(["ISBN", "Book-Rating"]).group_by("ISBN").sum().sort(descending=True, by="Book-Rating")[:RECOMMENDED_NUMBER * 10]

    def predict(self, user: int):
        user_history = set(self.train_df.filter(pl.col("User-ID") == user)["ISBN"])
        filtered_books = self.best_rated_books.filter(~pl.col("ISBN").is_in(user_history))
        return list(filtered_books["ISBN"])[:RECOMMENDED_NUMBER]

    def __str__(self):
        return "Sum of Ratings Recommender"


class RecommenderBestRatedBookMean(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.best_rated_books = None

    def load(self):
        self.best_rated_books = self.train_df.group_by("ISBN").agg(
    pl.col("User-ID").count(),
        pl.col("Book-Rating").mean(),
    ).sort(descending=True, by=["Book-Rating", "User-ID"])[:RECOMMENDED_NUMBER*10]

    def predict(self, user: int):
        user_history = set(self.train_df.filter(pl.col("User-ID") == user)["ISBN"])
        filtered_books = self.best_rated_books.filter(~pl.col("ISBN").is_in(user_history))
        return list(filtered_books["ISBN"])[:RECOMMENDED_NUMBER]

    def __str__(self):
        return "Mean of Ratings Recommender"


class RecommenderCommonHistory(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.most_read_books = None

    def load(self):
        ratings_per_book_count = self.train_df["ISBN"].value_counts().sort(descending=True, by="count")
        self.most_read_books = list(ratings_per_book_count["ISBN"][:RECOMMENDED_NUMBER])

    def predict(self, user: int):
        user_history = self.train_df.filter(pl.col("User-ID") == user)
        # number of books rated by each user
        books_by_user = self.train_df.group_by("User-ID").len()
        # keep only ratings relevant to the target user
        ratings_df_reduced = self.train_df.filter(pl.col("User-ID") != user).filter(
            pl.col("ISBN").is_in(user_history["ISBN"]))
        recommended_books = []

        if not ratings_df_reduced.is_empty():
            df_joined = ratings_df_reduced.join(user_history, on="ISBN", how="inner", suffix="_target")
            df_joined = df_joined.with_columns(
                (
                        (pl.col("Book-Rating") != 0) & (pl.col("Book-Rating_target") != 0)
                )
                .alias("Both_explicit_rating")
            )
            df_joined = df_joined.with_columns(
                pl.when(pl.col("Both_explicit_rating"))
                .then(
                    (pl.col("Book-Rating") - pl.col("Book-Rating_target")).abs()
                )
                .otherwise(None)
                .alias("Ratings_diff")
            )
            # calculate the ratings similarity
            df_joined_agg = df_joined.group_by("User-ID").agg(
                n_common=pl.len(),
                ratings_similarity=1 - (pl.col("Ratings_diff").mean() / 9),
                shared_ratings=pl.col("Both_explicit_rating").sum()
            ).sort("ratings_similarity", descending=True)
            df_joined_agg = df_joined_agg.with_columns(
                pl.col("ratings_similarity").fill_null(0)
            )

            df_joined_agg = df_joined_agg.join(books_by_user, on="User-ID", how="inner")
            # Calculate same books read similarity
            df_joined_agg = df_joined_agg.with_columns(
                (pl.col("n_common") / (pl.col("len") + len(user_history)))
                .alias("n_common_norm")
            )
            # Combine similarities
            df_joined_agg = df_joined_agg.with_columns(
                (pl.col("n_common_norm") + pl.col("ratings_similarity"))
                .alias("similarity_score")
            ).sort("similarity_score", descending=True)
            user_similarity = df_joined_agg[["User-ID", "similarity_score"]]

            user_already_read_books = set(user_history["ISBN"])
            for row in user_similarity.iter_rows():
                similar_user_books = set(
                    self.train_df.filter(pl.col("User-ID") == row[0]).sort("Book-Rating", descending=True)["ISBN"])
                recommended_books.extend(similar_user_books - user_already_read_books.union(set(recommended_books)))
                if len(recommended_books) >= RECOMMENDED_NUMBER:
                    break

        if len(recommended_books) < RECOMMENDED_NUMBER:
            recommended_books.extend(self.most_read_books)

        return recommended_books[:RECOMMENDED_NUMBER]

    def __str__(self):
        return "Common History Recommender"


class RecommenderClusters(AbstractRecommender):
    def __init__(self, train_df: pl.DataFrame | None = None):
        super().__init__(train_df)
        self.most_read_books = None
        self.user_to_cluster = None
        self.cluster_to_users = None
        self.cluster_to_best_books = {}

    def load(self):
        users, rows = np.unique(self.train_df["User-ID"].to_numpy(), return_inverse=True)
        books, cols = np.unique(self.train_df["ISBN"].to_numpy(), return_inverse=True)

        # ignoring ratings by setting all read books to 1, all unread to 0
        train_df = self.train_df.with_columns(
            pl.lit(1).alias("Book-Rating")
        )
        ratings = train_df["Book-Rating"].to_numpy()

        R = csr_matrix(
            (ratings, (rows, cols)),
            shape=(len(users), len(books))
        )

        # Normalize to popularity of item, reduce dimensions, and rescale values
        R_tfidf = TfidfTransformer().fit_transform(R)
        user_emb = TruncatedSVD(n_components=50).fit_transform(R_tfidf)
        user_emb = normalize(user_emb)

        # calculate clusters
        kmeans = KMeans(n_clusters=50, n_init=10)
        clusters = kmeans.fit_predict(user_emb)
        self.user_to_cluster =  {user_id: cluster for user_id, cluster in zip(users, clusters)}
        self.cluster_to_users = {c: users[clusters == c] for c in np.unique(clusters)}
        for cluster in self.cluster_to_users:
            cluster_ratings = self.train_df.filter(pl.col("User-ID").is_in(self.cluster_to_users[cluster]))
            most_read = cluster_ratings["ISBN"].value_counts().sort(descending=True, by="count")
            self.cluster_to_best_books[cluster] = most_read[:RECOMMENDED_NUMBER * 10]

    def predict(self, user: int):
        user_cluster = self.user_to_cluster[user]
        cluster_most_read = self.cluster_to_best_books[user_cluster]
        user_history = set(self.train_df.filter(pl.col("User-ID") == user)["ISBN"])
        filtered_books = cluster_most_read.filter(~pl.col("ISBN").is_in(user_history))
        return list(filtered_books[:RECOMMENDED_NUMBER]["ISBN"])

    def __str__(self):
        return "Clusters Recommender"




