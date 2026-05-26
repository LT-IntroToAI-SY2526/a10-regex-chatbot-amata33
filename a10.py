import re, string, calendar, requests, time
from wikipedia import WikipediaPage
import wikipedia
from bs4 import BeautifulSoup
from match import match
from typing import List, Callable, Tuple, Any, Match
import unicodedata
import lyricsgenius
genius = lyricsgenius.Genius("uFtMzxU9bDsCh46XITZRu2WKBNE_vjf0dYlig4YbIaZ5Mx_OeUiB4PPjxZ_NGUU-")




def get_page_html(title: str) -> str:
    search_response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": title, "format": "json"},
        headers={"User-Agent": "intro-ai-class/1.0"},
        timeout=10
    )
    results = search_response.json().get("query", {}).get("search", [])
    if results:
        title = results[0]["title"]  
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
    """Gets first infobox html from a Wikipedia page (summary box)


    Args:
        html - the full html of the page


    Returns:
        html of just the first infobox
    """
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all(class_="infobox")


    if not results:
        raise LookupError("Page has no infobox")
    return results[0].text




def clean_text(text: str) -> str:
    # 1. Normalize unicode (converts fancy dashes/accents to standard ones)
    text = unicodedata.normalize('NFKD', text)
   
    # 2. Filter out non-printable characters BUT keep newlines (\n)
    # This keeps the 'Label' on its own line so Regex can find it
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
    """Finds regex matches for a pattern


    Args:
        text - text to search within
        pattern - pattern to attempt to find within text
        error_text - text to display if pattern fails to match


    Returns:
        text that matches
    """
    p = re.compile(pattern, re.DOTALL | re.IGNORECASE)
    match = p.search(text)


    if not match:
        raise AttributeError(error_text)
    return match




def get_polar_radius(planet_name: str) -> str:
    """Gets the radius of the given planet


    Args:
        planet_name - name of the planet to get radius of


    Returns:
        radius of the given planet
    """
    infobox_text = clean_text(get_first_infobox_text(get_page_html(planet_name)))
    pattern = r"(?:Polar radius|Mean radius)(?:[^\d]*)(?P<radius>[\d,.]+)(?:.*?)km"
    error_text = "Page infobox has no polar radius information"
    match = get_match(infobox_text, pattern, error_text)


    return match.group("radius")




def get_birth_date(name: str) -> str:
    """Gets birth date of the given person


    Args:
        name - name of the person


    Returns:
        birth date of the given person
    """
    infobox_text = clean_text(get_first_infobox_text(get_page_html(name)))
    print(infobox_text)
    pattern = r"(?:Born|Date of birth|Born:)(?:\D*)(?P<birth>\d{4}-\d{2}-\d{2})"
    error_text = (
        "Page infobox has no birth information (at least none in xxxx-xx-xx format)"
    )
    match = get_match(infobox_text, pattern, error_text)


    return match.group("birth")


def get_death_date(name: str) -> str:
    """Gets death date of the given person


    Args:
        name - name of the person


    Returns:
        death date of the given person
    """
    infobox_text = clean_text(get_first_infobox_text(get_page_html(name)))
    print(infobox_text)
    pattern = r"(?:Died)(?:[\w \d,]*\()(?P<death>\d{4}-\d{2}-\d{2})"
    error_text = (
        "Page infobox has no death information (at least none in xxxx-xx-xx format)"
    )
    match = get_match(infobox_text, pattern, error_text)


    return match.group("death")


# Getter functions Music
def get_album_genre(album_name: str) -> str:
    """Extracts the musical genre of an album."""
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))


    pattern = r"(?:Genre)\n(?P<genre>[A-Za-z-]+)"
    match = get_match(infobox_text, pattern, "Could not find the genre for this album.")
    return match.group("genre").strip()


def get_album_producer(album_name: str) -> str:
 
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))
   
 
    pattern = r"Producer(?:s)?\s*[:\s]*(?P<producer>.*)"
   


    match = re.search(pattern, infobox_text, re.IGNORECASE | re.MULTILINE)
   
    if not match:
        raise AttributeError("Could not find the producer for this album.")
   
 
    result = match.group("producer").strip()
   


    if not result or len(result) < 2:
        return "Multiple producers (see full Wikipedia article)"
       
    return result






def get_album_label(album_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(album_name)))


    pattern = r"Label\s*(?P<label>.+)"
   
    match = re.search(pattern, infobox_text, re.IGNORECASE)
    if not match:
        raise AttributeError("Label not found")
   


    return match.group("label").strip(": ").split('\n')[0]


#Getter functions Genius
def get_song_lyrics(song_query: str) -> str:
    """Fetches a song from Genius and uses Regex to strip out API metadata artifacts."""
    try:
        # Search for the song using the query string
        song = genius.search_song(song_query)
        if not song:
            return f"Could not find the song '{song_query}' on Genius."
       
        raw_lyrics = song.lyrics


        # --- REGEX CLEANING ---
        # 1. Strip the "Song Title Lyrics" header from the start of the text
        # Example: "Bohemian Rhapsody Lyrics [Verse 1]" -> " [Verse 1]"
        cleaned = re.sub(r"^.*?Lyrics", "", raw_lyrics, flags=re.IGNORECASE)


        # 2. Strip the trailing "Embed" and trailing digits from the very end of the text
        # Example: "Mama, life had just begun... 42Embed" -> "Mama, life had just begun..."
        cleaned = re.sub(r"\d*Embed$", "", cleaned)


        # 3. Strip the "You might also like" text if it shows up at the bottom
        cleaned = re.sub(r"You might also like.*$", "", cleaned, flags=re.IGNORECASE)


        return cleaned.strip()


    except Exception as e:
        return f"An error occurred while fetching lyrics: {str(e)}"

