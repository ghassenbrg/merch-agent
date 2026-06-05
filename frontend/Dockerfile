FROM node:24-alpine AS build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM node:24-alpine

WORKDIR /app/frontend
COPY --from=build /app/frontend/.output ./.output

ENV HOST=0.0.0.0 \
    PORT=3000 \
    NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000 \
    NUXT_PUBLIC_API_TOKEN=
EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
