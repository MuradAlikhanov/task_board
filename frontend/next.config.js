/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // standalone: минимальный server.js без полного node_modules в runtime-образе
  // (см. frontend/Dockerfile — runner-стадия).
  output: "standalone",
};

module.exports = nextConfig;
