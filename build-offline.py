#!/usr/bin/env python3
"""把 global-view.html 與 vendor/mermaid.min.js 組成單一離線檔。

用法：
    python3 build-offline.py

改動一律改 global-view.html，然後跑這支腳本重新產生 global-view.offline.html。
不要直接編輯 .offline.html，它是產物，下次組裝就會被覆蓋。
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "global-view.html"
LIB = HERE / "vendor" / "mermaid.min.js"
OUT = HERE / "global-view.offline.html"


def main() -> int:
    for p in (SRC, LIB):
        if not p.exists():
            print(f"找不到 {p.relative_to(HERE)}", file=sys.stderr)
            return 1

    html = SRC.read_text(encoding="utf-8")
    lib = LIB.read_text(encoding="utf-8")

    # sourceMappingURL 會讓瀏覽器去抓外部 .map，離線版不要留
    lib, n_map = re.subn(r"//# sourceMappingURL=\S+", "", lib)
    # JS 字串裡的 </script> 會提早關閉標籤
    n_close = lib.count("</script>")
    lib = lib.replace("</script>", "<\\/script>")

    if "</head>" not in html:
        print("global-view.html 裡找不到 </head>，無法插入", file=sys.stderr)
        return 1

    OUT.write_text(
        html.replace("</head>", f"<script>{lib}</script>\n</head>", 1),
        encoding="utf-8",
    )

    # 確認沒有任何會發出請求的外部引用
    out_text = OUT.read_text(encoding="utf-8")
    external = re.findall(r'<(?:script|link)[^>]+(?:src|href)="https?://[^"]+"', out_text)

    print(f"已寫出 {OUT.name}：{OUT.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"  移除 sourceMap 註解 {n_map} 處、跳脫 </script> {n_close} 處")
    if external:
        print(f"  警告：仍有 {len(external)} 個外部引用", file=sys.stderr)
        for e in external[:5]:
            print(f"    {e}", file=sys.stderr)
        return 1
    print("  外部引用：0（確認為完全離線）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
