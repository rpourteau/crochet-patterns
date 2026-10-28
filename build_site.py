#!/usr/bin/env python3
"""Build a phone-friendly website from the Org patterns.

Every .org file in a category directory becomes an HTML page where each
"- [ ]" round is a tappable checkbox and each "Rounds X – Y" repeat gets a
-/+ counter. Progress is saved in the browser (localStorage), per pattern.

Usage: python3 build_site.py [output_dir]   (default: _site)
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

HEADING = re.compile(r"^(\*+)\s+(.*)$")
ITEM = re.compile(r"^\s*[-+]\s+(?:\[([ xX-])\]\s+)?(.*)$")
REPEAT = re.compile(r"\bRounds?\s+(\d+)\s*[–—-]\s*(\d+)")


def inline(text):
    """Org inline markup -> HTML (bold, italic, stitch counts)."""
    t = html.escape(text, quote=False)
    t = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w/:])/(?=\S)(.+?)(?<=\S)/(?![\w/])", r"<em>\1</em>", t)
    t = re.sub(r"\[(\d+ sts?)\]", r'<span class="count">[\1]</span>', t)
    return t


def short_hash(*parts):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def parse(path):
    """Return (title, blocks); blocks are ('h', level, text), ('item', text, is_checkbox) or ('p', text)."""
    title = path.stem.replace("_", " ").title()
    blocks = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if m := re.match(r"#\+TITLE:\s*(.*)", line, re.I):
            title = m[1]
        elif line.startswith("#") or not line.strip():
            if not line.strip() and blocks and blocks[-1][0] == "p":
                blocks.append(("break",))
        elif m := HEADING.match(line):
            blocks.append(("h", len(m[1]), m[2]))
        elif m := ITEM.match(line):
            blocks.append(("item", m[2], m[1] is not None))
        elif line[0].isspace() and blocks and blocks[-1][0] == "item":
            kind, text, box = blocks[-1]
            blocks[-1] = (kind, f"{text} {line.strip()}", box)
        elif blocks and blocks[-1][0] == "p":
            blocks[-1] = ("p", f"{blocks[-1][1]} {line.strip()}")
        else:
            blocks.append(("p", line.strip()))
    return title, [b for b in blocks if b[0] != "break"]


def render_step(text, step_id):
    m = REPEAT.search(text)
    total = int(m[2]) - int(m[1]) + 1 if m and int(m[2]) > int(m[1]) else 1
    label = f'<label><input type="checkbox"><span>{inline(text)}</span></label>'
    if total == 1:
        return f'<li class="step" data-id="{step_id}">{label}</li>'
    return (
        f'<li class="step counter" data-id="{step_id}" data-total="{total}">{label}'
        f'<div class="ctr"><button type="button" class="dec" aria-label="One less">−</button>'
        f"<output>0 / {total}</output>"
        f'<button type="button" class="inc" aria-label="One more">+</button></div></li>'
    )


def render_body(blocks):
    out, path, seen = [], [], set()
    in_section = in_list = False
    for block in blocks:
        kind = block[0]
        if kind != "item" and in_list:
            out.append("</ul>")
            in_list = False
        if kind == "h":
            _, level, text = block
            path = path[: level - 1] + [text]
            if level == 1:
                if in_section:
                    out.append("</details>")
                out.append(
                    f'<details open data-id="{short_hash(text)}"><summary>'
                    f'<span>{inline(text)}</span><span class="progress"></span></summary>'
                )
                in_section = True
            else:
                tag = f"h{min(level + 1, 6)}"
                out.append(f"<{tag}>{inline(text)}</{tag}>")
        elif kind == "item":
            _, text, is_checkbox = block
            if not in_list:
                out.append('<ul class="steps">')
                in_list = True
            if is_checkbox:
                step_id = short_hash(*path, text)
                while step_id in seen:
                    step_id = short_hash(step_id)
                seen.add(step_id)
                out.append(render_step(text, step_id))
            else:
                out.append(f"<li>{inline(text)}</li>")
        else:
            out.append(f"<p>{inline(block[1])}</p>")
    if in_list:
        out.append("</ul>")
    if in_section:
        out.append("</details>")
    return "\n".join(out)


CSS = """
:root {
  --bg: #fbf8f4; --surface: #ffffff; --text: #2b2622; --muted: #8a8079;
  --border: #e6ded6; --accent: #b4536b; --accent-soft: #f6e4e8; --done: #f1eeea;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1917; --surface: #262220; --text: #eee7e1; --muted: #9c928a;
    --border: #3a3431; --accent: #e08aa0; --accent-soft: #3d2a2f; --done: #211e1c;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 18px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 44rem; margin: 0 auto; padding: 1rem 1rem 4rem; }
a { color: var(--accent); }
h1 { font-size: 1.5rem; line-height: 1.25; margin: .5rem 0 1rem; }
h3 { font-size: 1.05rem; margin: 1.5rem 0 .5rem; color: var(--accent); }
.toolbar { display: flex; flex-wrap: wrap; gap: .5rem 1rem; align-items: center; font-size: .95rem; }
.toolbar a { margin-right: auto; }
.toolbar button {
  font: inherit; padding: .35rem .8rem; border-radius: .5rem;
  border: 1px solid var(--border); background: var(--surface); color: var(--text);
}
.toolbar label { display: flex; gap: .4rem; align-items: center; }
details { background: var(--surface); border: 1px solid var(--border); border-radius: .75rem; margin: 1rem 0; padding: 0 1rem; }
summary { display: flex; justify-content: space-between; gap: 1rem; padding: .9rem 0; font-weight: 600; cursor: pointer; }
.progress { color: var(--muted); font-weight: 400; white-space: nowrap; }
ul { padding-left: 1.2rem; }
ul.steps { list-style: none; padding: 0; margin: 0 0 1rem; }
ul.steps > li:not(.step) { margin: .5rem 0 .5rem 1.2rem; list-style: disc; }
.step { border-top: 1px solid var(--border); padding: .7rem 0; }
.step label { display: flex; gap: .8rem; align-items: flex-start; cursor: pointer; }
.step input { flex: none; width: 1.6rem; height: 1.6rem; margin: 0; accent-color: var(--accent); }
.step.done { background: var(--done); }
.step.done span { color: var(--muted); }
.count { font-weight: 600; white-space: nowrap; }
.ctr { display: flex; align-items: center; justify-content: flex-end; gap: 1rem; margin-top: .5rem; }
.ctr button {
  width: 3.2rem; height: 3.2rem; border-radius: 50%; font-size: 1.6rem; line-height: 1;
  border: 1px solid var(--border); background: var(--accent-soft); color: var(--text);
}
.ctr output { min-width: 4.5rem; text-align: center; font-size: 1.2rem; font-variant-numeric: tabular-nums; }
.index li { margin: .4rem 0; }
"""

JS = """
const KEY = 'crochet:' + PAGE;
const load = k => { try { return JSON.parse(localStorage.getItem(k)) || {}; } catch { return {}; } };
const store = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
let state = load(KEY);
const closed = load(KEY + ':closed');
const steps = [...document.querySelectorAll('.step')];
const total = li => +li.dataset.total || 1;

function render(li) {
  const n = Math.min(state[li.dataset.id] || 0, total(li));
  li.querySelector('input').checked = n >= total(li);
  li.classList.toggle('done', n >= total(li));
  const out = li.querySelector('output');
  if (out) out.textContent = n + ' / ' + total(li);
}
function progress() {
  document.querySelectorAll('details').forEach(d => {
    const all = d.querySelectorAll('.step').length;
    d.querySelector('.progress').textContent = all ? d.querySelectorAll('.step.done').length + ' / ' + all : '';
  });
}
function set(li, n) {
  n = Math.max(0, Math.min(total(li), n));
  if (n) state[li.dataset.id] = n; else delete state[li.dataset.id];
  store(KEY, state); render(li); progress();
}
steps.forEach(li => {
  render(li);
  li.querySelector('input').addEventListener('change', e => set(li, e.target.checked ? total(li) : 0));
  li.querySelector('.inc')?.addEventListener('click', () => set(li, (state[li.dataset.id] || 0) + 1));
  li.querySelector('.dec')?.addEventListener('click', () => set(li, (state[li.dataset.id] || 0) - 1));
});
progress();

document.querySelectorAll('details').forEach(d => {
  if (closed[d.dataset.id]) d.open = false;
  d.addEventListener('toggle', () => {
    if (d.open) delete closed[d.dataset.id]; else closed[d.dataset.id] = 1;
    store(KEY + ':closed', closed);
  });
});

document.getElementById('reset').addEventListener('click', () => {
  if (!confirm('Untick every step of this pattern?')) return;
  state = {}; store(KEY, state); steps.forEach(render); progress();
});

const wake = document.getElementById('wake');
let lock = null;
async function acquire() {
  try { lock = await navigator.wakeLock.request('screen'); } catch { wake.checked = false; }
}
if (!('wakeLock' in navigator)) wake.parentElement.hidden = true;
wake.addEventListener('change', () => { if (wake.checked) acquire(); else { lock?.release(); lock = null; } });
document.addEventListener('visibilitychange', () => {
  if (wake.checked && document.visibilityState === 'visible') acquire();
});
"""


def page(title, body, script=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
{body}
</main>
{f"<script>{script}</script>" if script else ""}
</body>
</html>
"""


def build(out_dir):
    patterns = {}
    for org in sorted(ROOT.glob("*/*.org")):
        category = org.parent.name
        if category.startswith((".", "_")):
            continue
        rel = org.relative_to(ROOT).with_suffix("")
        title, blocks = parse(org)
        toolbar = (
            '<div class="toolbar"><a href="../index.html">← All patterns</a>'
            '<label><input type="checkbox" id="wake"> Keep screen on</label>'
            '<button type="button" id="reset">Reset</button></div>'
        )
        body = f"{toolbar}\n<h1>{inline(title)}</h1>\n{render_body(blocks)}"
        script = f"const PAGE = {json.dumps(rel.as_posix())};\n{JS}"
        target = out_dir / rel.with_suffix(".html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(title, body, script), encoding="utf-8")
        patterns.setdefault(category, []).append((title, rel.with_suffix(".html").as_posix()))

    sections = []
    for category, entries in patterns.items():
        links = "".join(f'<li><a href="{href}">{inline(title)}</a></li>' for title, href in entries)
        sections.append(f"<h3>{html.escape(category.capitalize())}</h3><ul>{links}</ul>")
    body = '<h1>Crochet patterns</h1>\n<div class="index">' + "\n".join(sections) + "</div>"
    (out_dir / "index.html").write_text(page("Crochet patterns", body), encoding="utf-8")
    count = sum(len(e) for e in patterns.values())
    print(f"Built {count} pattern page(s) into {out_dir}")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_site").resolve())
