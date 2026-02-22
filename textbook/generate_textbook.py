#!/usr/bin/env python3
"""
ダーマトロジー スキンケア検定 公式テキスト PDF生成スクリプト
- A4縦、マージン25mm
- 日本語フォント（Noto Sans JP / Noto Serif JP）埋め込み
- Markdownパース: ## → 章, ### → セクション, **太字** → 3級テキスト, 通常段落 → 2級テキスト
"""

import os
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CONTENT_MD = os.path.join(ASSETS_DIR, "content.md")
OUTPUT_PDF = os.path.join(OUTPUT_DIR, "dermatology_skincare_textbook.pdf")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Colors ---
PRIMARY = HexColor("#1B3A4B")
ACCENT = HexColor("#3D8B7A")
BOX_BG = HexColor("#EDF6F3")
TEXT_COLOR = HexColor("#2C2C2C")
SUB_COLOR = HexColor("#666666")
WHITE = HexColor("#FFFFFF")
LIGHT_BG = HexColor("#F7FAFA")

# --- Register Fonts ---
GOTHIC = "NotoSansJP"
MINCHO = "NotoSerifJP"

pdfmetrics.registerFont(TTFont(GOTHIC, os.path.join(FONTS_DIR, "NotoSansJP.ttf")))
pdfmetrics.registerFont(TTFont(MINCHO, os.path.join(FONTS_DIR, "NotoSerifJP.ttf")))

# --- Page dimensions ---
PAGE_W, PAGE_H = A4  # 210mm x 297mm
MARGIN = 25 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ========================================================
# Custom Flowables
# ========================================================

class AccentBar(Flowable):
    """セクションタイトル左端のアクセントバー付き見出し"""
    def __init__(self, text):
        super().__init__()
        self.text = text
        self._height = 0

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        # Calculate text height
        style = ParagraphStyle("_measure", fontName=GOTHIC, fontSize=14, leading=20)
        p = Paragraph(self.text, style)
        _, h = p.wrap(availWidth - 16, availHeight)
        self._height = max(h + 4, 24)
        return (availWidth, self._height + 6)

    def draw(self):
        canvas = self.canv
        # Accent bar (3px wide, full height)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, 0, 3, self._height, fill=1, stroke=0)
        # Text
        canvas.setFillColor(PRIMARY)
        canvas.setFont(GOTHIC, 14)
        canvas.drawString(14, self._height - 16, self.text)


class GradeBox(Flowable):
    """3級テキスト用のボックス（背景色 + 角丸）"""
    def __init__(self, text):
        super().__init__()
        self.text = text
        self._para = None
        self._para_height = 0

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        style = ParagraphStyle(
            "grade3box",
            fontName=GOTHIC,
            fontSize=9.5,
            leading=9.5 * 1.7,
            textColor=PRIMARY,
            firstLineIndent=9.5,
        )
        self._para = Paragraph(self.text, style)
        pw, ph = self._para.wrap(availWidth - 24, availHeight)
        self._para_height = ph
        total_h = ph + 20  # padding top 10pt + bottom 10pt
        return (self._width, total_h)

    def draw(self):
        canvas = self.canv
        h = self._para_height + 20
        # Background rounded rect
        canvas.setFillColor(BOX_BG)
        canvas.roundRect(0, 0, self._width, h, 4, fill=1, stroke=0)
        # Draw paragraph inside (12pt from left, 10pt from bottom)
        self._para.drawOn(canvas, 12, 10)


class ChapterTitle(Flowable):
    """章の扉ページ — chapter_label (例:"Chapter 1"), title, subtitle"""
    def __init__(self, chapter_label, title, subtitle=""):
        super().__init__()
        self.chapter_label = chapter_label
        self.title = title
        self.subtitle = subtitle

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        return (availWidth, 220)

    def draw(self):
        canvas = self.canv
        y = 180

        # Chapter label (小さめ、アクセントカラー)
        if self.chapter_label:
            canvas.setFillColor(ACCENT)
            canvas.setFont(GOTHIC, 13)
            canvas.drawString(0, y, self.chapter_label)
            y -= 45

        # Title (大きく、明朝体、プライマリ)
        canvas.setFillColor(PRIMARY)
        canvas.setFont(MINCHO, 24)
        title = self.title
        # Wrap long titles
        if len(title) > 18:
            # Find a break point around the middle
            mid = len(title) // 2
            break_chars = "のとをはがでにへもや、。）」"
            found = False
            for offset in range(8):
                for pos in [mid + offset, mid - offset]:
                    if 0 < pos < len(title) and title[pos] in break_chars:
                        canvas.drawString(0, y, title[:pos + 1])
                        y -= 34
                        canvas.drawString(0, y, title[pos + 1:])
                        found = True
                        break
                if found:
                    break
            if not found:
                canvas.drawString(0, y, title)
        else:
            canvas.drawString(0, y, title)

        y -= 30

        # Accent line
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(2)
        canvas.line(0, y, 80, y)
        y -= 25

        # Subtitle
        if self.subtitle:
            canvas.setFillColor(SUB_COLOR)
            canvas.setFont(GOTHIC, 11)
            canvas.drawString(0, y, self.subtitle)


