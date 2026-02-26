import Head from "next/head";

export default function WordPressNode({ node }) {
  if (!node) return <p>Not found</p>;

  return (
    <>
      <Head>
        <title>{node.title}</title>
      </Head>
      <main style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
        <a href="/">&larr; Back</a>
        <h1>{node.title}</h1>
        {node.date && <time>{new Date(node.date).toLocaleDateString()}</time>}
        <div dangerouslySetInnerHTML={{ __html: node.content }} />
      </main>
    </>
  );
}

export async function getServerSideProps(context) {
  const wpUrl = process.env.NEXT_PUBLIC_WORDPRESS_URL || "http://localhost:80";
  const slug = context.params?.wordpressNode?.join("/") || "";
  const uri = `/${slug}`;

  const res = await fetch(`${wpUrl}/graphql`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: `query GetContent($uri: String!) {
        nodeByUri(uri: $uri) {
          ... on Post { title content date }
          ... on Page { title content }
        }
      }`,
      variables: { uri },
    }),
  });
  const json = await res.json();
  const node = json.data?.nodeByUri || null;

  if (!node) return { notFound: true };
  return { props: { node } };
}
