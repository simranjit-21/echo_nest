# app/utils.py
import pathlib

# --------------------------------------------------------------
# Colour palette (editable in one place)
# --------------------------------------------------------------
PALETTE = {
    # Primary (soft pastel peach) - background of navbar, buttons etc.
    "primary": "#FFB7A5",

    # Accent - used for AI-forecast card and any "highlight"
    "accent": "#7EDFC0",        # mint (cool, calming)

    # Mood-based background tones (feel free to use elsewhere)
    "calm":    "#A8D5BA",       # calm & relax
    "energy":  "#F8C784",       # energy & motivation
    "happy":   "#FFF9A6",       # happiness
    "focus":   "#D4B4E2",       # focus
    "peace":   "#C9E4FF",       # peace
    "sad":     "#8FA6BF",       # cool grey-blue
    "angry":   "#E98282",       # activated red
    "gloomy":  "#6B7280",       # dark muted tone

    # General backgrounds / text
    "bg_light": "#FDF7F1",      # very light, near-white
    "bg_dark":  "#15202B",      # optional dark card background
    "text_dark":"#212529",
    "text_light":"#E5E7EB",
    "ink_soft": "#5F5A56",
    "line_soft": "#E7DDD5",
}

def write_css(
    output_path: pathlib.Path = pathlib.Path(__file__).parent / "static" / "css" / "main.css",
) -> None:
    """Write `static/css/main.css` with custom properties from PALETTE."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "/* Auto-generated colour palette - edit PALETTE in utils.py */",
        ":root {"
    ]
    for name, value in PALETTE.items():
        lines.append(f"  --{name}: {value};")
    lines.append("}")

    # Small helper classes (Bootstrap-like)
    lines.extend([
        "",
        ".bg-primary { background-color: var(--primary) !important; }",
        ".text-primary { color: var(--primary) !important; }",
        ".bg-accent { background-color: var(--accent) !important; }",
        ".text-accent { color: var(--accent) !important; }",
        ".border-accent { border-color: var(--accent) !important; }",
        "",
        ".card {",
        "  background: var(--bg_light);",
        "  border: 1px solid #e2e8f0;",
        "  border-radius: .5rem;",
        "  padding: 1rem;",
        "}",
        ".card-accent { border-left: .4rem solid var(--accent); }",
        ".surface-card { box-shadow: 0 18px 45px rgba(21, 32, 43, 0.08); }",
        "",
        "body {",
        "  background:",
        "    radial-gradient(circle at top left, rgba(255, 183, 165, 0.18), transparent 32%),",
        "    radial-gradient(circle at top right, rgba(126, 223, 192, 0.18), transparent 28%),",
        "    linear-gradient(180deg, #fffaf6 0%, var(--bg_light) 100%);",
        "  color: var(--text_dark);",
        "  font-family: 'Segoe UI', 'Trebuchet MS', Arial, sans-serif;",
        "  min-height: 100vh;",
        "}",
        ".navbar { backdrop-filter: blur(16px); }",
        ".dashboard-hero {",
        "  display: flex;",
        "  justify-content: space-between;",
        "  gap: 1.5rem;",
        "  align-items: end;",
        "  padding: 2rem;",
        "  border-radius: 1.25rem;",
        "  background: linear-gradient(135deg, rgba(255, 183, 165, 0.92), rgba(126, 223, 192, 0.82));",
        "  box-shadow: 0 24px 60px rgba(21, 32, 43, 0.12);",
        "}",
        ".dashboard-title {",
        "  font-size: clamp(2rem, 3vw, 3.2rem);",
        "  line-height: 1.05;",
        "  max-width: 12ch;",
        "}",
        ".dashboard-copy, .muted-copy { color: var(--ink_soft); max-width: 62ch; }",
        ".hero-cta { white-space: nowrap; border-radius: 999px; padding: 0.9rem 1.3rem; }",
        ".eyebrow { text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.75rem; color: rgba(21, 32, 43, 0.62); }",
        ".metric-card {",
        "  background: rgba(255, 255, 255, 0.72);",
        "  border: 1px solid var(--line_soft);",
        "  border-radius: 1rem;",
        "  padding: 1rem 1.1rem;",
        "  display: flex;",
        "  flex-direction: column;",
        "  gap: 0.25rem;",
        "  min-height: 100%;",
        "}",
        ".metric-label, .metric-note { color: var(--ink_soft); }",
        ".metric-value { font-size: 1.85rem; line-height: 1; }",
        ".metric-state { display: inline-flex; padding: 0.35rem 0.75rem; border-radius: 999px; align-self: start; }",
        ".metric-state-calm { background: rgba(121, 199, 197, 0.18); color: #2b6f74; }",
        ".metric-state-energy { background: rgba(243, 155, 61, 0.18); color: #a65d0f; }",
        ".metric-state-happy { background: rgba(243, 211, 74, 0.2); color: #8a6d04; }",
        ".metric-state-focus { background: rgba(165, 122, 217, 0.18); color: #6235a4; }",
        ".metric-state-peace { background: rgba(243, 183, 204, 0.25); color: #a14a72; }",
        ".metric-state-sad { background: rgba(143, 166, 191, 0.2); color: #4d6077; }",
        ".metric-state-angry { background: rgba(233, 130, 130, 0.2); color: #9b2e2e; }",
        ".metric-state-gloomy { background: rgba(107, 114, 128, 0.22); color: #2f3642; }",
        ".section-head { display: flex; justify-content: space-between; gap: 1rem; align-items: start; margin-bottom: 1rem; }",
        ".pill { border-radius: 999px; background: rgba(126, 223, 192, 0.22); padding: 0.4rem 0.8rem; color: var(--text_dark); font-size: 0.9rem; }",
        ".chart-shell { min-height: 280px; }",
        ".state-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.9rem; }",
        ".state-card { border-radius: 1rem; padding: 1rem; border: 1px solid rgba(21, 32, 43, 0.08); }",
        ".state-card-calm { background: rgba(121, 199, 197, 0.14); }",
        ".state-card-energy { background: rgba(243, 155, 61, 0.14); }",
        ".state-card-happy { background: rgba(243, 211, 74, 0.16); }",
        ".state-card-focus { background: rgba(165, 122, 217, 0.14); }",
        ".state-card-peace { background: rgba(243, 183, 204, 0.18); }",
        ".state-card-sad { background: rgba(143, 166, 191, 0.18); }",
        ".state-card-angry { background: rgba(233, 130, 130, 0.18); }",
        ".state-card-gloomy { background: rgba(107, 114, 128, 0.2); color: #f4f5f7; }",
        ".state-card-gloomy .state-card-title, .state-card-gloomy .state-card-copy { color: rgba(244, 245, 247, 0.78); }",
        ".state-card-title { display: block; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink_soft); }",
        ".state-card-count { display: block; font-size: 2rem; line-height: 1; margin: 0.45rem 0; }",
        ".state-card-copy { color: var(--ink_soft); font-size: 0.92rem; }",
        ".metric-stack { display: grid; gap: 0.9rem; }",
        ".mini-metric { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line_soft); padding-bottom: 0.8rem; }",
        ".suggestion-stack { display: grid; gap: 0.75rem; }",
        ".suggestion-card { border-radius: 1rem; background: rgba(255,255,255,0.78); border: 1px solid var(--line_soft); padding: 0.9rem 1rem; color: var(--ink_soft); }",
        ".companion-response { border-radius: 1.1rem; border: 1px solid rgba(126, 223, 192, 0.35); background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(126, 223, 192, 0.12)); padding: 1rem 1.1rem; color: var(--text_dark); line-height: 1.7; }",
        ".companion-meta { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: end; align-items: center; }",
        ".companion-chat-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.9rem; align-items: end; }",
        ".companion-flags { display: flex; flex-wrap: wrap; gap: 0.6rem; }",
        ".support-card { border-radius: 1rem; border: 1px solid var(--line_soft); background: rgba(255,255,255,0.72); padding: 1rem; min-height: 100%; }",
        ".music-stack { display: grid; gap: 0.85rem; }",
        ".music-card { display: flex; justify-content: space-between; gap: 1rem; align-items: center; border-radius: 1rem; border: 1px solid var(--line_soft); background: rgba(255,255,255,0.74); padding: 1rem; }",
        ".music-links { display: flex; flex-wrap: wrap; gap: 0.5rem; }",
        ".mini-panel { height: 100%; border-radius: 1rem; border: 1px solid var(--line_soft); background: rgba(255,255,255,0.72); padding: 1rem; display: grid; gap: 0.75rem; align-content: start; }",
        ".goal-progress { width: 100%; height: 12px; border-radius: 999px; background: rgba(21, 32, 43, 0.08); overflow: hidden; }",
        ".goal-progress-bar { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--primary)); transition: width 180ms ease; }",
        ".badge-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }",
        ".badge-card { border-radius: 1rem; border: 1px dashed rgba(95, 90, 86, 0.32); background: rgba(255,255,255,0.62); padding: 0.95rem; color: var(--ink_soft); }",
        ".badge-card.is-earned { border-style: solid; border-color: rgba(126, 223, 192, 0.45); background: linear-gradient(135deg, rgba(126, 223, 192, 0.14), rgba(255,255,255,0.88)); color: var(--text_dark); }",
        ".activity-list { display: flex; flex-wrap: wrap; gap: 0.75rem; }",
        ".activity-chip {",
        "  display: inline-flex;",
        "  align-items: center;",
        "  justify-content: space-between;",
        "  gap: 0.75rem;",
        "  min-width: 145px;",
        "  border-radius: 999px;",
        "  border: 1px solid var(--line_soft);",
        "  padding: 0.55rem 0.9rem;",
        "  background: rgba(255, 255, 255, 0.75);",
        "}",
        ".state-legend { display: flex; flex-wrap: wrap; gap: 0.6rem; }",
        ".state-pill { display: inline-flex; align-items: center; border-radius: 999px; padding: 0.45rem 0.8rem; font-size: 0.9rem; }",
        ".state-pill-calm { background: rgba(121, 199, 197, 0.16); color: #2b6f74; }",
        ".state-pill-energy { background: rgba(243, 155, 61, 0.16); color: #a65d0f; }",
        ".state-pill-happy { background: rgba(243, 211, 74, 0.2); color: #8a6d04; }",
        ".state-pill-focus { background: rgba(165, 122, 217, 0.17); color: #6235a4; }",
        ".state-pill-peace { background: rgba(243, 183, 204, 0.23); color: #a14a72; }",
        ".state-pill-sad { background: rgba(143, 166, 191, 0.2); color: #4d6077; }",
        ".state-pill-angry { background: rgba(233, 130, 130, 0.2); color: #9b2e2e; }",
        ".state-pill-gloomy { background: rgba(107, 114, 128, 0.2); color: #2f3642; }",
        ".activity-console { overflow: hidden; }",
        ".micro-activity-card { border-radius: 1.15rem; padding: 1.25rem; color: var(--text_dark); }",
        ".micro-activity-calm { background: linear-gradient(135deg, rgba(121, 199, 197, 0.2), rgba(168, 213, 186, 0.32)); }",
        ".micro-activity-energy { background: linear-gradient(135deg, rgba(243, 155, 61, 0.2), rgba(248, 199, 132, 0.3)); }",
        ".micro-activity-happy { background: linear-gradient(135deg, rgba(243, 211, 74, 0.2), rgba(255, 249, 166, 0.34)); }",
        ".micro-activity-focus { background: linear-gradient(135deg, rgba(165, 122, 217, 0.18), rgba(212, 180, 226, 0.32)); }",
        ".micro-activity-peace { background: linear-gradient(135deg, rgba(243, 183, 204, 0.22), rgba(201, 228, 255, 0.32)); }",
        ".micro-activity-sad { background: linear-gradient(135deg, rgba(143, 166, 191, 0.24), rgba(201, 228, 255, 0.28)); }",
        ".micro-activity-angry { background: linear-gradient(135deg, rgba(233, 130, 130, 0.24), rgba(248, 199, 132, 0.24)); }",
        ".micro-activity-gloomy { background: linear-gradient(135deg, rgba(77, 85, 99, 0.9), rgba(107, 114, 128, 0.85)); color: var(--text_light); }",
        ".micro-activity-title { font-size: 1.6rem; line-height: 1.1; margin-bottom: 0.75rem; }",
        ".micro-activity-button { border-radius: 999px; padding-inline: 1rem; }",
        ".micro-activity-timer { font-size: 1.8rem; line-height: 1; }",
        ".micro-steps { display: grid; gap: 0.75rem; }",
        ".micro-step { border-radius: 0.95rem; border: 1px solid var(--line_soft); padding: 0.9rem 1rem; background: rgba(255,255,255,0.68); color: var(--ink_soft); transition: transform 160ms ease, background 160ms ease, border-color 160ms ease; }",
        ".micro-step.is-active { transform: translateX(4px); border-color: var(--primary); background: rgba(255, 183, 165, 0.16); color: var(--text_dark); }",
        ".micro-step.is-complete { border-color: var(--accent); background: rgba(126, 223, 192, 0.16); color: var(--text_dark); }",
        "@media (max-width: 767px) {",
        "  .dashboard-hero { align-items: start; flex-direction: column; }",
        "  .hero-cta { width: 100%; text-align: center; }",
        "  .companion-chat-row { grid-template-columns: 1fr; }",
        "  .companion-meta { justify-content: start; }",
        "  .music-card { align-items: start; flex-direction: column; }",
        "}",
    ])

    css_text = "\n".join(lines)
    if output_path.exists() and output_path.read_text(encoding="utf-8") == css_text:
        return

    output_path.write_text(css_text, encoding="utf-8")
