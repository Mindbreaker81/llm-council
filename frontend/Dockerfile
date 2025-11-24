FROM node:22-alpine

WORKDIR /app

COPY package.json .
# Copy package-lock.json if it exists, otherwise this might fail or warn, but usually safe to try or skip if we are sure. 
# Since I don't see package-lock.json in the file list, I'll skip it for now or just copy package*.json
COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
