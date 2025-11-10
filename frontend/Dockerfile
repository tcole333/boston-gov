# Boston Government Services Frontend
# Uses Node 18 and Vite for development

FROM node:18-alpine AS development

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
# If package.json hasn't changed, Docker will use cached layers
COPY package.json package-lock.json ./

# Install dependencies using npm ci for reproducible builds
# npm ci is faster and more reliable than npm install for CI/CD
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server
# --host flag allows connections from outside the container
# Note: vite.config.ts already has host: true, but CLI flag ensures compatibility
CMD ["npm", "run", "dev", "--", "--host"]
