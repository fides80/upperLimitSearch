import json
import os
import re
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today_str = now.strftime('%Y-%m-%d')
time_str = now.strftime('%H:%M')

NAVER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36'
}
GEMINI_MODEL = 'gemini-3.1-flash-lite'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'


def get_upper_limit_stocks():
    """네이버페이 증권 API에서 가격제한폭 종목을 수집한다."""
    url = 'https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=ALL&orderType=up&startIdx=0&pageSize=100'
    response = requests.get(url, headers=NAVER_HEADERS, timeout=30)
    response.raise_for_status()
    rows = response.json()
    stocks = []
    for row in rows:
        if str(row.get('nowPrice')) != str(row.get('upperLimitPrice')):
            continue
        stocks.append({
            'name': row.get('itemname', ''),
            'code': row.get('itemcode', ''),
            'price': int(float(row.get('nowPrice') or 0)),
            'rate': float(row.get('prevChangeRate') or 0),
            'volume': int(float(row.get('tradeVolume') or 0)),
            'trade_amount': int(float(row.get('tradeAmount') or 0)),
        })
    return stocks


def search_stock_news(stock_code):
    """네이버 종목 뉴스 API에서 최신 뉴스와 본문 요약을 가져온다."""
    url = f'https://stock.naver.com/api/domestic/detail/news?itemCode={stock_code}&page=1&pageSize=15'
    response = requests.get(url, headers=NAVER_HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()
    news = []
    seen = set()
    for cluster in payload.get('clusters', []):
        for item in cluster.get('items', []):
            title = (item.get('title') or '').strip()
            article_id = item.get('articleId', '')
            office_id = item.get('officeId', '')
            if not title or title in seen:
                continue
            seen.add(title)
            news.append({
                'title': title,
                'source': item.get('officeName', ''),
                'date': item.get('datetime', ''),
                'body': (item.get('body') or '').strip(),
                'link': f'https://n.news.naver.com/mnews/article/{office_id}/{article_id}'
            })
            if len(news) >= 5:
                return news
    return news


def fmt_volume(value):
    return f'{value / 100_000_000:.1f}억주' if value >= 100_000_000 else f'{value / 10_000:.0f}만주'


def fmt_amount(value):
    return f'{value / 100_000_000:.0f}억' if value >= 100_000_000 else f'{value / 10_000_000:.1f}억'


def analyze_with_gemini(stocks_with_news):
    """수집한 뉴스 요약을 Gemini로 보내 상한가 원인과 분류를 분석한다."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return {}, 'GEMINI_API_KEY가 설정되지 않았습니다.'

    compact_input = []
    for stock in stocks_with_news:
        compact_input.append({
            'name': stock['name'],
            'code': stock['code'],
            'rate': stock['rate'],
            'news': [
                {
                    'title': item['title'],
                    'source': item['source'],
                    'date': item['date'],
                    'body': item['body']
                }
                for item in stock['news']
            ]
        })

    prompt = f'''당신은 한국 주식시장 특징주 분석가입니다.
아래는 오늘 가격제한폭에 도달한 종목과 네이버 증권에서 수집한 뉴스입니다.
각 종목의 상한가 이유를 뉴스에 근거해 한국어로 분석하세요.
뉴스에 직접 근거가 없으면 "직접적인 당일 재료 확인 안 됨"이라고 명시하고,
테마나 수급 추정은 반드시 "추정"이라고 표시하세요. 뉴스에 없는 계약, 금액,
인수, 임상 결과를 만들지 마세요.

반드시 JSON 배열만 반환하세요. Markdown 코드펜스나 설명은 넣지 마세요.
각 원소는 code, reason, classification 키를 가져야 합니다.
reason은 1~2문장, classification은 짧은 분류명으로 작성하세요.

데이터:
{json.dumps(compact_input, ensure_ascii=False)}'''

    payload = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}
    }
    response = requests.post(
        GEMINI_URL,
        headers={'x-goog-api-key': api_key, 'Content-Type': 'application/json'},
        json=payload,
        timeout=90
    )
    response.raise_for_status()
    result = response.json()
    text = result['candidates'][0]['content']['parts'][0]['text'].strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.IGNORECASE)
    parsed = json.loads(text)
    return {str(item['code']): item for item in parsed}, None


def generate_markdown(stocks):
    lines = [
        '# 오늘의 상한가 보고서',
        '',
        f'기준일: {today_str}  ',
        f'기준 시각: 한국시간 {time_str}',
        ''
    ]

    if not stocks:
        lines.extend([
            '금일 상한가를 기록한 종목이 없거나 국내 증시 휴장일입니다.',
            '',
            '※ 본 보고서는 공개된 시세와 뉴스를 요약한 정보이며 투자 권유가 아닙니다.'
        ])
        return '\n'.join(lines)

    for stock in stocks:
        stock['news'] = search_stock_news(stock['code'])
    analysis, analysis_error = analyze_with_gemini(stocks)

    if analysis_error:
        lines.extend([f'> AI 분석 미실행: {analysis_error}', ''])

    for stock in stocks:
        result = analysis.get(stock['code'], {})
        reason = result.get('reason', '당일 뉴스와 공시를 추가 확인해야 합니다.')
        classification = result.get('classification', '시장 특징주')
        lines.append(
            f"[상한가] {stock['name']} ({stock['code']}) | +{stock['rate']:.2f}% | "
            f"{stock['price']:,}원 | 거래량 {fmt_volume(stock['volume'])} | "
            f"거래대금 {fmt_amount(stock['trade_amount'])}"
        )
        lines.append(f'원인: {reason}')
        lines.append(f'분류: {classification}')
        lines.append('')
        lines.append('관련 뉴스:')
        if stock['news']:
            for item in stock['news'][:3]:
                lines.append(f"- [{item['title']}]({item['link']})")
        else:
            lines.append('- 당일 등록된 주요 네이버 증권 뉴스 없음')
        lines.append('')

    lines.append('※ 본 보고서는 공개된 시세와 뉴스를 요약한 정보이며 투자 권유가 아닙니다.')
    return '\n'.join(lines)


def main():
    os.makedirs('reports', exist_ok=True)
    stocks = get_upper_limit_stocks()
    md_content = generate_markdown(stocks)
    file_path = os.path.join('reports', f'{today_str}.md')
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(md_content)
    print(f'보고서 저장 완료: {file_path}')


if __name__ == '__main__':
    main()
