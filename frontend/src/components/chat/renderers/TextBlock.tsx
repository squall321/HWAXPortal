// Plain-text result renderer. graph/cad renderers (iframe sandbox / OCCT-wasm) are Phase 4.

export function TextBlock({ text }: { text: string }) {
  return <div className="chat-text">{text}</div>;
}
