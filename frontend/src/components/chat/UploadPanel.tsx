// 물성 파일 업로드 패널 — 첨부→메타 입력→dry_run 미리보기→확정. 챗 입력 위에 인라인으로 뜬다.
import { useState } from 'react';
import {
  analyzeUpload,
  commitUpload,
  type StagedFile,
  type UploadMeta,
  type UploadResult,
} from '../../api/upload.api';

const CATEGORIES = ['metal', 'polymer', 'rubber', 'composite', 'ceramic', 'foam'];

export function UploadPanel({ staged, onClose }: { staged: StagedFile; onClose: () => void }) {
  const [meta, setMeta] = useState<UploadMeta>({
    staging_id: staged.staging_id,
    filename: staged.filename,
    material_name: staged.filename.replace(/\.[^.]+$/, ''),
    category: 'metal',
    gauge_length_mm: 25,
    width_mm: 5,
    thickness_mm: 1,
  });
  const [preview, setPreview] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState<'' | 'preview' | 'commit'>('');
  const [err, setErr] = useState('');
  const [done, setDone] = useState<UploadResult | null>(null);

  const set = <K extends keyof UploadMeta>(k: K, v: UploadMeta[K]) =>
    setMeta((m) => ({ ...m, [k]: v }));

  async function run(kind: 'preview' | 'commit') {
    setBusy(kind);
    setErr('');
    try {
      const res = kind === 'preview' ? await analyzeUpload(meta) : await commitUpload(meta);
      if (res.stage === 'parse' && res.needs_manual_mapping) {
        setErr(`${res.reason ?? '파일에서 변형률/응력 열을 찾지 못했습니다.'}`);
      } else if (res.error) {
        setErr(res.error);
      } else if (kind === 'commit' && res.stage === 'committed') {
        setDone(res);
      } else {
        setPreview(res);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : '실패했습니다.');
    } finally {
      setBusy('');
    }
  }

  if (done) {
    return (
      <div className="upl-panel upl-done" role="status">
        <b>✓ 등록 완료</b> — 재료 #{done.material_id}, 시험 #{done.test_id}
        {done.properties && (
          <span className="upl-props">
            E {done.properties.E_GPa}GPa · 항복 {done.properties.yield_MPa}MPa · UTS{' '}
            {done.properties.UTS_MPa}MPa
          </span>
        )}
        <button type="button" className="upl-x" onClick={onClose}>
          닫기
        </button>
      </div>
    );
  }

  const p = preview?.properties;
  return (
    <div className="upl-panel">
      <div className="upl-head">
        <b>물성 파일 업로드</b>
        <span className="upl-file">{staged.filename}</span>
        <button type="button" className="upl-x" onClick={onClose} aria-label="닫기">
          ✕
        </button>
      </div>

      <div className="upl-grid">
        <label>
          재료명
          <input
            value={meta.material_name ?? ''}
            onChange={(e) => set('material_name', e.target.value)}
            placeholder="예: SPFC980Y"
          />
        </label>
        <label>
          분류
          <select value={meta.category} onChange={(e) => set('category', e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          기존 재료 ID (선택)
          <input
            type="number"
            value={meta.material_id ?? ''}
            onChange={(e) => set('material_id', e.target.value ? Number(e.target.value) : null)}
            placeholder="비우면 새 재료"
          />
        </label>
        <label>
          게이지 길이 mm
          <input
            type="number"
            value={meta.gauge_length_mm}
            onChange={(e) => set('gauge_length_mm', Number(e.target.value))}
          />
        </label>
        <label>
          폭 mm
          <input
            type="number"
            value={meta.width_mm}
            onChange={(e) => set('width_mm', Number(e.target.value))}
          />
        </label>
        <label>
          두께 mm
          <input
            type="number"
            value={meta.thickness_mm}
            onChange={(e) => set('thickness_mm', Number(e.target.value))}
          />
        </label>
      </div>

      {preview && (
        <div className="upl-preview">
          {p && p.E_GPa != null ? (
            <>
              <b>미리보기 (저장 안 됨)</b>
              <span className="upl-props">
                E {p.E_GPa}GPa · 항복 {p.yield_MPa}MPa · UTS {p.UTS_MPa}MPa · 연신 {p.elong_pct}%
              </span>
              {preview.fits && preview.fits.length > 0 && (
                <span className="upl-fits">
                  피팅: {preview.fits.map((f) => `${f.model}(R²${f.r2})`).join(' · ')}
                </span>
              )}
            </>
          ) : (
            <span className="upl-note">{preview.note ?? '미리보기 준비됨.'}</span>
          )}
        </div>
      )}

      {err && (
        <div className="upl-err" role="alert">
          ⚠ {err}
        </div>
      )}

      <div className="upl-actions">
        <button type="button" onClick={() => run('preview')} disabled={busy !== ''}>
          {busy === 'preview' ? '계산 중…' : '미리보기'}
        </button>
        <button
          type="button"
          className="upl-commit"
          onClick={() => run('commit')}
          disabled={busy !== '' || (!preview && !meta.material_id)}
          title={!preview ? '먼저 미리보기로 값을 확인하세요' : '물성 DB 에 등록'}
        >
          {busy === 'commit' ? '등록 중…' : '등록 확정'}
        </button>
      </div>
    </div>
  );
}
