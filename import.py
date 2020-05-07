import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

DATABASE_URL="postgres://egqfcobdaxoapu:698b8a61621b798f2d166e4e79ff82002a969f0d5477f04332be7bbcb4236f99@ec2-52-23-14-156.compute-1.amazonaws.com:5432/d2qnu95qr432pv"
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("D:/Projects/project1/books.csv")
    
    reader = csv.reader(f)
    
    for isbn, title, author, year in reader:
    
        db.execute("INSERT INTO tblbooks (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added book {title} to our inventory.")
    db.commit()

if __name__ == "__main__":
    main()
