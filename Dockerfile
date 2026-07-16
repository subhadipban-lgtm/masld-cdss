FROM node:20-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install bun
RUN npm install -g bun@1

# Install dependencies
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Copy source
COPY . .

# Build
RUN bun run build

# Expose
EXPOSE 3000

CMD ["bun", "run", "start"]