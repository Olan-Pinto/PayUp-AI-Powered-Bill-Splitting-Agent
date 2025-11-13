FROM node:20-bullseye

WORKDIR /app

COPY package*.json ./

# Clean install with explicit native binary
RUN rm -rf node_modules package-lock.json
RUN npm install --include=dev --legacy-peer-deps
RUN npm install @rollup/rollup-linux-x64-gnu --save-optional --no-save

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]