"""Auto-generated GraphQL queries from WordPress schema."""

CONTENTNODE_QUERY = """
query Contentnode($id: ID!, $idType: ContentNodeIdTypeEnum, $contentType: ContentTypeEnum, $asPreview: Boolean) {
  contentNode(id: $id, idType: $idType, contentType: $contentType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

PAGE_QUERY = """
query Page($id: ID!, $idType: PageIdType, $asPreview: Boolean) {
  page(id: $id, idType: $idType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

PAGES_QUERY = """
query Pages($first: Int, $last: Int, $after: String, $before: String, $where: RootQueryToPageConnectionWhereArgs) {
  pages(first: $first, last: $last, after: $after, before: $before, where: $where) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

POST_QUERY = """
query Post($id: ID!, $idType: PostIdType, $asPreview: Boolean) {
  post(id: $id, idType: $idType, asPreview: $asPreview) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

POSTS_QUERY = """
query Posts($first: Int, $last: Int, $after: String, $before: String, $where: RootQueryToPostConnectionWhereArgs) {
  posts(first: $first, last: $last, after: $after, before: $before, where: $where) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

CREATEPAGE_QUERY = """
mutation Createpage($input: CreatePageInput!) {
  createPage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

CREATEPOST_QUERY = """
mutation Createpost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

DELETEPAGE_QUERY = """
mutation Deletepage($input: DeletePageInput!) {
  deletePage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

DELETEPOST_QUERY = """
mutation Deletepost($input: DeletePostInput!) {
  deletePost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

UPDATEPAGE_QUERY = """
mutation Updatepage($input: UpdatePageInput!) {
  updatePage(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

UPDATEPOST_QUERY = """
mutation Updatepost($input: UpdatePostInput!) {
  updatePost(input: $input) {
    ... on Post {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
    ... on Page {
      databaseId
      title
      slug
      status
      content
      date
      modified
    }
  }
}
"""

