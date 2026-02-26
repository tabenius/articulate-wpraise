import { getWordPressProps, WordPressTemplate } from "@faustwp/core";

export default function Page(props) {
  return <WordPressTemplate {...props} />;
}

export async function getServerSideProps(context) {
  return getWordPressProps({ ctx: context });
}
