// PPT·Word·PDF 원본을 붙였을 때 — DRM 때문에 이 PC 에서 추출해야 한다고 알리고 추출기를 준다
import { kindLabel } from './docAttach';

interface Props {
  filename: string;
  onClose: () => void;
}

/** DRM 문서는 그 PC·그 사용자 세션에서만 복호화된다. 서버가 원본을 받아 파싱하면 암호화된
 *  바이트만 본다 — ReportArchive 의 /imports/pptx 도, AI 데이터 허브의 convert_file 도 거기서
 *  막힌다. 그래서 추출을 PC 로 옮긴다. 올라가는 것은 원본이 아니라 추출된 글이다. */
export function DocExtractHint({ filename, onClose }: Props) {
  const ext = filename.slice(filename.lastIndexOf('.') + 1).toLowerCase();
  const label = kindLabel({ kind: ext === 'pptx' || ext === 'ppt' ? 'ppt' : ext === 'pdf' ? 'pdf' : 'word' });

  return (
    <div className="doc-hint" role="region" aria-label="문서 추출 안내">
      <div className="doc-hint-head">
        <strong>{filename}</strong>
        <span className="doc-hint-sub">{label} 는 이 PC 에서 읽습니다.</span>
        <button type="button" className="doc-hint-x" onClick={onClose} aria-label="닫기">×</button>
      </div>
      <p className="doc-hint-why">
        사내 DRM 문서는 <b>그 PC, 그 계정</b>에서만 복호화됩니다. 파일을 그대로 올리면 서버는
        암호화된 바이트만 보게 됩니다. 그래서 PC 에 설치된 Office 로 한 번 읽어 <b>글만</b>
        올립니다 — 원본 파일은 PC 를 떠나지 않습니다.
      </p>
      <ol className="doc-hint-steps">
        <li>
          아래 <b>두 파일을 같은 폴더</b>에 내려받습니다.
          <span className="doc-hint-dl">
            <a href="/doc-extract/hwax-doc-extract.bat" download>hwax-doc-extract.bat</a>
            <a href="/doc-extract/hwax-doc-extract.ps1" download>hwax-doc-extract.ps1</a>
          </span>
        </li>
        <li>
          <b>처음 한 번만</b> — <code>hwax-doc-extract.bat</code> 를 그냥 두 번 눌러 자가 시험을
          돌립니다(이 PC 에서 Office 를 부를 수 있는지 확인).
        </li>
        <li>
          <code>{filename}</code> 를 <code>hwax-doc-extract.bat</code> <b>위로 끌어다 놓습니다.</b>
          옆에 <code>{filename.replace(/\.[^.]+$/, '')}.hwax.md</code> 가 생깁니다.
        </li>
        <li>그 <code>.hwax.md</code> 를 여기 붙이면 내용을 읽고 심의합니다.</li>
      </ol>
      <p className="doc-hint-note">
        Word·PowerPoint 가 이미 열려 있어도 괜찮습니다 — 작업 중인 창은 건드리지 않습니다.
        스캔한 PDF 는 글자가 없어 빈 결과가 나옵니다.
      </p>
    </div>
  );
}
