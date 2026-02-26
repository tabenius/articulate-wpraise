import { gql, useQuery } from "@faustwp/core";
import Head from "next/head";

const GET_POSTS = gql`
  query GetPosts {
    posts(first: 10) {
      nodes {
        id
        title
        excerpt
        uri
        date
      }
    }
    generalSettings {
      title
      description
    }
  }
`;

export default function Home() {
  const { data, loading } = useQuery(GET_POSTS);

  if (loading) return <p>Loading...</p>;

  const { posts, generalSettings } = data || {};

  return (
    <>
      <Head>
        <title>{generalSettings?.title}</title>
        <meta name="description" content={generalSettings?.description} />
      </Head>
      <main style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
        <h1>{generalSettings?.title}</h1>
        <p>{generalSettings?.description}</p>
        {posts?.nodes?.map((post) => (
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

Home.query = GET_POSTS;
