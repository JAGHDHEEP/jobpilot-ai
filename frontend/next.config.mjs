/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  // Don't let a stray type error block the deploy build (CI still type-checks).
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
