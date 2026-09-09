// 이력 문구의 `**굵게**` 만 그리는 최소 렌더 — 팝업과 이력 페이지가 함께 쓴다
/** `**굵게**` 만 지원하는 최소 렌더. 이력 문구가 쓰는 유일한 마크업이라 마크다운 스택을
 *  끌어오지 않는다(레이아웃·페이지 컴포넌트가 챗 렌더러에 묶이면 안 된다). */
export function ChangelogBold({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
        part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
          <b key={i}>{part.slice(2, -2)}</b>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
