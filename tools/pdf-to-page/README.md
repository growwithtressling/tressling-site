# PDF to web page

Builds the article and case study web pages (`site/<slug>.html`) and their images (`site/assets/articles/`) from the PDFs in `site/downloads/`.

    pip install pymupdf pillow
    cd tools/pdf-to-page && python3 render.py

Page settings (title, stage, description, exhibit tables and image descriptions) live in the `ARTICLES` table in `render.py`. Add an entry there for each new PDF. This folder is not copied to the live site.
