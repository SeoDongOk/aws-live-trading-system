# 주식 자동매매 백엔드 시스템

증권사 Open API를 활용한 실시간 데이터 수집 및 모의 자동매매 시스템

## 주요 구현
- WebSocket 실시간 체결 데이터 수신
- REST API 자동 호출 및 토큰 관리
- asyncio 기반 비동기 매매 로직
- PostgreSQL 데이터 연동
- systemd 24시간 운영
- 일별 로그 파일 자동 생성

## 기술 스택
- Python 3.11
- asyncio, requests, websockets
- PostgreSQL (Supabase)
- AWS EC2, systemd
