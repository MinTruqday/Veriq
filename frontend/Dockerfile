FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN apk add --no-cache curl \
    && curl --fail --location --retry 5 --retry-all-errors --output /tmp/pnpm.tgz https://registry.npmmirror.com/pnpm/-/pnpm-10.17.1.tgz \
    && echo "a1e0133f6801c13039ae41309e5e5a7d1058a3a1e1edd020a4944a83c5368d04  /tmp/pnpm.tgz" | sha256sum -c - \
    && npm install --global /tmp/pnpm.tgz --no-audit --no-fund \
    && apk del curl \
    && rm /tmp/pnpm.tgz

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
RUN mkdir -p public && pnpm run format:check && pnpm run lint && pnpm run build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

RUN mkdir -p .next/cache/images
RUN chown -R nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER 1001:1001

EXPOSE 3000
ENV PORT=3000

HEALTHCHECK --interval=30s --timeout=20s --start-period=30s --retries=3 CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["node","server.js"]
