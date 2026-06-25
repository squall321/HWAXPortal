<!-- cae00에서 HWAX 포털을 https://hwax.sec.samsung.net 으로 올리는 TLS/HTTPS go-live 런북 -->
# TLS / HTTPS go-live 런북 — `https://hwax.sec.samsung.net`

포털을 HTTPS로 정식 오픈하는 절차입니다. **이 작업은 도메인이 가리키는 호스트(cae00)에서 직접 실행**합니다.

| 항목 | 값 |
|---|---|
| 도메인 | `hwax.sec.samsung.net` → **10.252.39.140 (cae00)** |
| 실행 위치 | **cae00** (빌드 박스 `smarttwincluster`(110.15.177.120)에서는 cae00에 네트워크 도달 불가 → 원격 실행 불가) |
| 포털 평문 | nginx `HTTP_PORT`(기본 `8088`) — rootless라 1024 미만은 못 바인딩 |
| 구현 상태 | 스크립트·템플릿·인증서 생성기·문서 모두 **커밋 완료**(아래 절차만 실행) |

> 인증서/키(`infra/tls/`)는 `.gitignore` 처리되어 레포에 올라가지 않습니다. cae00에서 생성하거나 사내 인증서를 직접 둡니다.

---

## 0. 먼저 `:443` 점유 여부 확인 (분기점)

cae00의 `:443`에 **이미 다른 리버스 프록시(corp LB / 시스템 nginx)** 가 떠 있을 수 있습니다. 점유 상태에 따라 경로가 갈립니다.

```bash
# cae00에서
ss -ltnp | grep ':443 ' || echo "비어 있음"
curl -sk -o /dev/null -w '%{http_code}\n' --max-time 5 https://127.0.0.1/ || echo "연결 안 됨"
```

- **`:443`가 비어 있음(연결 거부/ERR_CONNECTION_RESET)** → **절차 A**(포털 nginx가 :443에서 직접 TLS 종단). 원래 플랜의 기본 경로.
- **`:443`에 이미 nginx/LB가 응답** → **절차 B**(기존 프록시 뒤에 포털을 둠). 이 프록시를 포털 `:8088`로 forward.

> 참고: 빌드 박스 `smarttwincluster`의 `:443`은 별도 시스템 nginx가 `/auth_portal/`·`/mx-white-paper/`만 서빙(HWAX 포털 경로는 404)했습니다. cae00도 유사할 수 있으니 0단계를 꼭 확인하세요.

---

## 절차 A — 포털 nginx가 `:443`에서 직접 TLS 종단 (`:443`가 비어 있을 때)

1. `infra/.env` 설정
   ```ini
   ENABLE_TLS=true
   HTTPS_PORT=443
   TLS_SERVER_NAME=hwax.sec.samsung.net
   PUBLIC_BASE_URL=https://hwax.sec.samsung.net
   COOKIE_SECURE=true
   ```
2. 실행
   ```bash
   git pull
   ./infra/scripts/gen-tls-cert.sh          # 자체서명 인증서 → infra/tls/ (sudo 불필요)
   sudo ./infra/scripts/grant-net-bind.sh   # 1회: rootless 프로세스가 :443 바인딩 허용
   ./infra/scripts/restart.sh               # nginx가 :443(HTTPS) + :8088(평문) 동시 서빙
   ```
   - `grant-net-bind.sh`는 `net.ipv4.ip_unprivileged_port_start=443`을 `/etc/sysctl.d/99-hwax-ports.conf`에 영구 적용(리부팅 생존). 되돌리려면 `sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1024 && sudo rm /etc/sysctl.d/99-hwax-ports.conf`.
   - **sudo가 아예 불가**하면 고포트로: `HTTPS_PORT=8443` → `https://hwax.sec.samsung.net:8443`. 평문 `:8088`은 그대로 유지되어 헬스/LAN 접근 가능.

---

## 절차 B — 기존 `:443` 프록시 뒤에 포털을 둠 (`:443`가 이미 점유돼 있을 때)

포털은 평문 `:8088`로 그대로 두고, **이미 떠 있는 corp LB / 시스템 nginx가 포털로 forward**하게 합니다(이중 TLS 바인딩 충돌 회피).

1. `infra/.env`는 **평문 유지**하되 공개 주소만 https로:
   ```ini
   ENABLE_TLS=false
   PUBLIC_BASE_URL=https://hwax.sec.samsung.net
   COOKIE_SECURE=true
   ```
   ```bash
   git pull && ./infra/scripts/restart.sh
   ```
2. 시스템/corp nginx(`:443`)에 포털 라우팅 추가(해당 호스트 관리자 권한 필요). 예:
   ```nginx
   server {
       listen 443 ssl;
       server_name hwax.sec.samsung.net;
       # ssl_certificate ... (사내 인증서)
       location / {
           proxy_pass http://127.0.0.1:8088;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-Proto https;
           proxy_set_header X-Forwarded-Prefix /;
       }
   }
   ```
   - 포털이 만드는 절대 URL(설치파일·다운로드 등)이 깨지지 않도록 `X-Forwarded-Proto https`를 꼭 전달.

---

## 사내 인증서 교체 (자체서명 → 정식)

자체서명이면 브라우저가 경고합니다. 사내 발급 인증서를 **같은 경로에 드롭인**하고 재시작하면 됩니다(설정 변경 없음).

```bash
cp <사내발급>.crt infra/tls/hwax.crt
cp <사내발급>.key infra/tls/hwax.key      # 또는 TLS_CERT_PATH / TLS_KEY_PATH 로 경로 지정
./infra/scripts/restart.sh
```

---

## 검증

```bash
# cae00 로컬
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1/health           # → 200
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1/report-archive/   # → 연동 서비스 응답

# 브라우저
https://hwax.sec.samsung.net           # 자체서명이면 경고 1회(정식 인증서 교체 시 사라짐)
```

- `200`이면 TLS 종단 + 포털 라우팅 정상. 원래 증상이던 `ERR_CONNECTION_RESET`(=:443에 아무도 안 듣던 상태)이 해소됨.

## 롤백

```bash
# 절차 A를 되돌릴 때: TLS 끄고 평문만
# infra/.env → ENABLE_TLS=false
./infra/scripts/restart.sh
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1024 && sudo rm -f /etc/sysctl.d/99-hwax-ports.conf
```

---

## 참고
- README의 **HTTPS / TLS (:443)** 섹션 — 같은 내용 요약 + corp LB/시스템 프록시 전제(라인 100-101).
- 스크립트: `infra/scripts/gen-tls-cert.sh`, `infra/scripts/grant-net-bind.sh`, `infra/scripts/gen-nginx-conf.sh`(`ENABLE_TLS=true`면 동일 라우트 + 인증서로 `listen 443 ssl` server 블록 생성), `infra/scripts/restart.sh`.
- SSO(mock → 사내 AD SAML) 전환은 `docs/GO-LIVE.md` 참조(HTTPS가 먼저 올라와 있어야 함).
