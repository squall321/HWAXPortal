# Phoenix 를 웹 포트 하나(OTLP/HTTP 와 화면)로만 띄운다 — 늘 모든 인터페이스에 여는 gRPC 수신기를 끄고 phoenix.server.main 을 부른다
"""Phoenix 이미지 안에서 `python3.13 /hwax/phoenix_serve.py serve` 로 돈다(infra/scripts/call-trace.sh run).

왜 — Phoenix 의 gRPC OTLP 수신기는 PHOENIX_HOST 를 보지 않고 `[::]:<PHOENIX_GRPC_PORT>`(모든 인터페이스)에 연다
(phoenix/server/grpc_server.py 의 add_insecure_port, 20.19.0). 끄는 환경값이 없다 — 읽기 전용 모드에서만 꺼지는데 그러면 웹 수신도 막힌다.
인증 없는 수신기를 박스의 모든 인터페이스에 열지 않으려고 그 수신기의 시작을 비운다. 기록기(에이전트 서버 call_trace.py)는 웹 포트의
/v1/traces 로만 보내므로 잃는 것이 없다.

판이 바뀌어 그 자리(phoenix.server.grpc_server.GrpcServer)가 없으면 띄우지 않고 끝난다 — 조용히 [::] 에 열리지 않게. 판을 올리면
build-phoenix.sh 의 판과 이 파일을 함께 본다.

이미지의 PYTHONPATH 는 끝이 `:` 라 띄운 자리(cwd)가 import 경로에 들어간다 — 그 자리의 .py 가 Phoenix 의 모듈을 가리지 않게 뺀다.
"""
import os
import sys


def main() -> int:
    here = os.getcwd()
    sys.path[:] = [p for p in sys.path if p not in ("", ".", here)]
    try:
        from phoenix.server import grpc_server
        cls = grpc_server.GrpcServer
        cls.__aenter__  # noqa: B018 — 자리가 있는지만 본다
    except Exception as exc:  # noqa: BLE001 — 무엇이든 이 판에서는 수신기를 끌 수 없다는 뜻이다
        print(f"✗ Phoenix 의 gRPC 수신기 자리(phoenix.server.grpc_server.GrpcServer)를 찾지 못했다({type(exc).__name__}) — "
              "모든 인터페이스에 열리지 않게 띄우지 않는다. build-phoenix.sh 의 판과 infra/call-trace/phoenix_serve.py 를 함께 본다",
              file=sys.stderr, flush=True)
        return 3

    async def _no_grpc(self):
        self._server = None             # __aexit__ 는 이것이 None 이면 그냥 돌아간다

    cls.__aenter__ = _no_grpc
    from phoenix.server.main import main as phoenix_main
    phoenix_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
