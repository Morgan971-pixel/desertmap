# DesertMap model card

A 2-page PDF model card (`desertmap_model_card.pdf`, also published as `site/model-card.pdf`) in the Mitchell et al. (2019) format. Every number in it comes from `site/data/summary.json` through the generated `numbers.tex`.

Rebuild from the repo root (needs `brew install tectonic`): `uv run python docs/model_card/make_assets.py && tectonic docs/model_card/model_card.tex`, then copy `docs/model_card/model_card.pdf` to `docs/model_card/desertmap_model_card.pdf` and `site/model-card.pdf`.
