# 5차 변경 요청 반영 — 한글 이름 ste 자격 중계 500(145회) · 권한 표 구멍 3 · 선택 셋

> 2026-10-01 요청서(요청자 koo.park, 기준 cae00 HEAD `1fd1b88`). 원문은 요청자 리포의 PORTAL-CHANGE-REQUEST-5.md.
> 요청서의 행 번호는 그 커밋 기준이다 — 이 리포는 그 뒤로도 바뀌어 번호가 다를 수 있다.

## 반영 표
| § | 무엇 | 어디 | 비고 |
|---|---|---|---|
| 1-b | ste 자격 중계의 `except` 에 `UnicodeEncodeError` | `auth/routes/ste_credential.py` | 요청 그대로 — 500 트레이스백 대신 설계대로 502 |
| 1-a | 이름 헤더 형식 | 포털: 비ASCII(와 `%`)만 **퍼센트 인코딩** · ste: `unquote` | 요청의 "UTF-8 바이트" 대신(D-1) — ste 도 이 리포 계열이라 양쪽을 같이 맞춘다 |
| 1-c | 회귀 시험 | `tests/test_ste_credential.py` | 한글 이름 사용자 200 + 헤더 왕복 · 1-b 를 따로 고정 |
| 2-a·b·c | `simflow` · `plmdefect` 플랫폼, `knoxbridge.gateway` | `config/access.yaml` | 백엔드 키는 요청서의 cae00 실측값 |
| 2-d | 대조자 이름 정정 + 대조 시험 + **운영 박스 점검** | `access.yaml` 주석 · `test_access_control.py` · update-all §6 | 게이트웨이 `/health`(공유 시크릿)의 실제 백엔드가 권한 표에 다 있는가 |
| 3 | dist 표식이 없거나 HEAD 와 다르면 업로드를 멈춘다 | `infra/scripts/images-to-drive.sh` | 옛 dist 에 지금 HEAD 표식을 찍던 '구제' 경로를 없앤다 |
| 4 | IdP 메타데이터 URL 은 TLS 검증 | `auth/saml_sp.py` + 설정 | 끄는 손잡이를 남긴다(사내 CA 는 `SSL_CERT_FILE` 이 정석) |
| 5 | '매핑된 서비스 없음' 다운 백엔드를 경고로 + 끝에 **경고 요약** | update-all | 종료코드는 그대로(비치명) |
