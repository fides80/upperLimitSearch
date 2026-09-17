# 네이버 오늘의 상한가 자동 보고서

PC가 꺼져 있어도 GitHub Actions가 매주 월요일부터 금요일까지 한국시간 16:30에 실행되어 `reports/YYYY-MM-DD.md` 파일을 생성합니다.

## GitHub에 업로드하는 방법

1. GitHub에서 새 저장소를 만듭니다. 비공개 저장소도 가능합니다.
2. 이 프로젝트 전체 파일을 저장소에 업로드합니다.
3. GitHub 저장소의 `Actions` 탭에서 `Daily Stock Upper Limit Report` 워크플로우가 활성화되어 있는지 확인합니다.
4. `Actions` 탭에서 `Run workflow`를 눌러 수동으로 한 번 테스트할 수 있습니다.
5. 매일 생성된 파일은 `reports/날짜.md`에 저장됩니다.

## 주의사항

- GitHub Actions의 일정 실행은 몇 분 정도 지연될 수 있습니다.
- 네이버 페이지 구조가 변경되면 `collector.py`의 HTML 선택자를 수정해야 할 수 있습니다.
- 뉴스 링크는 네이버 증권 종목 뉴스 화면에 표시되는 링크 기준입니다.
- 시세와 뉴스는 투자 참고용이며 투자 권유가 아닙니다.
