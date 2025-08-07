import time, json, requests, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

with open('config.json', 'r') as f:
    config = json.load(f)

NAS_IP = str(config['NAS']['ip'])
NAS_PORT = int(config['NAS']['port'])
NAS_USER = str(config['NAS']['username'])
NAS_PWD = str(config['NAS']['password'])
FAILED_LOG = "logs/failed.txt"

os.makedirs(os.path.dirname(FAILED_LOG), exist_ok=True)

class Colors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"

def get_movie_list(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        movies = [line.strip() for line in f if line.strip()]

    return movies

def search_yts(movie_title):
    """
    Search YTS for a movie title and return the movie page URL.
    """
    query = movie_title.replace(" ", "%20")
    url = f"https://yts.mx/browse-movies/{query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')
    movie_link_tag = soup.select_one('.browse-movie-wrap a')

    return urljoin("https://yts.mx", movie_link_tag['href']) if movie_link_tag else None


def get_best_quality_magnet(movie_page_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(movie_page_url, headers=headers, timeout=10)

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')

    for quality in ["2160p", "1080p", "720p"]:
        for tag in soup.select('.modal-torrent'):
            if quality in tag.text:
                magnet = tag.select_one('a[href^="magnet:"]')
                if magnet:
                    return magnet['href']

    return None


def send_to_synology(magnet_link):
    login_payload = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": NAS_USER,
        "passwd": NAS_PWD,
        "session": "DownloadStation",
        "format": "sid"
    }
    login_url = f"{NAS_IP}:{NAS_PORT}/webapi/auth.cgi"
    login_resp = requests.get(login_url, params=login_payload, timeout=10)

    if not login_resp.ok or not login_resp.json().get("success"):
        raise Exception("Login failed")

    sid = login_resp.json()["data"]["sid"]

    download_payload = {
        "api": "SYNO.DownloadStation.Task",
        "version": "1",
        "method": "create",
        "uri": magnet_link,
        "_sid": sid
    }
    download_url = f"{NAS_IP}:{NAS_PORT}/webapi/DownloadStation/task.cgi"
    download_resp = requests.post(download_url, data=download_payload, timeout=10)

    if not download_resp.ok or not download_resp.json().get("success"):
        raise Exception("Failed to add magnet link to Download Station")

    requests.get(login_url, params={
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "logout",
        "session": "DownloadStation",
        "_sid": sid
    }, timeout=5)


def log_failed_movie(movie, error_message):
    with open(FAILED_LOG, "a", encoding="utf-8") as failed_file:
        failed_file.write(f"{movie} - {error_message}\n")

def main():
    file_path = input(Colors.CYAN + ">" + Colors.RESET + " Location of (.txt) file: ").strip()

    try:
        movies = get_movie_list(file_path)
    except Exception as e:
        print(Colors.RED + "[ERROR]" + Colors.RESET + f"{e}")
        return

    print(Colors.GREEN + "[SUCCESS]" + Colors.RESET + f" Loaded {len(movies)} movies from file.")

    for movie in movies:
        print(Colors.CYAN + "[ATTEMPT]" + Colors.RESET + f" \nSearching: {movie}")
        try:
            page = search_yts(movie)
            if not page:
                print(Colors.RED + "[NOT FOUND]" + Colors.RESET + f" Not found: {movie}")
                log_failed_movie(movie, "Not found on YTS")
                continue

            magnet = get_best_quality_magnet(page)
            if not magnet:
                print(Colors.YELLOW + "[ERROR]" + Colors.RESET + f" No magnet link for item: {movie}")
                log_failed_movie(movie, "No magnet link found")
                continue

            print(Colors.GREEN + f"[SUCCESS]" + Colors.RESET + f" Sending to Synology: {movie}")
            send_to_synology(magnet)

            time.sleep(2)

        except Exception as e:
            print(Colors.RED + "[ERROR]" + Colors.RESET + f" Error: {movie} - {e}")
            log_failed_movie(movie, str(e))

    print(Colors.GREEN + "[SUCCESS]" + Colors.RESET + " Finished all items from list!")


if __name__ == "__main__":
    main()