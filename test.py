res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "UtauKBEM7Nz0Mj0mPAPNg", "isbns": isbn})
books = res.json()
print(f'The book "{title}" has an average rating of {books["books"][0]["average_rating"]} with {books["books"][0]["work_reviews_count"]} reviews', file=sys.stderr)
