// 메시지 컴포저 — 자동 높이 textarea, Enter 전송/Shift+Enter 줄바꿈(IME 안전), 스트리밍 중지 버튼
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type DragEvent as ReactDragEvent,
  type FormEvent,
  type KeyboardEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { useChat } from '../../state/ChatContext';
import { shortName } from './personaColor';
import { SearchToggle } from './SourcePanel';
import { ThinkToggle } from './ThinkPanel';
import { ExpertToggle } from './ExpertToggle';
import { RoutineToggle } from './RoutineToggle';
import { IconFile, IconPlus, IconSend, IconStop, IconUser } from './icons';
import { useAuth } from '../../auth/useAuth';
import { useCan } from '../../auth/useCan';
import { canUpload, fetchUploadExts, uploadFile, type StagedFile, type DocforgeJob } from '../../api/upload.api';
import { classify, extOf, readDoc, kindLabel, unitsLabel, isEncryptedOffice, DOC_MAX } from './docAttach';
import { IMAGES_MAX, isImageFile, readImage, type AttachedImage } from './imageAttach';
import { DocExtractHint } from './DocExtractHint';
import { DocActions } from './DocActions';
import { UploadRouter } from './UploadRouter';
import { DocDispatchPanel } from './DocDispatchPanel';
import { DocforgeResume } from './DocforgeResume';

export interface ComposerHandle {
  focus: () => void;
}

// '+' 로 고를 수 있는 파일 — 끌어다 놓은 파일도 같은 목록으로 거른다(놓기는 accept 를 지나지 않는다, docs/chat-ppt PP-D16).
const ACCEPT = '.md,.txt,.pptx,.ppt,.docx,.doc,.pdf,.htm,.html,.csv,.xlsx,.step,.stp,.msh,.zip,.k,.key,.dyn,.inc,.png,.jpg,.jpeg,.gif,.webp';
const ACCEPT_EXTS = ACCEPT.split(',').map((x) => x.slice(1));
// 끄는 중 표시를 거두는 때 — 마지막 dragover 뒤 이만큼. 브라우저는 끄는 동안 350ms 마다 dragover 를 낸다(손이 멈춰 있어도). 창 밖으로
// 나가거나 Esc 로 그만둔 것은 dragleave 만으로는 브라우저마다 다르게 알린다.
const DRAG_IDLE_MS = 800;
const isFileDrag = (dt: DataTransfer | null) => Array.from(dt?.types ?? []).includes('Files');
// 루틴 턴의 ■ — 중계는 브라우저가 떠나도 상류를 끝까지 읽고 실행기는 구독이 끊겨도 돈다(R3-design D7 · D9). 실행 id 를 받기 전에 끊어도 그렇다.
// 실행을 그치는 것은 루틴 칸의 '멈춤'(cancelRun)이다 — 힌트 줄(챗 화면)과 단추 풀이(힌트 줄이 없는 독)가 같은 말을 한다.
const ROUTINE_STOP_HINT = '■ 는 이 화면의 연결만 끊습니다 — 루틴은 서버에서 계속 돌고, 그치려면 루틴 칸의 ‘멈춤’';
// 실행이 이미 끝난 루틴 턴(RA 초안 올리기 · '이미 끝났다' 이어서 — routineClosed)의 ■ — 그칠 실행이 없어 '멈춤' 은 어디에도 없다. 중계는 그 턴도
// 끝까지 읽으므로 '연결만 끊는다' 는 그대로다(R3 반대 검토 2차 #16).
const ROUTINE_CLOSED_HINT = '■ 는 이 화면의 연결만 끊습니다 — 올리기 · 안내는 서버에서 마칩니다';
// 켜 둔 루틴이 실릴 발화에 붙인 그림 · 문서가 있다 — 실행기는 그것을 읽지 않는다. 말없이 버리거나 비우지 않고 보내기를 멈춘다(R3 반대 검토 2차 #14)
const ROUTINE_ATTACH_BLOCK = '켜 둔 루틴은 붙인 그림 · 문서를 쓰지 않습니다 — 그림 · 문서를 떼거나 루틴을 끈 뒤 보냅니다. 붙인 것은 그대로 둡니다.';

