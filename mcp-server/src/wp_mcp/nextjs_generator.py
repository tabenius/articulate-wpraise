"""Next.js project generator from WordPress export data."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


ContentFormat = Literal["react", "blocks", "mdx", "html"]
RenderStrategy = Literal["ssg", "ssr", "isr", "headless"]
MediaStrategy = Literal["download", "keep_urls", "cdn", "next_image"]


class NextJSGenerator:
    """Generate a complete Next.js project from WordPress export data."""

    def __init__(
        self,
        export_data: dict[str, Any],
        output_dir: str,
        content_format: ContentFormat = "react",
        render_strategy: RenderStrategy = "ssg",
        media_strategy: MediaStrategy = "download",
    ):
        """Initialize the generator.

        Args:
            export_data: WordPress export manifest
            output_dir: Directory to generate Next.js project in
            content_format: How to render WordPress blocks
            render_strategy: Next.js rendering strategy
            media_strategy: How to handle media files
        """
        self.export_data = export_data
        self.output_dir = Path(output_dir)
        self.content_format = content_format
        self.render_strategy = render_strategy
        self.media_strategy = media_strategy

    def generate(self) -> dict[str, Any]:
        """Generate the complete Next.js project.

        Returns:
            Generation result with file manifest
        """
        files_created = []

        # Create project structure
        self._create_directory_structure()
        files_created.extend(self._get_directory_list())

        # Generate configuration files
        files_created.append(self._generate_package_json())
        files_created.append(self._generate_next_config())
        files_created.append(self._generate_tsconfig())
        files_created.append(self._generate_tailwind_config())
        files_created.append(self._generate_gitignore())
        files_created.append(self._generate_readme())

        # Generate app directory files
        files_created.append(self._generate_root_layout())
        files_created.append(self._generate_home_page())

        # Generate content pages
        post_files = self._generate_post_pages()
        page_files = self._generate_page_pages()
        files_created.extend(post_files)
        files_created.extend(page_files)

        # Generate components
        component_files = self._generate_components()
        files_created.extend(component_files)

        # Generate lib utilities
        lib_files = self._generate_lib_files()
        files_created.extend(lib_files)

        # Generate styles
        files_created.append(self._generate_globals_css())

        return {
            "success": True,
            "output_dir": str(self.output_dir),
            "files_created": len(files_created),
            "files": files_created,
        }

    def _create_directory_structure(self) -> None:
        """Create the Next.js project directory structure."""
        dirs = [
            "",
            "app",
            "app/(posts)",
            "app/(posts)/[slug]",
            "app/(pages)",
            "app/(pages)/[[...slug]]",
            "components",
            "components/blocks",
            "components/layout",
            "lib",
            "public",
            "public/media",
            "styles",
        ]

        for dir_path in dirs:
            (self.output_dir / dir_path).mkdir(parents=True, exist_ok=True)

    def _get_directory_list(self) -> list[str]:
        """Get list of created directories."""
        return [
            "app/",
            "components/",
            "lib/",
            "public/",
            "styles/",
        ]

    def _generate_package_json(self) -> str:
        """Generate package.json with appropriate dependencies."""
        dependencies = {
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        }

        dev_dependencies = {
            "typescript": "^5.0.0",
            "@types/node": "^20.0.0",
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "tailwindcss": "^3.4.0",
            "postcss": "^8.4.0",
            "autoprefixer": "^10.4.0",
        }

        if self.content_format == "blocks":
            dependencies["@wordpress/block-library"] = "^8.0.0"
            dependencies["@wordpress/blocks"] = "^12.0.0"

        if self.content_format == "mdx":
            dependencies["@next/mdx"] = "^14.0.0"
            dependencies["@mdx-js/loader"] = "^3.0.0"
            dependencies["@mdx-js/react"] = "^3.0.0"

        package_json = {
            "name": "nextjs-from-wordpress",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
            },
            "dependencies": dependencies,
            "devDependencies": dev_dependencies,
        }

        file_path = self.output_dir / "package.json"
        with open(file_path, "w") as f:
            json.dump(package_json, f, indent=2)

        return "package.json"

    def _generate_next_config(self) -> str:
        """Generate next.config.js."""
        config_lines = [
            "/** @type {import('next').NextConfig} */",
            "const nextConfig = {",
        ]

        if self.render_strategy == "ssg":
            config_lines.append("  output: 'export',")

        if self.media_strategy in ["download", "next_image"]:
            config_lines.extend([
                "  images: {",
                "    unoptimized: true,",
                "  },",
            ])

        config_lines.extend([
            "}",
            "",
            "module.exports = nextConfig",
        ])

        file_path = self.output_dir / "next.config.js"
        with open(file_path, "w") as f:
            f.write("\n".join(config_lines))

        return "next.config.js"

    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json."""
        tsconfig = {
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [
                    {
                        "name": "next"
                    }
                ],
                "paths": {
                    "@/*": ["./*"]
                }
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"]
        }

        file_path = self.output_dir / "tsconfig.json"
        with open(file_path, "w") as f:
            json.dump(tsconfig, f, indent=2)

        return "tsconfig.json"

    def _generate_tailwind_config(self) -> str:
        """Generate tailwind.config.js."""
        config = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""

        file_path = self.output_dir / "tailwind.config.js"
        with open(file_path, "w") as f:
            f.write(config)

        # Also create postcss.config.js
        postcss_config = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
        postcss_path = self.output_dir / "postcss.config.js"
        with open(postcss_path, "w") as f:
            f.write(postcss_config)

        return "tailwind.config.js"

    def _generate_gitignore(self) -> str:
        """Generate .gitignore."""
        gitignore = """# dependencies
/node_modules
/.pnp
.pnp.js

# testing
/coverage

# next.js
/.next/
/out/

# production
/build

# misc
.DS_Store
*.pem

# debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# local env files
.env*.local

# vercel
.vercel

# typescript
*.tsbuildinfo
next-env.d.ts
"""

        file_path = self.output_dir / ".gitignore"
        with open(file_path, "w") as f:
            f.write(gitignore)

        return ".gitignore"

    def _generate_readme(self) -> str:
        """Generate README.md."""
        site_title = self.export_data.get("site", {}).get("title", "My Site")
        export_date = datetime.now().strftime("%Y-%m-%d")

        readme = f"""# {site_title}

This is a Next.js site generated from WordPress.

**Export Date:** {export_date}
**Rendering Strategy:** {self.render_strategy.upper()}
**Content Format:** {self.content_format}

## Getting Started

First, install dependencies:

```bash
npm install
# or
yarn install
# or
pnpm install
```

Then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Build for Production

```bash
npm run build
npm run start
```

## Deploy

This site can be deployed to any static hosting service (Vercel, Netlify, Cloudflare Pages, etc.).

```bash
npm run build
```

The output will be in the `out/` directory (for static export) or can be deployed directly to Vercel.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [WordPress Migration Guide](https://github.com/your-repo/wp-to-nextjs)
"""

        file_path = self.output_dir / "README.md"
        with open(file_path, "w") as f:
            f.write(readme)

        return "README.md"

    def _generate_root_layout(self) -> str:
        """Generate app/layout.tsx."""
        site_title = self.export_data.get("site", {}).get("title", "My Site")
        site_description = self.export_data.get("site", {}).get("description", "")

        layout = f"""import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{site_title}',
  description: '{site_description}',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>
        <header className="border-b">
          <div className="container mx-auto px-4 py-6">
            <h1 className="text-2xl font-bold">{site_title}</h1>
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          {{children}}
        </main>
        <footer className="border-t mt-12">
          <div className="container mx-auto px-4 py-6 text-center text-sm text-gray-600">
            © {datetime.now().year} {site_title}
          </div>
        </footer>
      </body>
    </html>
  )
}}
"""

        file_path = self.output_dir / "app" / "layout.tsx"
        with open(file_path, "w") as f:
            f.write(layout)

        return "app/layout.tsx"

    def _generate_home_page(self) -> str:
        """Generate app/page.tsx."""
        posts = self.export_data.get("content", {}).get("posts", [])

        page = """import Link from 'next/link'

export default function Home() {
  const posts = """ + json.dumps(posts[:10], indent=2) + """

  return (
    <div>
      <h1 className="text-4xl font-bold mb-8">Latest Posts</h1>
      <div className="grid gap-6">
        {posts.map((post: any) => (
          <article key={post.databaseId} className="border rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-2">
              <Link href={`/${post.slug}`} className="hover:text-blue-600">
                {post.title}
              </Link>
            </h2>
            {post.excerpt && (
              <div className="text-gray-600" dangerouslySetInnerHTML={{ __html: post.excerpt }} />
            )}
            <div className="mt-4 text-sm text-gray-500">
              {new Date(post.date).toLocaleDateString()}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
"""

        file_path = self.output_dir / "app" / "page.tsx"
        with open(file_path, "w") as f:
            f.write(page)

        return "app/page.tsx"

    def _generate_globals_css(self) -> str:
        """Generate app/globals.css."""
        css = """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
}
"""

        file_path = self.output_dir / "app" / "globals.css"
        with open(file_path, "w") as f:
            f.write(css)

        return "app/globals.css"

    def _generate_post_pages(self) -> list[str]:
        """Generate individual post pages."""
        posts = self.export_data.get("content", {}).get("posts", [])

        # Generate dynamic route
        page_content = """export async function generateStaticParams() {
  return """ + json.dumps([{"slug": p["slug"]} for p in posts], indent=2) + """
}

export default function Post({ params }: { params: { slug: string } }) {
  const posts = """ + json.dumps(posts, indent=2) + """

  const post = posts.find((p: any) => p.slug === params.slug)

  if (!post) {
    return <div>Post not found</div>
  }

  return (
    <article>
      <h1 className="text-4xl font-bold mb-4">{post.title}</h1>
      <div className="text-gray-600 mb-8">
        {new Date(post.date).toLocaleDateString()}
      </div>
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: post.content }}
      />
    </article>
  )
}
"""

        file_path = self.output_dir / "app" / "(posts)" / "[slug]" / "page.tsx"
        with open(file_path, "w") as f:
            f.write(page_content)

        return ["app/(posts)/[slug]/page.tsx"]

    def _generate_page_pages(self) -> list[str]:
        """Generate individual page pages."""
        pages = self.export_data.get("content", {}).get("pages", [])

        # Generate catch-all route
        page_content = """export async function generateStaticParams() {
  return """ + json.dumps([{"slug": [p["slug"]]} for p in pages], indent=2) + """
}

export default function Page({ params }: { params: { slug?: string[] } }) {
  const pages = """ + json.dumps(pages, indent=2) + """

  const pageSlug = params.slug?.[0] || 'home'
  const page = pages.find((p: any) => p.slug === pageSlug)

  if (!page) {
    return <div>Page not found</div>
  }

  return (
    <article>
      <h1 className="text-4xl font-bold mb-8">{page.title}</h1>
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: page.content }}
      />
    </article>
  )
}
"""

        file_path = self.output_dir / "app" / "(pages)" / "[[...slug]]" / "page.tsx"
        with open(file_path, "w") as f:
            f.write(page_content)

        return ["app/(pages)/[[...slug]]/page.tsx"]

    def _generate_components(self) -> list[str]:
        """Generate reusable components."""
        # For now, placeholder
        return []

    def _generate_lib_files(self) -> list[str]:
        """Generate library/utility files."""
        # For now, placeholder
        return []
