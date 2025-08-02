import os, json, time, argparse, requests
from openai import OpenAI


BASE_API = "http://localhost:8001"

def crawl_news(query: str):
    r = requests.get(f"{BASE_API}/crawl", params={"query": query}, timeout=15)
    r.raise_for_status()
    return r.json()["articles"]            

def fetch_article(url: str):
    r = requests.get(f"{BASE_API}/article", params={"url": url}, timeout=15)
    r.raise_for_status()
    return r.json()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))          # OPENAI_API_KEY 환경변수 사용


functions = [
    {
        "name": "crawl_news",
        "description": "키워드로 뉴스 기사 메타데이터 목록을 가져온다",
        "parameters": {
            "type": "object",
            "properties": { "query": { "type": "string" } },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_article",
        "description": "기사 URL에서 제목·본문·발행일을 가져온다",
        "parameters": {
            "type": "object",
            "properties": { "url": { "type": "string" } },
            "required": ["url"]
        }
    }
]
tools = [{"type": "function", "function": f} for f in functions]

def run_timeline_builder(query: str, tags: list[str]) -> str:
    system_msg = (
        "너는 뉴스 분석 어시스턴트다.\n"
        "목표: 사용자의 검색어로 기사를 수집한 뒤, "
        "관심 키워드와 가장 연관된 **하나의 사건(Event)** 을 정의하고, "
        "그 사건의 흐름을 'timelines' 배열로 날짜순 정리해 JSON으로 출력한다.\n\n"
        "JSON 형식 예시:\n"
        "{\n"
        '  "title": "<사건 제목>",\n'
        '  "summary": "<사건 한줄 요약>",\n'
        '  "timelines": [\n'
        '    {"date":"YYYY-MM-DDThh:mm:ss±hh:mm", "title":"<뉴스 제목>", "summary":"<120자 이하 요약>"},\n'
        "    ... (최대 10개)\n"
        "  ]\n"
        "}\n"
        "※ 반드시 위 구조와 키 이름을 그대로 사용할 것."
    )
    user_msg = f"검색어: {query}\n관심 키워드: {', '.join(tags)}"

    messages = [
        {"role":"system", "content": system_msg},
        {"role":"user",   "content": user_msg}
    ]

    while True:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.3
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)                 
            for call in msg.tool_calls:          
                fn_name = call.function.name
                args    = json.loads(call.function.arguments or "{}")

                result = crawl_news(**args) if fn_name == "crawl_news" else fetch_article(**args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,     
                    "name": fn_name,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            time.sleep(0.2)
            continue

        return msg.content.strip()

def main():
    ap = argparse.ArgumentParser(description="GPT 뉴스 타임라인 봇")
    ap.add_argument("--query",    required=True, help="검색어")
    ap.add_argument("--keywords", required=True, help="관심 키워드(쉼표)")

    args, _ = ap.parse_known_args()
    tags = [k.strip() for k in args.keywords.split(",") if k.strip()]

    timeline_json = run_timeline_builder(args.query, tags)

    print("\n=== 타임라인 JSON ===")
    print(timeline_json)

if __name__ == "__main__":
    main()
