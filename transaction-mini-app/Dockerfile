# --- 1. Build stage ---
FROM node:20-alpine AS builder

# Install build dependencies
RUN apk add --no-cache python3 make g++ gcc libc-dev

# Create .npmrc file for peer dependency issues
WORKDIR /app
RUN echo "legacy-peer-deps=true" > .npmrc

# Установка зависимостей
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Копирование исходного кода
COPY . .

# Add type declaration file for Telegram
RUN mkdir -p src/types && echo 'interface TelegramWebApp { WebApp: any; } interface Window { Telegram?: TelegramWebApp; }' > src/types/telegram.d.ts

# Сборка Next.js приложения
ENV NODE_OPTIONS="--max-old-space-size=4096" 
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build 

# Debug what was built
RUN ls -la .next/

# --- 2. Production stage ---
FROM node:20-alpine AS runner

# Install build dependencies for native modules
RUN apk add --no-cache python3 make g++ gcc libc-dev

# Create .npmrc file for peer dependency issues
WORKDIR /app
RUN echo "legacy-peer-deps=true" > .npmrc

# Установка только production-зависимостей
COPY package*.json ./
RUN npm install --omit=dev --legacy-peer-deps

# Копируем собранный Next.js билд из builder-слоя
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/package.json ./
COPY --from=builder /app/.env.local ./

# Debug what was copied
RUN ls -la .next/

# Стартовое окружение
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000

CMD ["npm", "start"]