def get_album_tracklist(album_query: str) -> str:
    """Fetches an album from Genius, using Regex to handle artist splits and clean track names."""
    try:
        # 1. Regex to check if the user specified an artist using "by [Artist]"
        # Example: "After Hours by The Weeknd" -> Group 1: "After Hours", Group 2: "The Weeknd"
        artist_split = re.search(r"^(.*?)\s+by\s+(.*)$", album_query, flags=re.IGNORECASE)
        
        if artist_split:
            album_name = artist_split.group(1).strip()
            artist_name = artist_split.group(2).strip()
            # search_album performs much better when artist and album are separated
            album = genius.search_album(album_name, artist_name)
        else:
            album = genius.search_album(album_query)
            
        if not album:
            return f"Could not find the album '{album_query}' on Genius."
        
        tracklist_lines = []
        for track in album.tracks:
            track_num = track.number
            track_title = track.song.title
            
            # 2. Regex to clean hidden zero-width spaces/unicode artifacts common in Genius data
            track_title = re.sub(r"[\u200b\u200e\u200f\u00ad]", "", track_title).strip()
            
            tracklist_lines.append(f"{track_num}. {track_title}")
            
        return f"\n--- {album.name} Tracklist ---\n" + "\n".join(tracklist_lines)

    except Exception as e:
        return f"An error occurred while fetching the tracklist: {str(e)}"


def album_tracklist(matches: List[str]) -> List[str]:
    """Action function that joins the parsed match strings and looks up the tracklist."""
    return [get_album_tracklist(" ".join(matches))]

def birth_date(matches: List[str]) -> List[str]:
    """Returns birth date of named person in matches


    Args:
        matches - match from pattern of person's name to find birth date of


    Returns:
        birth date of named person
    """
    return [get_birth_date(" ".join(matches))]


def death_date(matches: List[str]) -> List[str]:
    """Returns death date of named person in matches


    Args:
        matches - match from pattern of person's name to find death date of


    Returns:
        death date of named person
    """
    return [get_death_date(" ".join(matches))]


def polar_radius(matches: List[str]) -> List[str]:
    """Returns polar radius of planet in matches


    Args:
        matches - match from pattern of planet to find polar radius of


    Returns:
        polar radius of planet
    """
    return [get_polar_radius(matches[0])]


# Action functions
def album_genre(matches: List[str]) -> List[str]:
    return [get_album_genre(" ".join(matches))]


def album_producer(matches: List[str]) -> List[str]:
    return [get_album_producer(" ".join(matches))]


def album_label(matches: List[str]) -> List[str]:
    return [get_album_label(" ".join(matches))]


# dummy argument is ignored and doesn't matter
def bye_action(dummy: List[str]) -> None:
    raise KeyboardInterrupt


def song_lyrics(matches: List[str]) -> List[str]:
    """Action function that joins the parsed match strings and looks up the lyrics."""
    return [get_song_lyrics(" ".join(matches))]

# pa_list: List[Tuple[List[str], Callable[[List[str]], List[Any]]]] = [...]
Pattern = List[str]
Action = Callable[[List[str]], List[Any]]


# The pattern-action list for the natural language query system. It must be declared
# here, after all of the function definitions
pa_list: List[Tuple[Pattern, Action]] = [
    ("when was % born".split(), birth_date),
    ("when did % die".split(), death_date),
    ("what is the polar radius of %".split(), polar_radius),
    # album patterns lol
    ("what genre is %".split(), album_genre),
    ("who produced %".split(), album_producer),
    ("what label released %".split(), album_label),
    ("who put out %".split(), album_label),
    ("which record label released %".split(), album_label),
    # New lyric patterns
    ("what are the lyrics to %".split(), song_lyrics),
    ("sing %".split(), song_lyrics),
    ("tracklist for %".split(), album_tracklist),
    ("what tracks are on %".split(), album_tracklist),
    ("show tracks for %".split(), album_tracklist),
    (["bye"], bye_action)
]




def search_pa_list(src: List[str]) -> List[str]:
    """Takes source, finds matching pattern and calls corresponding action. If it finds
    a match but has no answers it returns ["No answers"]. If it finds no match it
    returns ["I don't understand"].


    Args:
        source - a phrase represented as a list of words (strings)


    Returns:
        a list of answers. Will be ["I don't understand"] if it finds no matches and
        ["No answers"] if it finds a match but no answers
    """
    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            answer = act(mat)
            return answer if answer else ["No answers"]


    return ["I don't understand"]






def query_loop() -> None:
    """The simple query loop. The try/except structure is to catch Ctrl-C or Ctrl-D
    characters and exit gracefully"""
    print("Welcome to the wikipedia chatbot!\n")
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




# uncomment the next line once you've implemented everything are ready to try it out
query_loop()
