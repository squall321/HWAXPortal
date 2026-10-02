// 화면 점검(e2e/ui.spec.ts) 설정 — 임시 포털 주소는 scripts/ui-check.sh 가 UI_BASE 로 넘긴다
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/.results',
  timeout: 180_000,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.UI_BASE ?? 'http://127.0.0.1:8794',
    locale: 'ko-KR',
    colorScheme: 'light', // 사용자 PC(Windows) 기본값과 같게 — 다크 전용 앱이 OS 설정에 흔들리지 않는지도 같이 본다
  },
});
