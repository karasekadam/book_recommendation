from pathlib import Path

import polars as pl

from database import parse_location
from recommender_model import RecommenderMostReadBook, RecommenderBestRatedBookSum, RecommenderBestRatedBookMean, \
    RecommenderCommonHistory, RecommenderClusters, RecommenderMostReadBookByCountry

available_recommenders = [RecommenderMostReadBookByCountry, RecommenderClusters, RecommenderMostReadBook, RecommenderBestRatedBookSum,
                          RecommenderBestRatedBookMean, RecommenderCommonHistory]


def train_test_split(ratings_path: Path, user_paths: Path, test_size: float = 0.3) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Create training and testing dataset. Takes one last rating from selected test users as test sample.
    :param ratings_path: path to ratings file
    :param user_paths: path to users file
    :param test_size: fraction of test users
    :return: train and test df
    """
    df_users = pl.read_csv(user_paths)
    column_types = pl.Struct({"city": pl.String, "state": pl.String, "country": pl.String})

    df_users = df_users.with_columns(
        pl.col("Location")
        .map_elements(
            lambda loc: dict(zip(["city", "state", "country"], parse_location(loc))),
            return_dtype=column_types,
        )
        .alias("loc")
    ).unnest("loc")[["User-ID", "country"]]

    df = pl.read_csv(ratings_path)
    df = df.with_row_index("_row_id")
    df = df.join(df_users, how="left", on=["User-ID"])
    ratings_per_user = df["User-ID"].value_counts()
    many_ratings_per_user = ratings_per_user.filter(pl.col("count") > 3)
    df_active_users = df.filter(pl.col("User-ID").is_in(set(many_ratings_per_user["User-ID"])))

    test_users = (
        df_active_users.select("User-ID").unique()
        .sample(fraction=test_size)
        .to_series()
    )

    df_active_users = df_active_users.with_columns(
        pos=pl.int_range(pl.len()).over("User-ID"),
        n=pl.len().over("User-ID"),
    )

    is_test = (
            pl.col("User-ID").is_in(test_users)
            & (pl.col("pos") == (pl.col("n") - 1))
    )

    df_active_users = df_active_users.with_columns(is_test=is_test)

    train = df_active_users.filter(~pl.col("is_test")).select("User-ID", "ISBN", "Book-Rating", "country")
    test = df_active_users.filter(pl.col("is_test")).select("User-ID", "ISBN", "Book-Rating", "country")

    return train, test


def experiment_run() -> None:
    """
    Run the experiment on all available recommenders. Prints the recall
    :return: None
    """
    ratings_path = Path(__file__).parent / "archive" / "Ratings.csv"
    users_path = Path(__file__).parent / "archive" / "Users.csv"

    for recommender_class in available_recommenders:
        train, test = train_test_split(ratings_path, users_path)
        top_k_matches = 0
        recommender = recommender_class(train)
        print(f"Running {str(recommender)}")
        recommender.load()

        for i, row in enumerate(test.iter_rows()):
            if i % 1000 == 0:
                print(f"Processed {i} rows")
            # recommended_books = recommend_based_on_common_history(train, row[0])
            recommended_books = recommender.predict(row[0])
            true_label = test.filter(pl.col("User-ID") == row[0])["ISBN"].item()
            if true_label in recommended_books:
                top_k_matches += 1

        precision = round((top_k_matches / len(test)) * 100, 4)
        print(f"Recall: {precision}%")
        print()


if __name__ == "__main__":
    experiment_run()