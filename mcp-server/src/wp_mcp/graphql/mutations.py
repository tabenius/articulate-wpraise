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

UPDATE_POST = """
mutation UpdatePost($input: UpdatePostInput!) {
  updatePost(input: $input) {
    post {
      databaseId
      title
      slug
      status
      content
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

CREATE_CATEGORY = """
mutation CreateCategory($input: CreateCategoryInput!) {
  createCategory(input: $input) {
    category {
      databaseId
      name
      slug
      description
    }
  }
}
"""

CREATE_TAG = """
mutation CreateTag($input: CreateTagInput!) {
  createTag(input: $input) {
    tag {
      databaseId
      name
      slug
      description
    }
  }
}
"""
