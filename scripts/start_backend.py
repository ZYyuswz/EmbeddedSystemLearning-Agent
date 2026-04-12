"""启动 FastAPI 后端。"""
from __future__ import annotations

import uvicorn



def main() -> None:
    """启动后端服务。"""
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
