FROM node:24.21.0-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS build
WORKDIR /app/frontend
COPY examples/task-board/frontend/package.json examples/task-board/frontend/package-lock.json examples/task-board/frontend/.npmrc ./
COPY examples/task-board/frontend/tooling/ ./tooling/
RUN npm ci
COPY examples/task-board/frontend/ ./
RUN npm run build

FROM nginx:1.30.3-alpine@sha256:0d3b80406a13a767339fbe2f41406d6c7da727ab89cf8fae399e81f780f814d1
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY infra/nginx/task-board.conf.template /etc/nginx/templates/default.conf.template
