import os
from pathlib import Path

import polars as pl
import seaborn as sns
from matplotlib import pyplot as plt


def check_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)


def check_all_files_size(folder_path: str) -> None:
    for file in os.listdir(folder_path):
        print(f"File {file} has size {check_file_size(folder_path + file) / 1000} KBs")


def data_exploration(ratings_path: Path, users_path: Path, books_path: Path) -> None:
    df_books = pl.read_csv(books_path, infer_schema_length=0)
    df_books = df_books.with_columns(pl.col('Year-Of-Publication').cast(pl.Int32, strict=False))
    print(f"Number of books with Nan or non numeric year of publication - {df_books['Year-Of-Publication'].null_count()}")
    print(
        f"Number of books with future year of publication - {len(df_books.filter(pl.col('Year-Of-Publication') > 2026))}")
    print(
        f"Number of books with year of publication at 0 - {len(df_books.filter(pl.col('Year-Of-Publication') == 0))}")
    df_books = df_books.drop_nulls()
    print(f"Number of ISBN duplicates is {df_books["ISBN"].is_duplicated().sum()}.")
    print(f"There is {len(df_books)} books.\n")

    df_users = pl.read_csv(users_path)
    print(f"Number of user id duplicates is {df_users["User-ID"].is_duplicated().sum()}.")
    print(f"There is {len(df_users)} users.")
    print(f"There is {df_users["Age"].null_count()} without age.")
    print(f"There is {df_users["Location"].null_count()} without location.\n")

    df_ratings = pl.read_csv(ratings_path)
    sns.histplot(data=df_ratings, x="Book-Rating")
    plt.show()

    print(f"There are {len(set(df_ratings["User-ID"]))} unique users with ratings.")
    print(f"There are {len(set(df_ratings["User-ID"]) - set(df_users["User-ID"]))} users from ratings unmapped to the Users.csv.")

    print(f"There are {len(set(df_ratings["ISBN"]))} books with at least one rating.")
    print(
        f"There are {len(set(df_ratings["ISBN"]) - set(df_books["ISBN"]))} books from ratings unmapped to the Books.csv.")

    ratings_per_book_count = df_ratings["ISBN"].unique_counts().sort(descending=True)
    sns.histplot(ratings_per_book_count, bins=50)
    plt.yscale("log")
    plt.xlabel("Number of ratings per book")
    plt.ylabel("Number of books")
    plt.show()

    ratings_per_user_count = df_ratings["User-ID"].unique_counts().sort(descending=True)
    sns.histplot(ratings_per_user_count, bins=50)
    plt.yscale("log")
    plt.xlabel("Number of ratings per user")
    plt.ylabel("Number of users")
    plt.show()


if __name__ == "__main__":
    data_exploration(Path("archive/Ratings.csv"), Path("archive/Users.csv"), Path("archive/Books.csv"))