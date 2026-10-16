import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import re
import random

def fetch_mal_top_anime(session, limit, retries=3):
    """Lấy HTML trang danh sách top anime."""
    url = f"https://myanimelist.net/topanime.php?limit={limit}"
    
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=15)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                print(f"Bị chặn 403 ở limit={limit}. Đợi 5s...")
                time.sleep(5)
            elif response.status_code == 429:
                print("Lỗi 429 Too Many Requests. Đợi 10s...")
                time.sleep(10)
            else:
                print(f"Lỗi {response.status_code} ở limit={limit}. Thử lại...")
                time.sleep(3)
                
        except Exception as e:
            print(f"Lỗi kết nối trang danh sách: {e}. Thử lại...")
            time.sleep(3)
            
    return None

def fetch_anime_details(session, url, retries=3):
    """Lấy thông tin chi tiết từng anime."""
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                details = {}
                
                # Lấy thông tin ở cột bên trái
                for div in soup.select('.spaceit_pad, .borderClass > div'):
                    span = div.select_one('.dark_text')
                    if span:
                        key = span.text.strip().replace(':', '')
                        links = div.find_all('a')
                        # Lấy danh sách từ các thẻ link
                        if links and key in ['Studios', 'Genres', 'Producers', 'Licensors', 'Theme', 'Themes']:
                            val = ', '.join([a.text.strip() for a in links if a.text.strip()])
                        else:
                            val = div.text.replace(span.text, '').strip()
                        details[key] = val
                
                # Tách scored_by từ chuỗi điểm số
                scored_by = None
                score_str = details.get("Score")
                if score_str:
                    match = re.search(r'scored by ([\d,]+)', score_str)
                    if match:
                        scored_by = int(match.group(1).replace(',', ''))
                
                # Xử lý favorites và popularity
                fav_str = details.get("Favorites")
                favorites = int(fav_str.replace(',', '')) if fav_str and fav_str.replace(',', '').isdigit() else None
                
                pop_str = details.get("Popularity")
                popularity = int(pop_str.replace('#', '').replace(',', '')) if pop_str else None

                # Gộp thể loại và chủ đề
                genres = details.get("Genres", "")
                themes = details.get("Theme", "") or details.get("Themes", "")
                full_genres = genres
                if themes:
                    full_genres = f"{genres}, {themes}" if genres else themes

                return {
                    "genres": full_genres,
                    "studio": details.get("Studios"),
                    "source": details.get("Source"),
                    "duration": details.get("Duration"),
                    "rating": details.get("Rating"),
                    "scored_by": scored_by,
                    "favorites": favorites,
                    "popularity": popularity
                }
                
            elif resp.status_code == 403:
                print("      Bị chặn 403 ở trang con. Đợi 5s...")
                time.sleep(5)
            elif resp.status_code == 429:
                print("      Lỗi 429 ở trang con. Đợi 10s...")
                time.sleep(10)
            else:
                time.sleep(2)
        except Exception as e:
            print(f"      Lỗi request trang con {url}: {e}")
            time.sleep(2)
            
    return None

def parse_anime_list_html(html):
    """Bóc tách danh sách anime từ HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    anime_list = []
    
    rows = soup.select('.ranking-list')
    for row in rows:
        try:
            rank_el = row.select_one('.rank span')
            rank = rank_el.text.strip() if rank_el else None
            
            title_el = row.select_one('.detail h3 a')
            title = title_el.text.strip() if title_el else None
            url = title_el['href'] if title_el else ""
            
            mal_id = None
            match_id = re.search(r'/anime/(\d+)/', url)
            if match_id:
                mal_id = match_id.group(1)
                
            score_el = row.select_one('.score .text')
            score_text = score_el.text.strip() if score_el else None
            score = float(score_text) if score_text and score_text != 'N/A' else None
            
            info_el = row.select_one('.information')
            anime_type = episodes = aired_year = members = None
            
            if info_el:
                info_lines = [line.strip() for line in info_el.text.strip().split('\n') if line.strip()]
                if len(info_lines) >= 3:
                    type_ep = info_lines[0]
                    if '(' in type_ep:
                        anime_type = type_ep.split('(')[0].strip()
                        ep_match = re.search(r'(\d+|\?) eps', type_ep)
                        if ep_match:
                            episodes = ep_match.group(1)
                    else:
                        anime_type = type_ep
                        
                    aired_str = info_lines[1]
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', aired_str)
                    if year_match:
                        aired_year = year_match.group(1)
                        
                    members_str = info_lines[2].replace(',', '').replace(' members', '')
                    members = int(members_str) if members_str.isdigit() else None

            anime_list.append({
                "mal_id": mal_id,
                "title": title,
                "rank": int(rank) if rank and rank.isdigit() else None,
                "score": score,
                "type": anime_type,
                "episodes": episodes,
                "aired_year": aired_year,
                "members": members,
                "url": url
            })
            
        except Exception as e:
            print(f"Lỗi parse dòng anime: {e}")
            
    return anime_list

def save_to_csv(data, filename):
    """Lưu dữ liệu ra file CSV."""
    if not data:
        return
    keys = data[0].keys()
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"Đã lưu file CSV: {filename}")
    except Exception as e:
        print(f"Lỗi lưu CSV: {e}")

def save_to_json(data, filename):
    """Lưu dữ liệu ra file JSON."""
    if not data:
        return
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Đã lưu file JSON: {filename}")
    except Exception as e:
        print(f"Lỗi lưu JSON: {e}")

def main():
    print("Bắt đầu cào dữ liệu từ MyAnimeList...")
    
    # Khởi tạo session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    })
    
    total_anime = 1000
    anime_per_page = 50
    total_pages = total_anime // anime_per_page
    
    all_anime_data = []
    
    for page in range(total_pages):
        limit = page * anime_per_page
        print(f"\nĐang tải trang danh sách {page + 1}/{total_pages} (limit={limit})...")
        
        html = fetch_mal_top_anime(session, limit)
        if not html:
            print(f"Bỏ qua trang danh sách {page + 1} do lỗi kết nối.")
            continue
            
        list_data = parse_anime_list_html(html)
        
        # Duyệt từng anime để lấy thông tin chi tiết
        for idx, item in enumerate(list_data):
            url = item.get("url")
            title = item.get("title")
            
            if url:
                # Delay ngẫu nhiên giữa các request
                delay = random.uniform(1.5, 2.5)
                time.sleep(delay)
                
                details = fetch_anime_details(session, url)
                
                if details:
                    item.update(details)
                    print(f"    [{len(all_anime_data) + 1}/{total_anime}] Lấy chi tiết: {title}")
                else:
                    print(f"    [{len(all_anime_data) + 1}/{total_anime}] Bỏ qua chi tiết: {title}")
            
            all_anime_data.append(item)
            
    print("\nLưu dữ liệu...")
    save_to_csv(all_anime_data, "mal_html_data_full.csv")
    save_to_json(all_anime_data, "mal_html_data_full.json")
    print("Hoàn tất cào dữ liệu.")

if __name__ == "__main__":
    main()
