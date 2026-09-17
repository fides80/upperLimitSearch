# 네이버 오늘의 상한가 자동 보고서

GitHub Actions가 PC 전원과 관계없이 평일 한국시간 16:30에 실행되어 네이버 상한가 종목과 뉴스 내용을 Gemini로 분석하고 `reports/YYYY-MM-DD.md` 파일로 저장합니다.

## GitHub 설정

1. GitHub 저장소의 `Settings` → `Secrets and variables` → `Actions`로 이동합니다.
2. `New repository secret`을 클릭합니다.
3. 이름을 정확히 다음처럼 입력합니다.

```text
GEMINI_API_KEY
```

4. Google AI Studio에서 발급한 Gemini API 키를 Secret 값으로 붙여넣고 저장합니다.
5. `Actions` 탭에서 `Daily Stock Upper Limit Report`를 선택합니다.
6. `Run workflow`로 수동 실행해 보고서가 생성되는지 확인합니다.

사용 모델은 안정 버전 식별자 `gemini-3.1-flash-lite`입니다. API 키는 코드나 보고서에 기록되지 않고 GitHub Actions Secret으로만 전달됩니다.

## 파일 구성

- `collector.py`: 네이버페이 증권 시세·뉴스 API 수집 및 Gemini 분석
- `.github/workflows/daily.yml`: 평일 16:30 KST 자동 실행
- `reports/YYYY-MM-DD.md`: 날짜별 Markdown 보고서

## 주의사항

- GitHub Actions의 예약 실행은 몇 분 지연될 수 있습니다.
- 네이버 API 응답 구조가 변경되면 `collector.py` 수정이 필요할 수 있습니다.
- Gemini API 사용량에 따라 비용이 발생할 수 있습니다.
- 보고서는 투자 권유가 아닌 정보 요약입니다.
