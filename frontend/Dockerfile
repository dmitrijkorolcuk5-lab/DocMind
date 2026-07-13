FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN chown node:node /app

USER node
EXPOSE 5173
CMD ["npm", "run", "dev"]
