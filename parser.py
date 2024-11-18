#Jeffrey Ni

from pymongo import MongoClient
from bs4 import BeautifulSoup

def log_status(message):
    print(f"[STATUS] {message}")

def connect_to_database():
    try:
        client = MongoClient('localhost', 27017)
        log_status("Successfully connected to MongoDB.")
        return client, client['cs_crawler']
    except Exception as e:
        log_status(f"Failed to connect to MongoDB: {e}")
        exit()

def get_page_content(collection, url):
    log_status(f"Searching for content in the database for URL: {url}")
    page_data = collection.find_one({'url': url})
    if page_data:
        log_status("HTML content retrieved successfully.")
        return page_data['html'].decode('utf-8')
    else:
        log_status("No HTML content found for the provided URL.")
        return None

def extract_faculty_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    faculty_sections = soup.select('div.clearfix')
    log_status(f"Number of faculty sections found: {len(faculty_sections)}")

    faculty_list = []

    for section in faculty_sections:
        header = section.find('h2')
        name = header.get_text(strip=True) if header else None

        if not name:
            log_status("Skipped a section with no name found.")
            continue

        position, office, phone, email, website = "", "", "", "", ""

        detail_block = section.find('p')
        if detail_block:
            text_segments = detail_block.get_text(separator="|", strip=True).split('|')

            details_mapping = {
                'title': '',
                'office': '',
                'phone': '',
                'email': '',
                'web': ''
            }

            for segment in text_segments:
                segment_lower = segment.lower()
                if 'title' in segment_lower:
                    details_mapping['title'] = segment.split(':', 1)[-1].strip()
                elif 'office' in segment_lower:
                    details_mapping['office'] = segment.split(':', 1)[-1].strip()
                elif 'phone' in segment_lower:
                    details_mapping['phone'] = segment.split(':', 1)[-1].strip()
                elif 'email' in segment_lower:
                    email_link = detail_block.find('a', href=True, text=lambda t: t and 'mailto:' in t)
                    if email_link:
                        details_mapping['email'] = email_link['href'].replace('mailto:', '')
                elif 'web' in segment_lower:
                    website_link = detail_block.find('a', href=True)
                    if website_link:
                        details_mapping['web'] = website_link['href']

            position = details_mapping['title']
            office = details_mapping['office']
            phone = details_mapping['phone']
            email = details_mapping['email']
            website = details_mapping['web']

        faculty_list.append({
            'name': name,
            'title': position,
            'office': office,
            'phone': phone,
            'email': email,
            'web': website
        })
        log_status(f"Extracted data for: {name}")

    return faculty_list

def store_faculty_data(collection, data_list):
    for record in data_list:
        collection.insert_one(record)
        log_status(f"Stored faculty data: {record['name']}")

mongo_client, db = connect_to_database()
pages_collection = db['pages']
professors_collection = db['professors']

target_page_url = 'https://www.cpp.edu/sci/computer-science/faculty-and-staff/permanent-faculty.shtml'
html_data = get_page_content(pages_collection, target_page_url)

if html_data:
    faculty_data = extract_faculty_data(html_data)
    store_faculty_data(professors_collection, faculty_data)
    log_status("All faculty data has been processed and stored.")
else:
    log_status("Failed to retrieve the HTML data. Exiting.")

mongo_client.close()
log_status("MongoDB connection closed.")
