# Project website

Static, author-free project page built from the supplied manuscript. Paper-reported results are independent from the small Qwen software validation documented in `../guides/validation.md`.

Enable GitHub Pages from branch `main`, folder `/docs`. The site uses relative asset paths and includes `.nojekyll`; no build process or external service credentials are needed.

For local preview:

```bash
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. The repository homepage links to `https://pm1255.github.io/embodied-corrector/`.
