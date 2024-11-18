#Jeffrey Ni

from bs4 import BeautifulSoup
import urllib.request
from pymongo import MongoClient, errors
from urllib.parse import urljoin, urlparse

try:
    mongo_client = MongoClient('localhost', 27017)
    db = mongo_client['cs_web_crawl']
    pages_collection = db['pages']
    print("Connected to MongoDB successfully.")
except errors.ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
    exit()

def store_html_to_db(url, content):
    try:
        pages_collection.insert_one({"url": url, "html": content.decode('utf-8', errors='ignore')})
        print(f"Page content for {url} stored in MongoDB.")
    except Exception as e:
        print(f"Failed to store content for {url}: {e}")

def is_target_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    header = soup.find('h1', class_='cpp-h1')
    if header and 'Permanent Faculty' in header.text:
        print("Target page found: 'Permanent Faculty'.")
        return True
    return False

def retrieve_html(url):
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request) as response:
            if 'text/html' in response.getheader('Content-Type', ''):
                page_content = response.read()
                print(f"Retrieved {url} (Size: {len(page_content)} bytes).")
                return page_content
            else:
                print(f"Skipped non-HTML content at {url}.")
    except urllib.error.HTTPError as http_err:
        print(f"HTTP error for {url}: {http_err}")
    except urllib.error.URLError as url_err:
        print(f"URL error for {url}: {url_err}")
    except Exception as e:
        print(f"Error retrieving {url}: {e}")
    return None

def extract_valid_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for anchor in soup.find_all('a', href=True):
        absolute_url = urljoin(base_url, anchor['href'])
        if urlparse(absolute_url).scheme in ['http', 'https'] and absolute_url.endswith(('.html', '.shtml')):
            links.add(absolute_url)
    return links

class CrawlerFrontier:
    def __init__(self, start_url):
        self.frontier = [start_url]
        self.visited = set()
        print(f"Starting with initial URL: {start_url}")

    def next_url(self):
        if self.frontier:
            url = self.frontier.pop(0)
            self.visited.add(url)
            print(f"Processing URL: {url}")
            return url
        return None

    def add_url(self, url):
        if url not in self.visited and url not in self.frontier:
            self.frontier.append(url)

    def is_done(self):
        return not self.frontier

    def clear_frontier(self):
        self.frontier.clear()
        print("Frontier cleared.")

def crawler_thread(frontier):
    while not frontier.is_done():
        current_url = frontier.next_url()
        if current_url:
            page_html = retrieve_html(current_url)
            if page_html:
                store_html_to_db(current_url, page_html)
                if is_target_page(page_html):
                    print(f"Target page located at {current_url}.")
                    frontier.clear_frontier()
                    return
                new_links = extract_valid_links(page_html, current_url)
                for link in new_links:
                    print(f"Found link: {link}")
                    frontier.add_url(link)

start_url = "https://www.cpp.edu/sci/computer-science/"
crawler_frontier = CrawlerFrontier(start_url)
crawler_thread(crawler_frontier)
mongo_client.close()
print("MongoDB connection closed.")
