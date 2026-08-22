FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Expose host to bind on 0.0.0.0 so we can access it outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
