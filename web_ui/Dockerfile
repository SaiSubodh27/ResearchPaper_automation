FROM node:18-alpine

WORKDIR /app

# Copy package and install
COPY package.json package-lock.json* ./
RUN npm install

# Copy frontend source code
COPY . .

# Expose port
EXPOSE 3000

# Start server
CMD ["node", "server.js"]
