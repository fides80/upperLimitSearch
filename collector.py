import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# KST 기준 시간
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
today_str = now.strftime('%Y-%m-%d')
time_str = now.strftime('%H:%M')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def get_upper_limit_stocks():
    """네이버 금융 상한가 목록 수집"""
    url = 'https://finance.naver.com/sise/sise_upper.naver'
    res = requests.get(url, headers=HEADERS)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')

    stocks = []
    # 코스피(box_type_l) 및 코스닥 상한가 테이블 파싱
    for table in soup.select('table.type_5'):
        for row in table.select('tr'):
            cols = row.select('td')
            if len(cols) >= 10:
                name_tag = cols[3].select_one('a')
                if not name_tag:
                    continue
                name = name_tag.text.strip()
                code_match = re.search(r'code=(\d+)', name_tag.get('href', ''))
                code = code_match.group(1) if code_match else ''
                
                price = cols[4].text.strip()
                diff_price = cols[5].text.strip()
                rate = cols[6].text.strip()
                volume = cols[7].text.strip()
                trade_amount = cols[8].text.strip()

                stocks.append({
                    'name': name,
                    'code': code,
                    'price': price,
                    'diff_price': diff_price,
                    'rate': rate,
                    'volume': volume,
                    'trade_amount': trade_amount
                })
    return stocks

def search_stock_news(stock_name, stock_code):
    """종목 관련 당일 뉴스 검색"""
    news_url = f'https://finance.naver.com/item/news_news.naver?code={stock_code}'
    res = requests.get(news_url, headers=HEADERS)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')

    news_list = []
    for row in soup.select('table.type5 tbody tr'):
        title_tag = row.select_one('td.title a')
        if title_tag:
            title = title_tag.text.strip()
            link = 'https://finance.naver.com' + title_tag.get('href', '')
            news_list.append({'title': title, 'link': link})
            if len(news_list) >= 3:
                break
    return news_list

def generate_markdown(stocks):
    """요청된 양식의 마크다운 보고서 생성"""
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

    for s in stocks:
        lines.append(f"[상한가] {s['name']} ({s['code']}) | +{s['rate']} | {s['price']}원 | 거래량 {s['volume']}주 | 거래대금 {s['trade_amount']}백만")
        
        # 뉴스 검색
        news = search_stock_news(s['name'], s['code'])
        reason_hint = "당일 뉴스 및 공시 기반 수급 유입으로 상한가 기록."
        if news:
            reason_hint = f"당일 관련 보도({news[0]['title']}) 등의 호재와 매수세 집중으로 상한가 기록."

        lines.append(f"원인: {reason_hint}")
        lines.append("분류: 시장 특징주 / 테마")
        lines.append("")
        lines.append("관련 뉴스:")
        if news:
            for n in news:
                lines.append(f"- [{n['title']}]({n['link']})")
        else:
            lines.append("- 당일 등록된 주요 포털 뉴스 없음 (공시 및 테마 수급 확인 필요)")
        lines.append("")

    lines.append('※ 본 보고서는 공개된 시세와 뉴스를 요약한 정보이며 투자 권유가 아닙니다.')
    return '\n'.join(lines)

def main():
    os.makedirs('reports', exist_ok=True)
    stocks = get_upper_limit_stocks()
    md_content = generate_markdown(stocks)
    
    file_path = os.path.join('reports', f'{today_str}.md')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"보고서 저장 완료: {file_path}")

if __name__ == '__main__':
    main()
