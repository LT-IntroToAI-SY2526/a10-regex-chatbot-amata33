import re
import string
import calendar
import requests
import time
import unicodedata
from typing import List, Callable, Tuple, Any, Match
from bs4 import BeautifulSoup
from wikipedia import WikipediaPage
import wikipedia
import lyricsgenius
from match import match  # Assumes match.py is in your local directory

# =====================================================================
# CRITICAL FIX: Replace the placeholder below with your real token!
# Go to https://genius.com/api-clients to generate one if you haven't.
# =====================================================================


# Put your brand new Client Access Token here
genius = lyricsgenius.Genius("_6OpzpxlsFfIxCcCOTcP7wZE6kegTVd4SK8_i8Vkyx9EAhAIifdjGYAeRdKhD_rL")

try:
    # Try a simple fetch to see if it authenticates
    song = genius.search_song("Thriller", "Michael Jackson")
    print("Success! Token is valid.")
    print(song.lyrics[:100]) # Print just the first 100 characters
except Exception as e:
    print(f"Token failed. Error: {e}")

def get_page_html(title: str) -> str:
    search_response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": title, "format": "json"},
        headers={"User-Agent": "intro-ai-class/1.0"},
        timeout=10
    )
    results = search_response.json().get("query", {}).get("search", [])
    if results:
        title = results[0]["title"]  # use the top search result title
        print(f"Searching Wikipedia for: {title}")
    
    for attempt in range(5):
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json",
                "redirects": True,
            },
            headers={"User-Agent": "intro-ai-class/1.0"}
        )
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited — waiting {wait}s before retrying '{title}'...")
            time.sleep(wait)
            continue
        if response.status_code == 200 and response.text.strip():
            data = response.json()
            if "error" not in data:
                time.sleep(2)  # polite delay after every successful call
                return data["parse"]["text"]["*"]
    raise ConnectionError(f"Could not retrieve Wikipedia page for '{title}' after 5 attempts")


def get_first_infobox_text(html: str) -> str:
    """Gets first infobox html from a Wikipedia page (summary box)"""
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all(class_="infobox")

    if not results:
        raise LookupError("Page has no infobox")
    return results[0].text


def clean_text(text: str) -> str:
    # 1. Normalize unicode (converts fancy dashes/accents to standard ones)
    text = unicodedata.normalize('NFKD', text)
    
    # 2. Filter out non-printable characters BUT keep newlines (\n)
    clean_chars = []
    for char in text:
        if char in string.printable or char == '\n':
            clean_chars.append(char)
    
    cleaned = "".join(clean_chars)
    
    # 3. Collapse multiple spaces but DO NOT collapse newlines yet
    cleaned = re.sub(r" +", " ", cleaned)
    
    return cleaned


def get_match(
    text: str,
    pattern: str,
    error_text: str = "Page doesn't appear to have the property you're expecting",
) -> Match:
    """Finds regex matches for a pattern"""
    p = re.compile(pattern, re.DOTALL | re.IGNORECASE)
    match_obj = p.search(text)

    if not match_obj:
        raise AttributeError(error_text)
    return match_obj


def get_polar_radius(planet_name: str) -> str:
    """Gets the radius of the given planet"""
    infobox_text = clean_text(get_first_infobox_text(get_page_html(planet_name)))
    pattern = r"(?:Polar radius|Mean radius)(?:[^\d]*)(?P<radius>[\d,.]+)(?:.*?)km"
    error_text = "Page infobox has no polar radius information"
    match_obj = get_match(infobox_text, pattern, error_text)

    return match_obj.group("radius")


def get_birth_date(name: str) -> str:
    """Gets birth date of the given person"""
    infobox_text = clean_text(get_first_infobox_text(get_page_html(name)))
    print(infobox_text)
    pattern = r"(?:Born|Date of birth|Born:)(?:\D*)(?P<birth>\d{4}-\d{2}-\d{2})"
    error_text = "Page infobox has no birth information (at least none in xxxx-xx-xx format)"
    match_obj = get_match(infobox_text, pattern, error_text)

    return match_obj.group("birth")


def get_death_date(name: str) -> str:
    """Gets death date of the given person"""
    infobox_text = clean_text(get_first_infobox_text(get_page_html(name)))
    print(infobox_text)
    pattern = r"(?:Died)(?:[\w \d,]*\()(?P<death>\d{4}-\d{2}-\d{2})"
    error_text = "Page infobox has no death information (at least none in xxxx-xx-xx format)"
    match_obj = get_match(infobox_text, pattern, error_text)

    return match_obj.group("death")


