import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'WP-AI Documentation',
  description: 'AI-powered WordPress content editor with Claude',
  base: '/docs/',
  ignoreDeadLinks: true,  // TODO: Fix symlinks in Docker build

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
      { text: 'Deployment', link: '/deployment/' },
      { text: 'Security', link: '/security' },
      { text: 'GitHub', link: 'https://github.com/tabenius/wpraise' }
    ],

    sidebar: {
      '/': [
        {
          text: 'Introduction',
          items: [
            { text: 'What is WP-AI?', link: '/' },
            { text: 'Getting Started', link: '/getting-started' },
            { text: 'Architecture', link: '/architecture' },
            { text: 'Features', link: '/features' }
          ]
        },
        {
          text: 'Deployment',
          items: [
            { text: 'Overview', link: '/deployment/' },
            { text: 'Quick Reference', link: '/deployment/quick-reference' },
            { text: 'Automated Setup', link: '/deployment/automated-setup' },
            { text: 'Reverse Proxies', link: '/deployment/reverse-proxies' },
            { text: 'HAProxy + Caddy', link: '/deployment/haproxy-caddy' },
            { text: 'SSL/TLS Setup', link: '/deployment/ssl' },
            { text: 'Security Hardening', link: '/deployment/security' }
          ]
        },
        {
          text: 'Configuration',
          items: [
            { text: 'Environment Variables', link: '/config/environment' },
            { text: 'Domain Configuration', link: '/config/domain' },
            { text: 'Multi-User Setup', link: '/config/multi-user' }
          ]
        },
        {
          text: 'Security',
          items: [
            { text: 'Security Guide', link: '/security' },
            { text: 'Authentication', link: '/security/authentication' },
            { text: 'Rate Limiting', link: '/security/rate-limiting' },
            { text: 'Audit Logging', link: '/security/audit-logging' }
          ]
        },
        {
          text: 'Development',
          items: [
            { text: 'Project Structure', link: '/dev/structure' },
            { text: 'MCP Tools', link: '/dev/mcp-tools' },
            { text: 'Contributing', link: '/dev/contributing' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/tabenius/wpraise' }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-present'
    },

    search: {
      provider: 'local'
    }
  }
})
