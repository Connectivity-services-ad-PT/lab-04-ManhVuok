# RUN_LOCAL.md – Hướng dẫn chạy Lab 04 (team-gate / Access Gate)

Tài liệu này giúp người khác clone repo sạch và chạy lại Access Gate service trong Docker trong 3–5 bước.

---

## 1. Clone repo + cài dependencies cho Newman/Spectral

```bash
git clone <repo-url>
cd lab-04-ManhVuok
npm install
```

---

## 2. Build Docker image

```bash
docker build -t fit4110/access-gate:lab04 .
```

---

## 3. Run container

```bash
docker run --rm \
  --name fit4110-access-gate-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/access-gate:lab04
```

Mở terminal khác, kiểm tra health:

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "access-gate",
  "time": "2026-05-26T08:00:00Z"
}
```

---

## 4. Chạy Newman test trên container

```bash
npm run test:local
```

Report sinh tại:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

Kết quả mong đợi: **15 requests / 30 assertions, 0 failed** (functional, auth, negative, boundary).

---

## 5. Dừng container

```bash
docker stop fit4110-access-gate-lab04
```

---

## Lệnh nhanh bằng Makefile

```bash
make build         # build image
make run-detached  # chạy container nền
make health        # curl /health
make test-docker   # chạy Newman trên container
make stop          # dừng container
```

---

## Ghi chú

- Service chạy bằng user **non-root** (`appuser`) trong container, có `HEALTHCHECK` gọi `GET /health`.
- Token mặc định lấy từ `.env.example` (`AUTH_TOKEN=local-dev-token`) — **không phải secret thật**.
- Các endpoint: `GET /health`, `GET /access/logs/recent`, `GET /access/logs/{logId}`,
  `GET /gates/{gateId}/status`, `GET /cards/{cardId}`, `POST /events`. Lỗi trả theo dạng
  `application/problem+json` (ProblemDetails).
- Image tag theo quy ước: `ghcr.io/<owner>/team-gate:v0.1.0-team-gate`.
