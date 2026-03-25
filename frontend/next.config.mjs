/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/status",
        destination: "http://127.0.0.1:8000/api/status",
      },
      {
        source: "/api/artifacts",
        destination: "http://127.0.0.1:8000/api/artifacts",
      },
      {
        source: "/api/events/stream",
        destination: "http://127.0.0.1:8000/api/events/stream",
      },
    ];
  },
};

export default nextConfig;
