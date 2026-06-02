# Docker Readiness Checklist

## Dockerfile

- [x] Có base image hợp lý. (`python:3.11-slim`, multi-stage builder + runtime)
- [x] Có `WORKDIR`. (`/build`, `/app`)
- [x] Có copy dependency trước source để tận dụng cache. (`COPY requirements.txt` trước, build venv)
- [x] Có `EXPOSE`. (`EXPOSE 8000`)
- [x] Có `CMD` hoặc `ENTRYPOINT`. (`uvicorn access_gate.main:app`)
- [x] Có `HEALTHCHECK`. (gọi `GET /health`)
- [x] Có user non-root. (`appuser`/`appgroup`)
- [x] Không chứa secret thật. (chỉ `AUTH_TOKEN=local-dev-token` mặc định)

## Runtime

- [x] Container chạy được.
- [x] Port map đúng. (`-p 8000:8000`)
- [x] `/health` trả `200`. (`{"status":"ok","service":"access-gate",...}`)
- [x] Log khởi động rõ ràng. (uvicorn startup complete)
- [x] Cấu hình qua ENV. (`--env-file .env.example`)

## Testing

- [x] Chạy lại Postman Collection từ Lab 03. (collection Access Gate, 4 nhóm: Functional/Auth/Negative/Boundary)
- [x] Newman report sinh ra trong `reports/`. (`newman-lab04-local.xml/.html`)
- [x] Functional test pass. (health, logs, log by id, card, gate, POST event)
- [x] Auth test pass trên local/container. (thiếu/sai token → 401)
- [x] Negative test pass trên local/container. (gateId sai → 422, card không tồn tại → 404, payload sai → 400)
- [x] Boundary test pass hoặc có giải thích hợp đồng. (limit=100 ok, limit=101 → 422)

## Evidence

- [x] Có ảnh/log `docker build`. (`templates/docker-evidence-template.md`)
- [x] Có ảnh/log `docker run`. (`reports/docker-evidence.txt`)
- [x] Có ảnh/log `curl /health`. (`reports/docker-evidence.txt`)
- [x] Có Newman HTML/XML report. (`reports/newman-lab04-local.html` + `.xml`)
- [x] Có tag image đúng quy ước. (`ghcr.io/manhvuok/team-gate:v0.1.0-team-gate`)
