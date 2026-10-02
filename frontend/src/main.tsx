import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
// 한국어 UI 글꼴(OFL) — 빌드에 번들된다(woff2 를 dist 로 복사, 글자 범위별로 필요한 조각만 받는다). 런타임 CDN 없음.
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import './styles/tokens.css';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
