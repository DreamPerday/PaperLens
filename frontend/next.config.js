/** @type {import('next').NextConfig} */

const API_PORT = process.env.API_PORT || process.env.NEXT_PUBLIC_API_PORT || '8000'

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['katex'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://localhost:${API_PORT}/api/:path*`,
      },
      {
        source: '/static/:path*',
        destination: `http://localhost:${API_PORT}/static/:path*`,
      },
    ]
  },
}

module.exports = nextConfig