// 챗에 올릴 그림을 브라우저에서 읽어 줄인다 — 보낼 때만 원본(data URL)을 싣고, 대화에는 서버가 돌려준 주소만 남긴다
/** 한 발화에 올릴 수 있는 그림 수 — 포털 _IMAGES_MAX · 에이전트 서버 VISION_MAX_IMAGES 와 같은 수(backend tests/test_chat_images_route.py). */
export const IMAGES_MAX = 12;
/** 그림 한 장의 바이트 상한 — 포털 _IMAGE_BYTES_MAX · 에이전트 서버 VISION_MAX_BYTES 와 같은 수. 넘으면 포털이 422 다. */
export const IMAGE_BYTES_MAX = 8 * 1024 * 1024;
/** 긴 변이 이보다 크면 줄인다 — 그림 토큰과 전송량을 줄이고, 응력 지도 범례 · 축 눈금 글자는 이 크기에서 읽힌다. */
export const IMAGE_MAX_SIDE = 1568;

export type ImageMime = 'image/png' | 'image/jpeg' | 'image/gif' | 'image/webp';

export interface AttachedImage {
  name: string;
  mime: ImageMime;
  /** data URL — 보낼 때 그대로 싣고(포털 · 에이전트 서버가 data URL 머리를 받는다) 썸네일에도 쓴다. 대화에 영속하지 않는다(쿼터). */
  dataUrl: string;
  width: number;
  height: number;
  bytes: number;
  /** 줄였으면 원래 긴 변(px). */
  scaledFrom?: number;
}

const MIMES: ImageMime[] = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];

/** 그림 파일인가 — 형식(type)이 비어 오는 경우(일부 붙여넣기 · 드래그)가 있어 이름도 본다. */
export function isImageFile(f: { name: string; type: string }): boolean {
  return (MIMES as string[]).includes(f.type) || /\.(png|jpe?g|gif|webp)$/i.test(f.name);
}

/** 긴 변을 max 에 맞춘 크기. 이미 작으면 그대로(키우지 않는다). */
export function fitSize(w: number, h: number, max = IMAGE_MAX_SIDE): { w: number; h: number; scaled: boolean } {
  const side = Math.max(w, h);
  if (side <= max) return { w, h, scaled: false };
  const k = max / side;
  return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)), scaled: true };
}

/** data URL 의 바이트 수(base64 본문에서). */
export function dataUrlBytes(dataUrl: string): number {
  const b64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
  return Math.floor((b64.length * 3) / 4) - (b64.endsWith('==') ? 2 : b64.endsWith('=') ? 1 : 0);
}

function readAsDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error ?? new Error('그림을 읽지 못했습니다.'));
    r.readAsDataURL(blob);
  });
}

function toBlob(c: HTMLCanvasElement, mime: string, q?: number): Promise<Blob> {
  return new Promise((resolve, reject) =>
    c.toBlob((b) => (b ? resolve(b) : reject(new Error('그림을 줄이지 못했습니다.'))), mime, q));
}

/** 파일 → 보낼 그림. 긴 변이 IMAGE_MAX_SIDE 보다 크면 줄이고(PNG 는 PNG 로 — 화면 갈무리의 글자가 번지지 않게, 사진은 JPEG 로),
 *  그래도 IMAGE_BYTES_MAX 를 넘으면 JPEG 로 한 번 더 줄인다. 그래도 크면 거절한다(조용히 빼지 않는다). */
export async function readImage(f: File): Promise<AttachedImage> {
  const mime0 = (MIMES as string[]).includes(f.type) ? (f.type as ImageMime) : 'image/png';
  const bmp = await createImageBitmap(f).catch(() => {
    throw new Error(`${f.name || '그림'} — 그림으로 읽히지 않습니다(깨졌거나 지원하지 않는 형식).`);
  });
  const side0 = Math.max(bmp.width, bmp.height);     // close() 뒤에는 0 이 된다 — 먼저 쥔다
  const { w, h, scaled } = fitSize(bmp.width, bmp.height);
  const name = f.name || `붙여넣은 그림.${mime0.split('/')[1]}`;
  if (!scaled && f.size <= IMAGE_BYTES_MAX) {
    bmp.close();
    return { name, mime: mime0, dataUrl: await readAsDataUrl(f), width: w, height: h, bytes: f.size };
  }
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  c.getContext('2d')?.drawImage(bmp, 0, 0, w, h);
  bmp.close();
  let mime: ImageMime = mime0 === 'image/jpeg' ? 'image/jpeg' : 'image/png';
  let blob = await toBlob(c, mime, 0.9);
  if (blob.size > IMAGE_BYTES_MAX) {
    mime = 'image/jpeg';
    blob = await toBlob(c, mime, 0.85);
  }
  if (blob.size > IMAGE_BYTES_MAX) {
    throw new Error(`${name} — 줄여도 ${(blob.size / 1048576).toFixed(1)}MB 라 한 장 상한 ${IMAGE_BYTES_MAX / 1048576}MB 를 넘습니다.`);
  }
  return {
    name, mime, dataUrl: await readAsDataUrl(blob), width: w, height: h, bytes: blob.size,
    ...(scaled ? { scaledFrom: side0 } : {}),
  };
}
