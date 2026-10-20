# site/: the Session Kit overview page

One static page that shows a newcomer, in under a minute, what Session Kit
is: the six packages, the one install line, and one concrete moment (mail
wakes an idle agent).

The page is not hosted anywhere: no server serves it and no domain points
at it. It says so in a banner at the top. You read it by opening the file.

## Preview it

Open the file. No server and no build step:

```bash
open site/index.html
```

To check that it makes no requests, open the browser's Network panel and
reload. The only entries are `index.html` and `style.css`, both `file://`.

From the repo root, these two lines print nothing:

```bash
grep -nE '(href|src)="(https?:)?//' site/*.html
grep -n '<scr[i]pt' site/*.html   # [i] keeps this file out of a grep of site/
```

`make check` runs `tests/test_site.py` with the rest of the suite.

## What is here

| file | what |
|---|---|
| `index.html` | the page: plain HTML, no script |
| `style.css` | the only stylesheet: system fonts, light and dark |
| `README.md` | this file |

The rules:

- **Plain HTML and CSS.** No build step, no framework, no JavaScript.
- **No third-party requests.** No CDN, no web fonts, no analytics, no
  badges, no images.
- **No absolute URLs.** Every link is relative.
- **Content Security Policy.** A `<meta>` sets `default-src 'none';
  style-src 'self'`, so the browser itself refuses anything else.
- **What is not available yet reads "coming".** It has no link, and the
  page marks it *coming* (`class="coming"`, so a grep finds each one).
  Places with no link of their own, such as the source code and PyPI, are
  named in plain text.

The docs links leave `site/` (`../README.md`, `../docs/...`). They resolve
in a checkout of this repo and in its release archive. On a host, these
links need the public repo's URLs.

A future part page goes at `site/<part>/index.html`. It links
`../style.css`, and `../` back to the overview.

## Does the CSP block the stylesheet under file://?

**No. It was measured on 2030-06-09, on macOS 27.0.**

- **Chrome 155** (`--headless=new --screenshot`, from `file://`): the page
  renders styled, and the sticky banner pixel matches the stylesheet's
  colour. A control copy with `style-src 'none'` renders unstyled (white).
  So the CSP is enforced, and `'self'` admits the sibling `style.css`.
- **WebKit, Safari's engine** (Safari 27.0 is installed): measured with a
  `WKWebView` loading the page via `loadFileURL`, reading computed style
  from the host. The banner computes `position: sticky` with the
  stylesheet's background, and `document.styleSheets.length` is 1. The
  `style-src 'none'` control gives `static`, a transparent background and
  0 sheets. This is the engine, not the Safari app. Driving Safari.app
  itself needs its remote-automation setting, and that was not changed.

So the CSP `<meta>` stays, and the fallback (drop the meta, and rely on the
grep and the test) is not needed.

Also measured in WebKit: at 320 px and 375 px wide, the page's scroll width
equals the viewport, and nothing outside a code block overflows.
