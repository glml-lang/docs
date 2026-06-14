#!/usr/bin/env python3

# mdBook preprocessor to turn inline GLML in `glml,live` fenced block
# into live shader examples with emitted GLSL source code

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from markdown_it import MarkdownIt

GLML_BIN = "glml"
MARKDOWN_IT = MarkdownIt()


# `Compiled(true, glsl)` or `Compiled(false, err_msg)`
class Compiled(NamedTuple):
    ok: bool
    output: str


# Runs `glml build` on string
def compile_glml(src: str) -> Compiled:
    with tempfile.NamedTemporaryFile("w", suffix=".glml", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        proc = subprocess.run([GLML_BIN, "build", path], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(f"glml_preprocess: `{GLML_BIN}` not found")
    finally:
        Path(path).unlink(missing_ok=True)
    return Compiled(
        proc.returncode == 0, proc.stdout if proc.returncode == 0 else proc.stderr
    )


# Markdown for GLML soruce, `canvas` read by `glml-runner`, collapsable GLSL
def live_block(block_id: str, src: str, glsl: str) -> str:
    return f"""
```glml
{src}
```

<canvas class="glml-canvas" data-glml-src="{block_id}"></canvas>
<script type="text/x-glsl" id="{block_id}">
{glsl}
</script>

<details><summary>Compiled GLSL</summary>

```glsl
{glsl}
```

</details>"""


# Markdown for snippet that failed to compile
def error_block(src: str, diagnostic: str) -> str:
    quoted = "\n".join("> " + line for line in diagnostic.splitlines())
    return f"```glml\n{src}\n```\n\n> **GLML compile error:**\n{quoted}\n"


# Compile snippet and format as live or error block
def render_fence(src: str, block_id: str) -> str:
    result = compile_glml(src)
    if result.ok:
        return live_block(block_id, src, result.output)
    return error_block(src, result.output)


# Use `render_frame` in every `glml,live` fence
def transform_content(slug: str, content: str) -> str:
    lines = content.split("\n")
    edits = []
    block_n = 0
    for token in MARKDOWN_IT.parse(content):
        if token.type != "fence" or token.info.strip() != "glml,live":
            continue
        src = token.content.rstrip()
        rendered = render_fence(src, f"glml-shader-{slug}-{block_n}")
        start, end = token.map
        edits.append((start, end, rendered.splitlines()))
        block_n += 1
    for start, end, replacement in reversed(edits):
        lines[start:end] = replacement
    return "\n".join(lines)


# Transforms chapter path to safe HTML id
def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text)


# Transform items (chapters only)
def transform_item(item):
    if not isinstance(item, dict) or "Chapter" not in item:
        return item
    chapter = dict(item["Chapter"])
    # `path` is None for drafts
    slug = slugify(chapter.get("path") or "chapter")
    chapter["content"] = transform_content(slug, chapter["content"])
    chapter["sub_items"] = [transform_item(sub) for sub in chapter["sub_items"]]
    return {"Chapter": chapter}


def transform_book(book):
    book["items"] = [transform_item(item) for item in book["items"]]
    return book


# `mdbook` is called with `mdbook supports html` and `mdbook` with piped book
def main():
    if sys.argv[1:2] == ["supports"]:
        return
    _, book = json.load(sys.stdin)
    json.dump(transform_book(book), sys.stdout)


if __name__ == "__main__":
    main()
