import requests
from bs4 import BeautifulSoup
import json
import os
import time
import hashlib
from urllib.parse import urljoin, urlparse
import logging
import re
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("metamask_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MetaMaskScraper:
    def __init__(self, base_url="https://support.metamask.io/", output_dir="metamask_data"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        })
        self.visited_urls = set()
        self.article_data = []
        self.image_mapping = {}  # Map to track which images belong to which articles
        
        # Создаем директории для сохранения данных
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            # Очищаем директорию от предыдущих данных
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    
        # Создаем структуру директорий для статей и изображений
        self.articles_dir = os.path.join(output_dir, "articles")
        self.images_dir = os.path.join(output_dir, "images")
        
        if not os.path.exists(self.articles_dir):
            os.makedirs(self.articles_dir)
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
    
    def get_page(self, url):
        """Получает содержимое страницы"""
        try:
            logging.info(f"Fetching page: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            # Проверяем, что получили валидный контент
            if response.text and len(response.text) > 1000:
                logging.info(f"Successfully retrieved page: {url}")
                return response.text
            else:
                logging.warning(f"Received suspiciously short response from {url}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching page {url}: {e}")
            return None
    
    def save_image(self, image_url, article_id, image_title=None):
        """Сохраняет изображение и возвращает информацию о нем"""
        try:
            if not image_url.startswith(('http://', 'https://')):
                image_url = urljoin(self.base_url, image_url)
            
            # Создаем хеш URL для имени файла
            image_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
            
            # Получаем расширение файла
            extension = os.path.splitext(image_url.split('?')[0])[1].lower()
            if not extension or extension not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                extension = '.jpg'  # По умолчанию
            
            # Формируем имя файла
            image_filename = f"{image_hash}{extension}"
            local_path = os.path.join(self.images_dir, image_filename)
            
            # Создаем запись для изображения
            image_info = {
                "id": image_hash,
                "original_url": image_url,
                "filename": image_filename,
                "article_id": article_id,
                "title": image_title or f"Image {image_hash}",
                "local_path": os.path.join("images", image_filename)
            }
            
            # Проверяем, существует ли уже файл
            if not os.path.exists(local_path):
                response = self.session.get(image_url, stream=True)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logging.info(f"Saved image: {image_filename}")
                time.sleep(0.2)  # Небольшая задержка
            
            # Добавляем изображение в маппинг, если его там еще нет
            if image_hash not in self.image_mapping:
                self.image_mapping[image_hash] = image_info
            
            # Также добавляем это изображение в список изображений для конкретной статьи
            if article_id not in self.image_mapping.get("articles", {}):
                if "articles" not in self.image_mapping:
                    self.image_mapping["articles"] = {}
                self.image_mapping["articles"][article_id] = []
            
            if article_id in self.image_mapping.get("articles", {}):
                if image_hash not in [img["id"] for img in self.image_mapping["articles"][article_id]]:
                    self.image_mapping["articles"][article_id].append(image_info)
            
            # Возвращаем информацию об изображении
            return image_info
            
        except Exception as e:
            logging.error(f"Error saving image {image_url}: {e}")
            return None
    
    def process_article(self, url):
        """Обрабатывает статью"""
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        # Получаем HTML-код страницы
        html_content = self.get_page(url)
        if not html_content:
            return
        
        # Парсим HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Получаем заголовок статьи
        title_element = soup.find('h1')
        if title_element:
            title = title_element.get_text(strip=True)
            logging.info(f"Found title: {title}")
        else:
            title = "Untitled"
            logging.warning(f"No title found for {url}")
        
        # Получаем содержимое статьи
        article_element = soup.find('article')
        if not article_element:
            logging.warning(f"No article content found for {url}")
            return
        
        # Создаем уникальный идентификатор
        article_id = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        # Список изображений в статье
        article_images = []
        
        # Словарь для маркеров изображений
        image_markers = {}
        
        # Обрабатываем изображения и создаем уникальные маркеры
        for img in article_element.find_all('img', src=True):
            img_url = img['src']
            img_alt = img.get('alt', '')
            
            # Создаем уникальный маркер для этого изображения
            marker_id = str(uuid.uuid4())[:8]
            marker_tag = f"[[IMAGE:{marker_id}]]"
            
            # Добавляем маркер в HTML
            placeholder_tag = soup.new_tag("span")
            placeholder_tag["class"] = "image-placeholder"
            placeholder_tag["data-marker"] = marker_id
            placeholder_tag.string = marker_tag
            img.replace_with(placeholder_tag)
            
            # Сохраняем изображение
            image_info = self.save_image(img_url, article_id, img_alt)
            if image_info:
                # Добавляем маркер в словарь маркеров
                image_markers[marker_id] = {
                    "marker": marker_tag,
                    "image": image_info
                }
                article_images.append(image_info)
        
        # Получаем текст с маркерами изображений
        article_text_with_markers = article_element.get_text(separator='\n', strip=True)
        
        # Получаем HTML
        article_html = str(article_element)
        
        # Заменяем маркеры изображений на более читабельный формат в тексте
        for marker_id, marker_info in image_markers.items():
            image_path = marker_info["image"]["local_path"]
            image_title = marker_info["image"]["title"]
            
            # Создаем читабельный маркер для текста
            readable_marker = f"[[IMAGE:{image_path}|{image_title}]]"
            
            # Заменяем маркер в тексте
            article_text_with_markers = article_text_with_markers.replace(
                marker_info["marker"], 
                readable_marker
            )
        
        # Формируем данные статьи
        article_data = {
            "id": article_id,
            "url": url,
            "title": title,
            "content_html": article_html,
            "content_text": article_text_with_markers,
            "images": article_images,
            "image_markers": image_markers
        }
        
        # Добавляем в общий список
        self.article_data.append(article_data)
        
        # Сохраняем в отдельный файл в директории articles
        filename = f"article_{article_id}.json"
        with open(os.path.join(self.articles_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Saved article: {title} with {len(article_images)} images and {len(image_markers)} image markers")
        
        # Задержка
        time.sleep(1)
    
    def extract_links(self, url):
        """Извлекает ссылки на другие статьи"""
        html_content = self.get_page(url)
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        links = []
        # Ищем все ссылки
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Пропускаем внешние ссылки и ссылки на файлы
            if not href.startswith(self.base_url) and not href.startswith('/'):
                continue
                
            if href.endswith(('.jpg', '.png', '.pdf', '.zip')):
                continue
            
            # Формируем полный URL
            full_url = urljoin(self.base_url, href)
            
            # Пропускаем ссылки на другие языки
            parsed_url = urlparse(full_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if path_parts and len(path_parts[0]) == 2 and path_parts[0] != 'en' and path_parts[0] != 'hc':
                continue
            
            # Пропускаем уже посещенные URL
            if full_url not in self.visited_urls:
                links.append(full_url)
        
        return links
    
    def create_image_index(self):
        """Создает индекс с информацией о всех изображениях"""
        # Собираем данные об изображениях
        images_data = {}
        for article in self.article_data:
            for img in article.get("images", []):
                if img["id"] not in images_data:
                    images_data[img["id"]] = {
                        "id": img["id"],
                        "filename": img["filename"],
                        "path": img["local_path"],
                        "title": img["title"],
                        "articles": []
                    }
                
                # Добавляем информацию о статье
                if article["id"] not in [a["id"] for a in images_data[img["id"]]["articles"]]:
                    images_data[img["id"]]["articles"].append({
                        "id": article["id"],
                        "title": article["title"],
                        "url": article["url"]
                    })
        
        # Сохраняем индекс изображений
        with open(os.path.join(self.output_dir, "image_index.json"), 'w', encoding='utf-8') as f:
            json.dump({
                "images": list(images_data.values())
            }, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Created image index with {len(images_data)} images")
    
    def crawl(self, start_url, max_articles=30):
        """Основной метод обхода сайта"""
        to_visit = [start_url]
        article_count = 0
        
        while to_visit and article_count < max_articles:
            current_url = to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            self.process_article(current_url)
            article_count += 1
            
            if article_count < max_articles:
                new_links = self.extract_links(current_url)
                # Добавляем только URL, которые содержат нужные разделы
                filtered_links = []
                for link in new_links:
                    if '/start/' in link or '/tutorials/' in link or '/guide/' in link:
                        filtered_links.append(link)
                
                to_visit.extend(filtered_links)
                logging.info(f"Found {len(filtered_links)} new relevant links")
        
        # Создаем индекс статей
        with open(os.path.join(self.output_dir, "article_index.json"), 'w', encoding='utf-8') as f:
            index_data = [{
                "id": article["id"],
                "url": article["url"],
                "title": article["title"],
                "image_count": len(article.get("images", [])),
                "images": [img["id"] for img in article.get("images", [])]
            } for article in self.article_data]
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # Создаем индекс изображений
        self.create_image_index()
        
        # Сохраняем все данные в один файл
        with open(os.path.join(self.output_dir, "all_data.json"), 'w', encoding='utf-8') as f:
            all_data = {
                "articles": self.article_data
            }
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # Создаем HTML-страницу для просмотра данных
        self.create_html_viewer()
        
        logging.info(f"Crawling completed. Processed {article_count} articles.")
        return self.article_data
    
    def create_html_viewer(self):
        """Создает HTML-страницу для просмотра собранных данных"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MetaMask Documentation Browser</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1200px; margin: 0 auto; }
                h1 { color: #1969ff; }
                h2 { color: #555; margin-top: 30px; }
                .article-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .article-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; transition: transform 0.2s; }
                .article-card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
                .article-title { font-weight: bold; margin-bottom: 10px; color: #1969ff; }
                .article-images { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
                .article-image { width: 80px; height: 80px; object-fit: cover; border-radius: 4px; }
                .view-btn { display: inline-block; margin-top: 10px; background: #1969ff; color: white; padding: 5px 10px; 
                             border-radius: 4px; text-decoration: none; }
                .view-btn:hover { background: #0044cc; }
                .article-detail { border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin-top: 20px; }
                .article-content { margin-top: 20px; }
                .image-marker { background-color: #f0f8ff; padding: 3px 6px; border-radius: 3px; color: #1969ff; 
                              font-weight: bold; cursor: pointer; }
                .preview-text { height: 100px; overflow: hidden; position: relative; margin-top: 10px; }
                .preview-text::after { 
                    content: "..."; 
                    position: absolute; 
                    bottom: 0; 
                    right: 0; 
                    background: linear-gradient(to right, transparent, white 50%); 
                    width: 50px; 
                    text-align: right;
                }
            </style>
        </head>
        <body>
            <h1>MetaMask Documentation Browser</h1>
            <p>This page allows you to browse through the scraped MetaMask documentation articles and images.</p>
            
            <h2>Articles</h2>
            <div class="article-list">
        """
        
        # Добавляем карточки статей
        for article in self.article_data:
            article_images_html = ""
            for img in article.get("images", [])[:4]:  # Ограничиваем до 4 изображений для превью
                article_images_html += f'<img src="{img["local_path"]}" alt="{img["title"]}" class="article-image">'
            
            # Создаем предпросмотр текста с маркерами изображений
            preview_text = article.get("content_text", "")[:500]
            
            # Заменяем маркеры изображений на HTML-элементы
            for marker_id, marker_info in article.get("image_markers", {}).items():
                image_path = marker_info["image"]["local_path"]
                image_title = marker_info["image"]["title"]
                
                # Шаблон для поиска маркера в тексте
                marker_pattern = f"\\[\\[IMAGE:{image_path}\\|{re.escape(image_title)}\\]\\]"
                
                # Заменяем маркер на HTML-элемент для отображения
                preview_text = re.sub(
                    marker_pattern,
                    f'<span class="image-marker">[Image: {image_title}]</span>',
                    preview_text
                )
            
            html_content += f"""
                <div class="article-card">
                    <div class="article-title">{article["title"]}</div>
                    <div>Images: {len(article.get("images", []))}</div>
                    <div class="preview-text">{preview_text}</div>
                    <div class="article-images">
                        {article_images_html}
                    </div>
                    <a href="articles/article_{article["id"]}.json" class="view-btn">View JSON</a>
                    <a href="#" onclick="viewArticle('{article["id"]}'); return false;" class="view-btn">View Article</a>
                </div>
            """
        
        html_content += """
            </div>
            
            <div id="article-detail" class="article-detail" style="display:none;">
                <h2 id="detail-title"></h2>
                <div id="detail-images"></div>
                <div id="detail-content" class="article-content"></div>
                <button onclick="hideArticle()" class="view-btn">Back to List</button>
            </div>
            
            <script>
                function viewArticle(id) {
                    fetch(`articles/article_${id}.json`)
                        .then(response => response.json())
                        .then(article => {
                            document.getElementById('detail-title').textContent = article.title;
                            
                            let contentHtml = article.content_text;
                            
                            // Replace image markers with actual images
                            const markerRegex = /\\[\\[IMAGE:([^|]+)\\|([^\\]]+)\\]\\]/g;
                            contentHtml = contentHtml.replace(markerRegex, (match, path, title) => {
                                return `<div style="text-align:center; margin:15px 0;">
                                    <img src="${path}" alt="${title}" style="max-width:100%; border-radius:5px;">
                                    <div style="font-style:italic; margin-top:5px;">${title}</div>
                                </div>`;
                            });
                            
                            document.getElementById('detail-content').innerHTML = contentHtml;
                            document.querySelector('.article-list').style.display = 'none';
                            document.getElementById('article-detail').style.display = 'block';
                        });
                }
                
                function hideArticle() {
                    document.querySelector('.article-list').style.display = 'grid';
                    document.getElementById('article-detail').style.display = 'none';
                }
            </script>
        </body>
        </html>
        """
        
        # Сохраняем HTML-страницу
        with open(os.path.join(self.output_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logging.info("Created HTML viewer for browsing the scraped data")

# Точка входа
if __name__ == "__main__":
    print("Starting MetaMask documentation scraper...")
    
    scraper = MetaMaskScraper()
    
    # Запускаем обход, начиная с английской версии
    starting_url = "https://support.metamask.io/start/getting-started-with-metamask/"
    articles = scraper.crawl(starting_url, max_articles=30)
    
    print(f"Processed {len(articles)} articles")
    print(f"Data saved to '{scraper.output_dir}' directory")
    print(f"You can browse the data by opening '{os.path.join(scraper.output_dir, 'index.html')}' in your browser")