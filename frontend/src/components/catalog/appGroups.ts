// 앱 분류 — 카탈로그의 영문 분류 9종을 한국어 네 묶음으로(분류마다 색·칩이 달라 묶음 역할을 못 했다, docs/ui-refresh 단계 4)
const GROUP: Record<string, string> = {
  Simulation: '해석·시뮬레이션',
  Management: '해석·시뮬레이션',
  Engineering: '설계·검증',
  'Design Automation': '설계·검증',
  Data: '데이터·지식',
  Knowledge: '데이터·지식',
  Reporting: '데이터·지식',
  'AI Platform': 'AI 플랫폼',
  Intelligence: 'AI 플랫폼',
};

export const GROUP_ORDER = ['해석·시뮬레이션', '설계·검증', '데이터·지식', 'AI 플랫폼', '기타'];

export function groupOf(category?: string | null): string {
  return (category && GROUP[category]) || '기타';
}
