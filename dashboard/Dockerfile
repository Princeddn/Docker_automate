FROM node:18-alpine

# Installation des dépendances pour better-sqlite3 (besoin de compilation)
RUN apk add --no-cache python3 make g++

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "sensor_dashboard.js"]
