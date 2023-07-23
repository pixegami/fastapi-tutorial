# %%
import os
from typing import Literal, Optional
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Depends
import random
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from mangum import Mangum
import psycopg2
import boto3
import json

# %%
def get_secret_name():
    sm_get_secret = boto3.client("secretsmanager",region_name="eu-west-1")
    
    secrets = sm_get_secret.list_secrets(Filters=[
        {
                "Key": "tag-key",
                "Values": ["Name"]
        },
        {
                "Key": "tag-value",
                "Values": ["two-stack-app-db"]
        },
    ])
    return secrets["SecretList"][0]["Name"]  



def get_cluster_name():
    rds = boto3.client("rds",region_name="eu-west-1")
    
    response = rds.describe_db_clusters(DBClusterIdentifier='two-stack-app-db')
    return response["DBClusters"][0]["Endpoint"], response["DBClusters"][0]["DatabaseName"]

SECRET_NAME = get_secret_name()
CLUSTER_ENDPOINT, DATABASE = get_cluster_name()

app = FastAPI()
handler = Mangum(app)

# %%
def get_database_url():
    # Retrieve secret values from AWS Secrets Manager
    secret_client = boto3.client("secretsmanager",region_name="eu-west-1")
    response = secret_client.get_secret_value(SecretId=SECRET_NAME)
    secret = response["SecretString"]
    secret_dict = json.loads(secret)
    # Form the DATABASE_URL string
    username = secret_dict["username"]
    password = secret_dict["password"]
    host = CLUSTER_ENDPOINT
    port = 5432
    database_name = DATABASE
    return f"postgresql://{username}:{password}@{host}:{port}/{database_name}"


class Book(BaseModel):
    name: str
    genre: Literal["fiction", "non-fiction"]
    price: float
    book_id: Optional[str] = uuid4().hex

# %%
def get_connection():
    # Establish a connection to the PostgreSQL database
    return psycopg2.connect(get_database_url())


# %% Create sample dat
def create_sample_data():
    BOOKS_FILE = "books.json"
    BOOKS = []

    if os.path.exists(BOOKS_FILE):
        with open(BOOKS_FILE, "r") as f:
            BOOKS = json.load(f)

    connection = psycopg2.connect(get_database_url())
    with connection.cursor() as cursor:
        query = 'CREATE TABLE IF NOT EXISTS books(book_id varchar(200) NOT NULL,genre varchar(100),name varchar(1000),price float)'
        cursor.execute(query)
        connection.commit()
        print(query)

    for book in BOOKS:
        query = "INSERT INTO books (name, genre, price, book_id) VALUES (%s, %s, %s, %s)"
        with connection.cursor() as cursor:
                cursor.execute(query, (book['name'], book['genre'], book['price'], book['book_id']))
                connection.commit()
                print(query)


create_sample_data()
# %%
@app.get("/")
async def root():
    return {"message": "Welcome to my bookstore app!"}

@app.get("/random-book")
async def random_book(connection=Depends(get_connection)):
    with connection.cursor() as cursor:
        query = "SELECT * FROM books"
        cursor.execute(query)
        books = cursor.fetchall()
        return random.choice(books)

@app.get("/list-books")
async def list_books(connection=Depends(get_connection)):
    with connection.cursor() as cursor:
        query = "SELECT * FROM books"
        cursor.execute(query)
        books = cursor.fetchall()
        return {"books": books}

@app.get("/book_by_index/{index}")
async def book_by_index(index: int, connection=Depends(get_connection)):
    with connection.cursor() as cursor:
        query = "SELECT * FROM books WHERE id = %s"
        cursor.execute(query, (index,))
        book = cursor.fetchone()
        if book:
            return book
        else:
            raise HTTPException(404, f"Book index {index} out of range.")

@app.post("/add-book")
async def add_book(book: Book, connection=Depends(get_connection)):
    with connection.cursor() as cursor:
        query = "INSERT INTO books (name, genre, price, book_id) VALUES (%s, %s, %s, %s) RETURNING id"
        book_id = uuid4().hex
        cursor.execute(query, (book.name, book.genre, book.price, book_id))
        connection.commit()
        return {"book_id": book_id}

@app.get("/get-book")
async def get_book(book_id: str, connection=Depends(get_connection)):
    with connection.cursor() as cursor:
        query = "SELECT * FROM books WHERE book_id = %s"
        cursor.execute(query, (book_id,))
        book = cursor.fetchone()
        if book:
            return book
        else:
            raise HTTPException(404, f"Book ID {book_id} not found in database.")



