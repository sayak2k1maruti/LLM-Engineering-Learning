import os
import sys
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv
import wikipediaapi

load_dotenv()

TMDB_BASE = "https://api.themoviedb.org/3"


def get_api_key():
    key = os.environ.get("TMDB_API_KEY")
    if not key:
        print("Error: TMDB_API_KEY environment variable not set.")
        print("Get an API key from https://www.themoviedb.org and set TMDB_API_KEY.")
        sys.exit(1)
    return key


def search_person(api_key: str, name: str):
    url = f"{TMDB_BASE}/search/person"
    resp = requests.get(url, params={"api_key": api_key, "query": name})
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    return results


def get_movie_credits(api_key: str, person_id: int):
    url = f"{TMDB_BASE}/person/{person_id}/movie_credits"
    resp = requests.get(url, params={"api_key": api_key})
    resp.raise_for_status()
    return resp.json()

def get_movie_details(api_key: str, movie_id: int):
    url = f"{TMDB_BASE}/movie/{movie_id}"
    resp = requests.get(url, params={"api_key": api_key})
    resp.raise_for_status()
    return resp.json()



def main():
    api_key = get_api_key()
    res = search_person(api_key, "Paoli Dam")
    # person_id = res[0]["id"] if res else None
    # movies = get_movie_credits(api_key, person_id)
    # with open("movies.json", "w") as f:
    #     import json

    #     json.dump(movies, f, indent=2)

    res = get_movie_details(api_key, 1020707)
    with open("movie.json", "w") as f:
        import json
        json.dump(res, f, indent=2)


    import wikipediaapi

    wiki = wikipediaapi.Wikipedia(

        language='en',

        user_agent='movie-finder-app'

    )

    page = wiki.page("Tobu Aporichito")
    print(page.text)
if __name__ == "__main__":
    main()
