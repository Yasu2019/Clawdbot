FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY app /app/app
EXPOSE 8090
CMD ["node", "app/server.js"]