# Getter functions Music
def get_album_genre(album_name: str) -> str:
    """Extracts the musical genre of an album."""
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))

    pattern = r"(?:Genre)\n(?P<genre>[A-Za-z-]+)"
    match_obj = get_match(infobox_text, pattern, "Could not find the genre for this album.")
    return match_obj.group("genre").strip()


def get_album_producer(album_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))
    pattern = r"Producer(?:s)?\s*[:\s]*(?P<producer>.*)"
    
    match_obj = re.search(pattern, infobox_text, re.IGNORECASE | re.MULTILINE)
    if not match_obj:
        raise AttributeError("Could not find the producer for this album.")
    
    result = match_obj.group("producer").strip()
    if not result or len(result) < 2:
        return "Multiple producers (see full Wikipedia article)"
        
    return result


def get_album_label(album_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))
    pattern = r"Label\s*(?P<label>.+)" 
    
    match_obj = re.search(pattern, infobox_text, re.IGNORECASE)
    if not match_obj:
        raise AttributeError("Label not found")
    
    return match_obj.group("label").strip(": ").split('\n')[0]


# Getter functions Genius
def get_song_lyrics(song_query: str) -> str:
    """Fetches a song from Genius and uses Regex to strip out API metadata artifacts."""
    if GENIUS_TOKEN == "YOUR_REAL_GENIUS_ACCESS_TOKEN_HERE":
        return "Error: You forgot to replace the placeholder token string with your actual Genius API token!"

    try:
        song = genius.search_song(song_query)
        if not song:
            return f"Could not find the song '{song_query}' on Genius."
        
        raw_lyrics = song.lyrics

        # --- REGEX CLEANING ---
        cleaned = re.sub(r"^.*?Lyrics", "", raw_lyrics, flags=re.IGNORECASE)
        cleaned = re.sub(r"\d*Embed$", "", cleaned)
        cleaned = re.sub(r"You might also like.*$", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    except Exception as e:
        return f"An error occurred while fetching lyrics: {str(e)}"


# Action functions
def birth_date(matches: List[str]) -> List[str]:
    return [get_birth_date(" ".join(matches))]


def death_date(matches: List[str]) -> List[str]:
    return [get_death_date(" ".join(matches))]


def polar_radius(matches: List[str]) -> List[str]:
    return [get_polar_radius(matches[0])]


def album_genre(matches: List[str]) -> List[str]:
    return [get_album_genre(" ".join(matches))]


def album_producer(matches: List[str]) -> List[str]:
    return [get_album_producer(" ".join(matches))]


def album_label(matches: List[str]) -> List[str]:
    return [get_album_label(" ".join(matches))]


def song_lyrics(matches: List[str]) -> List[str]:
    return [get_song_lyrics(" ".join(matches))]


def bye_action(dummy: List[str]) -> None:
    raise KeyboardInterrupt


Pattern = List[str]
Action = Callable[[List[str]], List[Any]]

pa_list: List[Tuple[Pattern, Action]] = [
    ("when was % born".split(), birth_date),
    ("when did % die".split(), death_date),
    ("what is the polar radius of %".split(), polar_radius),
    # Album patterns
    ("what genre is %".split(), album_genre),
    ("who produced %".split(), album_producer),
    ("what label released %".split(), album_label),
    ("who put out %".split(), album_label),
    ("which record label released %".split(), album_label),
    # Lyric patterns
    ("what are the lyrics to %".split(), song_lyrics),
    ("show me the lyrics for %".split(), song_lyrics),
    ("sing %".split(), song_lyrics),
    (["bye"], bye_action)
]


def search_pa_list(src: List[str]) -> List[str]:
    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            answer = act(mat)
            return answer if answer else ["No answers"]

    return ["I don't understand"]


def query_loop() -> None:
    print("Welcome to the chatbot!\n")
    while True:
        try:
            print()
            query = input("Your query? ").replace("?", "").lower().split()
            answers = search_pa_list(query)
            for ans in answers:
                print(ans)

        except (KeyboardInterrupt, EOFError):
            break

    print("\nSo long!\n")


if __name__ == "__main__":
    query_loop()