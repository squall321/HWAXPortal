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
  overrides: [
    { files: ['e2e/**/*.ts', 'scripts/**/*.mjs', 'playwright.config.ts'], env: { node: true, browser: true } },
    // 인라인 스타일을 토큰 CSS 로 옮긴 곳 — 다시 늘지 않게 막는다(docs/ui-refresh 단계 3). 옮기는 대로 여기 더한다.
    {
      files: [
        'src/pages/admin/**/*.tsx',
        'src/components/admin/**/*.tsx',
        'src/pages/TokenPage.tsx',
        'src/components/RaConnectionCard.tsx',
        'src/components/TestScopeConnectionCard.tsx',
        'src/components/HubAppsPanel.tsx',
        // 절차 — 상태에 따라 색이 바뀌는 9곳이 남은 ProceduresPage·RunSteps 는 넣지 않는다
        'src/pages/procedures/BuildView.tsx',
        'src/pages/procedures/ArgsForm.tsx',
      ],
      rules: {
        'no-restricted-syntax': [
          'error',
          { selector: "JSXAttribute[name.name='style']", message: '인라인 style 대신 토큰 CSS 클래스를 쓴다(docs/ui-refresh 단계 3).' },
        ],
      },
    },
  ],
};
