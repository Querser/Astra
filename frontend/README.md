# ASTRA web interface

The local React/Vite interface opens with an ASTRA telemetry dashboard. Its crew list, body diagram, readings, charts and event feed use the selected profile's saved observations, complaints and latest local analysis. Areas with no supporting records display "No data". The dashboard contains no invented communication link, mission day counter, checkup schedule or live sensor readings.

Use **Input and Analysis** or the actions in the left column for profile and mission editing, manual measurements, free-text complaints, the full analysis, the local explanation and forecasts. These functions continue to use the local API. The dashboard is an overview, not a separate data store.

The layout adapts to narrow screens. On desktop, each side column scrolls independently. All assets and styling are bundled locally; the UI does not need a remote font, image or CSS service.

The central figure uses a local anatomical atlas image created with generative artificial intelligence, using the user-supplied anatomy image `cbf7ca45fc41de9f8bc0f5e7fa10214c.jpg` as a composition and proportion reference. Accessible SVG hotspots, organ colors, status dots, selection and report details are rendered from the current profile's analysis.

## Windows setup

Run from this directory:

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Stop the development server with `Ctrl+C`.

Create a production build:

```powershell
npm run build
```
