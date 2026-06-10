# Jace Weekly ETF

개인 투자 모니터링 통합 대시보드 (완전 자급형 · 외부 저장소 의존 0건)

## 구성 (3탭)
1. `nasdaq/` — 나스닥100 현금전환 시그널 (일요일 09:00 KST 자동 생성)
2. `us/` — 미국 ETF Weekly, 1~7주 영업일 롤링 (매일 07:00 KST)
3. `kr/` — 한국 ETF Weekly, N주=5×N영업일 (평일 16:30 KST)

## 최초 1회 설정
1. Settings → Pages → Branch: `main` / `(root)` → Save
2. Actions 탭 → 워크플로우 3개 각각 Run workflow 1회 수동 실행
3. `https://jacelee660303-png.github.io/Jace-Weekly-ETF/` 접속 확인

## 데이터 흐름
각 폴더의 Python 스크립트가 GitHub Actions로 실행되어
같은 폴더의 출력 파일(index.html 또는 *.json)을 커밋 → Pages가 자동 반영.
이 저장소 하나만으로 수집·생성·표시가 모두 동작한다.
