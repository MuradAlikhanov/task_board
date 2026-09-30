// ESLint (flat config). `next lint` удалён в Next 16 — линтер запускается
// напрямую: npm run lint → eslint . (https://nextjs.org/docs/app/api-reference/config/eslint)
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
