FROM node:20 AS build
WORKDIR /app
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY package.json ./
RUN npm install --no-audit --no-fund --legacy-peer-deps
COPY . .
RUN npx ng build --configuration=production

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ai-governance-proxy-ui/browser /usr/share/nginx/html
EXPOSE 80
