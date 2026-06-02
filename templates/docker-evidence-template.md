# Docker Evidence – Lab 04

## Team

- Team name: **team-gate**
- Service: **Access Gate** (RFID access logs, gate status, card info, business events)
- Image tag: `fit4110/access-gate:lab04` → `ghcr.io/manhvuok/team-gate:v0.1.0-team-gate`

## 1. Build evidence

Command:

```bash
docker build -t fit4110/access-gate:lab04 .
```

Result: build thành công, multi-stage (python:3.11-slim builder + runtime), image ~180MB.

```text
=> exporting to image
=> => naming to docker.io/fit4110/access-gate:lab04   DONE
```

## 2. Run evidence

Command:

```bash
docker run --rm --name fit4110-access-gate-lab04 \
  -p 8000:8000 --env-file .env.example fit4110/access-gate:lab04
```

Container log khởi động:

```text
INFO:     Started server process [7]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     GET /health HTTP/1.1 200 OK
```

Container chạy bằng user non-root:

```bash
$ docker exec fit4110-access-gate-lab04 whoami
appuser
$ docker inspect --format='{{.State.Health.Status}}' fit4110-access-gate-lab04
healthy
```

## 3. Healthcheck evidence

Command:

```bash
curl http://localhost:8000/health
```

Result:

```json
{
  "status": "ok",
  "service": "access-gate",
  "time": "2026-05-26T08:00:00Z"
}
```

## 4. Newman evidence

Command:

```bash
npm run test:local
```

Result: **15 requests / 30 assertions, 0 failed** (01_Functional, 02_Auth, 03_Negative, 04_Boundary_Reliability).

Report path:

```text
reports/newman-lab04-local.html
reports/newman-lab04-local.xml
```

Bằng chứng log thêm: `reports/docker-evidence.txt`.

## 5. Notes

- Known limitation: dữ liệu lưu in-memory (seed theo example của contract Lab 03); không có DB thật trong Lab 04.
- Image đã tag theo quy ước `v0.1.0-team-gate`; để push lên GHCR cần `docker login ghcr.io` với token có quyền `write:packages`.
- Next step cho Lab 05: ghép Access Gate + Core Business bằng Docker Compose (nhiều service).
