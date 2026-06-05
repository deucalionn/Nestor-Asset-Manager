import { defineConfig } from "orval";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default defineConfig({
  nam: {
    input: `${apiUrl}/openapi.json`,
    output: {
      mode: "tags-split",
      target: "./src/api/generated",
      client: "react-query",
      override: {
        mutator: {
          path: "./src/api/mutator.ts",
          name: "customFetch",
        },
      },
    },
  },
});
