#필수 설치
#pip install selenium

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def run_naver_news_crawler(keyword):
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)

    article_list=[]

    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
        driver.get(url)

        container_css = "div.fds-news-item-list-tab"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, container_css + " > div"))
        )
        articles = driver.find_elements(By.CSS_SELECTOR, container_css + " > div")

        for i, art in enumerate(articles, 1):
            try:
                title_el = art.find_element(
                    By.CSS_SELECTOR, "span[class*='headline1']"
                )
                title = title_el.text.strip()
                body_el = art.find_element(By.CSS_SELECTOR, "span[class*='text-type-body1']")
                body = body_el.text.strip()
                link = title_el.find_element(By.XPATH, "./ancestor::a[1]").get_attribute("href")

                article = { "title": title, "body": body, "link": link }
                article_list.append(article)
            except Exception:
                continue
    finally:
        driver.quit()
        return article_list

if __name__ == "__main__":
    articles = run_naver_news_crawler("부천 샤브샤브집")
    for i, article in enumerate(articles, 1):
        print(f"{i}. Title: {article['title']}")
        print(f"   Body: {article['body']}")
        print(f"   Link: {article['link']}")
        print()
