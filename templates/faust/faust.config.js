import { setConfig } from "@faustwp/core";

/** @type {import('@faustwp/core').FaustConfig} */
export default setConfig({
  wpUrl: process.env.NEXT_PUBLIC_WORDPRESS_URL,
  apiClientSecret: process.env.FAUST_SECRET_KEY || "",
});
