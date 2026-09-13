# Google Maps scraper backend feature

Source kit: https://github.com/Mahanaicoach/google-maps-scraper-kit
Upstream engine: https://github.com/gosom/google-maps-scraper
Container version: `gosom/google-maps-scraper:v1.15.0`

Majlesyar exposes staff-authenticated endpoints and keeps the upstream container private:

- `GET /api/v1/maps-scraper/health/`
- `GET|POST /api/v1/maps-scraper/jobs/`
- `GET|DELETE /api/v1/maps-scraper/jobs/{id}/`
- `POST /api/v1/maps-scraper/jobs/{id}/refresh/`
- `GET /api/v1/maps-scraper/jobs/{id}/results/`
- `GET /api/v1/maps-scraper/jobs/{id}/results/?format=csv`
- `GET /api/v1/maps-scraper/jobs/{id}/results/?full=1`

Start locally with `docker compose up --build`. The scraper binds to `127.0.0.1:8081` (avoids Majlesyar
Vite's port `8080`); never expose it
publicly without an authentication proxy. Scraping Google Maps may violate Google's terms and can trigger
temporary IP rate limits. Use modest depth, one job at a time, and comply with privacy/anti-spam law.

## License

Integration and source kit use MIT license. Copyright (c) 2026 Mahan
(github.com/mahanjafari-dev). Engine uses MIT license, Copyright (c) 2023 Georgios Komninos.
Full notices: source kit `LICENSE` and `CREDITS.md`.
