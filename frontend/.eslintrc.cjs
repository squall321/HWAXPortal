module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['react-refresh'],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'vite.config.ts', 'e2e/.results', 'e2e/.shots'],
  rules: {
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
  },
  // 화면 점검·검사 스크립트는 node 에서 돈다(브라우저 앱 코드가 아니다)
  overrides: [{ files: ['e2e/**/*.ts', 'scripts/**/*.mjs', 'playwright.config.ts'], env: { node: true, browser: true } }],
};
