import Head from "next/head";

export default function Home({ posts, generalSettings }) {
  return (
    <>
      <Head>
        <title>{generalSettings?.title}</title>
        <meta name="description" content={generalSettings?.description} />
      </Head>
      <main style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
        <h1>{generalSettings?.title}</h1>
        <p>{generalSettings?.description}</p>
        {posts?.map((post) => (
          <article key={post.id} style={{ marginBottom: 24 }}>
            <h2>
              <a href={post.uri}>{post.title}</a>
            </h2>
            <div dangerouslySetInnerHTML={{ __html: post.excerpt }} />
            <time>{new Date(post.date).toLocaleDateString()}</time>
          </article>
        ))}
      </main>
    </>
  );
}

export async function getServerSideProps() {
  const wpUrl = process.env.NEXT_PUBLIC_WORDPRESS_URL || "http://localhost:80";
  const res = await fetch(`${wpUrl}/graphql`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: `query {
        posts(first: 10) {
          nodes { id title excerpt uri date }
        }
        generalSettings { title description }
      }`,
    }),
  });
  const json = await res.json();
  return {
    props: {
      posts: json.data?.posts?.nodes || [],
      generalSettings: json.data?.generalSettings || {},
    },
  };
}
