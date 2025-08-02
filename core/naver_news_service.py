#uvicorn main:app --host 0.0.0.0 --port 8001
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
from typing import List
import crawl_naver_news   # ← 방금 올린 함수 import
import news_bodyparser

app = FastAPI()

run_naver_news_crawler = crawl_naver_news.run_naver_news_crawler
run_news_bodyparser = news_bodyparser.news_bodyparser

class Article(BaseModel):
    title: str
    body: str
    link: str
    date:  Optional[str] = None

class CrawlResponse(BaseModel):
    query: str
    count: int
    articles: List[Article]

@app.get("/crawl", response_model=CrawlResponse)
async def crawl(query: str = Query(..., min_length=2)):
    items = run_naver_news_crawler(query)
    return {
        "query": query,
        "count": len(items),
        "articles": items
    }

@app.get("/article")
async def article(url: str = Query(...)):
    title, body, date = run_news_bodyparser(url, None)
    return {"url": url, "title": title, "body": body, "date": date}
