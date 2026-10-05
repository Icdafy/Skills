# -*- coding: utf-8 -*-
import sys, io
from docx import Document
from docx.document import Document as _Doc
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

def iter_block_items(parent):
    if isinstance(parent, _Doc):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        parent_elm = parent._element
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def main(path, outpath):
    doc = Document(path)
    out = []
    tbl_idx = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            style = block.style.name if block.style else ""
            text = block.text.strip()
            if not text:
                continue
            out.append(f"[{style}] {text}")
        elif isinstance(block, Table):
            tbl_idx += 1
            out.append(f"\n===== TABLE {tbl_idx} (rows={len(block.rows)}, cols={len(block.columns)}) =====")
            for r in block.rows:
                cells = [c.text.strip().replace("\n"," / ") for c in r.cells]
                out.append(" | ".join(cells))
            out.append("===== END TABLE =====\n")
    with io.open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("WROTE", outpath, "blocks:", len(out))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