interface ComposerProps {
  autoFocus?: boolean;
  placeholder?: string;
  /** 힌트 라인(Enter 전송 · Shift+Enter 줄바꿈) 표시 여부 — 독에서는 생략. */
  showHint?: boolean;
  /** 전송 가로채기 — 주어지면 sendMessage 대신 이 콜백을 호출(심의 전 전문가 선정 단계 진입). */
  onSubmitText?: (text: string) => void;
  /** 도구 줄에 '전문가' 알약 — 챗 화면만(심의는 좌석을 ExpertPicker 로 정하고, 독은 좁다). */
  showExpert?: boolean;
  /** 도구 줄에 '루틴' 알약 — 챗 화면만(독은 좁고, 심의 화면은 대화가 따로다). 켜 둔 루틴은 알약이 없는 입력창에서도 칩으로 보인다. */
  showRoutine?: boolean;
  /** 화면 어디에 끌어다 놓아도 이 입력창으로 올린다 — 입력창이 그 화면의 주인인 챗 · 심의 화면만. 독은 닫혀도 붙어 있어 켜지 않는다
   *  (켜면 '앱' 화면의 끌기를 닫힌 독이 가로챈다) — 독은 입력창 위에 놓을 때만 받는다(docs/chat-ppt PP-D16). */
  dropAnywhere?: boolean;
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  {
    autoFocus = false,
    placeholder = '무엇이든 물어보세요…',
    showHint = false,
    onSubmitText,
    showExpert = false,
    showRoutine = false,
    dropAnywhere = false,
  },
  ref,
) {
  const {
    input,
    setInput,
    sendMessage,
    stop,
    streaming,
    routineStreaming,
    routineClosed,
    pinnedTools,
    setPinnedTools,
    pinnedApps,
    setPinnedApps,
    pinnedAgent,
    pinnedAgentName,
    setPinnedAgent,
    pinnedHelpers,
    setPinnedHelpers,
    attachedDocs,
    setAttachedDocs,
    attachedImages,
    setAttachedImages,
    addUploadNotice,
    activeConversation,
    armedRoutine,
    setArmedRoutine,
  } = useChat();
  const taRef = useRef<HTMLTextAreaElement>(null);
  // 보내기 · PC 도우미는 기다린 뒤에 부른다 — 그 사이 사람이 쓴 글 · 붙인 문서를 낡은 값으로 덮지 않게 가장 새 값을 읽는다.
  const latest = useRef({ input, attachedDocs });
  latest.current = { input, attachedDocs };
  /** 지시문을 입력창에 — auto 면 비어 있을 때만(사람이 쓰던 글을 지우지 않는다, docs/chat-ppt PP-D4). */
  const fillInput = useCallback(
    (t: string, auto?: boolean) => {
      if (auto && latest.current.input.trim()) return;
      setInput(t);
      taRef.current?.focus();
    },
    [setInput],
  );
  const { user } = useAuth();
  // 권한이 없으면 입구를 아예 숨긴다(docs/access-control). 업로드는 종전 그룹 설정도 인정한다.
  const can = useCan();
  const canUp = can('feat:upload') || canUpload(user?.groups);
  // 박스 설정으로 정하는 확장자(SimFlow — SIMFLOW_UPLOAD_EXTS)를 서버에 묻고 위 목록에 더한다 — 고르기 · 끌어 놓기 둘 다(docs/request-1027 HP-15)
  const [serverExts, setServerExts] = useState<string[]>([]);
  useEffect(() => {
    if (!canUp) return;
    let live = true;
    void fetchUploadExts().then((v) => {
      if (live) setServerExts(v);
    });
    return () => {
      live = false;
    };
  }, [canUp]);
  const acceptExts = useMemo(() => [...new Set([...ACCEPT_EXTS, ...serverExts])], [serverExts]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [staged, setStaged] = useState<StagedFile | null>(null);
  // 창을 닫아 넣지 못한 정밀 변환 잡을 이어 본다(DocForge E15) — 이어 본 패널을 닫으면 목록을 다시 읽는다
  const [resume, setResume] = useState<DocforgeJob | null>(null);
  const [resumeTick, setResumeTick] = useState(0);
  const [upErr, setUpErr] = useState('');
  // Office 원본을 붙였을 때 띄우는 안내 — DRM 때문에 추출은 이 PC 에서 해야 한다.
  // 이름만이 아니라 **바이트**로 갈린다 — DRM 이 브라우저에도 투명하면 평문이 읽히고,
  // 그러면 COM 추출이 필요 없다(서버가 그대로 파싱한다). 짐작하지 않고 본다.
  const [comFile, setComFile] = useState<{ name: string; encrypted: boolean | null } | null>(null);
  // 붙인 파일이 갈 곳은 셋이고 **내용을 읽기 전에** 갈린다(확장자로만 판정).
  //   text      추출문·평문 → 브라우저에서 그대로 읽어 챗·심의 근거로. 서버에 안 올린다.
  //   needs-com PPT·Word·PDF 원본 → 서버가 파싱하면 DRM 에 막힌다. PC 추출 안내를 띄운다.
  //   upload    물성 CSV·STEP 등 → 종전 목적지 선택 경로 그대로.
  // 그림 — 브라우저에서 줄여(긴 변 1,568px) 이 발화에 싣는다. 서버가 저장하고 돌려준 주소가 그 발화에 남아 다음 턴 · 띵킹 · 심의가
  // 다시 본다(docs/chat-depth-context T5). 상한(IMAGES_MAX)을 넘거나 읽히지 않으면 말한다(조용히 빼지 않는다).
  const addImages = useCallback(
    async (files: File[], keep = false) => {
      // keep — 같은 동작에서 앞서 남긴 알림을 지우지 않고 잇는다(문서와 그림을 함께 놓았을 때, PP-D16)
      const say = (m: string) => setUpErr((e) => (keep && e ? `${e} · ${m}` : m));
      if (!keep) setUpErr('');
      const room = IMAGES_MAX - attachedImages.length;
      if (room <= 0) {
        say(`그림은 한 번에 ${IMAGES_MAX}장까지 올릴 수 있습니다.`);
        return;
      }
      const got: AttachedImage[] = [];
      const errs: string[] = [];
      for (const f of files.slice(0, room)) {
        try {
          got.push(await readImage(f));
        } catch (e) {
          errs.push(e instanceof Error ? e.message : '그림을 읽지 못했습니다.');
        }
      }
      if (files.length > room) errs.push(`${files.length - room}장은 한 번에 ${IMAGES_MAX}장 상한을 넘어 붙이지 않았습니다.`);
      if (got.length) setAttachedImages([...attachedImages, ...got]);
      if (errs.length) say(errs.join(' · '));
    },
    [attachedImages, setAttachedImages],
  );

  const onPick = useCallback(
    async (f: File | undefined) => {
      if (!f) return;
      setUpErr('');
      setComFile(null);
      if (isImageFile(f)) {
        await addImages([f]);
        return;
      }
      const verdict = classify(f.name);
      if (verdict === 'needs-com') {
        // **평문이면 서버가 읽는다** — 각 서비스가 자기 취입기를 갖고 있으므로 그냥 올린다.
        // DRM 이 브라우저 읽기까지 막는 경우에만 COM 추출기로 보낸다.
        const enc = await isEncryptedOffice(f);
        if (enc === false) {
          try {
            setStaged(await uploadFile(f));
          } catch (e) {
            setUpErr(e instanceof Error ? e.message : '업로드 실패');
          }
          return;
        }
        setComFile({ name: f.name, encrypted: enc });
        return;
      }
      if (verdict === 'text') {
        if (attachedDocs.length >= DOC_MAX) {
          setUpErr(`문서는 한 번에 ${DOC_MAX}건까지 붙일 수 있습니다.`);
          return;
        }
        try {
          setAttachedDocs([...attachedDocs, await readDoc(f)]);
        } catch (e) {
          setUpErr(e instanceof Error ? e.message : '문서를 읽지 못했습니다.');
        }
        return;
      }
      try {
        setStaged(await uploadFile(f));
      } catch (e) {
        setUpErr(e instanceof Error ? e.message : '업로드 실패');
      }
    },
    [attachedDocs, setAttachedDocs, addImages],
  );

  // '+' 로 고른 파일과 끌어다 놓은 파일은 같은 길로 간다(docs/chat-ppt PP-D16). 그림은 여럿을, 그 밖(문서 · 업로드)은 한 번에 하나를 —
  // 업로드 패널 · 추출 안내가 한 파일씩이다. 함께 고른 나머지 · 받지 않는 형식은 이름을 대고 말한다(조용히 빼지 않는다).
  const addFiles = useCallback(
    async (all: File[]) => {
      const odd = all.filter((f) => !isImageFile(f) && !acceptExts.includes(extOf(f.name)));
      const fs = all.filter((f) => !odd.includes(f));
      const imgs = fs.filter(isImageFile);
      const rest = fs.filter((f) => !isImageFile(f));
      const notes: string[] = [];
      if (rest.length > 1) notes.push(`파일은 한 번에 하나씩 붙습니다 — ${rest.slice(1).map((f) => f.name).join(', ')} 은(는) 따로 붙이세요`);
      if (odd.length) notes.push(`붙이지 않는 형식입니다 — ${odd.map((f) => f.name).join(', ')}`);
      if (rest.length) await onPick(rest[0]);
      else setUpErr('');
      if (imgs.length) await addImages(imgs, true);
      if (notes.length) setUpErr((e) => [e, ...notes].filter(Boolean).join(' · '));
    },
    [addImages, onPick, acceptExts],
  );

  // 놓은 파일 — '+' 단추가 보이는 때와 같은 때만 받는다(붙일 권한 · 답을 받는 중이 아님). 받지 않을 때도 까닭을 말한다.
  const dropFiles = useCallback(
    (fs: File[]) => {
      if (!fs.length) return;
      if (!canUp) {
        setUpErr('파일을 붙일 권한이 없습니다 — 내 권한 페이지에서 요청할 수 있습니다.');
        return;
      }
      if (streaming) {
        setUpErr('답을 받는 중에는 붙이지 않습니다 — 답이 끝난 뒤 다시 놓으세요.');
        return;
      }
      void addFiles(fs);
    },
    [canUp, streaming, addFiles],
  );
  const dropRef = useRef(dropFiles);
  dropRef.current = dropFiles;
  const [dragOn, setDragOn] = useState(false);

  // 화면 어디에 놓아도(dropAnywhere — 챗 · 심의 화면) — 창이 받는다. 끄는 동안 놓을 자리를 화면 전체에 보이고, 브라우저가 파일을 열어
  // 화면을 떠나지 않게 막는다(받는 중이던 답이 끊긴다). 파일이 아닌 끌기(글 · 링크)는 건드리지 않는다.
  useEffect(() => {
    if (!dropAnywhere) return;
    let timer = 0;
    const off = () => {
      window.clearTimeout(timer);
      setDragOn(false);
    };
    const over = (e: DragEvent) => {
      if (!isFileDrag(e.dataTransfer)) return;
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
      setDragOn(true);
      window.clearTimeout(timer);
      timer = window.setTimeout(off, DRAG_IDLE_MS);
    };
    const leave = (e: DragEvent) => {
      if (isFileDrag(e.dataTransfer) && e.relatedTarget === null) off();   // 창 밖으로
    };
    const drop = (e: DragEvent) => {
      if (!isFileDrag(e.dataTransfer)) return;
      e.preventDefault();
      off();
      dropRef.current(Array.from(e.dataTransfer?.files ?? []));
    };
    window.addEventListener('dragover', over);
    window.addEventListener('dragleave', leave);
    window.addEventListener('drop', drop);
    return () => {
      off();
      window.removeEventListener('dragover', over);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('drop', drop);
    };
  }, [dropAnywhere]);

  // 입력창 위에 놓을 때만(독) — 놓기를 여기서 끝낸다(창으로 올라가 다른 입력창이 한 번 더 받지 않게).
  const formDrop = dropAnywhere
    ? {}
    : {
        onDragOver: (e: ReactDragEvent<HTMLFormElement>) => {
          if (!isFileDrag(e.dataTransfer)) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = 'copy';
          setDragOn(true);
        },
        onDragLeave: (e: ReactDragEvent<HTMLFormElement>) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragOn(false);
        },
        onDrop: (e: ReactDragEvent<HTMLFormElement>) => {
          if (!isFileDrag(e.dataTransfer)) return;
          e.preventDefault();
          e.stopPropagation();
          setDragOn(false);
          dropFiles(Array.from(e.dataTransfer.files));
        },
      };

  // PC 도우미가 올린 글(.hwax.md) · 슬라이드 그림 — 손으로 붙이던 길(readDoc · addImages)과 같다(docs/chat-ppt B4). 까닭은 돌려준다.
  const attachPcResult = useCallback(
    async (doc: File, slides: File[]): Promise<string | void> => {
      const docs = latest.current.attachedDocs;
      if (docs.length >= DOC_MAX) return `문서는 한 번에 ${DOC_MAX}건까지 붙일 수 있습니다 — 칩 하나를 떼고 다시 누르세요.`;
      try {
        setAttachedDocs([...docs, await readDoc(doc)]);
      } catch (e) {
        return e instanceof Error ? e.message : '받은 글을 읽지 못했습니다.';
      }
      if (slides.length) await addImages(slides);
    },
    [setAttachedDocs, addImages],
  );

  // 붙여넣기 — 그림만 온 붙여넣기(화면 갈무리)는 그림으로. 글이 함께 오면(Office 복사는 글 + 그 글의 그림을 같이 싣는다) 글 붙여넣기다.
  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(e.clipboardData?.files ?? []).filter(isImageFile);
    if (!files.length || e.clipboardData.getData('text/plain')) return;
    e.preventDefault();
    void addImages(files);
  };

  useImperativeHandle(ref, () => ({ focus: () => taRef.current?.focus() }), []);

  // textarea 자동 높이 — 값이 바뀔 때마다 scrollHeight에 맞춰 늘리고 max는 CSS가 자른다.
  useLayoutEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${ta.scrollHeight}px`;
  }, [input]);

  useEffect(() => {
    if (autoFocus) taRef.current?.focus();
  }, [autoFocus]);

  // 켜 둔 루틴이 이 입력창의 다음 보내기에 실리는데(권한이 있고 심의 가로채기가 아니다 — sendMessage 가 싣는 조건) 붙인 그림 · 문서가 있다.
  // 실행기는 그것을 읽지 않는다 — 보내면 그림은 저장되지 않은 채 칩에서만 사라졌다(R3 반대 검토 2차 #14). 보내지 않고 까닭을 말한다(붙인 것은 둔다).
  // 말은 보내려 한 뒤에만 내고, 붙인 것을 떼거나 루틴을 끄면 저절로 거둔다.
  const attachClash =
    Boolean(armedRoutine) && !onSubmitText && can('feat:routines') && (attachedImages.length > 0 || attachedDocs.length > 0);
  const [attachTried, setAttachTried] = useState(false);

  // 루틴을 켜 두었으면 글 없이도 보낸다 — 빈 글이면 sendMessage 가 '루틴: <제목>' 을 글로 싣는다(서버는 글 1자 이상을 받는다). 그 글은 루틴에
  // 덧붙인 말이 아니다 — 덧붙인 말(note)은 사람이 쓴 글뿐이라 여기서 대신 지어 넘기지 않는다(docs/analysis-routines R3 §3.1 · C3)
  const submit = useCallback(() => {
    if (streaming) return;
    if (attachClash) {
      setAttachTried(true);
      return;
    }
    setAttachTried(false);
    const text = input.trim();
    if (!text && armedRoutine && !onSubmitText) {
      sendMessage('');
      return;
    }
    if (!text) return;
    if (onSubmitText) onSubmitText(text);
    else sendMessage(input);
  }, [streaming, sendMessage, input, onSubmitText, armedRoutine, attachClash]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 조합 중 Enter(isComposing)는 전송이 아니라 조합 확정 — 반드시 무시한다.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  // 빈 글 보내기는 루틴이 실릴 때만 뜻이 있다 — 권한이 없으면 sendMessage 가 빈 글을 보내지 않는다(눌러도 아무 일 없는 단추가 되지 않게)
  const canSend = (input.trim().length > 0 || (Boolean(armedRoutine) && !onSubmitText && can('feat:routines'))) && !streaming;
  const routinePill = showRoutine && can('feat:routines');
  const routineHint = routineClosed ? ROUTINE_CLOSED_HINT : ROUTINE_STOP_HINT;

  return (
    <form className={dragOn && !dropAnywhere ? 'composer composer-drop' : 'composer'} onSubmit={onSubmit} {...formDrop}>
      {dropAnywhere && dragOn && createPortal(
        // 놓을 자리 표시 — 손을 대지 않는다(pointer-events: none). 놓기는 창이 받는다.
        <div className="drop-veil" aria-hidden="true">
          <div className="drop-veil-card">
            <b>{!canUp ? '파일을 붙일 권한이 없습니다' : streaming ? '답을 받는 중에는 붙이지 않습니다' : '여기에 놓으면 업로드됩니다'}</b>
            <span>그림 · PPT · Word · PDF · 문서(.md) · CSV · STEP · K파일 — ‘+’ 와 같은 길</span>
          </div>
        </div>,
        document.body,
      )}
      {/* 지정 전문가·도구 칩 — 이 대화에 적용될 선택을 항상 보이게(× 로 즉시 해제). */}
      {(pinnedTools.length > 0 ||
        pinnedApps.length > 0 ||
        (pinnedAgent && !showExpert) ||
        (armedRoutine && !showRoutine) ||
        pinnedHelpers.length > 0) && (
        <div className="composer-pins" aria-label="지정 전문가·앱·도구">
          {armedRoutine && !showRoutine && (
            // 루틴 알약이 없는 입력창(독) — 챗 화면에서 켜 둔 루틴이 여기서 보내도 실린다. 보이고 끌 수 있어야 한다.
            <span className="composer-pin composer-pin-app composer-pin-routine" title="켜 둔 분석 루틴 — 다음 발화 한 번에 실립니다">
              <span className="composer-pin-text">루틴 · {armedRoutine.title}</span>
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setArmedRoutine(null)}
                aria-label={`루틴 ${armedRoutine.title} 끄기`}
                title="루틴 끄기"
              >
                ×
              </button>
            </span>
          )}
          {pinnedAgent && !showExpert && (
            // 기계 키가 아니라 사람 이름을 보여 준다(전문가 알약이 있으면 거기서 보이고 해제한다) — 키는 툴팁으로 남긴다(구 저장분은 이름이 없어
            // 키가 그대로 보인다).
            <span
              className="composer-pin composer-pin-agent"
              title={`지정 전문가 페르소나 — ${pinnedAgent}`}
            >
              <IconUser className="ico" width={14} height={14} /> {shortName(pinnedAgentName || pinnedAgent)}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedAgent(null)}
                aria-label={`전문가 ${pinnedAgentName || pinnedAgent} 해제`}
                title="전문가 해제"
              >
                ×
              </button>
            </span>
          )}
          {/* 보조 전문가 — 답은 주 전문가 한 목소리이고 이들은 판단 기준·도구만 빌려준다.
              누가 서 있는지 안 보이면 왜 그 도구를 쓰는지 알 수 없다. */}
          {pinnedHelpers.map((h) => (
            <span key={h.key} className="composer-pin" title={`보조 전문가 — ${h.key}`}>
              ＋{shortName(h.name || h.key)}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedHelpers(pinnedHelpers.filter((x) => x.key !== h.key))}
                aria-label={`보조 전문가 ${h.name || h.key} 빼기`}
                title="보조 빼기"
              >
                ×
              </button>
            </span>
          ))}
          {pinnedApps.length > 0 && <span className="composer-pins-label">지정 앱</span>}
          {pinnedApps.map((k) => (
            <span
              key={k}
              className="composer-pin composer-pin-app"
              title="이 앱의 기능 전체를 우선 사용"
            >
              {k}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedApps(pinnedApps.filter((x) => x !== k))}
                aria-label={`앱 ${k} 지정 해제`}
                title="지정 해제"
              >
                ×
              </button>
            </span>
          ))}
          {pinnedTools.length > 0 && <span className="composer-pins-label">지정 도구</span>}
          {pinnedTools.map((n) => (
            <span key={n} className="composer-pin">
              {n}
              <button
                type="button"
                className="composer-pin-x"
                onClick={() => setPinnedTools(pinnedTools.filter((x) => x !== n))}
                aria-label={`${n} 지정 해제`}
                title="지정 해제"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {!staged && !resume && canUp && can('plat:docforge') && (
        <DocforgeResume refresh={resumeTick} onResume={setResume} />
      )}
      {!staged && resume && (
        <DocDispatchPanel
          key={resume.job_id}
          staged={{ staging_id: `docforge-${resume.job_id}`, filename: resume.filename || resume.job_id, size: 0, ext: '', content_type: '' }}
          destination="reportarchive_precise"
          resumeJobId={resume.job_id}
          onClose={() => { setResume(null); setResumeTick((n) => n + 1); }}
          onFill={fillInput}
          onDispatched={addUploadNotice}
        />
      )}
      {/* key — 새 파일마다 고른 목적지 · 완료 표시를 새로 시작한다(패널이 열린 채 다른 파일을 붙이면 앞 파일의 상태가 이어졌다, A5) */}
      {staged && (
        <UploadRouter
          key={staged.staging_id}
          staged={staged}
          onClose={() => setStaged(null)}
          onFill={fillInput}
          onDispatched={addUploadNotice}
          // 이 대화에서 분석 — 읽어 온 글을 PC 도우미 결과와 같은 길로 붙인다(문서 칩)
          onAttachDoc={(f) => attachPcResult(f, [])}
        />
      )}
      {comFile && (
        <DocExtractHint
          filename={comFile.name}
          encrypted={comFile.encrypted}
          onClose={() => setComFile(null)}
          conversationId={activeConversation?.serverId ?? ''}
          onAttach={attachPcResult}
          onStaged={(st) => {
            setComFile(null);
            setStaged(st);
          }}
        />
      )}
      {attachedDocs.length > 0 && (
        <div className="doc-chips">
          {attachedDocs.map((d, i) => (
            <span
              key={`${d.name}-${i}`}
              className="doc-chip"
              title={`${d.chars.toLocaleString()}자`}
            >
              <IconFile className="ico" width={14} height={14} /> {d.name}
              <em>
                {[kindLabel(d.meta), unitsLabel(d.meta), `${d.chars.toLocaleString()}자`]
                  .filter(Boolean)
                  .join(' · ')}
              </em>
              {d.truncated && <b className="doc-chip-cut">잘림</b>}
              <button
                type="button"
                onClick={() => setAttachedDocs(attachedDocs.filter((_, j) => j !== i))}
                aria-label={`${d.name} 떼기`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {attachedImages.length > 0 && (
        <div className="img-chips" aria-label="올릴 그림">
          {attachedImages.map((im, i) => (
            <span
              key={`${im.name}-${i}`}
              className="img-chip"
              title={`${im.name} — ${im.width}×${im.height}px · ${(im.bytes / 1024).toFixed(0)}KB${
                im.scaledFrom ? ` (긴 변 ${im.scaledFrom}px 에서 줄임)` : ''}`}
            >
              <img src={im.dataUrl} alt={im.name} />
              <button
                type="button"
                onClick={() => setAttachedImages(attachedImages.filter((_, j) => j !== i))}
                aria-label={`그림 ${im.name} 떼기`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {attachedDocs.length > 0 && (
        <DocActions
          docs={attachedDocs}
          onFill={(t) => {
            setInput(t);
            taRef.current?.focus();
          }}
        />
      )}
      {upErr && (
        <div className="upl-err" role="alert">
          ⚠ {upErr}
        </div>
      )}
      {attachTried && attachClash && (
        <div className="upl-err" role="alert">
          ⚠ {ROUTINE_ATTACH_BLOCK}
        </div>
      )}
      <div className="composer-box">
        <textarea
          ref={taRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          placeholder={armedRoutine && !onSubmitText ? '루틴에 덧붙일 말(비워서 보내도 됩니다)' : placeholder}
          aria-label="메시지 입력"
        />
        {/* 도구 줄 — 첨부·검색·Thinking 을 입력창 안에(종전엔 입력창 위 전폭 막대 두 줄이 입력창보다 크게 자리를 차지했다) */}
        <div className={`composer-tools${routinePill ? ' has-routine' : ''}`}>
          {canUp && !streaming && (
            <>
              <input
                ref={fileRef}
                type="file"
                accept={acceptExts.map((x) => `.${x}`).join(',')}
                multiple
                style={{ display: 'none' }}
                onChange={(e) => {
                  // 끌어다 놓기와 같은 길 — 그림은 여럿, 그 밖(문서 · 업로드)은 한 번에 하나(나머지는 이름을 대고 알린다, PP-D16).
                  const fs = Array.from(e.target.files ?? []);
                  e.target.value = '';
                  void addFiles(fs);
                }}
              />
              <button
                type="button"
                className="composer-btn composer-attach"
                onClick={() => fileRef.current?.click()}
                aria-label="파일 붙이기"
                title="파일 붙이기 — 문서(PPT·Word·PDF) · 그림(PNG·JPG — 붙여넣기도 된다) · 물성 CSV · STEP·MSH·ZIP · K파일"
              >
                <IconPlus />
              </button>
            </>
          )}
          {can('plat:webresearch') && <SearchToggle />}
          {can('feat:thinking') && <ThinkToggle />}
          {showExpert && can('feat:expert-chat') && <ExpertToggle />}
          {routinePill && <RoutineToggle />}
          <span className="composer-tools-gap" />
          {streaming ? (
            <button
              type="button"
              className="composer-btn composer-stop"
              onClick={stop}
              aria-label="응답 중지"
              title={routineStreaming ? routineHint : '응답 중지'}
            >
              <IconStop width={17} height={17} />
            </button>
          ) : (
            <button
              type="submit"
              className="composer-btn composer-send"
              disabled={!canSend}
              aria-label="전송"
              title="전송 (Enter)"
            >
              <IconSend width={17} height={17} />
            </button>
          )}
        </div>
      </div>
      {showHint && (
        <div className="composer-hint" aria-hidden="true">
          {streaming
            ? routineStreaming
              ? routineHint
              : '응답 생성 중… 중지하려면 ■ 버튼'
            : 'Enter 전송 · Shift+Enter 줄바꿈 · 그림은 붙여넣기(Ctrl+V)'}
        </div>
      )}
    </form>
  );
});
