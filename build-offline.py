#!/usr/bin/env python3
"""把 index.html 與 vendor/mermaid.min.js 組成單一可攜的離線檔。

用法：
    python3 build-offline.py

index.html 本身就能離線使用，只要 vendor/ 在旁邊。這支腳本的用途是產生
「單一檔案」版本，方便寄給別人或存檔——它把 vendor 的 script 標籤替換成
內嵌的 mermaid，因此不再需要任何同目錄檔案。

改動一律改 index.html，然後重跑這支腳本。不要直接編輯產物。
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "index.html"
LIB = HERE / "vendor" / "mermaid.min.js"
OUT = HERE / "odoo-v19ce-erd-offline.html"
TAG = '<script src="vendor/mermaid.min.js"></script>'


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

    if TAG not in html:
        print(f"{SRC.name} 裡找不到 vendor 的 script 標籤，無法替換：\n  {TAG}", file=sys.stderr)
        return 1

    OUT.write_text(html.replace(TAG, f"<script>{lib}</script>", 1), encoding="utf-8")

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
