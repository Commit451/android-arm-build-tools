import { defineConfig } from "astro/config";

// Custom domain (see public/CNAME). GitHub Pages serves the site
// at this URL once DNS is wired up.
export default defineConfig({
  site: "https://android-arm-build-tools.commit451.com",
  trailingSlash: "never",
  build: {
    inlineStylesheets: "always",
  },
});
