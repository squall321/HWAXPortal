# SearxNG 를 Flask 내장 서버(threaded)로 띄운다.
#   granian(이미지 기본)은 mp 워커에서 searx 를 못 찾아 죽는다 — venv 에 .pth 를 넣어
#   부모 프로세스에서는 import 되지만 워커까지는 안 간다(실측). 여기는 루프백 전용이고
#   앞단(포털·게이트웨이)에서 인증이 이미 끝난, 동시성 낮은 내부 브로커라 threaded 로 충분하다.
import searx.webapp as w
w.app.run(host="127.0.0.1", port=8888, threaded=True, debug=False, use_reloader=False)
