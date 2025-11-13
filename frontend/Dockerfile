# ---- Build Stage ----
FROM node:20-bullseye AS build
WORKDIR /app

# Copy dependency manifests
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy ALL project files
COPY . .

# Accept build argument and set as environment variable for Vite
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build optimized static site
RUN npm run build

# ---- Serve Stage ----
FROM node:20-bullseye
WORKDIR /app

# Install lightweight static file server
RUN npm install -g serve

# Copy build output from previous stage
COPY --from=build /app/dist ./dist

# Expose Cloud Run port
EXPOSE 8080

# Serve on the expected Cloud Run port
CMD ["serve", "-s", "dist", "-l", "8080", "--single"]