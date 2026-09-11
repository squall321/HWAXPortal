// 전문가 상세 공용 조각 — HE팀 운영 앱 줄·보유 지식 제목(챗 조직도·심의 좌석 조직도 상세칸 공용)
import type { AgentDetail } from '../../api/chat.api';

/** 상세칸의 보유 지식 제목 — 목록은 미리보기(앞 20건)라서 실제 총수와 '전체 보기'를 함께 보인다.
 *  예전엔 '보유 지식 20건'이라 2,729건인 사람도 20건으로 읽혔다. */
export function RecordsHeading({ detail, onMore }: { detail: AgentDetail; onMore: () => void }) {
  const total = detail.records_total ?? detail.records.length;
  const preview = detail.records.length;
  return (
    <h4 className="pv-detail-h pv-rec-h">
      <span>
        보유 지식 {total.toLocaleString('ko-KR')}건
        {total > preview && <span className="pv-dim"> · 앞 {preview}건</span>}
      </span>
      <button type="button" className="pv-more" onClick={onMore}>
        전체 보기 →
      </button>
    </h4>
  );
}

/** HE팀 MCP 운영자 — 보유 지식이 0건인 게 정상이라, 무엇으로 답하는지(앱·도구 수)를 대신 보인다.
 *  이 서버 게이트웨이에 없는 앱(cae00 전용 arp·odb-hub 를 dev 에서 본 경우)은 그렇다고 적는다. */
export function OperatorApps({ detail }: { detail: AgentDetail }) {
  if (!detail.operator) return null;
  const apps = detail.apps ?? [];
  return (
    <div className="pv-op">
      <h4 className="pv-detail-h">MCP 운영자 — 대화하면 이 앱의 도구를 직접 호출해 답합니다</h4>
      <ul className="pv-op-apps">
        {apps.map((a) => (
          <li key={a.key} className={`pv-op-app${a.connected === false ? ' is-off' : ''}`}>
            <span className="pv-op-name">{a.label}</span>
            <span className="pv-dim">{a.connected === false ? '이 서버에 연결 안 됨' : `도구 ${a.tool_count}개`}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
