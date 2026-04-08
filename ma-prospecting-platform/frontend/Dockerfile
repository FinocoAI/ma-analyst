FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm install

ENV PATH /app/node_modules/.bin:$PATH

COPY . .

EXPOSE 3010
CMD ["npm", "run", "dev", "--port", "3010"]
