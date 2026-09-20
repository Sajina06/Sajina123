# Disease Risk Prediction System

Flask multi-disease health risk prediction project.

## UI behavior

- Public pages use a top navigation bar.
- Before login, the navigation stays at the top.
- After login, user/admin pages use a fixed left sidebar.
- Logged-in pages start in dark mode.
- Dark/light mode can be toggled and is remembered in the browser.
- Mobile screens use a collapsible sidebar.

## Run on Windows

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
flask --app app init-db
flask --app app run --debug
```

Open: http://127.0.0.1:5000

Admin:
- Email: admin@diseaserisk.local
- Password: Admin@123

Change the admin password before deployment.

The current prediction function is a demo placeholder. It is NOT a clinical diagnosis and should be replaced by five trained disease-specific ML pipelines.
