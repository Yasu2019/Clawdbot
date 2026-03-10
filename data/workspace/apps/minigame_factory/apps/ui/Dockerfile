FROM node:20-slim
WORKDIR /app
COPY package.json next.config.js ./
RUN npm install
COPY pages ./pages
EXPOSE 3000
CMD ["npm", "run", "dev"]
