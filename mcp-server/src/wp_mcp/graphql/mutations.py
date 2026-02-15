"""GraphQL mutation strings for writing WordPress data."""

CREATE_POST = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    post {
      databaseId
      title
      slug
      status
      content
    }
  }
}
"""

UPDATE_POST = """
mutation UpdatePost($input: UpdatePostInput!) {
  updatePost(input: $input) {
    post {
      databaseId
      title
      slug
      status
      content
    }
  }
}
"""

DELETE_POST = """
mutation DeletePost($input: DeletePostInput!) {
  deletePost(input: $input) {
    deletedId
    post {
      databaseId
      title
    }
  }
}
"""

CREATE_PAGE = """
mutation CreatePage($input: CreatePageInput!) {
  createPage(input: $input) {
    page {
      databaseId
      title
      slug
      status
      content
    }
  }
}
"""

UPDATE_PAGE = """
mutation UpdatePage($input: UpdatePageInput!) {
  updatePage(input: $input) {
    page {
      databaseId
      title
      slug
      status
      content
    }
  }
}
"""

DELETE_PAGE = """
mutation DeletePage($input: DeletePageInput!) {
  deletePage(input: $input) {
    deletedId
    page {
      databaseId
      title
    }
  }
}
"""
