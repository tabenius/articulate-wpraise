"""GraphQL query strings for reading WordPress data."""

GET_POSTS = """
query GetPosts($first: Int, $where: RootQueryToPostConnectionWhereArgs) {
  posts(first: $first, where: $where) {
    nodes {
      databaseId
      title
      slug
      status
      date
      modified
      excerpt
      author {
        node {
          name
        }
      }
      featuredImage {
        node {
          databaseId
          sourceUrl
          altText
          mediaDetails {
            width
            height
          }
        }
      }
    }
  }
}
"""

GET_POST = """
query GetPost($id: ID!) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    title
    slug
    status
    content
    date
    modified
    author {
      node {
        name
      }
    }
    featuredImage {
      node {
        databaseId
        sourceUrl
        altText
        mediaDetails {
          width
          height
        }
      }
    }
    categories {
      nodes {
        databaseId
        name
        slug
      }
    }
    tags {
      nodes {
        databaseId
        name
        slug
      }
    }
  }
}
"""

GET_POST_WITH_BLOCKS = """
query GetPostWithBlocks($id: ID!) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    title
    slug
    status
    content
    date
    modified
    editorBlocks(flat: true) {
      __typename
      name
      clientId
      parentClientId
      renderedHtml
      ... on CoreParagraph {
        attributes {
          content
          className
          align
          dropCap
        }
      }
      ... on CoreHeading {
        attributes {
          content
          level
          textAlign
          className
        }
      }
      ... on CoreImage {
        attributes {
          url
          alt
          caption
          width
          height
          className
          sizeSlug
        }
      }
      ... on CoreList {
        attributes {
          ordered
          values
          className
        }
      }
      ... on CoreQuote {
        attributes {
          value
          citation
          className
        }
      }
      ... on CoreCode {
        attributes {
          content
          className
        }
      }
      ... on CoreColumns {
        attributes {
          verticalAlignment
          className
        }
      }
      ... on CoreColumn {
        attributes {
          width
          verticalAlignment
          className
        }
      }
      ... on CoreGroup {
        attributes {
          tagName
          className
        }
      }
      ... on CoreButtons {
        attributes {
          className
        }
      }
      ... on CoreButton {
        attributes {
          text
          url
          className
        }
      }
      ... on CoreSpacer {
        attributes {
          height
          className
        }
      }
      ... on CoreSeparator {
        attributes {
          className
          opacity
        }
      }
    }
  }
}
"""

GET_PAGES = """
query GetPages($first: Int) {
  pages(first: $first) {
    nodes {
      databaseId
      title
      slug
      status
      date
      modified
    }
  }
}
"""

GET_PAGE = """
query GetPage($id: ID!) {
  page(id: $id, idType: DATABASE_ID) {
    databaseId
    title
    slug
    status
    content
    date
    modified
  }
}
"""

GET_PAGE_WITH_BLOCKS = """
query GetPageWithBlocks($id: ID!) {
  page(id: $id, idType: DATABASE_ID) {
    databaseId
    title
    slug
    status
    content
    date
    modified
    editorBlocks(flat: true) {
      __typename
      name
      clientId
      parentClientId
      renderedHtml
      ... on CoreParagraph {
        attributes {
          content
          className
          align
          dropCap
        }
      }
      ... on CoreHeading {
        attributes {
          content
          level
          textAlign
          className
        }
      }
      ... on CoreImage {
        attributes {
          url
          alt
          caption
          width
          height
          className
        }
      }
    }
  }
}
"""

GET_MEDIA = """
query GetMedia($first: Int) {
  mediaItems(first: $first) {
    nodes {
      databaseId
      title
      sourceUrl
      altText
      mediaDetails {
        width
        height
        file
      }
      mimeType
      date
    }
  }
}
"""

GET_MEDIA_ITEM = """
query GetMediaItem($id: ID!) {
  mediaItem(id: $id, idType: DATABASE_ID) {
    databaseId
    title
    sourceUrl
    altText
    caption
    mediaDetails {
      width
      height
      file
    }
    mimeType
    date
  }
}
"""

SEARCH_CONTENT = """
query SearchContent($search: String!, $first: Int) {
  posts(where: {search: $search}, first: $first) {
    nodes {
      databaseId
      title
      excerpt
      status
    }
  }
  pages(where: {search: $search}, first: $first) {
    nodes {
      databaseId
      title
      excerpt
      status
    }
  }
}
"""

GET_CATEGORIES = """
query GetCategories($first: Int) {
  categories(first: $first) {
    nodes {
      databaseId
      name
      slug
      description
      count
    }
  }
}
"""

GET_TAGS = """
query GetTags($first: Int) {
  tags(first: $first) {
    nodes {
      databaseId
      name
      slug
      description
      count
    }
  }
}
"""

GET_POST_REVISIONS = """
query GetPostRevisions($id: ID!, $first: Int = 20) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    revisions(first: $first, where: {orderby: {field: DATE, order: DESC}}) {
      nodes {
        databaseId
        date
        modified
        author {
          node {
            name
            email
          }
        }
        content
        title
      }
    }
  }
}
"""

GET_REVISION_DETAILS = """
query GetRevision($id: ID!) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    date
    modified
    title
    content
    author {
      node {
        name
        email
      }
    }
  }
}
"""

GET_VIEWER_CAPABILITIES = """
query GetViewerCapabilities {
  viewer {
    databaseId
    username
    email
    roles {
      nodes {
        name
      }
    }
  }
}
"""
