# Deploying to Streamlit Community Cloud

Free, no credit card, and you get a public URL anyone can open.

## 1. Build the data bundle (once, locally)

```bash
pip install -r requirements.txt
python pipeline.py --input data/complaints-2026-09-06_16_45.csv
python prepare_app_data.py
```

That writes `app_data/` — six files, about 450 KB. **Commit this folder.**
It is the only data the app reads; the 76 MB source CSV stays out of the repo.

Run it locally to check:

```bash
streamlit run app.py
```

## 2. Push

```bash
git add app.py prepare_app_data.py app_data .streamlit requirements.txt DEPLOY.md
git commit -m "Add Streamlit companion app"
git push
```

## 3. Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. **New app** → pick `complaint-operations-console`, branch `main`, main file `app.py`
3. Deploy

Two to three minutes, then you have a permanent URL:
`https://<something>.streamlit.app`

Set the subdomain in the deploy dialog — `complaint-operations` reads better
than the default hash.

## 4. Link it

Add the URL to three places:

- `README.md` — a **Live app** link at the top beside the case study link
- The project card in `index.html`
- `complaint-operations.html` — the case study page, as a live companion

## Notes

**Apps sleep after inactivity** on the free tier and take ~30 seconds to wake.
Fine for a portfolio; open it a few minutes before an interview.

**`app_data/` must be committed** or the app will start and immediately error.
It is deliberately small so this is safe.

**Rebuilding on new data:** re-run both scripts and commit the new `app_data/`.
Streamlit redeploys on push. Remember that CFPB revises records retroactively,
so the counts will move — update the figures in the README if they do.
