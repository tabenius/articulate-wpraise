"use client";

import { NextJSExportWizard } from "@/components/export/nextjs-export-wizard";

export default function ExportPage() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Export to Next.js</h1>
          <p className="text-muted-foreground mt-2">
            Transform your WordPress site into a modern, blazing-fast Next.js application
          </p>
        </div>

        <NextJSExportWizard />

        {/* Feature Highlights */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">⚡ Lightning Fast</h3>
            <p className="text-sm text-muted-foreground">
              Static generation delivers instant page loads and perfect Core Web Vitals
            </p>
          </div>
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">🔒 Secure</h3>
            <p className="text-sm text-muted-foreground">
              No WordPress vulnerabilities, no PHP, no database to hack
            </p>
          </div>
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold mb-2">💰 Cost Effective</h3>
            <p className="text-sm text-muted-foreground">
              Deploy to Vercel, Netlify, or Cloudflare Pages for free
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