class AccentLineFull(Flowable):
    """表紙用のアクセントライン（中央寄せ）"""
    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        return (availWidth, 3)

    def draw(self):
        center = self._width / 2
        line_w = 60
        self.canv.setStrokeColor(ACCENT)
        self.canv.setLineWidth(1.5)
        self.canv.line(center - line_w, 1.5, center + line_w, 1.5)


# ========================================================
# Markdown Parser
# ========================================================

def parse_markdown(filepath):
    """
    Parse markdown into structured elements:
    - ("chapter", label, title, subtitle)  # label = "Chapter 1" or ""
    - ("section", title)
    - ("grade3", text)
    - ("body", text)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    elements = []
    chapter_num = 0
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip blank, horizontal rules, and h1 (book title)
        if not line or re.match(r'^-{3,}$', line) or line.startswith("# "):
            i += 1
            continue

        # Skip metadata lines like "発行：..."
        if line.startswith("発行：") or line.startswith("発行:"):
            i += 1
            continue

        # ## → Chapter
        if line.startswith("## "):
            title_raw = line[3:].strip()

            # Check next line for 〜subtitle〜
            subtitle = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith("〜") or next_line.startswith("～"):
                    subtitle = next_line.strip("〜～ ")
                    i += 1  # consume subtitle line

            # Extract chapter number from title like "第１章　皮膚の構造"
            ch_match = re.match(r'^第[０-９0-9１-９]+章\s*', title_raw)
            if ch_match:
                chapter_num += 1
                title_clean = title_raw[ch_match.end():].strip()
                label = f"Chapter {chapter_num}"
            else:
                # "はじめに" or "おわりに" — no chapter number
                title_clean = title_raw
                # Split on ： or : for subtitle embedded in title
                parts = re.split(r'[：:]', title_clean, maxsplit=1)
                if len(parts) > 1:
                    title_clean = parts[0].strip()
                    if not subtitle:
                        subtitle = parts[1].strip()
                label = ""

            elements.append(("chapter", label, title_clean, subtitle))
            i += 1
            continue

        # ### → Section
        if line.startswith("### "):
            elements.append(("section", line[4:].strip()))
            i += 1
            continue

        # **bold** → Grade 3 box
        if line.startswith("**") and line.endswith("**"):
            bold_text = line[2:-2]
            i += 1
            # Collect consecutive bold lines
            while i < len(lines):
                nl = lines[i].strip()
                if nl.startswith("**") and nl.endswith("**"):
                    bold_text += "<br/>" + nl[2:-2]
                    i += 1
                else:
                    break
            elements.append(("grade3", bold_text))
            continue

        # Regular paragraph → body (Grade 2)
        para_lines = [line]
        i += 1
        while i < len(lines):
            nl = lines[i].strip()
            if not nl or nl.startswith("#") or nl.startswith("**") or re.match(r'^-{3,}$', nl):
                break
            para_lines.append(nl)
            i += 1

        para_text = "".join(para_lines)
        # Clean inline bold markers
        para_text = re.sub(r'\*\*(.+?)\*\*', r'\1', para_text)
        elements.append(("body", para_text))

    return elements


# ========================================================
# PDF Builder
# ========================================================

class TextbookBuilder:
    def __init__(self):
        self.story = []

        # --- Styles ---
        self.body_style = ParagraphStyle(
            "body",
            fontName=GOTHIC,
            fontSize=9.5,
            leading=9.5 * 1.7,
            textColor=TEXT_COLOR,
            firstLineIndent=9.5,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        )

        self.toc_chapter_style = ParagraphStyle(
            "toc_chapter",
            fontName=MINCHO,
            fontSize=12,
            leading=20,
            textColor=PRIMARY,
            spaceBefore=12,
            spaceAfter=2,
        )

        self.toc_section_style = ParagraphStyle(
            "toc_section",
            fontName=GOTHIC,
            fontSize=9,
            leading=14,
            textColor=TEXT_COLOR,
            leftIndent=20,
            spaceAfter=1,
        )

    # ----- Cover -----
    def build_cover(self):
        self.story.append(Spacer(1, 50 * mm))

        # IBCA text logo
        logo_style = ParagraphStyle(
            "logo", fontName=GOTHIC, fontSize=18, textColor=PRIMARY,
            alignment=TA_CENTER, spaceAfter=4, letterSpacing=4,
        )
        self.story.append(Paragraph("IBCA", logo_style))

        logo_sub = ParagraphStyle(
            "logo_sub", fontName=GOTHIC, fontSize=7.5, textColor=SUB_COLOR,
            alignment=TA_CENTER, spaceAfter=6,
        )
        self.story.append(Paragraph(
            "International Beauty Creation Association", logo_sub
        ))

        self.story.append(Spacer(1, 25 * mm))
        self.story.append(AccentLineFull())
        self.story.append(Spacer(1, 10 * mm))

        # Title
        title_style = ParagraphStyle(
            "cover_title", fontName=MINCHO, fontSize=28, leading=44,
            textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=6,
        )
        self.story.append(Paragraph(
            "ダーマトロジー<br/>スキンケア検定<br/>公式テキスト",
            title_style
        ))

        self.story.append(Spacer(1, 6 * mm))

        # Grade badge
        grade_style = ParagraphStyle(
            "cover_grade", fontName=GOTHIC, fontSize=14,
            textColor=ACCENT, alignment=TA_CENTER, spaceAfter=6,
        )
        self.story.append(Paragraph("3級・2級 対応", grade_style))

        self.story.append(Spacer(1, 25 * mm))
        self.story.append(AccentLineFull())
        self.story.append(Spacer(1, 20 * mm))

        # Publisher
        pub_style = ParagraphStyle(
            "cover_pub", fontName=GOTHIC, fontSize=10,
            textColor=SUB_COLOR, alignment=TA_CENTER,
        )
        self.story.append(Paragraph(
            "一般社団法人 国際美容創造協会（IBCA）", pub_style
        ))

        self.story.append(PageBreak())

    # ----- TOC -----
    def build_toc(self, elements):
        self.story.append(Spacer(1, 20 * mm))

        toc_title = ParagraphStyle(
            "toc_title", fontName=MINCHO, fontSize=20,
            textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=20,
        )
        self.story.append(Paragraph("目 次", toc_title))
        self.story.append(Spacer(1, 8 * mm))

        for elem in elements:
            if elem[0] == "chapter":
                _, label, title, subtitle = elem
                if label:
                    display = f"{label}　{title}"
                else:
                    display = title
                self.story.append(Paragraph(display, self.toc_chapter_style))
            elif elem[0] == "section":
                self.story.append(Paragraph(f"― {elem[1]}", self.toc_section_style))

        self.story.append(PageBreak())

    # ----- Content -----
    def build_content(self, elements):
        is_first_chapter = True
        for elem in elements:
            etype = elem[0]

            if etype == "chapter":
                _, label, title, subtitle = elem
                # TOC already ends with PageBreak, skip for first chapter
                if not is_first_chapter:
                    self.story.append(PageBreak())
                is_first_chapter = False
                self.story.append(Spacer(1, 30 * mm))
                self.story.append(ChapterTitle(label, title, subtitle))
                self.story.append(Spacer(1, 15 * mm))

            elif etype == "section":
                self.story.append(Spacer(1, 8 * mm))
                self.story.append(AccentBar(elem[1]))
                self.story.append(Spacer(1, 4 * mm))

            elif etype == "grade3":
                self.story.append(Spacer(1, 3 * mm))
                self.story.append(GradeBox(elem[1]))
                self.story.append(Spacer(1, 2 * mm))

            elif etype == "body":
                self.story.append(Paragraph(elem[1], self.body_style))

    # ----- Generate -----
    def generate(self):
        if not os.path.exists(CONTENT_MD):
            print(f"Error: {CONTENT_MD} not found.")
            sys.exit(1)

        print("Parsing markdown...")
        elements = parse_markdown(CONTENT_MD)

        n_chapters = sum(1 for e in elements if e[0] == "chapter")
        n_sections = sum(1 for e in elements if e[0] == "section")
        n_grade3 = sum(1 for e in elements if e[0] == "grade3")
        n_body = sum(1 for e in elements if e[0] == "body")
        print(f"  Chapters: {n_chapters}")
        print(f"  Sections: {n_sections}")
        print(f"  Grade-3 boxes: {n_grade3}")
        print(f"  Body paragraphs: {n_body}")

        print("Building PDF...")
        self.build_cover()
        self.build_toc(elements)
        self.build_content(elements)

        doc = SimpleDocTemplate(
            OUTPUT_PDF,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
            title="ダーマトロジー スキンケア検定 公式テキスト",
            author="一般社団法人国際美容創造協会（IBCA）",
        )

        current_page = [0]

        def on_page(canvas, doc):
            current_page[0] = doc.page
            # Skip page number on cover (page 1) and TOC (page 2)
            if doc.page <= 2:
                return
            canvas.saveState()
            canvas.setFont(GOTHIC, 8)
            canvas.setFillColor(SUB_COLOR)
            canvas.drawCentredString(PAGE_W / 2, 15 * mm, str(doc.page - 2))
            canvas.restoreState()

        doc.build(self.story, onFirstPage=on_page, onLaterPages=on_page)
        print(f"\nPDF generated successfully!")
        print(f"  Output: {OUTPUT_PDF}")
        print(f"  Total pages: {current_page[0]}")


# ========================================================
# Main
# ========================================================

if __name__ == "__main__":
    builder = TextbookBuilder()
    builder.generate()
