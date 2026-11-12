MovieCrwal
===========

Fetch all movie credits for an actor using The Movie Database (TMDB) API.

Setup
-----

- Install the dependency:

```bash
pip install requests
```

- Set your TMDB API key in the environment:

```bash
export TMDB_API_KEY="your_tmdb_api_key_here"
```

Usage
-----

- Search an actor and list their cast credits:

```bash
python main.py "Tom Hanks"
```

- Include crew credits as well:

```bash
python main.py "Tom Hanks" --include-crew
```

Notes
-----
- The script uses the first search result for the provided name. If multiple people share the same name, specify a more exact query.
- Do not commit your API key to source control.
